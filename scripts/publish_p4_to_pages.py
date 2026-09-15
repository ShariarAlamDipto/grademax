#!/usr/bin/env python3
"""
Publish verified IAL Pure Mathematics 4 (WMA14) workbook questions into the `topics`
and `pages` layer, so the test builder and worksheet generator can use them.

    python scripts/publish_p4_to_pages.py                        # dry run
    python scripts/publish_p4_to_pages.py --topics-only --execute
    python scripts/publish_p4_to_pages.py --execute
    python scripts/publish_p4_to_pages.py --execute --include-unverified

`pages` has NO row-level protection on verification -- anything written there is
immediately live in the test builder. So this publishes only questions a human
has signed off in `/admin/workbook/verify` unless `--include-unverified` is
passed deliberately. See `lib/ial_pages_publish.py`.

`--topics-only` writes the topic vocabulary without any questions. That is safe
to run now: topics come from the taxonomy migration, not from the classifier, so
nothing about them is unreviewed.
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

from lib.ial_classify import latest_section_migration, sections_from_migration  # noqa: E402
from lib.ial_pages_publish import build_pages, build_topics, fetch_all  # noqa: E402
from lib.ial_workbook_load import with_retry  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = REPO_ROOT / "data" / "workbook" / "p4_questions.json"

UNIT = "P4"
SUBJECT_CODE = "WMA14"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--topics-only", action="store_true")
    parser.add_argument(
        "--include-unverified",
        action="store_true",
        help="publish every classification, reviewed or not",
    )
    parser.add_argument(
        "--agreed-only",
        action="store_true",
        help=(
            "publish unverified questions ONLY where both classifier families "
            "agreed on the section; holds back disputed and same-chapter ones"
        ),
    )
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env.local")
    supabase = create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    )

    mode = "EXECUTE" if args.execute else "DRY RUN"
    print(f"=== {UNIT} ({SUBJECT_CODE}) -> topics + pages  [{mode}] ===\n")

    subject = supabase.table("subjects").select("id,name").eq("code", SUBJECT_CODE).execute().data
    if not subject:
        raise SystemExit(f"no subject row for {SUBJECT_CODE}")
    subject_id = subject[0]["id"]

    taxonomy = sections_from_migration(latest_section_migration(SUBJECT_CODE))
    wanted = build_topics(taxonomy, subject_id)

    existing_topics = fetch_all(
        lambda o, l: supabase.table("topics")
        .select("id,code")
        .eq("subject_id", subject_id)
        .range(o, o + l - 1)
    )
    have = {t["code"] for t in existing_topics}
    to_create = [t for t in wanted if t["code"] not in have]

    print(f"topics       : {len(wanted)} in taxonomy, {len(have)} already present, "
          f"{len(to_create)} to create")
    if args.execute and to_create:
        with_retry(
            lambda: supabase.table("topics").insert(to_create).execute(), "insert topics"
        )
        print(f"               created {len(to_create)}")

    if args.topics_only:
        if not args.execute:
            print("\nDry run only. Re-run with --execute to write the topics.")
        return 0

    # ── questions ────────────────────────────────────────────────────────────
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))

    rows = fetch_all(
        lambda o, l: supabase.table("workbook_questions")
        .select(
            "slug,verified_at,section_id,secondary_section_ids,"
            "qp_pdf_url,ms_pdf_url,review_priority"
        )
        .eq("subject_id", subject_id)
        .range(o, o + l - 1)
    )
    human_verified = {r["slug"] for r in rows if r["verified_at"]}
    verified_slugs = set(human_verified)

    # --agreed-only treats two independent model families agreeing as evidence
    # good enough to publish, which is weaker than a human check but much
    # stronger than a single opinion. Disputed and same_chapter rows are held
    # back for the verify queue.
    if args.agreed_only:
        agreed = {r["slug"] for r in rows if r["review_priority"] == "agreed"}
        verified_slugs = verified_slugs | agreed
        print(f"--agreed-only : {len(agreed)} questions where both models agreed")
    by_slug = {r["slug"]: r for r in rows}

    # Section ids -> codes, so the DB's verified assignment is what gets
    # published rather than the classifier file, which a human may have
    # overridden.
    chapters = fetch_all(
        lambda o, l: supabase.table("workbook_chapters")
        .select("id,number")
        .eq("subject_id", subject_id)
        .range(o, o + l - 1)
    )
    code_of_section: dict[str, str] = {}
    for chapter in chapters:
        for section in fetch_all(
            lambda o, l, cid=chapter["id"]: supabase.table("workbook_sections")
            .select("id,number")
            .eq("chapter_id", cid)
            .range(o, o + l - 1)
        ):
            code_of_section[section["id"]] = f"{chapter['number']}.{section['number']}"

    section_code_of = {
        slug: code_of_section.get(row["section_id"])
        for slug, row in by_slug.items()
        if row["section_id"]
    }
    secondary_codes_of = {
        slug: [code_of_section[s] for s in (row["secondary_section_ids"] or []) if s in code_of_section]
        for slug, row in by_slug.items()
    }

    papers = fetch_all(
        lambda o, l: supabase.table("papers")
        .select("id,year,season,paper_number")
        .eq("subject_id", subject_id)
        .range(o, o + l - 1)
    )
    paper_id_of = {f"{p['year']}_{p['season']}": p["id"] for p in papers}

    for question in questions:
        row = by_slug.get(question["slug"], {})
        question["_qp_url"] = row.get("qp_pdf_url")
        question["_ms_url"] = row.get("ms_pdf_url")

    plan = build_pages(
        questions,
        section_code_of,
        secondary_codes_of,
        verified_slugs,
        paper_id_of,
        args.include_unverified,
    )

    print(
        f"workbook rows: {len(rows)}  "
        f"human-verified: {len(human_verified)}  publishable: {len(verified_slugs)}"
    )
    print(f"pages to write: {len(plan.pages)}")
    print(f"held back     : {plan.skipped_unverified}")
    if plan.missing_papers:
        print(f"  !! no papers row for: {plan.missing_papers}")

    if not plan.pages:
        print(
            "\nNothing to publish. Verify questions at /admin/workbook/verify first,\n"
            "or pass --include-unverified to expose unreviewed classifications."
        )
        return 0

    if args.include_unverified:
        unreviewed = len(plan.pages) - len(verified_slugs & {q["slug"] for q in questions})
        print(f"\n  !! --include-unverified: {max(unreviewed, 0)} unreviewed rows will go live")

    if args.execute:
        # Replace this subject's pages rather than accumulating duplicates: the
        # pages layer is regenerable by design.
        paper_ids = list(paper_id_of.values())
        for paper_id in paper_ids:
            with_retry(
                lambda p=paper_id: supabase.table("pages").delete().eq("paper_id", p).execute(),
                f"clear pages for {paper_id}",
            )
        for start in range(0, len(plan.pages), 100):
            chunk = plan.pages[start : start + 100]
            with_retry(
                lambda c=chunk: supabase.table("pages").insert(c).execute(), "insert pages"
            )
        live = fetch_all(
            lambda o, l: supabase.table("pages")
            .select("id")
            .in_("paper_id", paper_ids)
            .range(o, o + l - 1)
        )
        print(f"\nlive pages   : {len(live)}")
        if len(live) != len(plan.pages):
            print(f"  !! expected {len(plan.pages)}")
            return 1
    else:
        print("\nDry run only. Re-run with --execute to write.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
