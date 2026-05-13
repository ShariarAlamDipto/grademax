#!/usr/bin/env python3
"""
Pre-migration sanity check: do any pages.qp_page_url / ms_page_url rows
contain RELATIVE paths instead of full https:// URLs?

If yes, pdfUtils.ts:toAbsolutePdfUrl uses SUPABASE_STORAGE_BASE to fill in
the host -- those rows would break after Supabase storage is deleted unless
we also fix them or update pdfUtils.ts.

Usage:
    python -X utf8 scripts/check_url_formats.py
"""

import os
import sys
from collections import Counter
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv(".env.local")

from supabase import create_client

supabase = create_client(
    os.getenv("NEXT_PUBLIC_SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
)
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")

print("=" * 70)
print("URL FORMAT AUDIT")
print("=" * 70)

cats = Counter()
samples_by_cat: dict[str, list[str]] = {}

offset = 0
while True:
    resp = (
        supabase.table("pages")
        .select("qp_page_url, ms_page_url")
        .range(offset, offset + 999)
        .execute()
    )
    rows = resp.data
    if not rows:
        break
    for row in rows:
        for col in ("qp_page_url", "ms_page_url"):
            url = row.get(col)
            if not url:
                cats[f"{col}: NULL"] += 1
                continue
            if url.startswith(SUPABASE_URL):
                cat = f"{col}: full Supabase URL"
            elif url.startswith("https://") or url.startswith("http://"):
                cat = f"{col}: full non-Supabase URL"
            elif url.startswith("subjects/"):
                cat = f"{col}: relative path 'subjects/...'"
            elif url.startswith("/"):
                cat = f"{col}: relative path leading slash"
            else:
                cat = f"{col}: other"
            cats[cat] += 1
            if cat not in samples_by_cat:
                samples_by_cat[cat] = []
            if len(samples_by_cat[cat]) < 3:
                samples_by_cat[cat].append(url[:120])
    if len(rows) < 1000:
        break
    offset += 1000

print()
for cat in sorted(cats):
    print(f"  {cats[cat]:6,d}  {cat}")
    for s in samples_by_cat.get(cat, [])[:2]:
        print(f"          e.g. {s}")
print()

# Final verdict
relative_count = sum(v for k, v in cats.items() if "relative" in k)
non_supabase_full = sum(v for k, v in cats.items() if "non-Supabase URL" in k)

print("VERDICT:")
if relative_count == 0:
    print("  All non-null URLs are absolute — safe to delete Supabase after migration.")
    print("  pdfUtils.ts:toAbsolutePdfUrl fallback is never triggered.")
else:
    print(f"  WARNING: {relative_count:,} rows have relative paths.")
    print("  pdfUtils.ts:toAbsolutePdfUrl will prepend SUPABASE_STORAGE_BASE for these.")
    print("  Action required: either fix these rows to full URLs, or update")
    print("  pdfUtils.ts SUPABASE_STORAGE_BASE to point at R2 after migration.")

if non_supabase_full > 0:
    print(f"  Note: {non_supabase_full:,} URLs already point at non-Supabase host.")
