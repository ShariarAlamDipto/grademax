#!/usr/bin/env python3
"""
GradeMax — Human Biology Classifier
=====================================
Classifies Human Biology (4HB1) question pages using keyword matching
against the 12-chapter spec (config/human_biology_topics.yaml).

Falls back to Groq (llama-3.1-8b-instant) for low-confidence matches.

Prerequisites:
  - ingest_human_biology_from_processed.py must have run first
  - config/human_biology_topics.yaml must exist
  - GROQ_API_KEY set in .env.local

Usage:
  python scripts/classify_human_biology.py
  python scripts/classify_human_biology.py --dry-run
  python scripts/classify_human_biology.py --resume
  python scripts/classify_human_biology.py --use-llm
"""

import os
import sys
import json
import time
import argparse
import re
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

try:
    from supabase import create_client, Client
except ImportError:
    print("[ERR]  Install supabase:  pip install supabase")
    sys.exit(1)

env_path = Path(__file__).parent.parent / ".env.local"
load_dotenv(env_path)

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SERVICE_KEY  = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
GROQ_KEY     = os.getenv("GROQ_API_KEY")

SUBJECT_CODE = "4HB1"
CONFIG_PATH  = Path(__file__).parent.parent / "config" / "human_biology_topics.yaml"


# =============================================================================
# KEYWORD CLASSIFIER
# =============================================================================

class KeywordClassifier:
    def __init__(self, config: dict):
        self.topics    = {t["id"]: t for t in config["topics"]}
        self.negatives = [n.lower() for n in config.get("negatives", [])]
        self._build_index(config)

    def _build_index(self, config: dict):
        self.keyword_index: dict[str, list[tuple[str, float]]] = {}
        for topic in config["topics"]:
            tid = topic["id"]
            for kw in topic.get("keywords", []):
                self.keyword_index.setdefault(kw.lower(), []).append((tid, 3.0))
            for f in topic.get("formulas", []):
                self.keyword_index.setdefault(f.lower(), []).append((tid, 5.0))
            for s in topic.get("synonyms", []):
                self.keyword_index.setdefault(s.lower(), []).append((tid, 2.0))
            for word in topic.get("description", "").lower().split():
                word = re.sub(r"[^a-z0-9]", "", word)
                if len(word) > 4:
                    self.keyword_index.setdefault(word, []).append((tid, 0.5))

    def classify(self, text: str) -> tuple[Optional[str], float]:
        text_lower = text.lower()
        scores: dict[str, float] = {}
        sorted_kws = sorted(self.keyword_index.keys(), key=len, reverse=True)
        matched_spans: list[tuple[int, int]] = []

        for kw in sorted_kws:
            pos = text_lower.find(kw)
            if pos == -1:
                continue
            span = (pos, pos + len(kw))
            overlaps = any(s[0] <= span[1] and span[0] <= s[1] for s in matched_spans)
            if not overlaps or len(kw) >= 8:
                matched_spans.append(span)
            for tid, w in self.keyword_index[kw]:
                scores[tid] = scores.get(tid, 0.0) + w

        if not scores:
            return None, 0.0

        best_tid   = max(scores, key=lambda t: scores[t])
        best_score = scores[best_tid]
        total      = sum(scores.values())
        confidence = min(best_score / (total + 1e-9), 1.0)

        scores_sorted = sorted(scores.values(), reverse=True)
        if len(scores_sorted) > 1:
            margin = (scores_sorted[0] - scores_sorted[1]) / (scores_sorted[0] + 1e-9)
            confidence = min(confidence + margin * 0.3, 1.0)

        return best_tid, round(confidence, 3)


# =============================================================================
# GROQ LLM FALLBACK
# =============================================================================

def classify_with_groq(text: str, topics: dict, api_key: str) -> tuple[Optional[str], float]:
    import requests
    topic_list = "\n".join(
        f"  {tid}: {t['name']} — {t['description']}"
        for tid, t in topics.items()
    )
    prompt = (
        "You are an Edexcel IGCSE Human Biology examiner. "
        "Classify this exam question into ONE topic from the list below.\n\n"
        f"TOPICS:\n{topic_list}\n\n"
        f"QUESTION:\n{text[:600]}\n\n"
        'Return ONLY valid JSON: {"topic": "<topic_id>", "confidence": 0.0-1.0}'
    )
    for attempt in range(4):
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 100,
                },
                timeout=20,
            )
            if resp.status_code == 429:
                time.sleep(2 ** attempt * 2)
                continue
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
            data = json.loads(raw)
            return str(data["topic"]), float(data.get("confidence", 0.7))
        except Exception:
            time.sleep(2 ** attempt)
    return None, 0.0


# =============================================================================
# DIFFICULTY ESTIMATOR
# =============================================================================

EASY_WORDS   = ["define", "state", "name", "identify", "label", "give", "list", "write down", "complete the table", "write the formula"]
HARD_WORDS   = ["design an experiment", "evaluate", "discuss", "assess", "justify", "suggest why", "analyse", "deduce", "devise"]
MEDIUM_WORDS = ["calculate", "explain", "describe", "compare", "suggest", "draw", "predict", "show that", "write an equation", "balance"]

def estimate_difficulty(text: str) -> str:
    t = text.lower()
    for h in HARD_WORDS:
        if h in t:
            return "hard"
    for e in EASY_WORDS:
        if t.startswith(e) or f" {e} " in t:
            return "easy"
    for m in MEDIUM_WORDS:
        if m in t:
            return "medium"
    return "medium"


# =============================================================================
# DB HELPERS
# =============================================================================

def get_subject_id(sb: "Client") -> str:
    result = sb.table("subjects").select("id").eq("code", SUBJECT_CODE).single().execute()
    if not result.data:
        raise ValueError(f"Subject {SUBJECT_CODE} not found in DB.")
    return result.data["id"]


def get_valid_topic_codes(sb: "Client", subject_id: str) -> set[str]:
    result = sb.table("topics").select("code").eq("subject_id", subject_id).execute()
    return {r["code"] for r in result.data}


def fetch_pages(sb: "Client", subject_id: str, resume: bool) -> list[dict]:
    papers = sb.table("papers").select("id").eq("subject_id", subject_id).execute()
    paper_ids = [p["id"] for p in papers.data]
    if not paper_ids:
        return []

    all_pages: list[dict] = []
    PAGE_SIZE = 1000
    offset = 0
    while True:
        result = (
            sb.table("pages")
            .select("id, text_excerpt, question_number, paper_id, topics")
            .in_("paper_id", paper_ids)
            .eq("is_question", True)
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = result.data or []
        all_pages.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    if resume:
        return [p for p in all_pages if not p.get("topics")]
    return all_pages


def flush_batch(sb: "Client", batch: list[dict]):
    for item in batch:
        for attempt in range(5):
            try:
                sb.table("pages").update({
                    "topics":     item["topics"],
                    "confidence": item["confidence"],
                    "difficulty": item["difficulty"],
                }).eq("id", item["id"]).execute()
                break
            except Exception as e:
                if attempt == 4:
                    print(f"\n  [DB ERR] page {item['id']}: {e}")
                time.sleep(2 ** attempt)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Classify Human Biology (4HB1) pages to chapter topics"
    )
    parser.add_argument("--dry-run",       action="store_true", help="No DB writes")
    parser.add_argument("--resume",        action="store_true", help="Skip already-classified pages")
    parser.add_argument("--use-llm",       action="store_true", help="Use Groq as fallback for low-confidence matches")
    parser.add_argument("--llm-threshold", type=float, default=0.5, help="Keyword confidence below which LLM is used (default 0.5)")
    args = parser.parse_args()

    if not SUPABASE_URL or not SERVICE_KEY:
        print("[ERR] Missing Supabase credentials in .env.local")
        sys.exit(1)

    if not CONFIG_PATH.exists():
        print(f"[ERR] Config not found: {CONFIG_PATH}")
        sys.exit(1)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    sb         = create_client(SUPABASE_URL, SERVICE_KEY)
    classifier = KeywordClassifier(config)
    subject_id = get_subject_id(sb)
    valid_codes = get_valid_topic_codes(sb, subject_id)

    print(f"\n{'='*70}")
    print(f"  Classifying HUMAN BIOLOGY ({SUBJECT_CODE})")
    print(f"{'='*70}")
    print(f"  Topics in DB : {len(valid_codes)}")
    print(f"  Mode         : {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"  LLM fallback : {'yes (Groq)' if args.use_llm and GROQ_KEY else 'no'}")
    print(f"  Resume       : {args.resume}")

    pages = fetch_pages(sb, subject_id, args.resume)
    print(f"  Pages to tag : {len(pages)}")

    if not pages:
        print("  [OK] Nothing to classify — all pages already tagged.")
        return

    stats = {"classified": 0, "skipped": 0, "errors": 0, "topic_counts": {}, "difficulty_counts": {}}
    batch: list[dict] = []
    BATCH_SIZE = 50

    for i, page in enumerate(pages):
        text = page.get("text_excerpt") or ""
        if not text.strip():
            stats["skipped"] += 1
            continue

        topic_id, confidence = classifier.classify(text)

        if args.use_llm and GROQ_KEY and (topic_id is None or confidence < args.llm_threshold):
            llm_topic, llm_conf = classify_with_groq(text, {t["id"]: t for t in config["topics"]}, GROQ_KEY)
            if llm_topic and llm_conf > confidence:
                topic_id   = llm_topic
                confidence = llm_conf
            time.sleep(0.5)

        if topic_id is None or topic_id not in valid_codes:
            topic_id   = sorted(valid_codes, key=int)[0]
            confidence = 0.1

        difficulty = estimate_difficulty(text)
        stats["topic_counts"][topic_id]       = stats["topic_counts"].get(topic_id, 0) + 1
        stats["difficulty_counts"][difficulty] = stats["difficulty_counts"].get(difficulty, 0) + 1

        batch.append({"id": page["id"], "topics": [topic_id], "confidence": confidence, "difficulty": difficulty})

        if len(batch) >= BATCH_SIZE:
            if not args.dry_run:
                flush_batch(sb, batch)
            stats["classified"] += len(batch)
            batch = []
            print(f"  [{i+1}/{len(pages)}] classified …", end="\r")

    if batch:
        if not args.dry_run:
            flush_batch(sb, batch)
        stats["classified"] += len(batch)

    print(f"\n\n  -- Results --")
    print(f"  Classified : {stats['classified']}")
    print(f"  Skipped    : {stats['skipped']}")
    print()
    print("  Topic distribution:")
    tc = stats.get("topic_counts", {})
    for code in sorted(valid_codes, key=int):
        count = tc.get(code, 0)
        bar   = "#" * min(count // 2, 40)
        print(f"    Ch{code:<3}  {count:>4}  {bar}")
    print()
    print("  Difficulty distribution:")
    dc = stats.get("difficulty_counts", {})
    total = max(sum(dc.values()), 1)
    for diff in ["easy", "medium", "hard"]:
        n   = dc.get(diff, 0)
        pct = n / total * 100
        print(f"    {diff:<8}  {n:>4}  ({pct:.0f}%)")

    print("\n[DONE]  Classification complete.")


if __name__ == "__main__":
    main()
