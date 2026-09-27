"""
Build the COMPLETE Further Pure Mathematics (4PM1) question index: every
segmented question, 2016-2022, in chapterwise book order.

WHY THIS EXISTS
---------------
The printed workbook (build_fpm_workbook_print.py) is scoped to 2018 onwards and
to database rows a human has verified, so its index holds 316 of the 431
questions. The worked-solutions pipeline needs all of them. This index is the
superset:

  * the 423 verified `workbook_questions` rows, in the database's own print
    order (section, then ordinal in chapter), keeping their stable slugs; and
  * the questions the classifier never reached, from
    data/workbook/fpm_manual_classifications.json (the 8 scanned 2019 May/June
    Paper 1 questions), appended to the end of their section under a
    provisional slug FPM.<paper_key>.Q<n>. They are not in the database yet.

Numbering restarts at 1 in every section, as in the printed book -- but over
2016-2022, so these printed numbers are NOT the 2018-22 book's.

READ-ONLY against the database.

USAGE
  python scripts/build_fpm_complete_index.py
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKBOOK_DIR = REPO_ROOT / "data" / "workbook"
QUESTIONS_PATH = WORKBOOK_DIR / "fpm_questions.json"
MANUAL_PATH = WORKBOOK_DIR / "fpm_manual_classifications.json"
OUT_PATH = WORKBOOK_DIR / "fpm_complete_index.json"

SUBJECT_CODE = "4PM1"
SESSION_LABEL = {
    "jan": "January", "may-jun": "May/June",
    "oct-nov": "October/November", "specimen": "Specimen",
}
PAGE_SIZE = 1000


def source_label(paper_key: str, question_number: int) -> str:
    year, season, paper = paper_key.split("_")
    return f"{year} {SESSION_LABEL.get(season, season.title())} Paper {paper} Q{question_number}"


def fetch_verified(supabase, subject_id: str) -> list[dict]:
    rows: list[dict] = []
    start = 0
    while True:
        page = (supabase.table("workbook_questions")
                .select("slug, section_id, ordinal_in_chapter, marks,"
                        " source_paper_key, source_question_number")
                .eq("subject_id", subject_id)
                .not_.is_("verified_at", "null")
                .order("ordinal_in_chapter")
                .range(start, start + PAGE_SIZE - 1)
                .execute().data)
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        start += PAGE_SIZE


def main() -> int:
    load_dotenv(REPO_ROOT / ".env.local")
    supabase = create_client(os.environ["NEXT_PUBLIC_SUPABASE_URL"],
                             os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    subject_id = (supabase.table("subjects").select("id")
                  .eq("code", SUBJECT_CODE).single().execute().data["id"])
    chapters = (supabase.table("workbook_chapters").select("id, number, title")
                .eq("subject_id", subject_id).order("number").execute().data)
    sections = (supabase.table("workbook_sections")
                .select("id, chapter_id, number, title")
                .in_("chapter_id", [c["id"] for c in chapters]).execute().data)
    chapter_by_id = {c["id"]: c for c in chapters}
    section_by_label = {
        f"{chapter_by_id[s['chapter_id']]['number']}.{s['number']}": s for s in sections
    }
    label_by_section_id = {s["id"]: label for label, s in section_by_label.items()}

    # (section label) -> ordered entries, database rows first.
    by_section: dict[str, list[dict]] = defaultdict(list)
    seen: set[tuple[str, int]] = set()
    for row in fetch_verified(supabase, subject_id):
        label = label_by_section_id.get(row["section_id"])
        if label is None:
            print(f"  skip {row['slug']}: section not in the taxonomy")
            continue
        by_section[label].append({
            "slug": row["slug"],
            "paper_key": row["source_paper_key"],
            "question_number": row["source_question_number"],
            "marks": row["marks"],
            "_order": row["ordinal_in_chapter"],
        })
        seen.add((row["source_paper_key"], row["source_question_number"]))

    marks_of = {
        (q["paper_key"], q["question_number"]): q["marks"]
        for q in json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    }
    manual = json.loads(MANUAL_PATH.read_text(encoding="utf-8"))["questions"]
    added = 0
    for item in manual:
        key = (item["paper_key"], item["question_number"])
        if key in seen:
            continue  # the database has it now; its row wins
        if item["section"] not in section_by_label:
            sys.exit(f"manual classification {key}: unknown section {item['section']}")
        by_section[item["section"]].append({
            "slug": f"FPM.{item['paper_key']}.Q{item['question_number']}",
            "paper_key": item["paper_key"],
            "question_number": item["question_number"],
            "marks": marks_of[key],
            "_order": float("inf"),
        })
        seen.add(key)
        added += 1

    def section_sort(label: str) -> tuple[int, int]:
        chapter, number = label.split(".")
        return int(chapter), int(number)

    questions: list[dict] = []
    for label in sorted(by_section, key=section_sort):
        section = section_by_label[label]
        chapter = chapter_by_id[section["chapter_id"]]
        entries = sorted(by_section[label], key=lambda e: e["_order"])
        for printed, entry in enumerate(entries, 1):
            questions.append({
                "slug": entry["slug"],
                "chapter": chapter["number"],
                "chapter_title": chapter["title"],
                "section": label,
                "section_title": section["title"],
                "printed_number": printed,
                "marks": entry["marks"],
                "source": source_label(entry["paper_key"], entry["question_number"]),
            })

    all_keys = set(marks_of)
    missing = sorted(all_keys - seen)
    OUT_PATH.write_text(json.dumps({
        "edition": "complete-2016-2022",
        "questions": questions,
    }, indent=2), encoding="utf-8")

    print(f"  database rows      : {len(questions) - added}")
    print(f"  hand-classified    : {added}")
    print(f"  total              : {len(questions)} of {len(all_keys)} segmented")
    if missing:
        print(f"  NOT INDEXED        : {missing}")
    print(f"  written            : {OUT_PATH.relative_to(REPO_ROOT)}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
