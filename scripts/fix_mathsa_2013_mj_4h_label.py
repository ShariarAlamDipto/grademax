#!/usr/bin/env python3
"""
Relabel the Maths A papers row "2013 May-Jun Paper 2H" as Paper 4H.

Its question paper's cover reads "Mathematics A Paper 4H Higher Tier, Tuesday
21 May 2013, 4MA0/4H" (barcode P42071A) and its mark scheme says "4MA0 Paper
4H" (scripts/audit_mathsa_r2_paper_identity.py). 4MA0 had no Paper 2H at all,
and the sitting has NO 4H row -- so this row is the only copy of that paper and
is relabelled, not hidden. Every other pre-June-2018 "1H/2H/1HR/2HR" row
duplicates a correctly named 3H/4H row and is simply not served by the tools.

Re-reads both covers from R2 before writing; refuses if either has changed.

    python -X utf8 scripts/fix_mathsa_2013_mj_4h_label.py            # dry run
    python -X utf8 scripts/fix_mathsa_2013_mj_4h_label.py --execute
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.live_paper_sources import r2_reader, supabase_client  # noqa: E402

SUBJECT_ID = "8b7b0cb0-e95c-480d-ac0a-c710f1e59213"
COVER_4H_RE = re.compile(r"4MA0\s*/?\s*4H|Paper\s*4H", re.I)


def cover_text(data: bytes) -> str:
    with fitz.open(stream=data, filetype="pdf") as doc:
        page = doc[0]
        text = page.get_text()
        if not COVER_4H_RE.search(text):  # shifted-font QP: read the picture instead
            text = page.get_textpage_ocr(dpi=200, full=True, tessdata=str(
                Path("C:/Program Files/Tesseract-OCR/tessdata"))).extractText()
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    sb = supabase_client()
    rows = (sb.table("papers").select("id,year,season,paper_number,pdf_url,markscheme_pdf_url")
            .eq("subject_id", SUBJECT_ID).eq("year", 2013).eq("season", "may-jun").execute().data)
    by_number = {r["paper_number"]: r for r in rows}
    if "4H" in by_number:
        print("a 4H row already exists -- nothing to do (or a duplicate to review):", by_number["4H"]["id"])
        return 1
    row = by_number.get("2H")
    if row is None:
        print("no 2013 May-Jun 2H row")
        return 1

    get_bytes, _ = r2_reader()
    for kind, url in (("QP", row["pdf_url"]), ("MS", row["markscheme_pdf_url"])):
        text = cover_text(get_bytes(url))
        ok = bool(COVER_4H_RE.search(text))
        print(f"{kind} cover says 4H: {ok}")
        if not ok:
            print("REFUSING: cover no longer reads 4H")
            return 1

    print(f"papers {row['id']}: paper_number 2H -> 4H")
    if args.execute:
        sb.table("papers").update({"paper_number": "4H"}).eq("id", row["id"]).execute()
        print("done")
    else:
        print("Dry run only. Re-run with --execute to write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
