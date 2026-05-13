#!/usr/bin/env python3
"""
Phase 6: Delete BOTH Supabase storage buckets after R2 migration.

Targets:
  - question-pdfs  (~2.9 GB)
  - lectures       (~6 MB)

Refuses to run if any DB row still points at Supabase.

Usage:
    python -X utf8 scripts/delete_supabase_storage_buckets.py --dry-run
    python -X utf8 scripts/delete_supabase_storage_buckets.py
"""

import os, sys
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv(".env.local")

from supabase import create_client

DRY_RUN = "--dry-run" in sys.argv
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

DELETE_BATCH = 100
TARGETS = ["question-pdfs", "lectures"]

# ── Safety: confirm no DB row references Supabase storage ────────────────────
print("=" * 72)
print(f"SUPABASE BUCKET DELETION{' [DRY-RUN]' if DRY_RUN else ''}")
print("=" * 72)
print("\n[Safety] Checking for DB rows still on Supabase...")

pages_n = supabase.table("pages").select("id", count="exact") \
    .or_(f"qp_page_url.like.{SUPABASE_URL}%,ms_page_url.like.{SUPABASE_URL}%") \
    .execute().count or 0
try:
    lec_n = supabase.table("lectures").select("id", count="exact") \
        .like("file_url", f"{SUPABASE_URL}%").execute().count or 0
except Exception:
    lec_n = 0

print(f"    pages on Supabase    : {pages_n}")
print(f"    lectures on Supabase : {lec_n}")

if pages_n or lec_n:
    print("\nABORT: DB still references Supabase storage. Run the SQL URL-flip first.")
    sys.exit(1)

print("    OK — all DB rows point at R2.\n")

# ── Walk + delete each target bucket ────────────────────────────────────────
def walk(bucket: str, prefix: str = "") -> list[str]:
    try:
        items = supabase.storage.from_(bucket).list(prefix, {"limit": 1000})
    except Exception as e:
        print(f"  list error {bucket}/{prefix}: {e}"); return []
    out = []
    for item in items:
        full = f"{prefix}/{item['name']}" if prefix else item["name"]
        if item.get("id") is None:
            out.extend(walk(bucket, full))
        else:
            out.append(full)
    return out

grand_total = 0
for bucket in TARGETS:
    print(f"[Bucket: {bucket}]")
    paths = walk(bucket)
    print(f"    Files found: {len(paths):,}")

    if DRY_RUN:
        print(f"    DRY-RUN: would delete {len(paths):,} files\n")
        grand_total += len(paths)
        continue

    deleted = 0
    for i in range(0, len(paths), DELETE_BATCH):
        batch = paths[i:i + DELETE_BATCH]
        try:
            supabase.storage.from_(bucket).remove(batch)
            deleted += len(batch)
        except Exception as e:
            print(f"    batch error: {e}")

    print(f"    Deleted: {deleted:,}\n")
    grand_total += deleted

print(f"Total {'would delete' if DRY_RUN else 'deleted'}: {grand_total:,} files")
if not DRY_RUN:
    print("\nSupabase storage cleared. Check dashboard — should show <10 MB total.")
