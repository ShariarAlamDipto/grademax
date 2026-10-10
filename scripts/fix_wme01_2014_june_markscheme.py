#!/usr/bin/env python3
"""
Point the IAL M1 (WME01) May-Jun 2014 paper at its real mark scheme.

The papers row's markscheme_pdf_url serves Pearson's UK GCE "Mechanics 1R
(6677_01R)" scheme -- a different paper. The question paper is the genuine
WME01/01 of Friday 6 June 2014 (cover read by OCR, 2026-10-10). Pearson's own
"Mark scheme - Paper M1 (WME01) - June 2014" is in
data/workbook/ial_sources/m1/2014_may-jun/MS.pdf (source URL in SOURCE.txt).

Uploads it to a NEW R2 key (nothing is overwritten) and updates the one
papers row; the old URL is printed and saved so the change can be undone.
The per-question schemes in the tools come from publish_m1_live_segments.py.

    python scripts/fix_wme01_2014_june_markscheme.py            # dry run
    python scripts/fix_wme01_2014_june_markscheme.py --execute
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.live_paper_sources import ROOT, r2_reader, subject_id, supabase_client  # noqa: E402

SOURCE = ROOT / "data" / "workbook" / "ial_sources" / "m1" / "2014_may-jun" / "MS.pdf"
KEY_DIR = "ial/mechanics-1/2014/may-jun"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    body = SOURCE.read_bytes()
    if b"WME01" not in body[:200000] and "WME01" not in SOURCE.with_name("SOURCE.txt").read_text():
        raise SystemExit("source does not look like the WME01 scheme")
    digest = hashlib.md5(body).hexdigest()[:10]
    key = f"{KEY_DIR}/Mathematics_M1_2014_May-Jun_MS-{digest}.pdf"

    sb = supabase_client()
    rows = (sb.table("papers").select("id,markscheme_pdf_url")
            .eq("subject_id", subject_id(sb, "WME01")).eq("year", 2014)
            .eq("season", "may-jun").execute().data)
    if len(rows) != 1:
        raise SystemExit(f"expected one papers row, found {len(rows)}")
    row = rows[0]
    _, prefix = r2_reader()
    print(f"papers {row['id']}\n  old: {row['markscheme_pdf_url']}\n  new: {prefix + key}")
    if not args.execute:
        print("Dry run only. Re-run with --execute to write.")
        return 0

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = ROOT / "data" / "backups" / f"wme01_2014_june_ms_{stamp}.json"
    backup.write_text(json.dumps(row, indent=1), encoding="utf-8")

    import ingest_2026_papers as ing  # noqa: PLC0415 -- env loaded by r2_reader
    ing.get_r2().put_object(Bucket=ing.R2_BUCKET, Key=key, Body=body,
                            ContentType="application/pdf")
    sb.table("papers").update({"markscheme_pdf_url": prefix + key}).eq("id", row["id"]).execute()
    check = sb.table("papers").select("markscheme_pdf_url").eq("id", row["id"]).execute().data[0]
    print(f"backup: {backup.relative_to(ROOT)}\nnow: {check['markscheme_pdf_url']}")
    return 0 if check["markscheme_pdf_url"] == prefix + key else 1


if __name__ == "__main__":
    sys.exit(main())
