#!/usr/bin/env python3
"""
GradeMax — Chemistry & Biology Re-Classifier v1.0
==================================================
Re-classifies existing Chemistry (4CH1) and Biology (4BI1) question pages
against the new granular chapter-level topic codes (1.1 – 5.x).

Prerequisites
-------------
  pip install supabase python-dotenv pyyaml requests

Usage
-----
  # Dry run (no DB writes)
  python scripts/reclassify_chem_bio.py --subject chemistry --dry-run

  # Classify chemistry only
  python scripts/reclassify_chem_bio.py --subject chemistry

  # Classify biology only
  python scripts/reclassify_chem_bio.py --subject biology

  # Classify both
  python scripts/reclassify_chem_bio.py --subject all

  # Resume from a specific page ID (skip already done)
  python scripts/reclassify_chem_bio.py --subject chemistry --resume

  # Use LLM for low-confidence keyword matches (requires GEMINI_API_KEY)
  python scripts/reclassify_chem_bio.py --subject all --use-llm
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

# ── Supabase ──────────────────────────────────────────────────────────────────
try:
    from supabase import create_client, Client
except ImportError:
    print("❌  Install supabase:  pip install supabase")
    sys.exit(1)

# ── Load .env ─────────────────────────────────────────────────────────────────
env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(env_path)

SUPABASE_URL  = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
SERVICE_KEY   = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
GEMINI_KEY    = os.getenv('GEMINI_API_KEY')
GROQ_KEY      = os.getenv('GROQ_API_KEY')

CONFIG_DIR = Path(__file__).parent.parent / 'config'

# ── Subject map ───────────────────────────────────────────────────────────────
SUBJECT_MAP = {
    'chemistry': {'code': '4CH1', 'yaml': 'chemistry_topics.yaml'},
    'biology':   {'code': '4BI1', 'yaml': 'biology_topics.yaml'},
}


# =============================================================================
# KEYWORD CLASSIFIER
# =============================================================================

class KeywordClassifier:
    """
    Fast keyword/formula scorer built from a subject YAML config.
    Returns (topic_id, confidence) for a given question text.
    """

    def __init__(self, config: dict):
        self.topics     = {t['id']: t for t in config['topics']}
        self.negatives  = [n.lower() for n in config.get('negatives', [])]
        self._build_index(config)

    def _build_index(self, config: dict):
        """Build keyword → (topic_id, weight) lookup."""
        self.keyword_index: dict[str, list[tuple[str, float]]] = {}

        for topic in config['topics']:
            tid   = topic['id']
            # keywords
            for kw in topic.get('keywords', []):
                kw_lower = kw.lower()
                self.keyword_index.setdefault(kw_lower, []).append((tid, 3.0))
            # formulas (higher weight — very specific)
            for f in topic.get('formulas', []):
                f_lower = f.lower()
                self.keyword_index.setdefault(f_lower, []).append((tid, 5.0))
            # synonyms
            for s in topic.get('synonyms', []):
                s_lower = s.lower()
                self.keyword_index.setdefault(s_lower, []).append((tid, 2.0))
            # description words (lowest weight)
            for word in topic.get('description', '').lower().split():
                word = re.sub(r'[^a-z0-9]', '', word)
                if len(word) > 4:
                    self.keyword_index.setdefault(word, []).append((tid, 0.5))

    def classify(self, text: str) -> tuple[Optional[str], float]:
        """
        Returns (topic_id, confidence) where confidence ∈ [0, 1].
        Returns (None, 0.0) if no match found.
        """
        text_lower = text.lower()

        # Reject if negative keyword present
        for neg in self.negatives:
            if neg in text_lower:
                pass  # negatives only reduce score, don't reject entirely

        scores: dict[str, float] = {}

        # Score multi-word phrases first (longer matches = more specific)
        sorted_kws = sorted(self.keyword_index.keys(), key=len, reverse=True)
        matched_spans: list[tuple[int, int]] = []

        for kw in sorted_kws:
            pos = text_lower.find(kw)
            if pos == -1:
                continue
            # Check overlap with already-matched spans
            span = (pos, pos + len(kw))
            overlaps = any(s[0] <= span[1] and span[0] <= s[1] for s in matched_spans)
            if overlaps and len(kw) < 8:
                # Allow short words to still score even if overlapping
                pass
            matched_spans.append(span)

            for (tid, w) in self.keyword_index[kw]:
                scores[tid] = scores.get(tid, 0.0) + w

        if not scores:
            return None, 0.0

        best_tid   = max(scores, key=lambda t: scores[t])
        best_score = scores[best_tid]
        total      = sum(scores.values())

        # Confidence = fraction of total score taken by winner
        confidence = min(best_score / (total + 1e-9), 1.0)
        # Boost confidence if margin over second-best is large
        scores_sorted = sorted(scores.values(), reverse=True)
        if len(scores_sorted) > 1:
            margin = (scores_sorted[0] - scores_sorted[1]) / (scores_sorted[0] + 1e-9)
            confidence = min(confidence + margin * 0.3, 1.0)

        return best_tid, round(confidence, 3)


# =============================================================================
# LLM CLASSIFIER (Gemini fallback)
# =============================================================================

def classify_with_gemini(text: str, topics: dict, api_key: str) -> tuple[Optional[str], float]:
    """Call Gemini Flash to classify a question when keyword confidence is low."""
    try:
        import requests
        topic_list = '\n'.join(
            f"  {tid}: {t['name']} — {t['description']}"
            for tid, t in topics.items()
        )
        prompt = (
            f"You are an Edexcel IGCSE examiner. "
            f"Classify this exam question into ONE topic from the list below.\n\n"
            f"TOPICS:\n{topic_list}\n\n"
            f"QUESTION:\n{text[:600]}\n\n"
            f'Return ONLY valid JSON: {{"topic": "<topic_id>", "confidence": 0.0-1.0}}'
        )
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.0-flash:generateContent?key={api_key}"
        )
        resp = requests.post(url, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 100}
        }, timeout=15)
        resp.raise_for_status()
        raw = resp.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        # Strip markdown code fences if present
        raw = re.sub(r'^```[a-z]*\n?', '', raw).rstrip('`').strip()
        data = json.loads(raw)
        return str(data['topic']), float(data.get('confidence', 0.7))
    except Exception as e:
        return None, 0.0


# =============================================================================
# DIFFICULTY ESTIMATOR
# =============================================================================

EASY_WORDS  = ['define', 'state', 'name', 'identify', 'label', 'give', 'list', 'write down', 'complete the table', 'write the formula']
HARD_WORDS  = ['design an experiment', 'evaluate', 'discuss', 'assess', 'justify', 'suggest why', 'analyse', 'deduce', 'devise']
MEDIUM_WORDS = ['calculate', 'explain', 'describe', 'compare', 'suggest', 'draw', 'predict', 'show that', 'write an equation', 'balance']

def estimate_difficulty(text: str) -> str:
    t = text.lower()
    for h in HARD_WORDS:
        if h in t:
            return 'hard'
    for e in EASY_WORDS:
        if t.startswith(e) or f' {e} ' in t:
            return 'easy'
    for m in MEDIUM_WORDS:
        if m in t:
            return 'medium'
    return 'medium'


# =============================================================================
# MAIN CLASSIFIER LOOP
# =============================================================================

def load_config(subject_key: str) -> dict:
    yaml_path = CONFIG_DIR / SUBJECT_MAP[subject_key]['yaml']
    if not yaml_path.exists():
        raise FileNotFoundError(f"Config not found: {yaml_path}")
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_subject_id(supabase: 'Client', subject_code: str) -> str:
    result = supabase.table('subjects').select('id').eq('code', subject_code).single().execute()
    if not result.data:
        raise ValueError(f"Subject {subject_code} not found in DB. Run the subjects migration first.")
    return result.data['id']


def get_valid_topic_codes(supabase: 'Client', subject_id: str) -> set[str]:
    """Fetch topic codes from DB to validate classifier output."""
    result = supabase.table('topics').select('code').eq('subject_id', subject_id).execute()
    return {r['code'] for r in result.data}


def fetch_unclassified_pages(supabase: 'Client', subject_id: str) -> list[dict]:
    """Fetch pages with empty topics array (needs classification)."""
    # Get all paper IDs for this subject
    papers = supabase.table('papers').select('id').eq('subject_id', subject_id).execute()
    paper_ids = [p['id'] for p in papers.data]
    if not paper_ids:
        return []

    # Pages with empty or null topics
    result = (
        supabase.table('pages')
        .select('id, text_excerpt, question_number, paper_id')
        .in_('paper_id', paper_ids)
        .eq('is_question', True)
        .execute()
    )
    # Filter to empty topics (Supabase doesn't have a great "array is empty" filter via SDK)
    return [p for p in result.data if not p.get('topics')]


def run_subject(
    subject_key: str,
    supabase: 'Client',
    dry_run: bool = False,
    use_llm: bool = False,
    resume: bool = False,
    llm_threshold: float = 0.5,
) -> dict:
    subject_code = SUBJECT_MAP[subject_key]['code']
    print(f"\n{'='*70}")
    print(f"  Classifying {subject_key.upper()} ({subject_code})")
    print(f"{'='*70}")

    config      = load_config(subject_key)
    classifier  = KeywordClassifier(config)
    subject_id  = get_subject_id(supabase, subject_code)
    valid_codes = get_valid_topic_codes(supabase, subject_id)

    print(f"  Topics in DB : {len(valid_codes)}")
    print(f"  Mode         : {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"  LLM fallback : {'yes (Gemini)' if use_llm and GEMINI_KEY else 'no'}")

    pages = fetch_unclassified_pages(supabase, subject_id)
    print(f"  Pages to tag : {len(pages)}")

    if not pages:
        print("  ✅ Nothing to classify — all pages already tagged.")
        return {'classified': 0, 'skipped': 0, 'errors': 0}

    stats = {'classified': 0, 'skipped': 0, 'errors': 0,
             'topic_counts': {}, 'difficulty_counts': {}}

    batch: list[dict] = []
    BATCH_SIZE = 50

    for i, page in enumerate(pages):
        text = page.get('text_excerpt') or ''
        if not text.strip():
            stats['skipped'] += 1
            continue

        topic_id, confidence = classifier.classify(text)

        # LLM fallback for low-confidence matches
        if use_llm and GEMINI_KEY and (topic_id is None or confidence < llm_threshold):
            llm_topic, llm_conf = classify_with_gemini(
                text,
                {t['id']: t for t in config['topics']},
                GEMINI_KEY
            )
            if llm_topic and llm_conf > confidence:
                topic_id   = llm_topic
                confidence = llm_conf
            time.sleep(0.4)  # Gemini rate limit

        if topic_id is None or topic_id not in valid_codes:
            # Fallback: pick first topic in spec order
            topic_id   = sorted(valid_codes)[0]
            confidence = 0.1

        difficulty = estimate_difficulty(text)

        stats['topic_counts'][topic_id]       = stats['topic_counts'].get(topic_id, 0) + 1
        stats['difficulty_counts'][difficulty] = stats['difficulty_counts'].get(difficulty, 0) + 1

        batch.append({
            'id':         page['id'],
            'topics':     [topic_id],
            'confidence': confidence,
            'difficulty': difficulty,
        })

        if len(batch) >= BATCH_SIZE:
            if not dry_run:
                _flush_batch(supabase, batch)
            stats['classified'] += len(batch)
            batch = []
            print(f"  [{i+1}/{len(pages)}] classified …", end='\r')

    # Final flush
    if batch:
        if not dry_run:
            _flush_batch(supabase, batch)
        stats['classified'] += len(batch)

    _print_report(subject_key, stats, valid_codes)
    return stats


def _flush_batch(supabase: 'Client', batch: list[dict]):
    """Write classifications back to DB in one upsert."""
    for item in batch:
        supabase.table('pages').update({
            'topics':     item['topics'],
            'confidence': item['confidence'],
            'difficulty': item['difficulty'],
        }).eq('id', item['id']).execute()


def _print_report(subject_key: str, stats: dict, valid_codes: set):
    print(f"\n  ── Results for {subject_key.upper()} ──")
    print(f"  Classified : {stats['classified']}")
    print(f"  Skipped    : {stats['skipped']}")
    print(f"  Errors     : {stats['errors']}")
    print()
    print("  Topic distribution:")
    tc = stats.get('topic_counts', {})
    for code in sorted(valid_codes):
        count = tc.get(code, 0)
        bar   = '█' * min(count // 2, 40)
        print(f"    {code:<6}  {count:>4}  {bar}")
    print()
    print("  Difficulty distribution:")
    dc = stats.get('difficulty_counts', {})
    total = max(sum(dc.values()), 1)
    for diff in ['easy', 'medium', 'hard']:
        n   = dc.get(diff, 0)
        pct = n / total * 100
        bar = '█' * int(pct / 2)
        print(f"    {diff:<8}  {n:>4}  ({pct:.0f}%)  {bar}")
    print()


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Re-classify Chemistry and Biology pages to granular chapter topics'
    )
    parser.add_argument('--subject', choices=['chemistry', 'biology', 'all'],
                        default='all', help='Which subject to classify')
    parser.add_argument('--dry-run', action='store_true',
                        help='Run without writing to DB')
    parser.add_argument('--use-llm', action='store_true',
                        help='Use Gemini as fallback for low-confidence matches')
    parser.add_argument('--resume', action='store_true',
                        help='Skip pages that already have topics assigned')
    parser.add_argument('--llm-threshold', type=float, default=0.5,
                        help='Minimum keyword confidence to skip LLM (default 0.5)')
    args = parser.parse_args()

    if not SUPABASE_URL or not SERVICE_KEY:
        print("❌  NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env.local")
        sys.exit(1)

    supabase: Client = create_client(SUPABASE_URL, SERVICE_KEY)

    subjects = ['chemistry', 'biology'] if args.subject == 'all' else [args.subject]

    for subj in subjects:
        run_subject(
            subj,
            supabase,
            dry_run=args.dry_run,
            use_llm=args.use_llm,
            resume=args.resume,
            llm_threshold=args.llm_threshold,
        )

    print("\n✅  Done.")


if __name__ == '__main__':
    main()
