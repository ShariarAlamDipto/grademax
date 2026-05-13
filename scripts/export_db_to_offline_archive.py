#!/usr/bin/env python3
"""
Export the entire GradeMax DB (read-only) to a local offline archive.
This becomes the source-of-truth backup so you are never hostage to Supabase.

Uses DIRECT POSTGRES (not PostgREST), which often still works during
storage-quota restrictions.

Output:
  ~/grademax_offline_archive/
    db_export/
      papers.json
      pages.json
      subjects.json
      tests.json
      test_items.json
      worksheets.json
      worksheet_items.json
      lectures.json
      profiles.json
      ...
    classification/
      topics_*.yaml          (copied from grademax/config/)
    README.md

Usage:
    pip install psycopg2-binary python-dotenv
    # Set DATABASE_URL in .env.local first (Supabase Dashboard -> Settings -> Database)
    python -X utf8 scripts/export_db_to_offline_archive.py
    python -X utf8 scripts/export_db_to_offline_archive.py --output "C:/path/to/archive"
"""

import os, sys, json, shutil
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv(".env.local")

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: pip install psycopg2-binary"); sys.exit(1)

# ── Config ──────────────────────────────────────────────────────────────────
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    print("ERROR: DATABASE_URL not set in .env.local")
    print("  Get it from Supabase Dashboard -> Project Settings -> Database -> Connection string")
    print("  Use the 'Transaction Pooler' URI (port 6543) and substitute your DB password.")
    sys.exit(1)

OUTPUT_BASE = Path.home() / "grademax_offline_archive"
for i, a in enumerate(sys.argv):
    if a == "--output" and i + 1 < len(sys.argv):
        OUTPUT_BASE = Path(sys.argv[i + 1])

OUTPUT = OUTPUT_BASE / "db_export"
OUTPUT.mkdir(parents=True, exist_ok=True)

# Tables we always want (entire dataset, no filters)
FULL_TABLES = [
    "subjects",
    "papers",
    "pages",
    "tests",
    "test_items",
    "worksheets",
    "worksheet_items",
    "lectures",
    "topics",
    "subject_topics",
    "profiles",
    "audit_log",
]

def json_default(o):
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, (bytes, memoryview)):
        return o.hex()
    if isinstance(o, set):
        return list(o)
    return str(o)

print("=" * 72)
print("GRADEMAX OFFLINE ARCHIVE - DB EXPORT")
print(f"Output: {OUTPUT_BASE}")
print("=" * 72)

# ── Connect ─────────────────────────────────────────────────────────────────
print("\nConnecting via direct PostgreSQL...")
try:
    conn = psycopg2.connect(DB_URL, connect_timeout=15)
    conn.set_session(readonly=True)
except Exception as e:
    print(f"  FAILED: {e}")
    print("  Check DATABASE_URL has the correct password and pooler endpoint.")
    sys.exit(1)
print("  OK\n")

cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ── Discover tables that actually exist ─────────────────────────────────────
cur.execute("""
    SELECT tablename FROM pg_tables WHERE schemaname = 'public'
""")
existing = {row["tablename"] for row in cur.fetchall()}

manifest = {
    "exported_at": datetime.utcnow().isoformat() + "Z",
    "source_db": DB_URL.split("@", 1)[1].split("/", 1)[0] if "@" in DB_URL else "unknown",
    "tables": {},
}

# ── Export each table ───────────────────────────────────────────────────────
for table in FULL_TABLES:
    if table not in existing:
        print(f"  {table}: SKIP (not in DB)")
        continue
    print(f"  {table}: ", end="", flush=True)
    try:
        cur.execute(f'SELECT * FROM "{table}"')
        rows = cur.fetchall()
        out = OUTPUT / f"{table}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump([dict(r) for r in rows], f, default=json_default, indent=2)
        size_mb = out.stat().st_size / 1024 / 1024
        manifest["tables"][table] = {
            "rows": len(rows),
            "file": f"db_export/{table}.json",
            "size_mb": round(size_mb, 2),
        }
        print(f"{len(rows):>6,d} rows  ({size_mb:.1f} MB)")
    except Exception as e:
        print(f"FAILED: {e}")
        manifest["tables"][table] = {"error": str(e)}

# ── Copy classification YAMLs ───────────────────────────────────────────────
config_src = Path("config")
config_dst = OUTPUT_BASE / "classification"
config_dst.mkdir(exist_ok=True)
copied = 0
if config_src.exists():
    for yml in config_src.glob("*.yaml"):
        shutil.copy2(yml, config_dst / yml.name)
        copied += 1
    for yml in config_src.glob("*.yml"):
        shutil.copy2(yml, config_dst / yml.name)
        copied += 1
print(f"\n  classification YAMLs: copied {copied}")

# ── Manifest + README ───────────────────────────────────────────────────────
with open(OUTPUT_BASE / "manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, default=json_default)

readme = f"""# GradeMax Offline Archive

Generated: {manifest['exported_at']}
Source DB: {manifest['source_db']}

## What's here

- `db_export/` - JSON snapshot of every row of every table
- `classification/` - subject taxonomies (topic codes, keywords)
- `manifest.json` - row counts + file sizes per table

## Sister archive (PDFs)

The actual PDFs live in `~/grademax_offline_pdfs/` (or under `data/processed/`
in the repo). Together they form the complete restorable state of the system.

## Restore procedure (worst case)

1. Stand up a fresh Postgres DB (Supabase or self-hosted)
2. Apply migrations from `supabase/migrations/`
3. For each table in `db_export/`:
     `psql DATABASE_URL -c "\\copy "{{table}}" FROM 'db_export/{{table}}.json'"`
   (or write a small loader script — JSON has the exact column names)
4. Re-upload PDFs to R2 from local archive
5. Run the URL-flip SQL to point pages.qp_page_url at R2

The system should be fully functional after step 5.
"""

with open(OUTPUT_BASE / "README.md", "w", encoding="utf-8") as f:
    f.write(readme)

cur.close()
conn.close()

total_rows = sum((t.get("rows") or 0) for t in manifest["tables"].values())
total_mb = sum((t.get("size_mb") or 0) for t in manifest["tables"].values())
print(f"\nDone. {total_rows:,} rows across {len(manifest['tables'])} tables")
print(f"Archive: {OUTPUT_BASE} ({total_mb:.1f} MB total)")
