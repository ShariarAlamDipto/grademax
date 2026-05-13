#!/usr/bin/env python3
"""
Bulk-download segmented PDFs for Biology, Chemistry, Human_Biology from Supabase
Storage using its S3-compatible endpoint.

We hit Supabase's S3 interface directly (same network, same auth gateway, but a
different code path than the public CDN URLs that are returning 402 right now).

Output layout (matches what upload_local_pdfs_to_r2.py expects):
  data/processed/Biology/{paper}/q1.pdf q1_ms.pdf ...
  data/processed/Chemistry/{paper}/...
  data/processed/Human_Biology/{paper}/...

Usage:
    pip install boto3 python-dotenv
    # Add to .env.local:
    #   SUPABASE_S3_ACCESS_KEY_ID=...
    #   SUPABASE_S3_SECRET_ACCESS_KEY=...
    #   SUPABASE_S3_REGION=ap-southeast-1   (your project region)
    python -X utf8 scripts/download_bio_chem_via_s3.py --test       # download 1 paper
    python -X utf8 scripts/download_bio_chem_via_s3.py --subject Biology
    python -X utf8 scripts/download_bio_chem_via_s3.py              # all 3 subjects
"""

import os, sys, time
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv(".env.local")

TEST_MODE = "--test" in sys.argv
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
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
ACCESS_KEY   = os.getenv("SUPABASE_S3_ACCESS_KEY_ID")
SECRET_KEY   = os.getenv("SUPABASE_S3_SECRET_ACCESS_KEY")
S3_REGION    = os.getenv("SUPABASE_S3_REGION", "ap-southeast-1")

if not (ACCESS_KEY and SECRET_KEY):
    print("ERROR: SUPABASE_S3_ACCESS_KEY_ID + SUPABASE_S3_SECRET_ACCESS_KEY must be set")
    print("  Get them from Supabase Dashboard -> Project Settings -> Storage -> S3 Connection")
    sys.exit(1)

if not SUPABASE_URL:
    print("ERROR: NEXT_PUBLIC_SUPABASE_URL not set"); sys.exit(1)

# Supabase S3-compatible endpoint
PROJECT_REF = SUPABASE_URL.split("//")[1].split(".")[0]  # e.g., tybaetnvnfgniotdfxze
S3_ENDPOINT = f"https://{PROJECT_REF}.supabase.co/storage/v1/s3"
BUCKET = "question-pdfs"

# Subjects to recover and their target local folder
SUBJECTS = [
    ("Biology",       "Biology"),
    ("Chemistry",     "Chemistry"),
    ("Human_Biology", "Human_Biology"),
]

PROCESSED = Path("data/processed")

# ── Connect ─────────────────────────────────────────────────────────────────
print(f"S3 endpoint: {S3_ENDPOINT}")
print(f"Bucket     : {BUCKET}\n")

s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    region_name=S3_REGION,
    config=Config(retries={"max_attempts": 5, "mode": "standard"},
                  signature_version="s3v4"),
)

def head(key: str) -> int | None:
    try:
        return s3.head_object(Bucket=BUCKET, Key=key)["ContentLength"]
    except ClientError:
        return None

def get(key: str) -> bytes | None:
    try:
        return s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "?")
        if code != "NoSuchKey":
            print(f"    GET {key}: {code}")
        return None

# ── Probe: confirm S3 endpoint works (not blocked by quota) ─────────────────
print("Probing S3 endpoint with HeadBucket...")
try:
    s3.head_bucket(Bucket=BUCKET)
    print("  OK — bucket accessible\n")
except ClientError as e:
    code = e.response.get("Error", {}).get("Code", "?")
    msg = e.response.get("Error", {}).get("Message", "")
    print(f"  FAILED ({code}): {msg}")
    if "402" in str(e) or "Payment" in msg or "quota" in msg.lower():
        print("\n  Supabase S3 endpoint is also quota-blocked.")
        print("  Fall back to manual Dashboard export, or upgrade to Pro temporarily.")
    sys.exit(1)

# ── List + download per subject ─────────────────────────────────────────────
print("=" * 72)
print(f"DOWNLOADING BIO / CHEM / HUMAN BIOLOGY{' [TEST: 1 paper only]' if TEST_MODE else ''}")
print("=" * 72)

total_files = total_bytes = 0
errors = 0

for storage_subj, local_folder in SUBJECTS:
    if SUBJECT_FILTER and SUBJECT_FILTER not in (storage_subj, local_folder):
        continue
    prefix = f"subjects/{storage_subj}/pages/"
    print(f"\n[{storage_subj}]  prefix={prefix}")

    # List ALL keys under this prefix
    keys: list[tuple[str, int]] = []  # (key, size)
    paginator = s3.get_paginator("list_objects_v2")
    try:
        for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append((obj["Key"], obj["Size"]))
    except ClientError as e:
        print(f"  LIST failed: {e}"); errors += 1; continue

    # Aggregate by paper folder for clean reporting
    by_paper: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for key, size in keys:
        # subjects/Biology/pages/2012_Jan_1/q1.pdf  ->  paper="2012_Jan_1"
        parts = key.split("/")
        if len(parts) >= 5:
            by_paper[parts[3]].append((key, size))

    print(f"  Found {len(keys):,} files across {len(by_paper)} paper folders")

    if TEST_MODE:
        sample_paper = next(iter(by_paper))
        keys = by_paper[sample_paper]
        by_paper = {sample_paper: keys}
        print(f"  TEST: only downloading {sample_paper} ({len(keys)} files)")

    subj_ok = subj_skip = subj_fail = 0
    start = time.time()
    for paper, file_list in sorted(by_paper.items()):
        out_dir = PROCESSED / local_folder / paper
        out_dir.mkdir(parents=True, exist_ok=True)
        for key, size in file_list:
            filename = key.split("/")[-1]
            dest = out_dir / filename
            if dest.exists() and dest.stat().st_size == size:
                subj_skip += 1; continue
            data = get(key)
            if data is None:
                subj_fail += 1; continue
            dest.write_bytes(data)
            subj_ok += 1
            total_bytes += len(data)

        if (subj_ok + subj_skip) % 100 < len(file_list):
            elapsed = time.time() - start
            rate = (subj_ok + subj_skip) / elapsed if elapsed > 0 else 0
            print(f"  ... {paper}: ok={subj_ok} skip={subj_skip} fail={subj_fail} "
                  f"({rate:.0f}/s)")

    total_files += subj_ok
    print(f"  {storage_subj}: ok={subj_ok}  skip={subj_skip}  fail={subj_fail}  "
          f"({time.time()-start:.0f}s)")

print(f"\nDownloaded {total_files:,} files, {total_bytes/1024/1024:.1f} MB")
print(f"Errors: {errors}")
print(f"\nNext step: python -X utf8 scripts/upload_local_pdfs_to_r2.py")
print(f"  (after I update SUBJECT_MAP to include the 3 new locally-recovered subjects)")
