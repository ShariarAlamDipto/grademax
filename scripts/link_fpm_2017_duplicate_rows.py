#!/usr/bin/env python3
"""
Give the 17 live IGCSE Further Pure rows filed under "2017 Oct-Nov" Papers 1/2
their mark schemes.

Those "papers" are the 2016 specimen papers refiled under a session that was
never sat (byte-identical text; see EXCLUDED_PAPERS in
build_fpm_workbook_segments.py). Each row's own question file was compared with
the specimen question of the same number: all 17 match at similarity 1.00
(data/analysis/live_rebuild/4PM1/dup2017/plan.json). So each row is pointed at
the specimen's rebuilt question file and its proven, Claude-read scheme.

    python scripts/link_fpm_2017_duplicate_rows.py            # dry run
    python scripts/link_fpm_2017_duplicate_rows.py --execute
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.live_paper_sources import ROOT, supabase_client  # noqa: E402

PLAN = ROOT / "data" / "analysis" / "live_rebuild" / "4PM1" / "dup2017" / "plan.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    plan = [p for p in json.loads(PLAN.read_text(encoding="utf-8"))
            if p["ratio"] >= 0.99 and p["spec_q"] == p["q"] and p["ms"]]
    print(f"rows to link: {len(plan)}")
    if not args.execute:
        print("Dry run only. Re-run with --execute to write.")
        return 0
    sb = supabase_client()
    ids = [p["id"] for p in plan]
    before = sb.table("pages").select("*").in_("id", ids).execute().data
    out = ROOT / "data" / "backups" / f"fpm_2017_dup_link_{dt.datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps(before, indent=1), encoding="utf-8")
    for p in plan:
        sb.table("pages").update({"qp_page_url": p["qp"], "ms_page_url": p["ms"]}).eq("id", p["id"]).execute()
        sb.table("questions").update({"page_pdf_url": p["qp"], "ms_pdf_url": p["ms"]}).eq("id", p["id"]).execute()
    after = sb.table("pages").select("ms_page_url").in_("id", ids).execute().data
    print(f"backup {out}; linked {sum(1 for r in after if r['ms_page_url'])}/{len(ids)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
