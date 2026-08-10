"""
Load the classified FPM workbook into R2 and the database.

Takes the Phase 1-3 output (clean segments, marks, sections, archetypes) and
turns it into the actual book: uploads every question and mark scheme PDF to R2,
creates the archetype rows, and writes `workbook_questions` with stable slugs
and a fixed print order.

STABLE SLUGS
------------
Each question gets `FPM.CH09.S04.Q021` -- chapter, section, ordinal in chapter.
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
`verified_at` is left NULL. The RLS policy on `workbook_questions` only exposes
verified rows publicly, so nothing reaches a student until Phase 4 signs it off.

USAGE
-----
    python scripts/load_fpm_workbook_to_db.py            # dry run
    python scripts/load_fpm_workbook_to_db.py --execute
    python scripts/load_fpm_workbook_to_db.py --execute --skip-upload
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
CLASSIFICATIONS_PATH = WORKBOOK_DIR / "fpm_classifications.json"
ARCHETYPES_PATH = WORKBOOK_DIR / "fpm_archetypes.json"

SUBJECT_CODE = "4PM1"
SLUG_PREFIX = "FPM"
# Separate prefix from `subjects/...`, which is the regenerable ingest layer.
# The workbook is a curated artifact and must not be clobbered by a re-ingest.
R2_PREFIX = "workbook/fpm"

# Session ordering within a year, for the chronological tiebreak.
SESSION_ORDER = {"specimen": 0, "jan": 1, "may-jun": 2, "oct-nov": 3}


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

    print(f"{'=' * 74}\nLOAD FPM WORKBOOK\n{'=' * 74}")
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

    sections = supabase.table("workbook_sections").select("id,chapter_id,number").execute().data
    number_by_chapter_id = {c["id"]: str(c["number"]) for c in chapters}
    section_id_by_code = {
        f"{number_by_chapter_id[s['chapter_id']]}.{s['number']}": s["id"]
        for s in sections
        if s["chapter_id"] in number_by_chapter_id
    }
    print(f"  sections     : {len(section_id_by_code)} in the database")

    bad = sorted({q["_section"] for q in classified if q["_section"] not in section_id_by_code})
    if bad:
        print(f"\n  ABORT: {len(bad)} section code(s) not in the database: {bad}")
        print("  Run remap_fpm_section_merges.py, or apply the newest section migration.")
        return 1

    ordered = build_print_order(classified, cluster_of)

    # Existing rows keep their slug and ordinal -- attempts reference them.
    existing = supabase.table("workbook_questions").select(
        "id,slug,source_paper_key,source_question_number,ordinal_in_chapter"
    ).eq("subject_id", subject_id).execute().data
    existing_by_source = {
        (row["source_paper_key"], row["source_question_number"]): row for row in existing
    }
    print(f"  already in DB: {len(existing)}")

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
    archetype_id_by_key: dict[str, str] = {}
    for cluster in clusters:
        key = f"{cluster['section']}|{cluster['label']}"
        section_id = section_id_by_code.get(cluster["section"])
        row = supabase.table("workbook_archetypes").insert(
            {"section_id": section_id, "label": cluster["label"],
             "description": f"{cluster['size']} question(s) in section {cluster['section']}"}
        ).execute().data[0]
        archetype_id_by_key[key] = row["id"]
    print(f"  archetypes written: {len(archetype_id_by_key)}")

    # ── Questions ────────────────────────────────────────────────────────────
    uploaded = inserted = updated = 0

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

        payload = {
            "slug": slug,
            "subject_id": subject_id,
            "section_id": section_id_by_code[question["_section"]],
            "archetype_id": archetype_id_by_key.get(cluster_of.get(question["_id"], "")),
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
            "text_status": question["text_status"],
            "secondary_section_ids": secondary_ids,
        }

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
    print(f"  verified      : 0 (Phase 4 sets verified_at; nothing is public yet)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
