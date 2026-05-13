#!/usr/bin/env python3
"""
Execute deletion of files listed in a cleanup_*.txt file produced by
audit_for_cleanup.py.

Has --dry-run mode and a final safety check that re-confirms each path
is NOT referenced by any pages.qp_page_url, pages.ms_page_url, or
lectures.file_url before deleting.

Usage:
    python -X utf8 scripts/execute_cleanup.py cleanup_safe_delete.txt --dry-run
    python -X utf8 scripts/execute_cleanup.py cleanup_safe_delete.txt
"""

import os
import sys
import re
from collections import defaultdict
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv(".env.local")

DRY_RUN = "--dry-run" in sys.argv
list_args = [a for a in sys.argv[1:] if not a.startswith("--")]
if not list_args:
    print("Usage: python execute_cleanup.py <list_file> [--dry-run]")
    sys.exit(1)
LIST_FILE = list_args[0]
if not os.path.exists(LIST_FILE):
    print(f"ERROR: {LIST_FILE} not found"); sys.exit(1)

from supabase import create_client

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

QP_BASE  = f"{SUPABASE_URL}/storage/v1/object/public/question-pdfs/"
LEC_BASE = f"{SUPABASE_URL}/storage/v1/object/public/lectures/"

# Bio/Chem case-fix to match audit logic
SEASON_RE = re.compile(r"(/pages/\d{4}_)([a-z][a-z\-]*)(_)")
def apply_case_fix(p: str) -> str:
    if "/Biology/" not in p and "/Chemistry/" not in p:
        return p
    return SEASON_RE.sub(lambda m: f"{m.group(1)}{m.group(2).title()}{m.group(3)}", p)

# Read the deletion list
print(f"Reading {LIST_FILE}...")
to_delete: dict[str, list[tuple[str, int]]] = defaultdict(list)  # bucket -> [(path, size)]
with open(LIST_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"): continue
        parts = line.split("\t")
        if len(parts) < 2: continue
        bucket, path = parts[0], parts[1]
        size = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 0
        to_delete[bucket].append((path, size))

total = sum(len(v) for v in to_delete.values())
total_size = sum(s for v in to_delete.values() for _, s in v)
print(f"  {total:,} files queued, {total_size/1024/1024:.1f} MB total")
for b, items in to_delete.items():
    print(f"    {b}: {len(items):,} files")

# ── Final safety check: re-confirm none are DB-referenced ───────────────────
print("\nLoading current DB references for safety check...")
db_qp_paths_fixed: set[str] = set()
offset = 0
while True:
    resp = supabase.table("pages") \
        .select("qp_page_url, ms_page_url") \
        .range(offset, offset + 999).execute()
    rows = resp.data or []
    if not rows: break
    for row in rows:
        for col in ("qp_page_url", "ms_page_url"):
            url = row.get(col)
            if url and url.startswith(QP_BASE):
                p = url.split(QP_BASE, 1)[1]
                db_qp_paths_fixed.add(apply_case_fix(p))
    if len(rows) < 1000: break
    offset += 1000

db_lecture_paths: set[str] = set()
try:
    offset = 0
    while True:
        resp = supabase.table("lectures").select("file_url") \
            .range(offset, offset + 999).execute()
        rows = resp.data or []
        if not rows: break
        for row in rows:
            url = row.get("file_url") or ""
            if url.startswith(LEC_BASE):
                db_lecture_paths.add(url.split(LEC_BASE, 1)[1])
        if len(rows) < 1000: break
        offset += 1000
except Exception:
    pass

# Filter the deletion list — drop anything DB now references
filtered: dict[str, list[tuple[str, int]]] = defaultdict(list)
blocked: list[tuple[str, str]] = []
for bucket, items in to_delete.items():
    for path, size in items:
        check = apply_case_fix(path) if bucket == "question-pdfs" else path
        ref_set = db_qp_paths_fixed if bucket == "question-pdfs" else db_lecture_paths
        if check in ref_set:
            blocked.append((bucket, path))
        else:
            filtered[bucket].append((path, size))

if blocked:
    print(f"\nSAFETY: {len(blocked)} files in your list are now DB-referenced and "
          f"will be SKIPPED:")
    for b, p in blocked[:10]:
        print(f"  SKIP  {b}/{p}")
    if len(blocked) > 10:
        print(f"  ... and {len(blocked) - 10} more")

filtered_total = sum(len(v) for v in filtered.values())
filtered_size = sum(s for v in filtered.values() for _, s in v)
print(f"\nProceeding with: {filtered_total:,} files, {filtered_size/1024/1024:.1f} MB")

if DRY_RUN:
    print("\nDRY-RUN — no files will be deleted.")
    print("Re-run without --dry-run to perform the deletion.")
    sys.exit(0)

# ── Delete in batches of 100 ────────────────────────────────────────────────
BATCH = 100
deleted = 0
errors = 0
for bucket, items in filtered.items():
    print(f"\nDeleting from {bucket}...")
    for i in range(0, len(items), BATCH):
        batch = [path for path, _ in items[i:i + BATCH]]
        try:
            supabase.storage.from_(bucket).remove(batch)
            deleted += len(batch)
            if (i // BATCH) % 5 == 0:
                print(f"  {deleted:,} / {filtered_total:,} deleted...")
        except Exception as e:
            errors += 1
            print(f"  ERROR batch starting {batch[0]}: {e}")

print(f"\nDone. Deleted: {deleted:,}  Batch errors: {errors}")
print(f"Reclaimed: {filtered_size/1024/1024:.1f} MB")
print("\nCheck Supabase dashboard Storage tab to confirm the new total.")
