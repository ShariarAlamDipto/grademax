#!/usr/bin/env python3
"""
Phase 4 for the IAL Statistics 1 (WST01) workbook: upload the segment PDFs to
R2 and load the question rows into Postgres.

    python scripts/load_s1_workbook_to_db.py                  # dry run
    python scripts/load_s1_workbook_to_db.py --execute
    python scripts/load_s1_workbook_to_db.py --execute --skip-upload

`verified_at` is left NULL on new rows, and the RLS policy on
`workbook_questions` exposes only verified rows publicly, so nothing reaches a
student until a human signs it off in `/admin/workbook/verify`.

A row a human HAS signed off is authoritative: a re-run refreshes its mechanical
fields but routes the classifier's newer opinion to `proposed_section_id` rather
than overwriting the section. See `lib/ial_workbook_load.py` for why, and for
the four failures the 4MB1 load hit that are guarded there.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.ial_workbook_load import (  # noqa: E402
    fetch_all,
    preflight,
    with_retry,
    public_url,
    r2_client,
    sync_archetypes,
    upload_pdf,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SEGMENT_DIR = REPO_ROOT / "data" / "workbook" / "s1"
QUESTIONS_PATH = REPO_ROOT / "data" / "workbook" / "s1_questions.json"
CLASSIFICATIONS_PATH = REPO_ROOT / "data" / "workbook" / "s1_classifications.json"
ARCHETYPES_PATH = REPO_ROOT / "data" / "workbook" / "s1_archetypes.json"

UNIT = "S1"
SUBJECT_CODE = "WST01"
R2_PREFIX = "workbook/s1"


def build_rows(
    questions: list[dict],
    classifications: dict[str, dict],
    archetype_of: dict[str, tuple[str, str]],
    section_id_of: dict[str, str],
    subject_id: str,
    archetype_ids: dict[tuple[str, str], str],
) -> list[dict]:
    """
    Assemble one row per question, in print order.

    Print order inside a section runs archetype (cheapest first) -> marks
    ascending -> chronological, so a student meets each shape at its simplest
    and then in the order the shapes were actually examined.
    """
    by_section: dict[str, list[dict]] = {}
    for question in questions:
        entry = classifications.get(question["slug"])
        if not entry or not entry.get("section"):
            continue
        by_section.setdefault(entry["section"], []).append(question)

    rows: list[dict] = []
    for section_code, members in by_section.items():
        section_id = section_id_of[section_code]

        def sort_key(q: dict) -> tuple:
            key = archetype_of.get(q["slug"])
            cheapest = archetype_ids.get(key, "") if key else ""
            label = key[1] if key else ""
            return (
                q.get("_archetype_min_marks", 999),
                label,
                q["marks"],
                q["year"],
                q["season"],
                q["source_question_number"],
            )

        for ordinal, question in enumerate(sorted(members, key=sort_key), start=1):
            entry = classifications[question["slug"]]
            key = archetype_of.get(question["slug"])
            paper_key = question["source_paper_key"]
            number = question["source_question_number"]

            qp_key = f"{R2_PREFIX}/{paper_key}/q{number}.pdf"
            ms_key = f"{R2_PREFIX}/{paper_key}/ms/q{number}.pdf"

            rows.append(
                {
                    "slug": question["slug"],
                    "subject_id": subject_id,
                    "section_id": section_id,
                    "archetype_id": archetype_ids.get(key) if key else None,
                    "ordinal_in_chapter": ordinal,
                    "source_paper_key": paper_key,
                    "source_question_number": number,
                    "marks": question["marks"],
                    "difficulty": question["difficulty"],
                    "sub_parts": question["sub_parts"] or None,
                    "qp_pdf_url": public_url(qp_key),
                    "ms_pdf_url": public_url(ms_key) if question["has_markscheme"] else None,
                    "stem": question["stem"][:8000],
                    "text_status": question["text_status"],
                    "secondary_section_ids": [
                        section_id_of[code]
                        for code in entry.get("secondary_sections", [])
                        if code in section_id_of
                    ],
                    "review_priority": entry.get("review_priority"),
                    "proposed_section_id": section_id_of.get(entry.get("proposed_section") or ""),
                    "_qp_local": SEGMENT_DIR / paper_key / "questions" / f"q{number}.pdf",
                    "_ms_local": (
                        SEGMENT_DIR / paper_key / "markschemes" / f"q{number}.pdf"
                        if question["has_markscheme"]
                        else None
                    ),
                    "_qp_key": qp_key,
                    "_ms_key": ms_key,
                }
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--skip-upload", action="store_true", help="rows only, no R2")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env.local")
    supabase = create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    )

    mode = "EXECUTE" if args.execute else "DRY RUN"
    print(f"=== {UNIT} ({SUBJECT_CODE}) workbook load  [{mode}] ===\n")

    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    classifications = {
        row["slug"]: row
        for row in json.loads(CLASSIFICATIONS_PATH.read_text(encoding="utf-8"))
    }
    archetypes = json.loads(ARCHETYPES_PATH.read_text(encoding="utf-8"))

    subject = supabase.table("subjects").select("id,name").eq("code", SUBJECT_CODE).execute().data
    if not subject:
        raise SystemExit(f"no subject row for {SUBJECT_CODE}")
    subject_id = subject[0]["id"]
    print(f"subject      : {subject[0]['name']}  {subject_id}")

    chapters = fetch_all(
        lambda o, l: supabase.table("workbook_chapters")
        .select("id,number")
        .eq("subject_id", subject_id)
        .range(o, o + l - 1)
    )
    section_id_of: dict[str, str] = {}
    for chapter in chapters:
        sections = fetch_all(
            lambda o, l, cid=chapter["id"]: supabase.table("workbook_sections")
            .select("id,number")
            .eq("chapter_id", cid)
            .range(o, o + l - 1)
        )
        for section in sections:
            section_id_of[f"{chapter['number']}.{section['number']}"] = section["id"]
    print(f"taxonomy     : {len(chapters)} chapters, {len(section_id_of)} sections")

    archetype_ids, arch_stats = sync_archetypes(
        supabase, archetypes, section_id_of, args.execute
    )
    print(f"archetypes   : {arch_stats['created']} created, {arch_stats['reused']} reused")

    archetype_of: dict[str, tuple[str, str]] = {}
    min_marks_of: dict[str, int] = {}
    for archetype in archetypes:
        section_id = section_id_of.get(archetype["section"])
        if section_id is None:
            continue
        for slug in archetype["slugs"]:
            archetype_of[slug] = (section_id, archetype["label"])
            min_marks_of[slug] = archetype["min_marks"]
    for question in questions:
        question["_archetype_min_marks"] = min_marks_of.get(question["slug"], 999)

    rows = build_rows(
        questions, classifications, archetype_of, section_id_of, subject_id, archetype_ids
    )
    print(f"rows built   : {len(rows)}")

    # Pre-flight runs in BOTH modes. A dry run never attempts an insert, so it
    # would otherwise never meet a CHECK constraint.
    checked = preflight([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows])
    print(f"pre-flight   : {len(checked.ok)} ok, {len(checked.problems)} problems")
    for problem in checked.problems[:20]:
        print(f"    !! {problem}")
    if not checked.passed:
        print("\nABORTED before writing anything. Fix the rows above and re-run.")
        return 1

    existing = fetch_all(
        lambda o, l: supabase.table("workbook_questions")
        .select("id,slug,source_paper_key,source_question_number,verified_at")
        .eq("subject_id", subject_id)
        .range(o, o + l - 1)
    )
    existing_by_key = {
        (row["source_paper_key"], row["source_question_number"]): row for row in existing
    }
    verified = sum(1 for row in existing if row["verified_at"])
    print(f"already in DB: {len(existing)} ({verified} human-verified, protected)")

    client = None
    bucket = None
    if args.execute and not args.skip_upload:
        client = r2_client()
        bucket = os.environ["R2_BUCKET_NAME"]

    created = updated = protected = uploaded = 0

    for row in rows:
        qp_local = row.pop("_qp_local")
        ms_local = row.pop("_ms_local")
        qp_key = row.pop("_qp_key")
        ms_key = row.pop("_ms_key")

        if client is not None:
            if qp_local.exists():
                upload_pdf(client, bucket, qp_local, qp_key)
                uploaded += 1
            if ms_local is not None and ms_local.exists():
                upload_pdf(client, bucket, ms_local, ms_key)
                uploaded += 1

        key = (row["source_paper_key"], row["source_question_number"])
        current = existing_by_key.get(key)

        if current is None:
            created += 1
            if args.execute:
                with_retry(
                    lambda r=row: supabase.table("workbook_questions").insert(r).execute(),
                    f"insert {row['slug']}",
                )
            continue

        # A verified row keeps its human-assigned section; only mechanical
        # fields are refreshed and the newer opinion goes to proposed_section_id.
        payload = dict(row)
        payload["slug"] = current["slug"]  # slugs are issued once
        if current["verified_at"]:
            protected += 1
            payload["proposed_section_id"] = row["section_id"]
            for field in ("section_id", "secondary_section_ids", "archetype_id"):
                payload.pop(field, None)
        else:
            updated += 1

        if args.execute:
            with_retry(
                lambda p=payload, i=current["id"]: supabase.table("workbook_questions")
                .update(p)
                .eq("id", i)
                .execute(),
                f"update {payload['slug']}",
            )

    print(f"\ncreate       : {created}")
    print(f"update       : {updated}")
    print(f"protected    : {protected} (verified rows, section left alone)")
    if args.execute and not args.skip_upload:
        print(f"uploaded     : {uploaded} PDFs to {R2_PREFIX}/")

    if args.execute:
        live = fetch_all(
            lambda o, l: supabase.table("workbook_questions")
            .select("id,verified_at,review_priority")
            .eq("subject_id", subject_id)
            .range(o, o + l - 1)
        )
        priorities: dict[str, int] = {}
        for item in live:
            priorities[item["review_priority"]] = priorities.get(item["review_priority"], 0) + 1
        print(f"\nlive rows    : {len(live)}")
        print(f"review queue : {priorities}")
        print(f"verified     : {sum(1 for i in live if i['verified_at'])}")
        if len(live) != len(rows):
            print(f"  !! expected {len(rows)} rows, found {len(live)}")
            return 1
    else:
        print("\nDry run only. Re-run with --execute to write.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
