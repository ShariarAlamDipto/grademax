#!/usr/bin/env python3
"""
Move the Edexcel IGCSE ICT (4IT1) paper links off the stray top-level `ICT/`
folder onto the one paper tree `igcse/ict/<year>/<season>/`, where every other
IGCSE subject lives. A row is re-pointed only when the igcse/ict object is
BYTE-IDENTICAL (same ETag and size) to the ICT/ object it replaces, so no
student sees a different file.

    python scripts/repoint_ict_papers_to_igcse.py            # dry run
    python scripts/repoint_ict_papers_to_igcse.py --execute

Backup of the rows written: data/backups/ict_repoint_<timestamp>.json.
The ICT/ objects are left in place; the R2 orphan clean-up removes them once
nothing references them.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.live_paper_sources import ROOT, fetch_rows, supabase_client  # noqa: E402

COLUMNS = ("pdf_url", "markscheme_pdf_url")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    import ingest_2026_papers as ing  # noqa: PLC0415
    r2, bucket = ing.get_r2(), ing.R2_BUCKET
    public = ing.R2_PUBLIC_URL.rstrip("/") + "/"

    def head(key: str):
        try:
            h = r2.head_object(Bucket=bucket, Key=key)
            return h["ETag"], h["ContentLength"]
        except Exception:  # noqa: BLE001 -- missing object
            return None

    sb = supabase_client()
    sid = sb.table("subjects").select("id").eq("code", "4IT1").execute().data[0]["id"]
    papers = fetch_rows(lambda o: sb.table("papers").select("id,year,season," + ",".join(COLUMNS))
                        .eq("subject_id", sid).range(o, o + 999))
    updates, refused = [], []
    for p in papers:
        change = {}
        for col in COLUMNS:
            url = p[col]
            if not url or not url.startswith(public + "ICT/"):
                continue
            old = url[len(public):]
            name = old.rsplit("/", 1)[1]
            new = f"igcse/ict/{p['year']}/{p['season']}/{name}"
            a, b = head(old), head(new)
            if a and b and a == b:
                change[col] = public + new
            else:
                refused.append((old, new, a, b))
        if change:
            updates.append((p, change))
    print(f"4IT1 rows: {len(papers)}; re-pointable links: {sum(len(c) for _, c in updates)}; "
          f"refused (target missing or different bytes): {len(refused)}")
    for r in refused:
        print("   refused", r[0], "->", r[1])
    if not args.execute:
        print("Dry run only. Re-run with --execute to write.")
        return 0
    backup = ROOT / "data" / "backups" / f"ict_repoint_{datetime.now():%Y%m%d_%H%M%S}.json"
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_text(json.dumps([p for p, _ in updates], indent=1), encoding="utf-8")
    for p, change in updates:
        sb.table("papers").update(change).eq("id", p["id"]).execute()
    print(f"re-pointed {len(updates)} rows (backup {backup.relative_to(ROOT)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
