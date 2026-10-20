#!/usr/bin/env python3
"""
Spec-section tags for every rebuilt Maths A (4MA1/4MA0) tool question ->
data/analysis/live_rebuild/4MA1/topics_new.json, read by
apply_mathsa_rebuild_topics.py after the publish.

Tags are 4MA1 Higher specification sections ("2.7" Quadratic equations), the
same 39-section tree as the Maths A workbook (supabase migration 20) and the
same granularity the IAL units use in the tools. 1.10 / 1.11 / 4.4 are process
statements and are never served as tags (no question is "about" them).

Where each tag comes from, in order:
  1. workbook  -- the workbook already classified this question (DB
     workbook_questions, primary + secondary). Used only when the workbook's
     stem and the new cut's text are the same question (token overlap), since
     the workbook was cut from a different copy of the archive.
  2. agreed    -- two different model families (gpt-oss-120b, qwen3.8) given the
     workbook's own prompt agree on the primary section.
  3. reviewed  -- anything else: read directly, decisions recorded
     in topic_reads.json {"<paper>|<q>": ["4.9", "4.10"]}. Nothing unread is
     ever tagged with a guess.

    python -X utf8 scripts/classify_mathsa_tool_topics.py
    python -X utf8 scripts/classify_mathsa_tool_topics.py --review-only
        # Apply recorded reads and cached model agreement locally; no API calls.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import time
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))

import classify_mathsa_workbook_sections as clf  # noqa: E402
from lib.live_paper_sources import REBUILD_DIR, fetch_rows, supabase_client  # noqa: E402

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

CODE = "4MA1"
SUBJECT_ID = "8b7b0cb0-e95c-480d-ac0a-c710f1e59213"
STAGE = REBUILD_DIR / CODE
CACHE = STAGE / "topic_model_cache.json"
READS = STAGE / "topic_reads.json"
READ_NOTES = STAGE / "topic_read_notes.json"
OUT = STAGE / "topics_new.json"
RECORD = STAGE / "topic_sources.json"
SAME_QUESTION_MIN = 0.5
MIN_TEXT = 40
BATCH = 6
FURNITURE_RE = re.compile(
    r"GradeMax|PhysicsAndMathsTutor\S*|Turn over|DO NOT WRITE IN THIS AREA|"
    r"\(Total for Question \d+ is \d+ marks?\)|\*P\d+A?\d*\*", re.I)


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}|\d+", text.lower()))


def overlap(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    return len(ta & tb) / max(1, min(len(ta), len(tb)))


def cut_text(path: Path) -> str:
    with fitz.open(path) as doc:
        text = " ".join(page.get_text() for page in doc)
    return " ".join(FURNITURE_RE.sub(" ", text).split())


def tags_of(primary: str, secondary: list[str]) -> list[str]:
    codes = [primary] + [c for c in secondary if c != primary]
    return [c for c in dict.fromkeys(codes) if c not in clf.SECONDARY_ONLY]


def validate_tags(tags: dict, valid_keys: set[str]) -> None:
    """Reject stale decisions and invalid/empty tags before replacing outputs."""
    for key, codes in tags.items():
        if key not in valid_keys:
            raise ValueError(f"Unknown question in topic decisions: {key}")
        if (not isinstance(codes, list) or not 1 <= len(codes) <= 4
                or any(not isinstance(c, str) or c not in clf.TAXONOMY
                       or c in clf.SECONDARY_ONLY for c in codes)
                or len(codes) != len(set(codes))):
            raise ValueError(f"Invalid topic tags for {key}: {codes!r}")


def recorded_workbook_index() -> dict[tuple[str, int], dict]:
    """Retain only previously matched workbook tags in an offline review run."""
    topics = json.loads(OUT.read_text(encoding="utf-8"))
    sources = json.loads(RECORD.read_text(encoding="utf-8"))
    out = {}
    for key, source in sources.items():
        if source != "workbook":
            continue
        if key not in topics:
            raise ValueError(f"Missing recorded workbook tags for {key}")
        paper, question = key.rsplit("|", 1)
        out[(paper, int(question))] = {"tags": topics[key], "stem": ""}
    return out


def section_codes(sb) -> dict[str, str]:
    """workbook_sections.id -> "chapter.section" code, e.g. "2.7"."""
    chapters = {c["id"]: c["number"] for c in sb.table("workbook_chapters").select("id,number")
                .eq("subject_id", SUBJECT_ID).execute().data}
    sections = fetch_rows(lambda o: sb.table("workbook_sections").select("id,number,chapter_id")
                          .in_("chapter_id", list(chapters)).range(o, o + 999))
    return {s["id"]: f"{chapters[s['chapter_id']]}.{s['number']}" for s in sections}


def workbook_index(sb) -> dict[tuple[str, int], dict]:
    code_of = section_codes(sb)
    rows = fetch_rows(lambda o: sb.table("workbook_questions")
                      .select("source_paper_key,source_question_number,section_id,"
                              "secondary_section_ids,stem")
                      .eq("subject_id", SUBJECT_ID).range(o, o + 999))
    out = {}
    for r in rows:
        if r["section_id"] not in code_of:
            continue
        out[(r["source_paper_key"], int(r["source_question_number"]))] = {
            "tags": tags_of(code_of[r["section_id"]],
                            [code_of[s] for s in (r["secondary_section_ids"] or []) if s in code_of]),
            "stem": r["stem"] or ""}
    return out


def model_pass(pending: list[dict], cache: dict) -> None:
    """Fill cache[id] = {"a": result, "b": result} for both model families."""
    for slot, provider in (("a", "gemini"), ("b", "groq")):  # see clf.classify_text_batch
        todo = [q for q in pending if slot not in cache.get(clf.question_id(q), {})]
        for i in range(0, len(todo), BATCH):
            batch = todo[i:i + BATCH]
            got = clf.classify_text_batch(batch, provider=provider)
            for q in batch:
                qid = clf.question_id(q)
                if qid in got:
                    cache.setdefault(qid, {})[slot] = got[qid]
            CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")
            time.sleep(clf.REQUEST_DELAY_S)
            print(f"  model {slot}: {min(i + BATCH, len(todo))}/{len(todo)}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-only", action="store_true",
                        help="use recorded workbook matches, model cache and reads without APIs")
    args = parser.parse_args()
    rows = json.loads((STAGE / "verdicts.json").read_text(encoding="utf-8"))["rows"]
    valid_keys = {f"{row['paper']}|{row['question']}" for row in rows}
    if len(valid_keys) != len(rows):
        raise ValueError("Duplicate question keys in rebuild verdicts")
    reads = json.loads(READS.read_text(encoding="utf-8")) if READS.is_file() else {}
    validate_tags(reads, valid_keys)
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.is_file() else {}
    notes = json.loads(READ_NOTES.read_text(encoding="utf-8")) if READ_NOTES.is_file() else {}
    wb = recorded_workbook_index() if args.review_only else workbook_index(supabase_client())

    topics, record, pending = {}, {}, []
    root = Path(__file__).resolve().parent.parent
    for row in rows:
        key = f"{row['paper']}|{row['question']}"
        text = cut_text(root / row["qp"])
        hit = wb.get((row["paper"], int(row["question"])))
        if key in reads:
            note = notes.get(key, {})
            if note.get("tags") is not None and note["tags"] != reads[key]:
                raise ValueError(f"Review notes disagree with topic reads for {key}")
            fingerprint = note.get("qp_sha256")
            if fingerprint and fingerprint != hashlib.sha256((root / row["qp"]).read_bytes()).hexdigest():
                raise ValueError(f"Question PDF changed since topic review: {key}")
            topics[key], record[key] = reads[key], "reviewed"
        elif hit and hit["tags"] and (args.review_only
                                     or overlap(text, hit["stem"]) >= SAME_QUESTION_MIN):
            topics[key], record[key] = hit["tags"], "workbook"
        elif len(text) < MIN_TEXT:
            record[key] = "claude_needed:no_text"
        else:
            pending.append({"paper_key": row["paper"], "question_number": row["question"],
                            "marks": row.get("marks") or "?", "stem": text, "_key": key})

    if not args.review_only:
        model_pass(pending, cache)
    for q in pending:
        got = cache.get(clf.question_id(q), {})
        a, b = got.get("a"), got.get("b")
        if a and b and a["primary"] == b["primary"]:
            topics[q["_key"]] = tags_of(a["primary"], a["secondary"])
            record[q["_key"]] = "agreed"
        else:
            record[q["_key"]] = (f"claude_needed:{(a or {}).get('primary')} vs "
                                 f"{(b or {}).get('primary')}")

    validate_tags(topics, valid_keys)
    OUT.write_text(json.dumps(topics, indent=1, sort_keys=True), encoding="utf-8")
    RECORD.write_text(json.dumps(record, indent=1, sort_keys=True), encoding="utf-8")
    kinds = {}
    for v in record.values():
        k = v.split(":")[0]
        kinds[k] = kinds.get(k, 0) + 1
    print(f"rows {len(rows)}  tagged {len(topics)}  {kinds}")
    need = sorted(k for k, v in record.items() if v.startswith("claude_needed"))
    print(f"remaining direct reads ({len(need)}):")
    for k in need:
        print("  ", k, record[k])
    return 1 if need else 0


if __name__ == "__main__":
    raise SystemExit(main())
