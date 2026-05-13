#!/usr/bin/env python3
"""
Update Supabase pages.qp_page_url + ms_page_url + lectures.file_url to point at R2/Appwrite.

Uses direct PostgreSQL (bypasses PostgREST quota restriction).

Two passes:
  1. Bio/Chem case-fix:    /pages/2012_jan_1/  ->  /pages/2012_Jan_1/
  2. Provider flip:         supabase.co/storage/v1/object/public/question-pdfs/  ->  R2 base
                            supabase.co/storage/v1/object/public/lectures/        ->  Appwrite base

Idempotent — safe to re-run.

Usage:
    pip install psycopg2-binary python-dotenv
    # Set DATABASE_URL in .env.local
    python -X utf8 scripts/flip_db_urls_to_r2.py --dry-run
    python -X utf8 scripts/flip_db_urls_to_r2.py
"""

import os, sys, re
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv(".env.local")

DRY_RUN = "--dry-run" in sys.argv

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: pip install psycopg2-binary"); sys.exit(1)

DB_URL          = os.getenv("DATABASE_URL")
SUPABASE_URL    = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
R2_PUBLIC_URL   = (os.getenv("NEXT_PUBLIC_R2_PUBLIC_URL") or "").rstrip("/")

if not all([DB_URL, SUPABASE_URL, R2_PUBLIC_URL]):
    print("ERROR: DATABASE_URL, NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_R2_PUBLIC_URL "
          "must be set in .env.local")
    sys.exit(1)

QP_BASE  = f"{SUPABASE_URL}/storage/v1/object/public/question-pdfs/"
LEC_BASE = f"{SUPABASE_URL}/storage/v1/object/public/lectures/"

print("=" * 72)
print(f"DB URL FLIP{' [DRY-RUN]' if DRY_RUN else ''}")
print(f"  question-pdfs source: {QP_BASE}")
print(f"  R2 target           : {R2_PUBLIC_URL}/")
print("=" * 72)

conn = psycopg2.connect(DB_URL)
conn.autocommit = False
cur = conn.cursor()

# ── 1. Bio/Chem case fix ────────────────────────────────────────────────────
print("\n[1] Bio/Chem case fix (regex over season segment)")
case_sql = """
UPDATE pages
SET
  qp_page_url = regexp_replace(
    qp_page_url,
    '(/pages/\\d{4}_)([a-z][a-z\\-]*)(_)',
    '\\1' || initcap('\\2') || '\\3'
  ),
  ms_page_url = CASE WHEN ms_page_url IS NULL THEN NULL ELSE
    regexp_replace(
      ms_page_url,
      '(/pages/\\d{4}_)([a-z][a-z\\-]*)(_)',
      '\\1' || initcap('\\2') || '\\3'
    )
  END
WHERE qp_page_url ~ '/(Biology|Chemistry)/pages/'
  AND qp_page_url ~ '/pages/\\d{4}_[a-z]'
"""
cur.execute(case_sql.replace("UPDATE", "SELECT count(*) FROM (SELECT 1 FROM").replace(
    "SET\n  qp_page_url = regexp_replace(", "")[:300] + ") s")
# Simpler: just count first
cur.execute("""
    SELECT count(*) FROM pages
    WHERE qp_page_url ~ '/(Biology|Chemistry)/pages/'
      AND qp_page_url ~ '/pages/\\d{4}_[a-z]'
""")
n_case = cur.fetchone()[0]
print(f"  Rows needing case fix: {n_case}")

if not DRY_RUN and n_case > 0:
    cur.execute(case_sql)
    print(f"  Applied case fix to {cur.rowcount} rows")

# ── 2. URL flip: question-pdfs -> R2 ────────────────────────────────────────
print(f"\n[2] Flipping pages URLs: Supabase question-pdfs -> R2")
cur.execute("""
    SELECT count(*) FROM pages
    WHERE qp_page_url LIKE %s OR ms_page_url LIKE %s
""", (f"{QP_BASE}%", f"{QP_BASE}%"))
n_pages = cur.fetchone()[0]
print(f"  pages rows pointing at Supabase: {n_pages}")

if not DRY_RUN and n_pages > 0:
    cur.execute("""
        UPDATE pages SET
            qp_page_url = replace(qp_page_url, %s, %s),
            ms_page_url = replace(ms_page_url, %s, %s)
        WHERE qp_page_url LIKE %s OR ms_page_url LIKE %s
    """, (QP_BASE, R2_PUBLIC_URL + "/",
          QP_BASE, R2_PUBLIC_URL + "/",
          f"{QP_BASE}%", f"{QP_BASE}%"))
    print(f"  Flipped {cur.rowcount} pages rows")

# ── 3. lectures.file_url flip ───────────────────────────────────────────────
print(f"\n[3] lectures.file_url:  Supabase -> Appwrite")
APPWRITE_ENDPOINT = os.getenv("NEXT_PUBLIC_APPWRITE_ENDPOINT", "https://sgp.cloud.appwrite.io/v1")
APPWRITE_PROJECT  = os.getenv("NEXT_PUBLIC_APPWRITE_PROJECT_ID")
APPWRITE_BUCKET   = os.getenv("NEXT_PUBLIC_APPWRITE_BUCKET_ID", "grademax-lectures")

cur.execute("SELECT count(*) FROM lectures WHERE file_url LIKE %s", (f"{LEC_BASE}%",))
n_lec = cur.fetchone()[0]
print(f"  lectures still on Supabase storage: {n_lec}")
if n_lec:
    print("  NOTE: lectures must be re-uploaded to Appwrite individually — they need")
    print("        new Appwrite file IDs. Run: scripts/migrate_lectures_to_appwrite.py")

# ── 3b. Disable Bio/Chem/HumanBio (their PDFs are still on locked Supabase) ──
# When --disable-orphaned-subjects is passed, we NULL-out qp_page_url/ms_page_url
# for subjects whose PDFs we couldn't migrate yet. This is the graceful way to
# keep Test Builder working: those subjects simply show 0 questions instead of
# rendering with broken 402 PDF URLs.
DISABLE_ORPHANED = "--disable-orphaned-subjects" in sys.argv
ORPHANED_SUBJECTS = ["Biology", "Chemistry", "Human Biology", "Human_Biology"]

if DISABLE_ORPHANED:
    print(f"\n[3b] Disabling subjects whose PDFs are still on locked Supabase: "
          f"{', '.join(ORPHANED_SUBJECTS)}")
    cur.execute("""
        SELECT count(*) FROM pages p
        JOIN papers pa ON pa.id = p.paper_id
        JOIN subjects s ON s.id = pa.subject_id
        WHERE s.name = ANY(%s)
          AND (p.qp_page_url IS NOT NULL OR p.ms_page_url IS NOT NULL)
    """, (ORPHANED_SUBJECTS,))
    n_orphaned = cur.fetchone()[0]
    print(f"  Pages to disable (NULL-out URLs): {n_orphaned}")

    if not DRY_RUN and n_orphaned > 0:
        cur.execute("""
            UPDATE pages SET qp_page_url = NULL, ms_page_url = NULL
            WHERE id IN (
                SELECT p.id FROM pages p
                JOIN papers pa ON pa.id = p.paper_id
                JOIN subjects s ON s.id = pa.subject_id
                WHERE s.name = ANY(%s)
            )
        """, (ORPHANED_SUBJECTS,))
        print(f"  Disabled {cur.rowcount} pages (Test Builder will skip them)")

# ── 4. Final verification ───────────────────────────────────────────────────
print("\n[4] Verification: rows still pointing at Supabase storage")
cur.execute("""
    SELECT 'pages.qp_page_url' AS field, count(*) AS n
    FROM pages WHERE qp_page_url LIKE %s
    UNION ALL
    SELECT 'pages.ms_page_url', count(*) FROM pages WHERE ms_page_url LIKE %s
    UNION ALL
    SELECT 'lectures.file_url', count(*) FROM lectures WHERE file_url LIKE %s
""", (f"{SUPABASE_URL}%", f"{SUPABASE_URL}%", f"{SUPABASE_URL}%"))
for row in cur.fetchall():
    print(f"  {row[0]:25s}  {row[1]:>6,d}")

if DRY_RUN:
    print("\nDRY-RUN — no changes committed.")
    conn.rollback()
else:
    conn.commit()
    print("\nCommitted.")

cur.close()
conn.close()
