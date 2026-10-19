"""
Load the Physics (4PH1) workbook into R2 and the database.

Port of load_mathsa_workbook_to_db.py, reading the SETTLED book
(data/workbook/physics_book.json, from assign_physics_workbook_sections.py)
rather than raw classifier output, so the web workbook and the printed book
carry the same sections in the same order.

Carries every rule the earlier loaders paid for:

  * Slugs are issued ONCE. A re-run matches on (subject, paper, question) and
    keeps the existing slug and ordinal; workbook_attempts points at them.
  * A row with `verified_at` set is AUTHORITATIVE: only mechanical fields are
    refreshed and the newer section goes to `proposed_section_id`.
  * Every PostgREST read is paged (1000-row silent cap).
  * Every row is PRE-FLIGHTED against the schema's CHECK constraints in the dry
    run too -- a dry run never inserts, so it can never meet a constraint.
  * Archetype rows are matched on (section, label) INCLUDING rows created
    earlier in the same run.

`verified_at` stays NULL on new rows, so RLS keeps them out of student view
until a human signs them off in /admin/workbook/verify. `review_priority` is
written from the two-model agreement, so that queue opens on the disputed ones.

ARCHETYPES
----------
A question's archetype is the first-pass classifier's shape label. A label is
made an archetype row only where at least two questions in the same section
share it; a one-off label is not a recurring shape and is left NULL.

USAGE
-----
    python scripts/load_physics_workbook_to_db.py            # dry run
    python scripts/load_physics_workbook_to_db.py --execute
    python scripts/load_physics_workbook_to_db.py --execute --skip-upload
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from supabase import create_client

REPO_ROOT = Path(__file__).resolve().parent.parent
BOOK_PATH = REPO_ROOT / "data" / "workbook" / "physics_book.json"

SUBJECT_CODE = "4PH1"
R2_PREFIX = "workbook/physics"

DB_TEXT_STATUS = {"ok", "repaired", "needs_vision"}
TEXT_STATUS_FALLBACK = {"partially_garbled": "repaired"}
DIFFICULTIES = {"easy", "medium", "hard"}
PRIORITIES = {"disputed", "same_chapter", "unconfirmed", "agreed"}


def db_text_status(status: str | None) -> str | None:
    if status is None or status in DB_TEXT_STATUS:
        return status
    return TEXT_STATUS_FALLBACK.get(status, "repaired")


def review_priority(question: dict) -> str:
    first, second = question.get("classification"), question.get("second_opinion")
    if not first or not second:
        return "unconfirmed"
    if first["primary"] == second["primary"]:
        return "agreed"
    if first["primary"].split(".")[0] == second["primary"].split(".")[0]:
        return "same_chapter"
    return "disputed"


def fetch_all_rows(supabase, table: str, columns: str, subject_id: str,
                   page_size: int = 500) -> list[dict]:
    rows: list[dict] = []
    start = 0
    while True:
        page = (supabase.table(table).select(columns).eq("subject_id", subject_id)
                .range(start, start + page_size - 1).execute().data)
        rows.extend(page)
        if len(page) < page_size:
            return rows
        start += page_size


def r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def public_url(key: str) -> str:
    return f"{os.environ['NEXT_PUBLIC_R2_PUBLIC_URL'].rstrip('/')}/{key}"


def upload_pdf(client, bucket: str, local_path: Path, key: str) -> str:
    """Upload one PDF unless it is already there. Returns the public URL."""
    try:
        client.head_object(Bucket=bucket, Key=key)
        return public_url(key)  # PDFs are immutable once uploaded
    except ClientError as error:
        if error.response["Error"]["Code"] not in ("404", "NoSuchKey", "403"):
            raise
    client.put_object(Bucket=bucket, Key=key, Body=local_path.read_bytes(),
                      ContentType="application/pdf",
                      CacheControl="public, max-age=31536000, immutable")
    return public_url(key)


def keys_for(question: dict) -> tuple[str, str]:
    base = f"{R2_PREFIX}/{question['source_paper_key']}/q{question['source_question_number']}"
    return f"{base}.pdf", f"{base}_ms.pdf"


def preflight(questions: list[dict], section_id_by_code: dict[str, str]) -> list[str]:
    problems: list[str] = []
    for q in questions:
        label = q["slug"]
        if q["section"] not in section_id_by_code:
            problems.append(f"{label}: section {q['section']} not in the database")
        if not isinstance(q["marks"], int) or q["marks"] <= 0:
            problems.append(f"{label}: marks {q['marks']!r}")
        if q["difficulty"] not in DIFFICULTIES:
            problems.append(f"{label}: difficulty {q['difficulty']!r}")
        if db_text_status(q["text_status"]) not in DB_TEXT_STATUS:
            problems.append(f"{label}: text_status {q['text_status']!r}")
        if review_priority(q) not in PRIORITIES:
            problems.append(f"{label}: review_priority")
        if not (REPO_ROOT / q["qp_pdf"]).is_file():
            problems.append(f"{label}: missing {q['qp_pdf']}")
        if q["ms_pdf"] and not (REPO_ROOT / q["ms_pdf"]).is_file():
            problems.append(f"{label}: missing {q['ms_pdf']}")
    return problems


def main() -> int:
    load_dotenv(REPO_ROOT / ".env.local")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--skip-upload", action="store_true")
    args = parser.parse_args()

    book = json.loads(BOOK_PATH.read_text(encoding="utf-8"))
    questions = book["questions"]

    # Book order -> one running ordinal per chapter (the column's meaning).
    running: Counter = Counter()
    for q in questions:
        chapter = q["section"].split(".")[0]
        running[chapter] += 1
        q["_ordinal_in_chapter"] = running[chapter]

    print(f"{'=' * 74}\nLOAD PHYSICS (4PH1) WORKBOOK  [{'EXECUTE' if args.execute else 'DRY RUN'}]\n{'=' * 74}")
    print(f"  questions    : {len(questions)}  (from {BOOK_PATH.name})")

    supabase = create_client(os.environ["NEXT_PUBLIC_SUPABASE_URL"],
                             os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    subject_id = (supabase.table("subjects").select("id").eq("code", SUBJECT_CODE)
                  .single().execute().data["id"])
    chapters = (supabase.table("workbook_chapters").select("id,number")
                .eq("subject_id", subject_id).execute().data)
    number_by_chapter_id = {c["id"]: str(c["number"]) for c in chapters}
    sections = (supabase.table("workbook_sections").select("id,chapter_id,number")
                .in_("chapter_id", list(number_by_chapter_id)).execute().data)
    section_id_by_code = {f"{number_by_chapter_id[s['chapter_id']]}.{s['number']}": s["id"]
                          for s in sections}
    print(f"  sections     : {len(section_id_by_code)} in the database")

    problems = preflight(questions, section_id_by_code)
    if problems:
        print(f"\n  ABORT: {len(problems)} row(s) would fail:")
        for problem in problems[:20]:
            print(f"    {problem}")
        return 1
    print(f"  pre-flight   : OK ({len(questions)} rows check out against the schema)")

    existing = fetch_all_rows(
        supabase, "workbook_questions",
        "id,slug,source_paper_key,source_question_number,ordinal_in_chapter,verified_at",
        subject_id)
    existing_by_source = {(r["source_paper_key"], r["source_question_number"]): r
                          for r in existing}
    print(f"  already in DB: {len(existing)}  "
          f"({sum(1 for r in existing if r['verified_at'])} human-verified, protected)")

    priorities = Counter(review_priority(q) for q in questions)
    print("  review queue : " + ", ".join(f"{k} {priorities.get(k, 0)}"
                                          for k in ("disputed", "same_chapter", "agreed", "unconfirmed")))

    # Recurring shapes only.
    shape_counts = Counter((q["section"], q["archetype"]) for q in questions if q["archetype"])
    recurring = {pair for pair, n in shape_counts.items() if n >= 2}
    print(f"  archetypes   : {len(recurring)} recurring shapes "
          f"({sum(shape_counts[p] for p in recurring)} questions)")

    if not args.execute:
        print(f"\n  Would upload up to {len(questions) + sum(1 for q in questions if q['ms_pdf'])} PDFs "
              f"to {R2_PREFIX}/")
        print(f"  Would write  {len(questions)} workbook_questions rows")
        print("\n  Dry run -- nothing uploaded or written. Re-run with --execute.")
        return 0

    # ── Archetypes ──────────────────────────────────────────────────────────
    prior = (supabase.table("workbook_archetypes").select("id,section_id,label")
             .in_("section_id", list(section_id_by_code.values())).execute().data)
    archetype_id = {(r["section_id"], r["label"]): r["id"] for r in prior}
    created = 0
    for section, label in sorted(recurring):
        pair = (section_id_by_code[section], label)
        if pair in archetype_id:
            continue
        row = supabase.table("workbook_archetypes").insert(
            {"section_id": pair[0], "label": label,
             "description": f"{shape_counts[(section, label)]} question(s) in section {section}"}
        ).execute().data[0]
        archetype_id[pair] = row["id"]  # recorded at once: see the module docstring
        created += 1
    print(f"  archetypes   : {created} created")

    # ── Questions ───────────────────────────────────────────────────────────
    client = None if args.skip_upload else r2_client()
    bucket = os.environ["R2_BUCKET_NAME"]
    uploaded = inserted = updated = protected = 0

    for q in questions:
        qp_key, ms_key = keys_for(q)
        if args.skip_upload:
            qp_url = public_url(qp_key)
            ms_url = public_url(ms_key) if q["ms_pdf"] else None
        else:
            qp_url = upload_pdf(client, bucket, REPO_ROOT / q["qp_pdf"], qp_key)
            uploaded += 1
            ms_url = None
            if q["ms_pdf"]:
                ms_url = upload_pdf(client, bucket, REPO_ROOT / q["ms_pdf"], ms_key)
                uploaded += 1

        previous = existing_by_source.get((q["source_paper_key"], q["source_question_number"]))
        first = q.get("classification") or {}
        payload = {
            "slug": previous["slug"] if previous else q["slug"],
            "subject_id": subject_id,
            "ordinal_in_chapter": (previous["ordinal_in_chapter"] if previous
                                   else q["_ordinal_in_chapter"]),
            "source_paper_key": q["source_paper_key"],
            "source_question_number": q["source_question_number"],
            "marks": q["marks"],
            "difficulty": q["difficulty"],
            "sub_parts": q["sub_parts"],
            "qp_pdf_url": qp_url,
            "ms_pdf_url": ms_url,
            "stem": q["stem"][:4000],
            "text_status": db_text_status(q["text_status"]),
            "review_priority": review_priority(q),
            "classifier_confidence": first.get("confidence"),
        }
        section_id = section_id_by_code[q["section"]]
        if previous and previous["verified_at"]:
            payload["proposed_section_id"] = section_id
            protected += 1
        else:
            payload["section_id"] = section_id
            payload["proposed_section_id"] = section_id
            payload["secondary_section_ids"] = [section_id_by_code[c]
                                                for c in q["secondary_sections"]
                                                if c in section_id_by_code]
            payload["archetype_id"] = archetype_id.get((section_id, q["archetype"]))

        if previous:
            supabase.table("workbook_questions").update(payload).eq("id", previous["id"]).execute()
            updated += 1
        else:
            supabase.table("workbook_questions").insert(payload).execute()
            inserted += 1
        if (inserted + updated) % 50 == 0:
            print(f"    {inserted + updated}/{len(questions)} rows...")

    print(f"\n  PDFs uploaded : {uploaded}")
    print(f"  rows inserted : {inserted}")
    print(f"  rows updated  : {updated}")
    print(f"  of which verified, section left untouched: {protected}")

    # Read back the artifact, not the counters.
    live = fetch_all_rows(supabase, "workbook_questions",
                          "slug,section_id,verified_at", subject_id)
    print(f"  live rows     : {len(live)}  distinct slugs {len({r['slug'] for r in live})}  "
          f"null section {sum(1 for r in live if not r['section_id'])}")
    return 0 if len(live) == len(questions) else 1


if __name__ == "__main__":
    sys.exit(main())
