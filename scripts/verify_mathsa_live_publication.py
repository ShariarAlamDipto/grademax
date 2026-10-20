#!/usr/bin/env python3
"""Verify every published Maths A row, storage checksum and public PDF samples."""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import fitz
import requests
from supabase import create_client
import os

from apply_mathsa_rebuild_topics import difficulty
from classify_mathsa_workbook_sections import TAXONOMY, SECONDARY_ONLY
from lib.live_paper_sources import ROOT, REBUILD_DIR, fetch_rows, r2_reader, supabase_client

STAGE = REBUILD_DIR / "4MA1"
SUBJECT_ID = "8b7b0cb0-e95c-480d-ac0a-c710f1e59213"


def main():
    rows = json.loads((STAGE / "verdicts.json").read_text())["rows"]
    topics = json.loads((STAGE / "topics_new.json").read_text())
    expected = {(r["paper_id"], str(r["question"])): r for r in rows}
    sb = supabase_client()
    paper_ids = sorted({r["paper_id"] for r in rows})
    pages = []
    for start in range(0, len(paper_ids), 50):
        part = paper_ids[start:start + 50]
        pages += fetch_rows(lambda o: sb.table("pages").select("*").in_("paper_id", part)
                            .eq("is_question", True).not_.is_("qp_page_url", "null").range(o, o + 999))
    found = {(p["paper_id"], str(p["question_number"])): p for p in pages}
    failures = []
    if len(pages) != len(expected) or set(found) != set(expected):
        failures.append("Published question coverage differs from staged questions")
    ids = [p["id"] for p in pages]
    mirrors, tags = [], []
    for start in range(0, len(ids), 100):
        part = ids[start:start + 100]
        mirrors += fetch_rows(lambda o: sb.table("questions").select("*").in_("id", part).range(o, o + 999))
        tags += fetch_rows(lambda o: sb.table("question_tags").select("question_id,topic")
                           .in_("question_id", part).range(o, o + 999))
    mirrored = {r["id"]: r for r in mirrors}
    if set(mirrored) != set(ids):
        failures.append("Question mirror coverage mismatch")
    definitions = sb.table("topics").select("code,name").eq("subject_id", SUBJECT_ID).execute().data
    if {d["code"]: d["name"] for d in definitions} != {
            k: v for k, v in TAXONOMY.items() if k not in SECONDARY_ONLY}:
        failures.append("Tool topic definitions differ from the reviewed taxonomy")
    _, prefix = r2_reader()
    import ingest_2026_papers as ing
    r2 = ing.get_r2()
    stored = {}
    for chunk in r2.get_paginator("list_objects_v2").paginate(
            Bucket=ing.R2_BUCKET, Prefix="subjects/MathsA/pages-v2/"):
        for obj in chunk.get("Contents", []):
            stored[obj["Key"]] = obj
    desired_tags, checked_objects, by_key = set(), set(), {}
    for key, row in expected.items():
        page = found.get(key)
        if not page:
            continue
        label = f"{row['paper']}|{row['question']}"
        by_key[label] = page
        if (page["topics"] != topics[label] or page["difficulty"] != difficulty(int(row["marks"]))
                or page["page_number"] != 1000 + int(row["question"])):
            failures.append(f"{label}: tags, difficulty or order mismatch")
        mirror = mirrored.get(page["id"], {})
        if (mirror.get("paper_id") != page["paper_id"]
                or str(mirror.get("question_number")) != page["question_number"]
                or mirror.get("difficulty") != page["difficulty"]):
            failures.append(f"{label}: mirror metadata mismatch")
        desired_tags.update((page["id"], tag) for tag in topics[label])
        for role, column, mirror_column in (("qp", "qp_page_url", "page_pdf_url"),
                                             ("ms", "ms_page_url", "ms_pdf_url")):
            local = ROOT / row[role]
            data = local.read_bytes()
            digest = hashlib.md5(data).hexdigest()
            suffix = "_ms" if role == "ms" else ""
            object_key = f"subjects/MathsA/pages-v2/{row['live_key']}/q{row['question']}{suffix}-{digest[:10]}.pdf"
            url = prefix + object_key
            if page.get(column) != url or mirror.get(mirror_column) != url:
                failures.append(f"{label}: {role} URL mismatch")
            obj = stored.get(object_key)
            if not obj or obj["Size"] != len(data) or obj["ETag"].strip('"') != digest:
                failures.append(f"{label}: {role} storage checksum/size mismatch")
            checked_objects.add(object_key)
    if {(t["question_id"], t["topic"]) for t in tags} != desired_tags:
        failures.append("Question tag mirrors differ from reviewed tags")
    print(f"Database and storage checked: {len(pages)} questions, {len(checked_objects)} objects", flush=True)
    public_checks = []
    samples = ["2011_may-jun_3H|1", "2013_may-jun_2H|11", "2015_may-jun_3H|11",
               "2019_jan_1H|3", "2019_jan_1HR|7", "2019_jan_2HR|18",
               "2026_may-jun_1H|21", "2026_may-jun_2H|24"]
    for label in samples:
        page = by_key[label]
        row = next(r for r in rows if f"{r['paper']}|{r['question']}" == label)
        for role, col in (("qp", "qp_page_url"), ("ms", "ms_page_url")):
            response = requests.get(page[col], timeout=45)
            if response.status_code != 200 or response.content != (ROOT / row[role]).read_bytes():
                failures.append(f"{label}: {role} public PDF download mismatch")
                continue
            with fitz.open(stream=response.content, filetype="pdf") as doc:
                public_checks.append({"question": label, "role": role, "pages": doc.page_count})
    anon = create_client(os.environ["NEXT_PUBLIC_SUPABASE_URL"], os.environ["NEXT_PUBLIC_SUPABASE_ANON_KEY"])
    anonymous_counts = {}
    for level in ("easy", "medium", "hard"):
        total = 0
        for start in range(0, len(paper_ids), 50):
            part = paper_ids[start:start + 50]
            total += anon.table("pages").select("id", count="exact", head=True).in_("paper_id", part) \
                .eq("is_question", True).not_.is_("qp_page_url", "null").eq("difficulty", level).execute().count or 0
        anonymous_counts[level] = total
    if anonymous_counts != dict(Counter(difficulty(int(r["marks"])) for r in rows)):
        failures.append("Public difficulty-filtered queries do not cover all questions")
    result = {"subject": "4MA1", "papers": len(paper_ids), "questions": len(pages),
              "question_mirrors": len(mirrors), "topic_definitions": len(definitions),
              "tag_assignments": len(tags), "storage_objects_verified": len(checked_objects),
              "public_pdf_samples": public_checks, "public_difficulty_counts": anonymous_counts,
              "failures": failures, "passed": not failures}
    (STAGE / "live_publication_audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
