#!/usr/bin/env python3
"""
Create the `topics` rows the test builder and worksheet generator list for
IGCSE Mathematics A (4MA1). The subject has none yet.

Topics are the 4MA1 Higher specification sections ("2.7 Quadratic equations"),
copied from the workbook taxonomy already applied live (workbook_chapters /
workbook_sections, supabase migration 20) so the tools and the workbook agree.
Codes are dotted, which src/lib/topicCodes.ts passes through unchanged, exactly
as for the IAL units.

1.10 Applying number, 1.11 Electronic calculators and 4.4 Measures are left
out: they are process statements no question is ever tagged with
(classify_mathsa_tool_topics.py drops them), so they would list as empty topics.

    python -X utf8 scripts/create_mathsa_tool_topics.py            # dry run
    python -X utf8 scripts/create_mathsa_tool_topics.py --execute
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.live_paper_sources import fetch_rows, supabase_client  # noqa: E402

SUBJECT_ID = "8b7b0cb0-e95c-480d-ac0a-c710f1e59213"
PROCESS_ONLY = {"1.10", "1.11", "4.4"}


def wanted(sb) -> list[dict]:
    chapters = {c["id"]: c for c in sb.table("workbook_chapters").select("id,number,title")
                .eq("subject_id", SUBJECT_ID).execute().data}
    sections = fetch_rows(lambda o: sb.table("workbook_sections").select("number,title,chapter_id")
                          .in_("chapter_id", list(chapters)).range(o, o + 999))
    rows = []
    for s in sections:
        chapter = chapters[s["chapter_id"]]
        code = f"{chapter['number']}.{s['number']}"
        if code in PROCESS_ONLY:
            continue
        rows.append({"subject_id": SUBJECT_ID, "code": code, "name": s["title"],
                     "description": f"{chapter['title']} -- 4MA1 Higher specification section {code}"})
    return sorted(rows, key=lambda r: [int(p) for p in r["code"].split(".")])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    sb = supabase_client()
    existing = {t["code"] for t in sb.table("topics").select("code")
                .eq("subject_id", SUBJECT_ID).execute().data}
    rows = [r for r in wanted(sb) if r["code"] not in existing]
    print(f"4MA1 topics: {len(existing)} exist, {len(rows)} to create")
    for r in rows:
        print(f"  {r['code']:5} {r['name']}")
    if not args.execute:
        print("\nDry run only. Re-run with --execute to write.")
        return 0
    if rows:
        sb.table("topics").insert(rows).execute()
    print(f"created {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
