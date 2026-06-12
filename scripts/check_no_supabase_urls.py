#!/usr/bin/env python3
"""
CI guard: fail with non-zero exit if any DB URL column still points at
Supabase Storage. Prevents future regressions where a code path
accidentally writes a Supabase URL after the Phase B/C migration to R2.

Runs daily from scheduled-jobs.yml and on every PR via a separate workflow.

Usage:
    python -X utf8 scripts/check_no_supabase_urls.py
    # exit 0 if clean, exit 1 if any leakage found
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv(".env.local")

from supabase import create_client

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if not all([SUPABASE_URL, SUPABASE_KEY]):
    print("ERROR: missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    sys.exit(2)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# Every URL column that should now point at Cloudflare R2.
# If any of these come back > 0, a writer regression has snuck in.
CHECKS = [
    ("pages", "qp_page_url"),
    ("pages", "ms_page_url"),
    # ("questions", ...) removed — table dropped by migration 11; pages is canonical.
    ("papers", "pdf_url"),
    ("papers", "markscheme_pdf_url"),
    ("papers", "data_file_url"),
    ("lectures", "file_url"),
]

print(f"Scanning for Supabase Storage URL leakage in DB...")
print(f"  source pattern: {SUPABASE_URL}/storage/v1/object/public/%")
print()

total_leaked = 0
for table, col in CHECKS:
    try:
        r = (
            sb.table(table)
            .select("id", count="exact", head=True)
            .like(col, f"{SUPABASE_URL}/storage/v1/object/public/%")
            .execute()
        )
        n = r.count or 0
        status = "OK" if n == 0 else "LEAK"
        print(f"  [{status:4s}] {table}.{col:24s} {n:>5d} rows")
        total_leaked += n
    except Exception as e:
        # Skip columns that legitimately don't exist (older branches)
        msg = str(e)
        if "does not exist" in msg:
            print(f"  [SKIP] {table}.{col:24s} (column not in this schema)")
        else:
            print(f"  [ERR ] {table}.{col:24s} {msg[:80]}")
            total_leaked += 1  # treat unknown errors as failures

print()
if total_leaked == 0:
    print("PASS: no Supabase Storage URLs remain in DB columns that should be on R2.")
    sys.exit(0)
else:
    print(f"FAIL: {total_leaked} DB rows still reference Supabase Storage.")
    print("      Inspect the offending writer and either move the file to R2")
    print("      or remove the offending row.")
    sys.exit(1)
