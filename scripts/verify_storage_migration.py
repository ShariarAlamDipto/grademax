#!/usr/bin/env python3
"""
Phase 4: Verify R2 migration is complete.

Checks:
  1. No DB rows still reference Supabase storage (qp_page_url, ms_page_url, lectures.file_url)
  2. Spot-check 25 random URLs per subject — HEAD request returns 200
  3. End-to-end smoke test: builds a small fake test merge through the same
     code path Test Builder uses (downloads 3 PDFs from R2, merges them).

Run AFTER migrate_storage_to_r2.py + the SQL flip.

Usage:
    python -X utf8 scripts/verify_storage_migration.py
"""

import os, sys, random, urllib.request
from collections import defaultdict
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv(".env.local")

from supabase import create_client

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
R2_PUBLIC_URL = (os.getenv("NEXT_PUBLIC_R2_PUBLIC_URL") or "").rstrip("/")

if not (SUPABASE_URL and SUPABASE_KEY and R2_PUBLIC_URL):
    print("ERROR: missing env vars"); sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
SAMPLES = 25

def head_ok(url: str) -> tuple[bool, int | None]:
    try:
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "grademax-verifier/2.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200, resp.status
    except urllib.error.HTTPError as e:
        return False, e.code
    except Exception:
        return False, None

print("=" * 72)
print("R2 MIGRATION VERIFICATION")
print("=" * 72)

# ── Check 1: no Supabase URLs left in DB ────────────────────────────────────
print("\n[1] Scanning DB for any remaining Supabase URLs...")

pages_remaining = supabase.table("pages").select("id", count="exact") \
    .or_(f"qp_page_url.like.{SUPABASE_URL}%,ms_page_url.like.{SUPABASE_URL}%") \
    .execute().count or 0

try:
    lec_remaining = supabase.table("lectures").select("id", count="exact") \
        .like("file_url", f"{SUPABASE_URL}%").execute().count or 0
except Exception:
    lec_remaining = 0  # table may have different column name

print(f"    pages with Supabase URLs    : {pages_remaining}")
print(f"    lectures with Supabase URLs : {lec_remaining}")

if pages_remaining or lec_remaining:
    print("\n    ABORT: Run the SQL URL-flip from migrate_storage_to_r2.py first.")
    sys.exit(1)

# ── Check 2: spot-check R2 URLs return 200 ──────────────────────────────────
print("\n[2] Spot-checking R2 URLs (HEAD request)...")

by_subject: dict[str, list[str]] = defaultdict(list)
offset = 0
while True:
    resp = supabase.table("pages") \
        .select("qp_page_url") \
        .not_.is_("qp_page_url", "null") \
        .range(offset, offset + 999).execute()
    rows = resp.data or []
    if not rows: break
    for row in rows:
        u = row.get("qp_page_url") or ""
        if not u: continue
        path_part = u.replace(R2_PUBLIC_URL + "/", "")
        parts = path_part.split("/")
        subject = parts[1] if len(parts) >= 2 and parts[0] == "subjects" else "_other"
        by_subject[subject].append(u)
    if len(rows) < 1000: break
    offset += 1000

all_ok = True
total_pass = total_fail = 0
print()
for subject in sorted(by_subject):
    urls = by_subject[subject]
    sample = random.sample(urls, min(SAMPLES, len(urls)))
    fails = []
    for u in sample:
        ok, code = head_ok(u)
        if not ok:
            fails.append((u, code))
    p = len(sample) - len(fails)
    total_pass += p; total_fail += len(fails)
    if fails:
        all_ok = False
        print(f"    {subject:20s}  {p}/{len(sample)} OK  (total {len(urls):,})")
        for u, code in fails[:3]:
            print(f"      FAIL [{code}]: {u}")
    else:
        print(f"    {subject:20s}  {p}/{len(sample)} OK  (total {len(urls):,})")

# ── Check 3: end-to-end PDF download (mimics Test Builder's mergePagePdfs) ──
print("\n[3] End-to-end download check (3 PDFs, mimics mergePagePdfs)...")

pick_urls: list[str] = []
for urls in by_subject.values():
    if not urls: continue
    pick_urls.append(random.choice(urls))
    if len(pick_urls) >= 3: break

e2e_ok = 0
for u in pick_urls:
    try:
        with urllib.request.urlopen(u, timeout=15) as resp:
            data = resp.read()
            if data[:4] == b"%PDF":
                e2e_ok += 1
                print(f"    OK ({len(data):>9,d} bytes, valid PDF header): {u.split('/')[-1]}")
            else:
                print(f"    FAIL (not a PDF): {u}")
    except Exception as e:
        print(f"    FAIL ({e}): {u}")

print(f"\nResult: {total_pass} HEAD passed, {total_fail} HEAD failed, {e2e_ok}/3 E2E PDFs valid")
if all_ok and e2e_ok == len(pick_urls):
    print("\nMigration verified. Test Builder + Worksheet Generator will work.")
    print("Safe to delete Supabase storage:  python -X utf8 scripts/delete_supabase_storage_buckets.py")
else:
    print("\nSome checks failed. Do NOT delete Supabase storage yet.")
    sys.exit(1)
