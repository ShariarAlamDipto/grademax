#!/usr/bin/env python3
"""
Create the Appwrite lectures bucket if it doesn't exist.

Idempotent: re-runs are no-ops.

Usage:
    pip install requests python-dotenv
    python -X utf8 scripts/setup_appwrite_bucket.py
"""

import os, sys, json
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv(".env.local")

import requests

ENDPOINT   = os.getenv("APPWRITE_ENDPOINT", "https://sgp.cloud.appwrite.io/v1")
PROJECT    = os.getenv("APPWRITE_PROJECT_ID")
API_KEY    = os.getenv("APPWRITE_API_KEY")
BUCKET_ID  = os.getenv("APPWRITE_BUCKET_ID", "grademax-lectures")
BUCKET_NAME = "GradeMax Lectures"

if not (PROJECT and API_KEY):
    print("ERROR: APPWRITE_PROJECT_ID + APPWRITE_API_KEY must be set in .env.local")
    sys.exit(1)

H = {
    "X-Appwrite-Project": PROJECT,
    "X-Appwrite-Key":     API_KEY,
    "Content-Type":       "application/json",
}

print(f"Checking bucket {BUCKET_ID} on {ENDPOINT}")

# 1. Try GET — does it already exist?
get = requests.get(f"{ENDPOINT}/storage/buckets/{BUCKET_ID}", headers=H, timeout=15)
if get.status_code == 200:
    info = get.json()
    print(f"  Bucket exists: name='{info.get('name')}' "
          f"size={info.get('maximumFileSize'):,} "
          f"public={'yes' if 'any' in (info.get('$permissions') or []) or any('read(\"any\")' in p for p in info.get('$permissions') or []) else 'no'}")
    sys.exit(0)
elif get.status_code != 404:
    print(f"  Unexpected response on GET: {get.status_code} {get.text[:300]}")
    sys.exit(1)

# 2. Create — public read for browser playback, server-side writes only.
print(f"  Bucket not found. Creating...")
payload = {
    "bucketId":          BUCKET_ID,
    "name":              BUCKET_NAME,
    "permissions":       ['read("any")'],
    "fileSecurity":      False,
    "enabled":           True,
    "maximumFileSize":   50 * 1000 * 1000,   # Appwrite free-tier max: 50 MB per file
    "allowedFileExtensions": ["pdf", "mp4", "m4v", "webm", "mov"],
    "compression":       "none",
    "encryption":        False,
    "antivirus":         False,
}

r = requests.post(f"{ENDPOINT}/storage/buckets", headers=H,
                  data=json.dumps(payload), timeout=15)

if r.status_code in (200, 201):
    info = r.json()
    print(f"  Created bucket {info.get('$id')} - '{info.get('name')}'")
    print(f"  Permissions: {info.get('$permissions')}")
    print(f"  Public read URL pattern:")
    print(f"    {ENDPOINT}/storage/buckets/{BUCKET_ID}/files/<FILE_ID>/view?project={PROJECT}")
else:
    print(f"  FAILED ({r.status_code}): {r.text[:500]}")
    sys.exit(1)
