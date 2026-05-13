#!/usr/bin/env python3
"""
Migrate lecture files from local disk -> Appwrite, then UPDATE lectures.file_url.

Why local disk: when Supabase is quota-restricted, public URLs return 402,
so we can't download from Supabase. You either:
  (a) have the lectures saved locally already, or
  (b) download them once via Supabase Dashboard -> Storage -> lectures
      and place them under data/lectures_export/ keeping the same path.

Local layout expected:
  data/lectures_export/<subject_id>/week_<n>/<lesson>/<filename.ext>

Each row in `lectures` table has:
  file_url    - currently a Supabase URL containing the path
  file_name   - original filename
  ...

Usage:
    pip install requests psycopg2-binary python-dotenv
    python -X utf8 scripts/migrate_lectures_to_appwrite.py --dry-run
    python -X utf8 scripts/migrate_lectures_to_appwrite.py
"""

import os, sys, json, mimetypes
from pathlib import Path
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv(".env.local")

DRY_RUN = "--dry-run" in sys.argv

try:
    import psycopg2
    import psycopg2.extras
    import requests
except ImportError:
    print("ERROR: pip install psycopg2-binary requests"); sys.exit(1)

DB_URL    = os.getenv("DATABASE_URL")
ENDPOINT  = os.getenv("APPWRITE_ENDPOINT", "https://sgp.cloud.appwrite.io/v1")
PROJECT   = os.getenv("APPWRITE_PROJECT_ID")
API_KEY   = os.getenv("APPWRITE_API_KEY")
BUCKET    = os.getenv("APPWRITE_BUCKET_ID", "grademax-lectures")
PUBLIC_EP = os.getenv("NEXT_PUBLIC_APPWRITE_ENDPOINT", ENDPOINT)
PUBLIC_PJ = os.getenv("NEXT_PUBLIC_APPWRITE_PROJECT_ID", PROJECT)
PUBLIC_BK = os.getenv("NEXT_PUBLIC_APPWRITE_BUCKET_ID", BUCKET)

LOCAL_BASE = Path("data/lectures_export")

if not all([DB_URL, PROJECT, API_KEY]):
    print("ERROR: DATABASE_URL + APPWRITE_PROJECT_ID + APPWRITE_API_KEY must be set")
    sys.exit(1)

H = {"X-Appwrite-Project": PROJECT, "X-Appwrite-Key": API_KEY}

def upload_file(file_path: Path) -> str | None:
    """Upload to Appwrite and return file ID."""
    if DRY_RUN: return f"DRYRUN_{file_path.stem}"
    mt = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, mt)}
        data = {"fileId": "unique()", "permissions[]": 'read("any")'}
        r = requests.post(f"{ENDPOINT}/storage/buckets/{BUCKET}/files",
                          headers=H, files=files, data=data, timeout=120)
    if r.status_code in (200, 201):
        return r.json()["$id"]
    print(f"    upload failed: {r.status_code} {r.text[:200]}")
    return None

# ── Connect ─────────────────────────────────────────────────────────────────
conn = psycopg2.connect(DB_URL)
conn.autocommit = False
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("SELECT id, file_url, file_name, subject_id, week_number, lesson_name "
            "FROM lectures WHERE file_url LIKE %s OR file_url LIKE %s",
            ("%supabase.co/storage%", "%/lectures/%"))
rows = cur.fetchall()
print(f"Found {len(rows)} lecture rows still on Supabase")

ok = fail = missing = 0
for row in rows:
    sanitized = (row['lesson_name'] or '').replace('/', '_')
    rel = f"{row['subject_id']}/week_{row['week_number']}/{sanitized}/{row['file_name']}"
    local = LOCAL_BASE / rel

    print(f"\n  Row {row['id']}: {rel}")

    if not local.exists():
        # try a fallback: file directly under LOCAL_BASE/<file_name>
        alt = LOCAL_BASE / row['file_name']
        if alt.exists():
            local = alt
        else:
            print(f"    LOCAL FILE MISSING: {local}")
            print(f"    (Place the file at this path or under {alt} and re-run)")
            missing += 1
            continue

    file_id = upload_file(local)
    if not file_id:
        fail += 1; continue

    new_url = f"{PUBLIC_EP}/storage/buckets/{PUBLIC_BK}/files/{file_id}/view?project={PUBLIC_PJ}"
    if not DRY_RUN:
        cur.execute("UPDATE lectures SET file_url = %s WHERE id = %s",
                    (new_url, row['id']))
    print(f"    {'WOULD UPDATE' if DRY_RUN else 'UPDATED'}: {new_url}")
    ok += 1

if not DRY_RUN:
    conn.commit()
    print("\nCommitted.")
else:
    conn.rollback()
    print("\nDRY-RUN — nothing committed.")

cur.close(); conn.close()
print(f"\nResult: ok={ok}  failed={fail}  missing-locally={missing}")
