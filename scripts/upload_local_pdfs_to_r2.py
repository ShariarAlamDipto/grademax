#!/usr/bin/env python3
"""
Upload locally-segmented per-question PDFs to R2.

Operates on:
  data/processed/Further Pure Maths Processed/   ->  subjects/Further Pure Mathematics/pages/...
  data/processed/Maths B/                         ->  subjects/MathsB/pages/...
  data/processed/Mechanics_1/                     ->  subjects/Mechanics 1/pages/...
  data/processed/Physics/                         ->  subjects/Physics/pages/...

Subject layout in each:
  <year>_<season>_<paper>/
      pages/q1.pdf q2.pdf ...
      markschemes/q1.pdf q2.pdf ...     (optional, named q1.pdf -> uploaded as q1_ms.pdf)

Outputs:
  data/processed/upload_manifest.json   - record of every uploaded file with R2 URL

Usage:
    pip install boto3 python-dotenv
    python -X utf8 scripts/upload_local_pdfs_to_r2.py --dry-run
    python -X utf8 scripts/upload_local_pdfs_to_r2.py --subject Physics
    python -X utf8 scripts/upload_local_pdfs_to_r2.py
"""

import os, sys, json, time
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv(".env.local")

DRY_RUN = "--dry-run" in sys.argv
SUBJECT_FILTER: str | None = None
for i, a in enumerate(sys.argv):
    if a == "--subject" and i + 1 < len(sys.argv):
        SUBJECT_FILTER = sys.argv[i + 1]

try:
    import boto3
    from botocore.exceptions import ClientError
    from botocore.config import Config
except ImportError:
    print("ERROR: pip install boto3"); sys.exit(1)

# ── Config ──────────────────────────────────────────────────────────────────
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET     = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET     = os.getenv("R2_BUCKET_NAME", "grademax-papers")
R2_PUBLIC_URL = (os.getenv("NEXT_PUBLIC_R2_PUBLIC_URL") or "").rstrip("/")

for k, v in [("R2_ACCOUNT_ID", R2_ACCOUNT_ID), ("R2_ACCESS_KEY_ID", R2_ACCESS_KEY),
             ("R2_SECRET_ACCESS_KEY", R2_SECRET), ("NEXT_PUBLIC_R2_PUBLIC_URL", R2_PUBLIC_URL)]:
    if not v:
        print(f"ERROR: {k} not in .env.local"); sys.exit(1)

PROCESSED_DIR = Path("data/processed")

# Local folder name -> R2 storage path subject name.
# These match the canonical paths used by the existing ingest scripts and
# stored in pages.qp_page_url. NB: naming is inconsistent across subjects
# (some use _ underscores, some run-together, etc.) — exact match to existing
# paths is what matters, so the URL flip later is a clean string-replace.
SUBJECT_MAP = {
    "Further Pure Maths Processed": "Further_Pure_Mathematics",  # underscores
    "Maths B":                       "MathsB",                    # run-together
    "Mechanics_1":                   "Mechanics_1",               # underscore
    "Physics":                       "Physics",                   # plain
    # Downloaded from Supabase S3 by scripts/download_bio_chem_via_s3.py:
    "Biology":                       "Biology",
    "Chemistry":                     "Chemistry",
    "Human_Biology":                 "Human_Biology",
}

r2 = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET,
    region_name="auto",
    config=Config(retries={"max_attempts": 5, "mode": "standard"}),
)

def r2_exists(key: str) -> bool:
    try:
        r2.head_object(Bucket=R2_BUCKET, Key=key); return True
    except ClientError:
        return False

def r2_upload(key: str, data: bytes) -> bool:
    if DRY_RUN: return True
    for attempt in range(3):
        try:
            r2.put_object(Bucket=R2_BUCKET, Key=key, Body=data,
                          ContentType="application/pdf",
                          CacheControl="public, max-age=31536000, immutable")
            return True
        except ClientError as e:
            if attempt == 2:
                print(f"    upload error: {e}"); return False
            time.sleep(1.5 ** attempt)
    return False

# ── Walk subjects ───────────────────────────────────────────────────────────
print("=" * 72)
print(f"LOCAL PDFs  ->  R2{' [DRY-RUN]' if DRY_RUN else ''}")
print(f"Bucket: {R2_BUCKET}    Public URL: {R2_PUBLIC_URL}")
print("=" * 72)

manifest: list[dict] = []
total_ok = total_skip = total_fail = 0
start = time.time()

for local_subject, db_subject in SUBJECT_MAP.items():
    if SUBJECT_FILTER and db_subject != SUBJECT_FILTER and local_subject != SUBJECT_FILTER:
        continue
    subj_root = PROCESSED_DIR / local_subject
    if not subj_root.exists():
        print(f"\n  {db_subject}: SKIP (no local folder {subj_root})"); continue

    print(f"\n[{db_subject}]  source: {subj_root}")

    counts = {"ok": 0, "skip": 0, "fail": 0}

    def upload_pdf(pdf_path: Path, r2_key: str, file_type: str, paper: str) -> str:
        """Upload one PDF, update counts dict in place, return status."""
        if r2_exists(r2_key):
            counts["skip"] += 1
            manifest.append({
                "local_path": str(pdf_path), "r2_key": r2_key,
                "url": f"{R2_PUBLIC_URL}/{r2_key}",
                "type": file_type, "subject": db_subject, "paper": paper,
                "status": "skipped_already_in_r2",
            })
            return "skip"
        data = pdf_path.read_bytes()
        if r2_upload(r2_key, data):
            counts["ok"] += 1
            manifest.append({
                "local_path": str(pdf_path), "r2_key": r2_key,
                "url": f"{R2_PUBLIC_URL}/{r2_key}",
                "type": file_type, "subject": db_subject, "paper": paper,
                "size": len(data), "status": "uploaded",
            })
            return "ok"
        counts["fail"] += 1
        return "fail"

    paper_folders = sorted(p for p in subj_root.iterdir() if p.is_dir())
    for paper_dir in paper_folders:
        paper_id = paper_dir.name  # e.g. 2019_May-Jun_P1
        pages_dir = paper_dir / "pages"
        ms_dir    = paper_dir / "markschemes"

        if pages_dir.exists() or ms_dir.exists():
            # Layout A: separate pages/ and markschemes/ subfolders
            # (FPM, MathsB, Mechanics_1, Physics — locally segmented)
            if pages_dir.exists():
                for pdf in sorted(pages_dir.glob("*.pdf")):
                    key = f"subjects/{db_subject}/pages/{paper_id}/{pdf.name}"
                    upload_pdf(pdf, key, "qp", paper_id)
            if ms_dir.exists():
                for pdf in sorted(ms_dir.glob("*.pdf")):
                    # local q1.pdf -> r2 q1_ms.pdf
                    key = f"subjects/{db_subject}/pages/{paper_id}/{pdf.stem}_ms.pdf"
                    upload_pdf(pdf, key, "ms", paper_id)
        else:
            # Layout B: flat — q*.pdf and q*_ms.pdf intermixed in paper folder
            # (Biology, Chemistry, Human_Biology — downloaded from Supabase S3)
            for pdf in sorted(paper_dir.glob("*.pdf")):
                key = f"subjects/{db_subject}/pages/{paper_id}/{pdf.name}"
                file_type = "ms" if pdf.stem.endswith("_ms") else "qp"
                upload_pdf(pdf, key, file_type, paper_id)

    print(f"  {db_subject}: ok={counts['ok']}  skip={counts['skip']}  fail={counts['fail']}")
    total_ok += counts['ok']; total_skip += counts['skip']; total_fail += counts['fail']

# ── Manifest output ─────────────────────────────────────────────────────────
manifest_path = PROCESSED_DIR / "upload_manifest.json"
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump({
        "generated_at": int(time.time()),
        "bucket": R2_BUCKET,
        "public_url": R2_PUBLIC_URL,
        "totals": {"ok": total_ok, "skip": total_skip, "fail": total_fail},
        "files": manifest,
    }, f, indent=2)

print(f"\nTotal: ok={total_ok}  skip={total_skip}  fail={total_fail}  "
      f"({time.time()-start:.0f}s)")
print(f"Manifest written: {manifest_path}")
print(f"  -> Use this to update DB qp_page_url / ms_page_url after migration.")
