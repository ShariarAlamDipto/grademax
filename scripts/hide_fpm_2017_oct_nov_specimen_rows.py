#!/usr/bin/env python3
"""
Hide the 17 Further Pure (4PM1) "2017 Oct-Nov" P1/P2 question rows from the
worksheet generator and test builder.

    python scripts/hide_fpm_2017_oct_nov_specimen_rows.py            # dry run
    python scripts/hide_fpm_2017_oct_nov_specimen_rows.py --execute

Why: those two `papers` rows have no question paper or mark scheme of their
own, and their questions point at the 2016 SPECIMEN cuts
(pages-v2/2016_specimen_P1|P2/...). So the tools show specimen questions
labelled "2017 Oct-Nov" -- a wrong sitting -- and serve each one twice (the
2016 specimen rows carry the same questions correctly labelled).
Found by scripts/audit_tool_question_identity.py (verdict NOT_STAGED).

Hiding = pages.is_question -> false (the convention the tools filter on, also
used for the duplicate Chem/Bio rows). Rows, URLs, topics and saved
worksheets/tests are kept, so it is reversible; a JSON backup is written first.
Every row is checked to point at the 2016 specimen before it is touched.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.live_paper_sources import ROOT, supabase_client  # noqa: E402

SPECIMEN_MARK = "/pages-v2/2016_specimen_P"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    sb = supabase_client()
    sid = sb.table("subjects").select("id").eq("code", "4PM1").execute().data[0]["id"]
    papers = (sb.table("papers").select("id,paper_number,pdf_url,markscheme_pdf_url")
              .eq("subject_id", sid).eq("year", 2017).eq("season", "oct-nov").execute().data)
    rows = []
    for p in papers:
        if p["pdf_url"] or p["markscheme_pdf_url"]:
            raise SystemExit(f"paper {p['id']} now has its own files -- re-check before hiding")
        rows += (sb.table("pages").select("id,paper_id,question_number,is_question,qp_page_url,ms_page_url")
                 .eq("paper_id", p["id"]).not_.is_("qp_page_url", "null").execute().data)
    not_specimen = [r for r in rows if SPECIMEN_MARK not in (r["qp_page_url"] or "")]
    if not_specimen:
        raise SystemExit(f"{len(not_specimen)} rows do not point at the 2016 specimen -- stopping")
    todo = [r for r in rows if r["is_question"]]
    print(f"4PM1 2017 Oct-Nov rows: {len(rows)}; still shown in the tools: {len(todo)}")
    if not args.execute:
        print("Dry run only. Re-run with --execute to write.")
        return 0
    backup = ROOT / "data" / "backups" / f"fpm_2017_oct_nov_hide_{datetime.now():%Y%m%d_%H%M%S}.json"
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    for r in todo:
        sb.table("pages").update({"is_question": False}).eq("id", r["id"]).execute()
    print(f"hidden {len(todo)} rows (backup {backup.relative_to(ROOT)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
