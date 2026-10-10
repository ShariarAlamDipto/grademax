#!/usr/bin/env python3
"""
Strip non-question pages out of the IGCSE Physics (4PH1) question segments.

The worksheet generator and test builder merge each page row's `qp_page_url`
verbatim, so any non-question page inside a segment reaches the student. An
audit of all 833 live segments (2026-09-26) found three kinds:

  * Equation Booklet (19 segments): every 2022-2025 paper's LAST question
    carries the 4-page separate Equation Booklet, whose first page is a full
    Pearson front cover ("Equation Booklet / Do not return this Booklet").
  * Paper front cover + formulae sheet (2 segments): 2022 May-Jun 1PR / 2PR q1
    start at page 1 of the paper.
  * "BLANK PAGE" pages (202 pages across 136 segments).

Each segment is rewritten in place on R2 (same key, so no DB change) with
only its question pages kept. A page is removed only if it is classified as
one of the above AND it carries no "Total for Question" fence; every segment
must keep at least one question page. Originals are backed up first.

Usage:
    python scripts/fix_physics_front_pages.py            # dry run (report only)
    python scripts/fix_physics_front_pages.py --apply    # back up + overwrite R2
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import fitz  # PyMuPDF
import requests
from dotenv import load_dotenv
from supabase import create_client

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env.local")

SUBJECT_CODE = "4PH1"
R2_PUBLIC_PREFIX = "https://pub-b96af5a8f7044337bcb17a51b3fd4a60.r2.dev/"
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "grademax-papers")
BACKUP_DIR = REPO_ROOT / "data" / "backups" / f"physics_front_pages_{date.today().isoformat()}"
REPORT = REPO_ROOT / "data" / "analysis" / "physics_front_pages_fix.json"

BARCODE = re.compile(r"\*(P\d{5}[A-Z]{0,2})(\d{4,5})\*")
TOTAL_FENCE = re.compile(r"Total for Question\s*\d+", re.I)
COVER_MARKERS = [
    r"Instructions", r"Candidate", r"Centre Number", r"Total Marks",
    r"Information", r"Advice", r"You must have",
]
# Boilerplate that appears on a genuinely blank page; whatever survives
# stripping it is real content.
BLANK_BOILERPLATE = re.compile(
    r"DO NOT WRITE IN THIS AREA|Turn over|BLANK PAGE|Questions? (?:begins?|ends?)[^.]*"
    r"|\*P\d+[A-Z]*\d*\*|P\d{5}[A-Z]{0,2}|GradeMax"
    r"|Physics · .*?QP 4PH\d \| \d{4} \| [A-Za-z/]+ \| Paper \w+"
)

COVER, FORMULAE, BOOKLET, BLANK, CONTENT = "cover", "formulae", "booklet", "blank", "content"
REMOVABLE = {COVER, FORMULAE, BOOKLET, BLANK}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def classify_page(text: str) -> str:
    """Classify one page by its text layer."""
    t = _norm(text)
    if re.search(r"Equation Booklet", t) and re.search(r"Do not return this Booklet", t, re.I):
        return BOOKLET
    if re.search(r"These (?:additional )?equations may be required", t):
        return BOOKLET
    m = BARCODE.search(t)
    paper_page = int(m.group(2)[:-2]) if m else None
    cover_hits = sum(bool(re.search(p, t)) for p in COVER_MARKERS)
    if paper_page == 1 or cover_hits >= 4:
        return COVER
    if re.search(r"(?:FORMULAE|EQUATIONS)\s+You may find the following", t, re.I) and not TOTAL_FENCE.search(t):
        return FORMULAE
    if "BLANK PAGE" in t:
        body = re.sub(r"\b\d+\b", " ", re.sub(r"[^\w]", " ", BLANK_BOILERPLATE.sub(" ", t)))
        if len(body.split()) < 8:
            return BLANK
    return CONTENT


def classify_segment(doc: fitz.Document) -> list[str]:
    """Per-page labels. The Equation Booklet is always the tail of a segment,
    so everything from its cover onwards is booklet (its page 3 has no
    distinctive heading of its own)."""
    labels = [classify_page(p.get_text()) for p in doc]
    for i, p in enumerate(doc):
        # The paper's own cover also says "Equation Booklet" (in its
        # instructions), so require the booklet cover's own wording.
        if re.search(r"Do not return this Booklet", _norm(p.get_text()), re.I):
            labels[i:] = [BOOKLET] * (len(labels) - i)
            break
    return labels


def plan_segment(pdf_bytes: bytes) -> dict:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    labels = classify_segment(doc)
    keep = [i for i, lab in enumerate(labels) if lab not in REMOVABLE]
    fences_before = [x for p in doc for x in TOTAL_FENCE.findall(p.get_text())]
    fences_after = [x for i in keep for x in TOTAL_FENCE.findall(doc[i].get_text())]
    return {"labels": labels, "keep": keep, "safe": bool(keep) and fences_before == fences_after}


def rewrite(pdf_bytes: bytes, keep: list[int]) -> bytes:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    doc.select(keep)
    return doc.tobytes(garbage=3, deflate=True)


def load_rows() -> list[dict]:
    sb = create_client(os.environ["NEXT_PUBLIC_SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    subject = sb.table("subjects").select("id").eq("code", SUBJECT_CODE).single().execute().data
    papers = sb.table("papers").select("id").eq("subject_id", subject["id"]).execute().data
    ids = [p["id"] for p in papers]
    rows: list[dict] = []
    for i in range(0, len(ids), 50):
        offset = 0
        while True:
            batch = (
                sb.table("pages").select("id,question_number,qp_page_url")
                .in_("paper_id", ids[i:i + 50]).eq("is_question", True)
                .not_.is_("qp_page_url", "null")
                .range(offset, offset + 999).execute().data
            )
            rows += batch
            if len(batch) < 1000:
                break
            offset += 1000
    return rows


def r2_client():
    import boto3
    from botocore.config import Config
    return boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto", config=Config(retries={"max_attempts": 3}),
    )


def fetch(url: str) -> bytes:
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.content


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="back up and overwrite the R2 objects")
    args = ap.parse_args()

    rows = load_rows()
    print(f"{len(rows)} {SUBJECT_CODE} question segments")
    urls = sorted({r["qp_page_url"] for r in rows})
    if any(not u.startswith(R2_PUBLIC_PREFIX) for u in urls):
        print("ERROR: unexpected URL host; refusing to guess the R2 key", file=sys.stderr)
        return 1

    with ThreadPoolExecutor(16) as ex:
        blobs = dict(zip(urls, ex.map(fetch, urls)))

    changes, unsafe = [], []
    for url in urls:
        plan = plan_segment(blobs[url])
        if len(plan["keep"]) == len(plan["labels"]):
            continue
        entry = {"key": url[len(R2_PUBLIC_PREFIX):], "labels": plan["labels"], "keep": plan["keep"]}
        (changes if plan["safe"] else unsafe).append(entry)

    removed = sum(len(c["labels"]) - len(c["keep"]) for c in changes)
    by_kind: dict[str, int] = {}
    for c in changes:
        for i, lab in enumerate(c["labels"]):
            if i not in c["keep"]:
                by_kind[lab] = by_kind.get(lab, 0) + 1
    print(f"segments to rewrite: {len(changes)}  pages removed: {removed}  {by_kind}")
    for c in unsafe:
        print(f"SKIPPED (would drop a question fence or empty the segment): {c['key']} {c['labels']}")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({"applied": args.apply, "changes": changes, "skipped": unsafe}, indent=1))
    print(f"report: {REPORT.relative_to(REPO_ROOT)}")
    if not args.apply:
        print("dry run - re-run with --apply to write")
        return 0

    client = r2_client()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for c in changes:
        url = R2_PUBLIC_PREFIX + c["key"]
        backup = BACKUP_DIR / c["key"].replace("/", "__")
        if not backup.exists():  # never overwrite the first (original) backup on a re-run
            backup.write_bytes(blobs[url])
        client.put_object(
            Bucket=R2_BUCKET, Key=c["key"], Body=rewrite(blobs[url], c["keep"]),
            ContentType="application/pdf",
        )
    print(f"rewrote {len(changes)} objects; originals in {BACKUP_DIR.relative_to(REPO_ROOT)}")

    # Verify from the public URL, not from what we think we uploaded.
    bad = [c["key"] for c in changes
           if any(lab in REMOVABLE for lab in classify_segment(fitz.open(stream=fetch(R2_PUBLIC_PREFIX + c["key"]), filetype="pdf")))]
    print("verify:", "OK - no front/booklet/blank pages remain" if not bad else f"STILL DIRTY: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
