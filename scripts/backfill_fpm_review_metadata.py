"""
Backfill review metadata onto workbook_questions, so Phase 4 can triage.

Migration 14 adds `proposed_section_id`, `review_priority` and
`classifier_confidence`. This fills them from the two classification passes.

The ordering it enables is the whole point of the verification screen: instead
of 423 questions at uniform attention, the reviewer gets ~54 that need real
thought, ~106 that need a glance at the section, and ~250 that are
confirm-and-move-on.

Requires migration 14. Idempotent.

USAGE
-----
    python scripts/backfill_fpm_review_metadata.py
    python scripts/backfill_fpm_review_metadata.py --execute
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

REPO_ROOT = Path(__file__).resolve().parent.parent
CLASSIFICATIONS_PATH = REPO_ROOT / "data" / "workbook" / "fpm_classifications.json"
SUBJECT_CODE = "4PM1"


def priority_for(primary: str | None, proposed: str | None) -> str:
    if not proposed:
        return "unconfirmed"
    if proposed == primary:
        return "agreed"
    if proposed.split(".")[0] == (primary or "").split(".")[0]:
        return "same_chapter"
    return "disputed"


def main() -> int:
    load_dotenv(REPO_ROOT / ".env.local")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="write to the database")
    args = parser.parse_args()

    data = json.loads(CLASSIFICATIONS_PATH.read_text(encoding="utf-8"))
    supabase = create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    )

    subject_id = (
        supabase.table("subjects").select("id").eq("code", SUBJECT_CODE).single().execute().data["id"]
    )

    chapters = supabase.table("workbook_chapters").select("id,number").eq(
        "subject_id", subject_id
    ).execute().data
    number_by_chapter_id = {c["id"]: str(c["number"]) for c in chapters}
    sections = supabase.table("workbook_sections").select("id,chapter_id,number").execute().data
    section_id_by_code = {
        f"{number_by_chapter_id[s['chapter_id']]}.{s['number']}": s["id"]
        for s in sections
        if s["chapter_id"] in number_by_chapter_id
    }

    rows = supabase.table("workbook_questions").select(
        "id,source_paper_key,source_question_number"
    ).eq("subject_id", subject_id).execute().data
    id_by_source = {(r["source_paper_key"], r["source_question_number"]): r["id"] for r in rows}
    print(f"  questions in database : {len(rows)}")

    updates: list[tuple[str, dict]] = []
    counts: Counter = Counter()

    for question in data:
        key = (question["paper_key"], question["question_number"])
        row_id = id_by_source.get(key)
        classification = question.get("classification")
        if row_id is None or not classification:
            continue

        second = question.get("second_opinion")
        proposed_code = second["primary"] if second else None
        priority = priority_for(classification["primary"], proposed_code)
        counts[priority] += 1

        updates.append(
            (
                row_id,
                {
                    "proposed_section_id": section_id_by_code.get(proposed_code) if proposed_code else None,
                    "review_priority": priority,
                    "classifier_confidence": classification.get("confidence"),
                },
            )
        )

    print(f"  to update             : {len(updates)}")
    for priority in ("disputed", "same_chapter", "unconfirmed", "agreed"):
        print(f"    {priority:<14} : {counts.get(priority, 0)}")

    if not args.execute:
        print("\n  Dry run -- nothing written. Re-run with --execute.")
        return 0

    for index, (row_id, payload) in enumerate(updates, 1):
        supabase.table("workbook_questions").update(payload).eq("id", row_id).execute()
        if index % 100 == 0:
            print(f"    {index}/{len(updates)}...")

    print(f"\n  updated: {len(updates)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
