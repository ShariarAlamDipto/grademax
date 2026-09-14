"""
Load the classified Maths A (4MA1) Higher workbook into R2 and the database.

Takes the Phase 1-3 output (clean segments, marks, sections, archetypes) and
turns it into the actual book: uploads every question and mark scheme PDF to R2,
creates the archetype rows, and writes `workbook_questions` with stable slugs
and a fixed print order.

STABLE SLUGS
------------
Each question gets `MA.CH04.S09.Q021` -- chapter, section, ordinal in chapter.
`workbook_attempts` references the row this creates, forever. That is the whole
reason this table exists rather than pointing homework at `pages.id`, which gets
deleted and recreated every time segmentation improves.

So slugs are assigned ONCE. Re-running this script updates a question in place
(matched on source paper + question number) and never renumbers an existing one.

PRINT ORDER
-----------
Within a chapter: section, then archetype cluster, then marks ascending, then
chronologically. Clusters are ordered by their cheapest question, so a section
opens with short single-skill questions and closes with full synoptic ones --
and the four years' worth of one recurring shape sit together, which is the
point of clustering them at all.

VERIFICATION
------------
`verified_at` is left NULL on new rows. The RLS policy on `workbook_questions`
only exposes verified rows publicly, so nothing reaches a student until Phase 4
signs it off.

A row that a human has already signed off is TREATED AS AUTHORITATIVE. Re-running
this script refreshes its mechanical fields (marks, PDFs, stem) but never touches
`section_id`, `secondary_section_ids` or `archetype_id` -- the classifier's newer
opinion goes to `proposed_section_id` instead, where the review UI can surface it.

Without that split a re-run would silently revert every manual reassignment while
leaving `verified_at` set, so the question would look signed off while carrying
the section a human had already rejected. That is worse than losing the work
outright, because nothing about it looks wrong.

USAGE
-----
    python scripts/load_mathsa_workbook_to_db.py            # dry run
    python scripts/load_mathsa_workbook_to_db.py --execute
    python scripts/load_mathsa_workbook_to_db.py --execute --skip-upload
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from supabase import create_client

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKBOOK_DIR = REPO_ROOT / "data" / "workbook"
CLASSIFICATIONS_PATH = WORKBOOK_DIR / "mathsa_classifications.json"
ARCHETYPES_PATH = WORKBOOK_DIR / "mathsa_archetypes.json"

SUBJECT_CODE = "4MA1"
SLUG_PREFIX = "MA"
# Separate prefix from `subjects/...`, which is the regenerable ingest layer.
# The workbook is a curated artifact and must not be clobbered by a re-ingest.
R2_PREFIX = "workbook/mathsa"

# Session ordering within a year, for the chronological tiebreak.
SESSION_ORDER = {"specimen": 0, "jan": 1, "may-jun": 2, "oct-nov": 3}

# What the column's CHECK constraint actually permits (migration 12).
#
# The enricher carries a fourth status, `partially_garbled` (12 stems here),
# for text whose second CMap variant leaves some capitals wrong. The database
# has never heard of it. On Maths B that inserted 295 rows and then aborted on
# the first one carrying it -- a failure the dry run could not predict, because
# a dry run never attempts an insert and so never meets a constraint. Hence the
# pre-flight below runs in dry-run mode too.
#
# It maps to `repaired`, which is true: the text was repaired, just not
# perfectly. The precise status stays in mathsa_questions.json, which is where
# it is used, and the book prints the PDF rather than the stem in any case.
DB_TEXT_STATUS = {"ok", "repaired", "needs_vision"}
TEXT_STATUS_FALLBACK = {"partially_garbled": "repaired"}


def db_text_status(status: str | None) -> str | None:
    if status is None or status in DB_TEXT_STATUS:
        return status
    return TEXT_STATUS_FALLBACK.get(status, "repaired")


def fetch_all_rows(
    supabase, table: str, columns: str, subject_id: str, page_size: int = 500
) -> list[dict]:
    """
    Every row for this subject, read in explicit pages.

    PostgREST caps a response at 1000 rows and says nothing about it, so a
    corpus of 1042 comes back looking like 1000. Paging is cheap; a silently
    truncated read is not -- it makes existing questions look new.
    """
    rows: list[dict] = []
    start = 0
    while True:
        page = (
            supabase.table(table)
            .select(columns)
            .eq("subject_id", subject_id)
            .range(start, start + page_size - 1)
            .execute()
            .data
        )
        rows.extend(page)
        if len(page) < page_size:
            return rows
        start += page_size


def session_rank(question: dict) -> tuple[int, int, str]:
    return (
        question["year"],
        SESSION_ORDER.get(question["season"], 9),
        question["paper_number"],
    )


def r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def upload_pdf(client, bucket: str, local_path: Path, key: str) -> str:
    """Upload one PDF unless it is already there. Returns the public URL."""
    public_url = f"{os.environ['NEXT_PUBLIC_R2_PUBLIC_URL'].rstrip('/')}/{key}"
    try:
        client.head_object(Bucket=bucket, Key=key)
        return public_url  # already uploaded; PDFs are immutable
    except ClientError as error:
        if error.response["Error"]["Code"] not in ("404", "NoSuchKey", "403"):
            raise

    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=local_path.read_bytes(),
        ContentType="application/pdf",
        CacheControl="public, max-age=31536000, immutable",
    )
    return public_url


def build_print_order(questions: list[dict], cluster_of: dict[str, str]) -> list[dict]:
    """
    Order questions within each chapter and stamp ordinal_in_chapter.

    Returns the questions in book order, each with `_section`, `_ordinal` set.
    """
    by_chapter: dict[str, list[dict]] = defaultdict(list)
    for question in questions:
        by_chapter[question["_section"].split(".")[0]].append(question)

    ordered: list[dict] = []

    for chapter in sorted(by_chapter, key=int):
        chapter_questions = by_chapter[chapter]

        # Cheapest question in a cluster decides where the cluster sits, so a
        # section builds from short single-skill work up to synoptic questions.
        cluster_floor: dict[str, int] = {}
        for question in chapter_questions:
            key = cluster_of.get(question["_id"], question["_id"])
            cluster_floor[key] = min(cluster_floor.get(key, 999), question["marks"])

        def sort_key(question: dict):
            cluster = cluster_of.get(question["_id"], question["_id"])
            return (
                int(question["_section"].split(".")[1]),  # section within chapter
                cluster_floor[cluster],                    # cluster position
                cluster,                                   # keep a cluster together
                question["marks"],                         # then easiest first
                session_rank(question),                    # then chronological
            )

        for ordinal, question in enumerate(sorted(chapter_questions, key=sort_key), 1):
            question["_ordinal"] = ordinal
            ordered.append(question)

    return ordered


def main() -> int:
    load_dotenv(REPO_ROOT / ".env.local")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="upload and write to the database")
    parser.add_argument("--skip-upload", action="store_true", help="assume PDFs are already on R2")
    args = parser.parse_args()

    data = json.loads(CLASSIFICATIONS_PATH.read_text(encoding="utf-8"))
    clusters = json.loads(ARCHETYPES_PATH.read_text(encoding="utf-8"))

    # question id -> archetype label (its cluster)
    cluster_of: dict[str, str] = {}
    for cluster in clusters:
        for question_id in cluster["question_ids"]:
            cluster_of[question_id] = f"{cluster['section']}|{cluster['label']}"

    classified = []
    unclassified = []
    for question in data:
        question["_id"] = f"{question['paper_key']}:{question['question_number']}"
        if question.get("classification"):
            question["_section"] = question["classification"]["primary"]
            classified.append(question)
        else:
            unclassified.append(question["_id"])

    print(f"{'=' * 74}\nLOAD MATHS B WORKBOOK\n{'=' * 74}")
    print(f"  classified   : {len(classified)}")
    if unclassified:
        print(f"  NOT loaded   : {len(unclassified)} unclassified -> {', '.join(unclassified[:4])}...")
        print("                 (re-run classification, then re-run this script)")

    supabase = create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    )

    subject = supabase.table("subjects").select("id").eq("code", SUBJECT_CODE).single().execute().data
    subject_id = subject["id"]

    chapters = supabase.table("workbook_chapters").select("id,number").eq(
        "subject_id", subject_id
    ).execute().data
    chapter_id_by_number = {str(c["number"]): c["id"] for c in chapters}

    # Scoped to THIS subject's chapters. An unfiltered read returns every
    # subject's sections (167 across the five books today) and relies on the
    # guard below to discard the rest -- which works only while the total stays
    # under PostgREST's silent 1000-row cap. Filtering keeps it correct however
    # many subjects land later.
    number_by_chapter_id = {c["id"]: str(c["number"]) for c in chapters}
    sections = (
        supabase.table("workbook_sections")
        .select("id,chapter_id,number")
        .in_("chapter_id", list(number_by_chapter_id))
        .execute()
        .data
    )
    section_id_by_code = {
        f"{number_by_chapter_id[s['chapter_id']]}.{s['number']}": s["id"]
        for s in sections
        if s["chapter_id"] in number_by_chapter_id
    }
    print(f"  sections     : {len(section_id_by_code)} in the database")

    bad = sorted({q["_section"] for q in classified if q["_section"] not in section_id_by_code})
    if bad:
        print(f"\n  ABORT: {len(bad)} section code(s) not in the database: {bad}")
        print("  Apply the newest section migration (20_workbook_mathsa_taxonomy.sql).")
        return 1

    ordered = build_print_order(classified, cluster_of)

    # Fail before writing, not 295 rows in. Everything the database constrains
    # and this script can check locally goes here -- a dry run that reports
    # "would write 1046 rows" and then dies a quarter of the way through is
    # worse than useless, because it was believed.
    problems: list[str] = []
    for question in ordered:
        mapped = db_text_status(question["text_status"])
        if mapped is not None and mapped not in DB_TEXT_STATUS:
            problems.append(f"{question['_id']}: text_status {question['text_status']!r}")
        if question["_section"] not in section_id_by_code:
            problems.append(f"{question['_id']}: section {question['_section']} not in the database")
        if not isinstance(question["marks"], int) or question["marks"] <= 0:
            problems.append(f"{question['_id']}: marks {question['marks']!r}")
    raw_statuses = {q["text_status"] for q in ordered}
    unmapped = raw_statuses - DB_TEXT_STATUS - set(TEXT_STATUS_FALLBACK) - {None}
    if unmapped:
        problems.append(f"text_status values with no database mapping: {sorted(unmapped)}")

    if problems:
        print(f"\n  ABORT: {len(problems)} row(s) would violate a database constraint:")
        for problem in problems[:15]:
            print(f"    {problem}")
        if len(problems) > 15:
            print(f"    ... and {len(problems) - 15} more")
        return 1
    print(f"  pre-flight   : OK ({len(ordered)} rows check out against the schema)")

    # Existing rows keep their slug and ordinal -- attempts reference them.
    # `verified_at` decides whether this script may overwrite the section.
    #
    # PAGED, and that is not optional here. PostgREST silently caps a response
    # at 1000 rows, and this corpus is 1042: an unpaged read would return the
    # first 1000, leave 42 existing rows looking new, and on a re-run either
    # collide with the unique key or hand an already-referenced question a
    # second slug. Maths B sat one row the other side of the same cliff.
    existing = fetch_all_rows(
        supabase,
        "workbook_questions",
        "id,slug,source_paper_key,source_question_number,ordinal_in_chapter,verified_at",
        subject_id,
    )
    existing_by_source = {
        (row["source_paper_key"], row["source_question_number"]): row for row in existing
    }
    already_verified = sum(1 for row in existing if row["verified_at"])
    print(f"  already in DB: {len(existing)}  ({already_verified} human-verified, protected)")

    papers = supabase.table("papers").select("id,year,season,paper_number").eq(
        "subject_id", subject_id
    ).execute().data
    paper_id_by_key = {
        f"{p['year']}_{p['season']}_{p['paper_number']}": p["id"] for p in papers
    }

    if not args.execute:
        print("\n  Print order preview (first question of each chapter):")
        seen = set()
        for question in ordered:
            chapter = question["_section"].split(".")[0]
            if chapter in seen:
                continue
            seen.add(chapter)
            slug = f"{SLUG_PREFIX}.CH{int(chapter):02d}.S{int(question['_section'].split('.')[1]):02d}.Q{question['_ordinal']:03d}"
            print(f"    {slug}  {question['_id']:<22} {question['marks']:>2}m  {cluster_of.get(question['_id'],'-').split('|')[-1][:36]}")
        print(f"\n  Would upload {sum(1 for q in ordered) + sum(1 for q in ordered if q['has_markscheme'])} PDFs")
        print(f"  Would write  {len(ordered)} workbook_questions rows")
        print("\n  Dry run -- nothing uploaded or written. Re-run with --execute.")
        return 0

    client = None if args.skip_upload else r2_client()
    bucket = os.environ["R2_BUCKET_NAME"]

    # ── Archetypes ───────────────────────────────────────────────────────────
    # There is no unique constraint on (section_id, label), so a blind insert
    # would create a fresh duplicate set on every run and repoint every question
    # at it, orphaning the previous rows. Match on the pair instead.
    section_ids = [sid for sid in section_id_by_code.values()]
    prior = supabase.table("workbook_archetypes").select(
        "id,section_id,label"
    ).in_("section_id", section_ids).execute().data
    archetype_id_by_pair = {(row["section_id"], row["label"]): row["id"] for row in prior}

    archetype_id_by_key: dict[str, str] = {}
    created = 0
    for cluster in clusters:
        key = f"{cluster['section']}|{cluster['label']}"
        section_id = section_id_by_code.get(cluster["section"])
        existing_id = archetype_id_by_pair.get((section_id, cluster["label"]))
        if existing_id:
            archetype_id_by_key[key] = existing_id
            continue
        row = supabase.table("workbook_archetypes").insert(
            {"section_id": section_id, "label": cluster["label"],
             "description": f"{cluster['size']} question(s) in section {cluster['section']}"}
        ).execute().data[0]
        archetype_id_by_key[key] = row["id"]
        # Record it immediately. Clustering can emit two clusters with the same
        # (section, label) -- 16 of them here, "ratio and proportion" in 1.2
        # seven times over -- and without this the map is only consulted for
        # rows that existed BEFORE the run, so each one inserts again. That is
        # what produced "409 created, -26 reused": 409 inserts collapsing into
        # 383 distinct keys, the negative count being the giveaway.
        archetype_id_by_pair[(section_id, cluster["label"])] = row["id"]
        created += 1
    print(f"  archetypes: {created} created, {len(archetype_id_by_key) - created} reused "
          f"({len(clusters)} clusters)")

    # ── Questions ────────────────────────────────────────────────────────────
    uploaded = inserted = updated = protected = 0

    for question in ordered:
        chapter, section_number = question["_section"].split(".")
        source_key = (question["paper_key"], question["question_number"])
        previous = existing_by_source.get(source_key)

        qp_url = ms_url = None
        if args.skip_upload:
            base = os.environ["NEXT_PUBLIC_R2_PUBLIC_URL"].rstrip("/")
            qp_url = f"{base}/{R2_PREFIX}/{question['paper_key']}/q{question['question_number']}.pdf"
            if question["has_markscheme"]:
                ms_url = f"{base}/{R2_PREFIX}/{question['paper_key']}/q{question['question_number']}_ms.pdf"
        else:
            qp_url = upload_pdf(
                client, bucket, REPO_ROOT / question["qp_pdf"],
                f"{R2_PREFIX}/{question['paper_key']}/q{question['question_number']}.pdf",
            )
            uploaded += 1
            if question["has_markscheme"] and question["ms_pdf"]:
                ms_url = upload_pdf(
                    client, bucket, REPO_ROOT / question["ms_pdf"],
                    f"{R2_PREFIX}/{question['paper_key']}/q{question['question_number']}_ms.pdf",
                )
                uploaded += 1

        classification = question["classification"]
        secondary_ids = [
            section_id_by_code[code]
            for code in classification.get("secondary", [])
            if code in section_id_by_code
        ]

        # A slug is issued once and never reissued.
        slug = previous["slug"] if previous else (
            f"{SLUG_PREFIX}.CH{int(chapter):02d}.S{int(section_number):02d}.Q{question['_ordinal']:03d}"
        )

        # Mechanical fields, safe to refresh on any row: they describe the PDF,
        # not the judgement about where it belongs.
        payload = {
            "slug": slug,
            "subject_id": subject_id,
            "ordinal_in_chapter": previous["ordinal_in_chapter"] if previous else question["_ordinal"],
            "source_paper_id": paper_id_by_key.get(question["paper_key"]),
            "source_paper_key": question["paper_key"],
            "source_question_number": question["question_number"],
            "marks": question["marks"],
            "difficulty": question["difficulty"],
            "sub_parts": question["sub_parts"],
            "qp_pdf_url": qp_url,
            "ms_pdf_url": ms_url,
            "stem": question["stem"][:4000],
            "text_status": db_text_status(question["text_status"]),
        }

        classifier_section_id = section_id_by_code[question["_section"]]

        if previous and previous["verified_at"]:
            # A human has ruled on this one. Record what the classifier now
            # thinks, but leave the ruling alone.
            payload["proposed_section_id"] = classifier_section_id
            protected += 1
        else:
            payload["section_id"] = classifier_section_id
            payload["secondary_section_ids"] = secondary_ids
            payload["archetype_id"] = archetype_id_by_key.get(cluster_of.get(question["_id"], ""))

        if previous:
            supabase.table("workbook_questions").update(payload).eq("id", previous["id"]).execute()
            updated += 1
        else:
            supabase.table("workbook_questions").insert(payload).execute()
            inserted += 1

        if (inserted + updated) % 50 == 0:
            print(f"    {inserted + updated}/{len(ordered)} rows...")

    print(f"\n  PDFs uploaded : {uploaded}")
    print(f"  rows inserted : {inserted}")
    print(f"  rows updated  : {updated}")
    print(f"  of which verified, section left untouched: {protected}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
