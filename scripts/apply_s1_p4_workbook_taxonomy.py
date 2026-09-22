#!/usr/bin/env python3
"""
Apply the S1 (WST01) and P4 (WMA14) workbook taxonomies to the database.

Migrations 18 and 19 are pure INSERTs into `workbook_chapters` and
`workbook_sections`, both of which already exist from migration 12. There is no
DDL, so they can go in over PostgREST with the service-role key rather than
being pasted into the Supabase SQL editor -- the same route migration 15 took
for Maths B.

The rows are read OUT OF THE MIGRATION FILES rather than restated here. A
second copy of a taxonomy is a second thing to keep in sync, and
`--check-taxonomy` in the classifiers already diffs against the migration, so
the migration is the one source of truth.

    python scripts/apply_s1_p4_workbook_taxonomy.py            # dry run
    python scripts/apply_s1_p4_workbook_taxonomy.py --execute

Idempotent: existing chapters and sections are matched on (subject, number) and
left alone. It never updates or deletes, so it cannot disturb a taxonomy that
questions have already been classified against.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = REPO_ROOT / "supabase" / "migrations"

SUBJECTS = {
    "WST01": MIGRATIONS_DIR / "18_workbook_s1_taxonomy.sql",
    "WMA14": MIGRATIONS_DIR / "19_workbook_p4_taxonomy.sql",
}

# (number, 'title', 'spec_ref') -- the chapter VALUES rows.
CHAPTER_RE = re.compile(r"^\s*\((\d+),\s*'((?:[^']|'')+)',\s*'((?:[^']|'')+)'\)", re.M)
# (chapter_number, section_number, 'title') -- the section VALUES rows.
SECTION_RE = re.compile(r"^\s*\((\d+),\s*(\d+),\s*'((?:[^']|'')+)'\)", re.M)


def unquote(value: str) -> str:
    """SQL escapes a literal quote by doubling it: 'Pythagoras'' theorem'."""
    return value.replace("''", "'")


def parse_migration(path: Path) -> tuple[list[dict], list[dict]]:
    """Pull the chapter and section VALUES rows out of a taxonomy migration."""
    text = path.read_text(encoding="utf-8")

    # Split on the two INSERT statements so a three-column section row can
    # never be mistaken for a three-column chapter row, and vice versa.
    try:
        ch_block, sec_block = text.split("INSERT INTO workbook_sections", 1)
    except ValueError:  # pragma: no cover - malformed migration
        raise SystemExit(f"{path.name}: no workbook_sections INSERT found")

    chapters = [
        {"number": int(num), "title": unquote(title), "spec_ref": unquote(ref)}
        for num, title, ref in CHAPTER_RE.findall(ch_block)
    ]
    sections = [
        {"chapter_number": int(ch), "number": int(num), "title": unquote(title)}
        for ch, num, title in SECTION_RE.findall(sec_block)
    ]
    if not chapters or not sections:
        raise SystemExit(f"{path.name}: parsed {len(chapters)} chapters / {len(sections)} sections")

    # Contiguity is what the book's contents page depends on; a gap here would
    # print as a missing heading rather than as an error.
    if [c["number"] for c in chapters] != list(range(1, len(chapters) + 1)):
        raise SystemExit(f"{path.name}: chapter numbers are not contiguous from 1")
    for chapter in chapters:
        nums = sorted(s["number"] for s in sections if s["chapter_number"] == chapter["number"])
        if nums != list(range(1, len(nums) + 1)):
            raise SystemExit(f"{path.name}: chapter {chapter['number']} sections not contiguous: {nums}")
    orphans = {s["chapter_number"] for s in sections} - {c["number"] for c in chapters}
    if orphans:
        raise SystemExit(f"{path.name}: sections reference missing chapters {sorted(orphans)}")

    return chapters, sections


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="write to the database")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env.local")
    url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise SystemExit("NEXT_PUBLIC_SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing from .env.local")
    supabase = create_client(url, key)

    mode = "EXECUTE" if args.execute else "DRY RUN"
    print(f"=== S1 / P4 workbook taxonomy  [{mode}] ===\n")

    exit_code = 0
    for code, migration in SUBJECTS.items():
        chapters, sections = parse_migration(migration)
        print(f"{code}  ({migration.name})")
        print(f"  parsed {len(chapters)} chapters / {len(sections)} sections")

        found = supabase.table("subjects").select("id,name").eq("code", code).execute().data
        if not found:
            print(f"  !! no subject row with code {code} -- skipped\n")
            exit_code = 1
            continue
        subject_id = found[0]["id"]
        print(f"  subject {found[0]['name']}  {subject_id}")

        # A taxonomy change under already-classified questions would silently
        # repoint them, so refuse rather than risk it. Nothing here updates
        # existing rows, but the check documents the invariant.
        existing_q = (
            supabase.table("workbook_questions")
            .select("id", count="exact")
            .eq("subject_id", subject_id)
            .limit(1)
            .execute()
        )
        if existing_q.count:
            print(f"  note: {existing_q.count} questions already reference this subject;"
                  f" only missing chapters/sections will be added")

        existing_ch = (
            supabase.table("workbook_chapters")
            .select("id,number,title")
            .eq("subject_id", subject_id)
            .execute()
            .data
        )
        by_number = {c["number"]: c for c in existing_ch}

        to_create = [c for c in chapters if c["number"] not in by_number]
        if to_create and args.execute:
            supabase.table("workbook_chapters").insert(
                [{"subject_id": subject_id, **c} for c in to_create]
            ).execute()
            existing_ch = (
                supabase.table("workbook_chapters")
                .select("id,number,title")
                .eq("subject_id", subject_id)
                .execute()
                .data
            )
            by_number = {c["number"]: c for c in existing_ch}
        print(f"  chapters: {len(to_create)} to create, {len(chapters) - len(to_create)} already present")

        # Sections are keyed on (chapter_id, number); without the chapter rows
        # a dry run has nothing to resolve against, which is expected.
        made = skipped = 0
        pending: list[dict] = []
        for section in sections:
            chapter = by_number.get(section["chapter_number"])
            if chapter is None:
                pending.append(section)
                continue
            current = (
                supabase.table("workbook_sections")
                .select("id")
                .eq("chapter_id", chapter["id"])
                .eq("number", section["number"])
                .execute()
                .data
            )
            if current:
                skipped += 1
                continue
            made += 1
            if args.execute:
                supabase.table("workbook_sections").insert(
                    {"chapter_id": chapter["id"], "number": section["number"], "title": section["title"]}
                ).execute()
        note = f", {len(pending)} unresolvable until chapters exist" if pending else ""
        print(f"  sections: {made} to create, {skipped} already present{note}")

        if args.execute:
            live_ch = (
                supabase.table("workbook_chapters")
                .select("id,number,title")
                .eq("subject_id", subject_id)
                .execute()
                .data
            )
            total = 0
            for chapter in sorted(live_ch, key=lambda c: c["number"]):
                n = (
                    supabase.table("workbook_sections")
                    .select("id", count="exact")
                    .eq("chapter_id", chapter["id"])
                    .limit(1)
                    .execute()
                    .count
                )
                total += n
                print(f"    {chapter['number']:>2}. {chapter['title']:<52} {n} sections")
            print(f"    -> {len(live_ch)} chapters / {total} sections live")
            if len(live_ch) != len(chapters) or total != len(sections):
                print("    !! live counts do not match the migration")
                exit_code = 1
        print()

    if not args.execute:
        print("Dry run only. Re-run with --execute to write.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
