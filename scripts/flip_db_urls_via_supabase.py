#!/usr/bin/env python3
"""
Same job as flip_db_urls_to_r2.py but uses supabase-py (PostgREST)
instead of direct postgres. Avoids the pooler/tenant issue.

Run AFTER the Supabase project is unblocked (storage quota restored to <1 GB).

Three passes:
  1. Bio/Chem case-fix: /pages/2012_jan_1/ -> /pages/2012_Jan_1/
  2. URL flip:           Supabase question-pdfs -> R2
  3. Disable orphaned:   NULL-out Bio/Chem/HumanBio rows so they don't render with 402 URLs

Usage:
    python -X utf8 scripts/flip_db_urls_via_supabase.py --dry-run
    python -X utf8 scripts/flip_db_urls_via_supabase.py
    python -X utf8 scripts/flip_db_urls_via_supabase.py --skip-disable  # keep Bio/Chem rows live
"""

import os, sys, re
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv(".env.local")

from supabase import create_client

DRY_RUN       = "--dry-run" in sys.argv
SKIP_DISABLE  = "--skip-disable" in sys.argv

SUPABASE_URL  = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY  = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
R2_PUBLIC_URL = (os.getenv("NEXT_PUBLIC_R2_PUBLIC_URL") or "").rstrip("/")

if not all([SUPABASE_URL, SUPABASE_KEY, R2_PUBLIC_URL]):
    print("ERROR: missing env vars"); sys.exit(1)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)
QP_BASE  = f"{SUPABASE_URL}/storage/v1/object/public/question-pdfs/"
LEC_BASE = f"{SUPABASE_URL}/storage/v1/object/public/lectures/"

# Bio/Chem regex case-fix (applied row-by-row in Python since PostgREST has no regexp_replace)
SEASON_RE = re.compile(r"(/pages/\d{4}_)([a-z][a-z\-]*)(_)")
def fix_case(url):
    if not url or ("/Biology/" not in url and "/Chemistry/" not in url):
        return url
    return SEASON_RE.sub(lambda m: f"{m.group(1)}{m.group(2).title()}{m.group(3)}", url)

print("=" * 72)
print(f"DB URL FLIP via PostgREST{' [DRY-RUN]' if DRY_RUN else ''}")
print(f"  source: {QP_BASE}")
print(f"  target: {R2_PUBLIC_URL}/")
print("=" * 72)

# ── 1+2: case-fix + provider flip in one pass ──────────────────────────────
print("\n[1+2] Fetching all pages with non-null qp_page_url...")
all_rows = []
offset = 0
while True:
    resp = sb.table("pages") \
        .select("id, qp_page_url, ms_page_url") \
        .not_.is_("qp_page_url", "null") \
        .range(offset, offset + 999).execute()
    rows = resp.data or []
    if not rows: break
    all_rows.extend(rows)
    if len(rows) < 1000: break
    offset += 1000

print(f"  {len(all_rows):,} rows to consider")

updates = []
for row in all_rows:
    new_qp = fix_case(row.get("qp_page_url"))
    new_ms = fix_case(row.get("ms_page_url"))
    # Flip provider
    if new_qp and new_qp.startswith(QP_BASE):
        new_qp = new_qp.replace(QP_BASE, R2_PUBLIC_URL + "/")
    if new_ms and new_ms.startswith(QP_BASE):
        new_ms = new_ms.replace(QP_BASE, R2_PUBLIC_URL + "/")
    if new_qp != row.get("qp_page_url") or new_ms != row.get("ms_page_url"):
        updates.append({"id": row["id"], "qp": new_qp, "ms": new_ms})

print(f"  Rows needing update: {len(updates):,}")

if not DRY_RUN and updates:
    done = 0
    for u in updates:
        sb.table("pages").update({"qp_page_url": u["qp"], "ms_page_url": u["ms"]}) \
          .eq("id", u["id"]).execute()
        done += 1
        if done % 200 == 0:
            print(f"  ...{done:,}/{len(updates):,}")
    print(f"  Updated {done:,} rows")

# ── 3: NULL-out Bio/Chem/HumanBio rows ──────────────────────────────────────
if SKIP_DISABLE:
    print("\n[3] --skip-disable passed; Bio/Chem/HumanBio rows kept as-is")
else:
    print("\n[3] Disabling Bio/Chem/HumanBio rows (NULL-out URLs)")
    sub_resp = sb.table("subjects").select("id, name").execute()
    target_ids = [s["id"] for s in (sub_resp.data or [])
                  if s["name"] in ("Biology", "Chemistry", "Human Biology", "Human_Biology")]
    print(f"  target subject IDs: {target_ids}")

    if target_ids:
        papers_resp = sb.table("papers").select("id").in_("subject_id", target_ids).execute()
        paper_ids = [p["id"] for p in (papers_resp.data or [])]
        print(f"  papers in those subjects: {len(paper_ids)}")

        if paper_ids and not DRY_RUN:
            # Batch the IN clause (PostgREST has URL length limits)
            BATCH = 500
            disabled = 0
            for i in range(0, len(paper_ids), BATCH):
                batch = paper_ids[i:i+BATCH]
                r = sb.table("pages") \
                    .update({"qp_page_url": None, "ms_page_url": None}) \
                    .in_("paper_id", batch).execute()
                disabled += len(r.data or [])
            print(f"  NULL-ed out {disabled:,} pages")

# ── 4: Verify ───────────────────────────────────────────────────────────────
print("\n[4] Verification — rows still pointing at Supabase storage:")
r1 = sb.table("pages").select("id", count="exact") \
    .like("qp_page_url", f"{SUPABASE_URL}%").execute()
r2 = sb.table("pages").select("id", count="exact") \
    .like("ms_page_url", f"{SUPABASE_URL}%").execute()
print(f"  pages.qp_page_url on Supabase: {r1.count or 0}")
print(f"  pages.ms_page_url on Supabase: {r2.count or 0}")

print("\nDone.")
