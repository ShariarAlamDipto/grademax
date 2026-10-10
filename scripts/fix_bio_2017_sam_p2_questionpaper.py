#!/usr/bin/env python3
"""
Point the IGCSE Biology (4BI1) 2017 specimen Paper 2 row at a COMPLETE question paper.

Our copy (papers.pdf_url) is missing printed page 14 (it jumps 13 -> 15), which
is question 5(b)(ii)-(c), so that question could not be shown whole. Pages
53-72 of Pearson's public "international-gcse-Biology-2017-SAM.pdf" are the
same paper (S52914A) with every page.

Uploads it to a NEW R2 key and sets the one papers row. Then re-run
publish_biology_live_segments.py --execute.

    python scripts/fix_bio_2017_sam_p2_questionpaper.py            # dry run
    python scripts/fix_bio_2017_sam_p2_questionpaper.py --execute
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

SOURCE = ROOT / "data" / "analysis" / ".pairing_cache" / "pearson_sams" / "IGCSE_Biology_2017_SAM_P2_QP.pdf"
KEY_DIR = "igcse/biology/2017/specimen"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    body = SOURCE.read_bytes()
    key = f"{KEY_DIR}/Biology_2017_Specimen_Paper_2_QP-{hashlib.md5(body).hexdigest()[:10]}.pdf"
    sb = supabase_client()
    rows = (sb.table("papers").select("id,paper_number,pdf_url")
            .eq("subject_id", subject_id(sb, "4BI1")).eq("year", 2017)
            .eq("season", "specimen").eq("paper_number", "2").execute().data)
    if len(rows) != 1:
        raise SystemExit(f"expected one papers row, found {len(rows)}")
    row = rows[0]
    _, prefix = r2_reader()
    print(f"papers {row['id']}\n  old: {row['pdf_url']}\n  new: {prefix + key}")
    if not args.execute:
        print("Dry run only. Re-run with --execute to write.")
        return 0
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = ROOT / "data" / "backups" / f"bio_2017_sam_p2_qp_{stamp}.json"
    backup.write_text(json.dumps(row, indent=1), encoding="utf-8")
    import ingest_2026_papers as ing  # noqa: PLC0415 -- env loaded by r2_reader
    ing.get_r2().put_object(Bucket=ing.R2_BUCKET, Key=key, Body=body, ContentType="application/pdf")
    sb.table("papers").update({"pdf_url": prefix + key}).eq("id", row["id"]).execute()
    check = sb.table("papers").select("pdf_url").eq("id", row["id"]).execute().data[0]
    print(f"backup: {backup.relative_to(ROOT)}\nnow: {check['pdf_url']}")
    return 0 if check["pdf_url"] == prefix + key else 1


if __name__ == "__main__":
    sys.exit(main())
