#!/usr/bin/env python3
"""
Unified migration: Supabase Storage  ->  Cloudflare R2.

Migrates BOTH heavy buckets in one pass:
  - question-pdfs  (~2.9 GB, used by Test Builder + Worksheet Generator)
  - lectures       (~6 MB,  used by admin lecture upload/playback)

Files are uploaded into the EXISTING R2 bucket (grademax-papers) under prefixes:
  question-pdfs/*  ->  R2 key:  subjects/.../pages/.../q1.pdf
  lectures/*       ->  R2 key:  lectures/...

Includes:
  - Generic Bio/Chem case-fix that handles ALL season variants
    (jan, jan-feb, feb-mar, may-jun, oct-nov) via regex.
  - --subject filter to test on one subject first.
  - --dry-run mode.
  - Skips files already in R2 (resumable).
  - Updates BOTH qp_page_url and ms_page_url, with fixed WHERE clause.

Usage:
    pip install boto3 supabase python-dotenv
    python -X utf8 scripts/migrate_storage_to_r2.py --dry-run
    python -X utf8 scripts/migrate_storage_to_r2.py --subject "Human Biology"   # pilot
    python -X utf8 scripts/migrate_storage_to_r2.py                              # full run

Env vars (already in .env.local from existing R2 setup):
    R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME,
    NEXT_PUBLIC_R2_PUBLIC_URL, NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
"""

import os
import re
import sys
import time
import urllib.request
from collections import defaultdict
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv(".env.local")

DRY_RUN  = "--dry-run" in sys.argv
VERBOSE  = "--verbose" in sys.argv
SUBJECT_FILTER: str | None = None
for i, arg in enumerate(sys.argv):
    if arg == "--subject" and i + 1 < len(sys.argv):
        SUBJECT_FILTER = sys.argv[i + 1]

try:
    import boto3
    from botocore.exceptions import ClientError
    from botocore.config import Config
except ImportError:
    print("ERROR: pip install boto3"); sys.exit(1)

try:
    from supabase import create_client
except ImportError:
    print("ERROR: pip install supabase"); sys.exit(1)

# ── Config (uses your existing R2 setup) ─────────────────────────────────────
SUPABASE_URL    = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY    = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
R2_ACCOUNT_ID   = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY   = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET       = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET       = os.getenv("R2_BUCKET_NAME", "grademax-papers")
R2_PUBLIC_URL   = (os.getenv("NEXT_PUBLIC_R2_PUBLIC_URL") or "").rstrip("/")

QP_BUCKET = "question-pdfs"
LECTURES_BUCKET = "lectures"
SB_QP_BASE = f"{SUPABASE_URL}/storage/v1/object/public/{QP_BUCKET}/"
SB_LEC_BASE = f"{SUPABASE_URL}/storage/v1/object/public/{LECTURES_BUCKET}/"

for name, val in [
    ("NEXT_PUBLIC_SUPABASE_URL", SUPABASE_URL),
    ("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_KEY),
    ("R2_ACCOUNT_ID", R2_ACCOUNT_ID),
    ("R2_ACCESS_KEY_ID", R2_ACCESS_KEY),
    ("R2_SECRET_ACCESS_KEY", R2_SECRET),
    ("NEXT_PUBLIC_R2_PUBLIC_URL", R2_PUBLIC_URL),
]:
    if not val:
        print(f"ERROR: {name} not set in .env.local"); sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
r2 = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET,
    region_name="auto",
    config=Config(retries={"max_attempts": 5, "mode": "standard"}),
)

# ── Bio/Chem case fix (regex-based — handles ALL season variants) ───────────
SEASON_PATH_RE = re.compile(
    r"(/pages/\d{4}_)([a-z][a-z\-]*)(_)",
    flags=re.IGNORECASE,
)

def fix_bio_chem_path(url: str) -> str:
    """For Biology/Chemistry: title-case the season segment in the path.
    Idempotent — running on already-Title-Case paths is a no-op.
    Examples:
       2012_jan_1     -> 2012_Jan_1
       2014_may-jun_2 -> 2014_May-Jun_2
       2025_oct-nov_1 -> 2025_Oct-Nov_1
    """
    if "/Biology/" not in url and "/Chemistry/" not in url:
        return url
    return SEASON_PATH_RE.sub(
        lambda m: f"{m.group(1)}{m.group(2).title()}{m.group(3)}",
        url,
    )

# ── R2 helpers ───────────────────────────────────────────────────────────────
def r2_exists(key: str) -> bool:
    try:
        r2.head_object(Bucket=R2_BUCKET, Key=key); return True
    except ClientError:
        return False

def r2_upload(key: str, data: bytes, content_type: str) -> bool:
    if DRY_RUN: return True
    for attempt in range(3):
        try:
            r2.put_object(
                Bucket=R2_BUCKET, Key=key, Body=data,
                ContentType=content_type,
                CacheControl="public, max-age=31536000, immutable",
            )
            return True
        except ClientError as e:
            if attempt == 2:
                if VERBOSE: print(f"    upload error: {e}")
                return False
            time.sleep(1.5 ** attempt)
    return False

def http_get(url: str) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "grademax-migrator/2.0"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            return resp.read()
    except Exception as e:
        if VERBOSE: print(f"    download error: {e}")
        return None

# ─────────────────────────────────────────────────────────────────────────────
# PASS 1: Migrate question-pdfs (the heavy lift)
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 72)
print(f"GRADEMAX STORAGE MIGRATION{' [DRY-RUN]' if DRY_RUN else ''}"
      f"{' subject=' + SUBJECT_FILTER if SUBJECT_FILTER else ''}")
print(f"Source : {SUPABASE_URL}/storage/v1/object/public/")
print(f"Target : {R2_PUBLIC_URL}/  (bucket: {R2_BUCKET})")
print("=" * 72)
print("\n[1/3] question-pdfs  ->  R2 (subjects/...)")

# Build the URL set, applying Bio/Chem case fix as we go
print("    Loading pages.qp_page_url + ms_page_url + paper subject...")
url_to_db_rows: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
# url -> [(row_id, column, original_url)]   so we can update DB later

offset = 0
while True:
    resp = (supabase.table("pages")
            .select("id, qp_page_url, ms_page_url, papers(subjects(name))")
            .not_.is_("qp_page_url", "null")
            .range(offset, offset + 999).execute())
    rows = resp.data or []
    if not rows: break
    for row in rows:
        subject = (((row.get("papers") or {}).get("subjects") or {}) or {}).get("name") or ""
        if SUBJECT_FILTER and subject != SUBJECT_FILTER:
            continue
        for col in ("qp_page_url", "ms_page_url"):
            orig = row.get(col)
            if not orig: continue
            fixed = fix_bio_chem_path(orig)
            url_to_db_rows[fixed].append((row["id"], col, orig))
    if len(rows) < 1000: break
    offset += 1000

case_fixes = sum(1 for url, refs in url_to_db_rows.items()
                 for _, _, orig in refs if orig != url)
if case_fixes:
    print(f"    Bio/Chem case fixes detected: {case_fixes} URL refs will be normalised")

supabase_urls = sorted(u for u in url_to_db_rows if u.startswith(SB_QP_BASE))
print(f"    Migrating {len(supabase_urls):,} unique question-pdfs URLs")

stats = defaultdict(lambda: {"ok": 0, "skip": 0, "fail": 0})
total = {"ok": 0, "fail": 0, "skip": 0}
start = time.time()

for idx, url in enumerate(supabase_urls, 1):
    key = url.split(SB_QP_BASE, 1)[1]
    parts = key.split("/")
    subj = parts[1] if len(parts) >= 2 else "unknown"

    if not DRY_RUN and r2_exists(key):
        stats[subj]["skip"] += 1; total["skip"] += 1; continue

    data = http_get(url)
    if not data:
        # try the original (non-case-fixed) URL too — in case Bio/Chem
        # storage actually has lowercase folders for this row
        for orig_row in url_to_db_rows[url]:
            alt = orig_row[2]
            if alt != url:
                data = http_get(alt)
                if data: break

    if not data:
        stats[subj]["fail"] += 1; total["fail"] += 1
        print(f"    [{idx}/{len(supabase_urls)}] FAIL download: {key}"); continue

    if r2_upload(key, data, "application/pdf"):
        stats[subj]["ok"] += 1; total["ok"] += 1
        if VERBOSE or idx % 100 == 0:
            elapsed = time.time() - start
            rate = idx / elapsed if elapsed else 0
            eta_m = (len(supabase_urls) - idx) / rate / 60 if rate else 0
            print(f"    [{idx}/{len(supabase_urls)}] OK  {key}  ({rate:.0f}/s ETA {eta_m:.0f}m)")
    else:
        stats[subj]["fail"] += 1; total["fail"] += 1
        print(f"    [{idx}/{len(supabase_urls)}] FAIL upload: {key}")

print(f"\n    question-pdfs: ok={total['ok']} skip={total['skip']} fail={total['fail']}  "
      f"({time.time()-start:.0f}s)")
print("    Per-subject:")
for subj in sorted(stats):
    s = stats[subj]
    print(f"      {subj:22s}  ok={s['ok']:5d}  skip={s['skip']:5d}  fail={s['fail']:5d}")

# ─────────────────────────────────────────────────────────────────────────────
# PASS 2: Migrate lectures bucket (small)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[2/3] lectures  ->  R2 (lectures/...)")

if SUBJECT_FILTER:
    print("    SKIP (subject filter active)")
    lec_ok = lec_skip = lec_fail = 0
else:
    lec_ok = lec_skip = lec_fail = 0
    try:
        # Walk the lectures bucket recursively
        def walk(prefix: str) -> list[str]:
            out = []
            try:
                items = supabase.storage.from_(LECTURES_BUCKET).list(
                    prefix, {"limit": 1000})
            except Exception as e:
                print(f"    list error {prefix}: {e}"); return out
            for item in items:
                name = item["name"]
                full = f"{prefix}/{name}" if prefix else name
                if item.get("id") is None:
                    out.extend(walk(full))
                else:
                    out.append(full)
            return out

        all_paths = walk("")
        print(f"    Found {len(all_paths)} lecture files")

        for path in all_paths:
            r2_key = f"lectures/{path}"
            url = f"{SB_LEC_BASE}{path}"
            if not DRY_RUN and r2_exists(r2_key):
                lec_skip += 1; continue
            data = http_get(url)
            if not data:
                lec_fail += 1; print(f"    FAIL download: {path}"); continue
            ct = "application/pdf" if path.endswith(".pdf") else "video/mp4" if path.endswith((".mp4", ".m4v")) else "application/octet-stream"
            if r2_upload(r2_key, data, ct):
                lec_ok += 1
            else:
                lec_fail += 1; print(f"    FAIL upload: {path}")

        print(f"    lectures: ok={lec_ok} skip={lec_skip} fail={lec_fail}")
    except Exception as e:
        print(f"    SKIP (lectures bucket error: {e})")

# ─────────────────────────────────────────────────────────────────────────────
# PASS 3: Print SQL to flip DB URLs (run by user after verification)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[3/3] DB URL flip SQL")

if total["fail"] > 0:
    print(f"\n    {total['fail']} files failed migration — DO NOT run the SQL flip yet.")
    print("    Re-run this script (it skips files already in R2).")
    sys.exit(1)

print(f"""
{'─' * 72}
{'PREVIEW — SQL to run after a successful real run:' if DRY_RUN else 'NEXT STEP — paste this into Supabase SQL Editor:'}
{'─' * 72}

-- 0)  Bio/Chem season case fix (run BEFORE the URL flip).
--     Idempotent — safe to re-run.  Handles all season variants.
UPDATE pages
SET
  qp_page_url = regexp_replace(
    qp_page_url,
    '(/pages/\\d{{4}}_)([a-z][a-z\\-]*)(_)',
    '\\1' || initcap('\\2') || '\\3'
  ),
  ms_page_url = CASE WHEN ms_page_url IS NULL THEN NULL ELSE
    regexp_replace(
      ms_page_url,
      '(/pages/\\d{{4}}_)([a-z][a-z\\-]*)(_)',
      '\\1' || initcap('\\2') || '\\3'
    )
  END
WHERE qp_page_url ~ '/(Biology|Chemistry)/pages/'
  AND qp_page_url ~ '/pages/\\d{{4}}_[a-z]';

-- 1)  Flip every Supabase question-pdfs URL to R2.
--     Match either column (the previous version had a logic bug here).
UPDATE pages
SET
  qp_page_url = replace(qp_page_url, '{SB_QP_BASE}', '{R2_PUBLIC_URL}/'),
  ms_page_url = replace(ms_page_url, '{SB_QP_BASE}', '{R2_PUBLIC_URL}/')
WHERE qp_page_url LIKE '{SB_QP_BASE}%'
   OR ms_page_url LIKE '{SB_QP_BASE}%';

-- 2)  Flip lectures.file_url from Supabase to R2.
UPDATE lectures
SET file_url = replace(file_url, '{SB_LEC_BASE}', '{R2_PUBLIC_URL}/lectures/')
WHERE file_url LIKE '{SB_LEC_BASE}%';

-- 3)  Verify (all should be 0):
SELECT 'pages on supabase' AS what,
       count(*) FILTER (WHERE qp_page_url LIKE '{SUPABASE_URL}%'
                          OR ms_page_url LIKE '{SUPABASE_URL}%') AS n
FROM pages
UNION ALL
SELECT 'lectures on supabase', count(*) FROM lectures
WHERE file_url LIKE '{SUPABASE_URL}%';
{'─' * 72}
""")
if DRY_RUN:
    print("Re-run without --dry-run to perform the actual migration.")
