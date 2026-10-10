#!/usr/bin/env python3
"""
Give the IGCSE Chemistry (4CH1) Oct-Nov 2025 Paper 1 row its mark scheme.

The papers row has a question paper (P78766RA, "1C") but no markscheme_pdf_url,
so its 10 tool questions showed "mark scheme not available". Pearson keeps the
November 2025 files behind its secure login; the scheme was collected from
Paperlords (archive.paperlords.org/library/IGCSE/Chemistry/Nov 2025/
IGCSE_CHEMISTRY_2025_Nov_P1_MS.pdf, title page "4CH1/1C November 2025"; its
question paper matches ours word for word, same P78766RA).

Uploads it to a NEW R2 key and sets the one papers row. Then re-run
publish_chemistry_live_segments.py --execute to link the 10 proven schemes.

    python scripts/fix_chem_2025_nov_p1_markscheme.py            # dry run
    python scripts/fix_chem_2025_nov_p1_markscheme.py --execute
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

SOURCE = ROOT / "data" / "analysis" / ".pairing_cache" / "paperlords_nov2025" / "files" / "chem_2025_nov_P1_MS.pdf"
KEY_DIR = "igcse/chemistry/2025/oct-nov"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    body = SOURCE.read_bytes()
    key = f"{KEY_DIR}/Chemistry_2025_Oct-Nov_Paper_1_MS-{hashlib.md5(body).hexdigest()[:10]}.pdf"
    sb = supabase_client()
    rows = (sb.table("papers").select("id,paper_number,markscheme_pdf_url")
            .eq("subject_id", subject_id(sb, "4CH1")).eq("year", 2025)
            .eq("season", "oct-nov").eq("paper_number", "1").execute().data)
    if len(rows) != 1:
        raise SystemExit(f"expected one papers row, found {len(rows)}")
    row = rows[0]
    _, prefix = r2_reader()
    print(f"papers {row['id']}\n  old: {row['markscheme_pdf_url']}\n  new: {prefix + key}")
    if not args.execute:
        print("Dry run only. Re-run with --execute to write.")
        return 0
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = ROOT / "data" / "backups" / f"chem_2025_nov_p1_ms_{stamp}.json"
    backup.write_text(json.dumps(row, indent=1), encoding="utf-8")
    import ingest_2026_papers as ing  # noqa: PLC0415 -- env loaded by r2_reader
    ing.get_r2().put_object(Bucket=ing.R2_BUCKET, Key=key, Body=body, ContentType="application/pdf")
    sb.table("papers").update({"markscheme_pdf_url": prefix + key}).eq("id", row["id"]).execute()
    check = sb.table("papers").select("markscheme_pdf_url").eq("id", row["id"]).execute().data[0]
    print(f"backup: {backup.relative_to(ROOT)}\nnow: {check['markscheme_pdf_url']}")
    return 0 if check["markscheme_pdf_url"] == prefix + key else 1


if __name__ == "__main__":
    sys.exit(main())
