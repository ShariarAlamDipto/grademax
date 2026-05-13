#!/usr/bin/env python3
"""
Export the entire GradeMax DB to a local offline archive via supabase-py
(PostgREST). Same purpose as export_db_to_offline_archive.py but uses the
Supabase JS-style API instead of direct postgres.

Run AFTER the Supabase project is unblocked (storage quota restored).

Output:
  ~/grademax_offline_archive/
    db_export/*.json
    classification/*.yaml

Usage:
    python -X utf8 scripts/export_db_via_supabase.py
    python -X utf8 scripts/export_db_via_supabase.py --output "C:/path"
"""

import os, sys, json, shutil
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv(".env.local")

from supabase import create_client

OUTPUT_BASE = Path.home() / "grademax_offline_archive"
for i, a in enumerate(sys.argv):
    if a == "--output" and i + 1 < len(sys.argv):
        OUTPUT_BASE = Path(sys.argv[i + 1])

OUTPUT = OUTPUT_BASE / "db_export"
OUTPUT.mkdir(parents=True, exist_ok=True)

sb = create_client(
    os.getenv("NEXT_PUBLIC_SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
)

TABLES = [
    "subjects", "papers", "pages",
    "tests", "test_items",
    "worksheets", "worksheet_items",
    "lectures",
    "topics", "subject_topics",
    "profiles", "audit_log",
]

print("=" * 72)
print(f"GRADEMAX OFFLINE ARCHIVE  ->  {OUTPUT_BASE}")
print("=" * 72)

manifest = {
    "exported_at": datetime.utcnow().isoformat() + "Z",
    "method": "supabase-py (PostgREST)",
    "tables": {},
}

for table in TABLES:
    print(f"  {table}:", end=" ", flush=True)
    try:
        rows = []
        offset = 0
        PAGE = 1000
        while True:
            r = sb.table(table).select("*").range(offset, offset + PAGE - 1).execute()
            batch = r.data or []
            rows.extend(batch)
            if len(batch) < PAGE: break
            offset += PAGE
        out = OUTPUT / f"{table}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, default=str)
        size_mb = out.stat().st_size / 1024 / 1024
        manifest["tables"][table] = {"rows": len(rows), "size_mb": round(size_mb, 2)}
        print(f"{len(rows):>6,d} rows ({size_mb:.1f} MB)")
    except Exception as e:
        print(f"SKIP ({str(e)[:80]})")
        manifest["tables"][table] = {"error": str(e)[:200]}

# Copy classification YAMLs
config_src = Path("config")
config_dst = OUTPUT_BASE / "classification"
config_dst.mkdir(exist_ok=True)
copied = 0
if config_src.exists():
    for ext in ("*.yaml", "*.yml"):
        for yml in config_src.glob(ext):
            shutil.copy2(yml, config_dst / yml.name)
            copied += 1
print(f"\n  Classification YAMLs copied: {copied}")

with open(OUTPUT_BASE / "manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)

# README
(OUTPUT_BASE / "README.md").write_text(f"""# GradeMax Offline Archive

Exported: {manifest['exported_at']}

## What's here
- `db_export/*.json` — every row of every table at export time
- `classification/*.yaml` — subject taxonomies
- `manifest.json` — row counts per table

## Sister archive (PDFs)
- Local segmented PDFs: data/processed/ in the grademax repo
- R2: https://pub-b96af5a8f7044337bcb17a51b3fd4a60.r2.dev/subjects/...

## Worst-case restore
1. Stand up a fresh Postgres (Supabase, Neon, anywhere)
2. Apply migrations from supabase/migrations/
3. For each table in db_export/, load JSON via a small Python script
4. Re-upload PDFs to R2 from local archive
5. URL-flip SQL points pages.qp_page_url at R2

System is fully functional after step 5.
""", encoding="utf-8")

total_rows = sum((t.get("rows") or 0) for t in manifest["tables"].values())
total_mb = sum((t.get("size_mb") or 0) for t in manifest["tables"].values())
print(f"\nDone. {total_rows:,} rows, {total_mb:.1f} MB at {OUTPUT_BASE}")
