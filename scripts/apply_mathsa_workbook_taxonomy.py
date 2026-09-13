#!/usr/bin/env python3
"""
Apply the Mathematics A (4MA1) Higher-tier workbook taxonomy to the database.

Migration 20 is a pure INSERT into `workbook_chapters` and `workbook_sections`,
both of which already exist from migration 12. There is no DDL, so it can go in
over PostgREST with the service-role key rather than being pasted into the
Supabase SQL editor -- the same route migrations 15, 18 and 19 took.

The rows are read OUT OF THE MIGRATION FILE rather than restated here. A second
copy of a taxonomy is a second thing to keep in sync, and `--check-taxonomy` in
the classifiers already diffs against the migration, so the migration stays the
one source of truth.

    python scripts/apply_mathsa_workbook_taxonomy.py            # dry run
    python scripts/apply_mathsa_workbook_taxonomy.py --execute

Idempotent: existing chapters and sections are matched on (subject, number) and
left alone. It never updates or deletes, so it cannot disturb a taxonomy that
questions have already been classified against.

Separate from apply_s1_p4_workbook_taxonomy.py on purpose -- every subject gets
its own script rather than growing a shared one.
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

SUBJECT_CODE = "4MA1"
MIGRATION = MIGRATIONS_DIR / "20_workbook_mathsa_taxonomy.sql"

# What the migration is expected to hold. Stated so a silent truncation of the
# VALUES block -- a lost trailing row, say -- fails here instead of quietly
# shipping a book with a missing heading.
EXPECT_CHAPTERS = 6
EXPECT_SECTIONS = 39

# (number, 'title', 'spec_ref') -- the chapter VALUES rows.
CHAPTER_RE = re.compile(r"^\s*\((\d+),\s*'((?:[^']|'')+)',\s*'((?:[^']|'')+)'\)", re.M)
# (chapter_number, section_number, 'title') -- the section VALUES rows.
SECTION_RE = re.compile(r"^\s*\((\d+),\s*(\d+),\s*'((?:[^']|'')+)'\)", re.M)


def unquote(value: str) -> str:
    """SQL escapes a literal quote by doubling it: 'Pythagoras'' theorem'."""
    return value.replace("''", "'")


def parse_migration(path: Path) -> tuple[list[dict], list[dict]]:
    """Pull the chapter and section VALUES rows out of the taxonomy migration."""
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
        raise SystemExit(
            f"{path.name}: parsed {len(chapters)} chapters / {len(sections)} sections"
        )
    if len(chapters) != EXPECT_CHAPTERS or len(sections) != EXPECT_SECTIONS:
        raise SystemExit(
            f"{path.name}: expected {EXPECT_CHAPTERS} chapters / {EXPECT_SECTIONS} "
            f"sections, parsed {len(chapters)} / {len(sections)}"
        )

    # Contiguity is what the book's contents page depends on; a gap here would
    # print as a missing heading rather than as an error.
    if [c["number"] for c in chapters] != list(range(1, len(chapters) + 1)):
        raise SystemExit(f"{path.name}: chapter numbers are not contiguous from 1")
    for chapter in chapters:
        nums = sorted(s["number"] for s in sections if s["chapter_number"] == chapter["number"])
        if nums != list(range(1, len(nums) + 1)):
            raise SystemExit(
                f"{path.name}: chapter {chapter['number']} sections not contiguous: {nums}"
            )
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
        raise SystemExit(
            "NEXT_PUBLIC_SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing from .env.local"
        )
    supabase = create_client(url, key)

    mode = "EXECUTE" if args.execute else "DRY RUN"
    print(f"=== Maths A ({SUBJECT_CODE}) workbook taxonomy  [{mode}] ===\n")

    exit_code = 0
    chapters, sections = parse_migration(MIGRATION)
    print(f"{SUBJECT_CODE}  ({MIGRATION.name})")
    print(f"  parsed {len(chapters)} chapters / {len(sections)} sections")

    found = supabase.table("subjects").select("id,name").eq("code", SUBJECT_CODE).execute().data
    if not found:
        raise SystemExit(f"  !! no subject row with code {SUBJECT_CODE}")
    subject_id = found[0]["id"]
    print(f"  subject {found[0]['name']}  {subject_id}")

    # A taxonomy change under already-classified questions would silently
    # repoint them, so say so rather than let it pass unremarked. Nothing here
    # updates existing rows, but the check documents the invariant.
    existing_q = (
        supabase.table("workbook_questions")
        .select("id", count="exact")
        .eq("subject_id", subject_id)
        .limit(1)
        .execute()
    )
    if existing_q.count:
        print(
            f"  note: {existing_q.count} questions already reference this subject;"
            f" only missing chapters/sections will be added"
        )

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

    # Sections are keyed on (chapter_id, number); without the chapter rows a
    # dry run has nothing to resolve against, which is expected.
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
                {
                    "chapter_id": chapter["id"],
                    "number": section["number"],
                    "title": section["title"],
                }
            ).execute()
    note = f", {len(pending)} unresolvable until chapters exist" if pending else ""
    print(f"  sections: {made} to create, {skipped} already present{note}")

    if args.execute:
        # Read the live tree back rather than trusting the counts above -- the
        # Maths B load taught that the tooling reports success while something
        # is wrong, so the artifact is what gets checked.
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
            print(f"    {chapter['number']:>2}. {chapter['title']:<42} {n} sections")
        print(f"    -> {len(live_ch)} chapters / {total} sections live")
        if len(live_ch) != len(chapters) or total != len(sections):
            print("    !! live counts do not match the migration")
            exit_code = 1

        # The other subjects must be untouched by this run.
        for other in ("4PM1", "4MB1", "WST01", "WMA14"):
            row = supabase.table("subjects").select("id").eq("code", other).execute().data
            if not row:
                continue
            n = (
                supabase.table("workbook_chapters")
                .select("id", count="exact")
                .eq("subject_id", row[0]["id"])
                .limit(1)
                .execute()
                .count
            )
            print(f"    {other}: {n} chapters (unchanged)")

    print()
    if not args.execute:
        print("Dry run only. Re-run with --execute to write.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
