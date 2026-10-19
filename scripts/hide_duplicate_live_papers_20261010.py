#!/usr/bin/env python3
"""
Hide the second copy of each duplicated IGCSE Chemistry / Biology paper from
the test builder and worksheet generator (2026-10-10 audit).

From 2019 the archive holds Pearson's papers under two names: the site's plain
"1"/"2"/"1R"/"2R" AND Pearson's own "1C"/"1CR" (Chemistry) or "1B"/"1BR"
(Biology). Both were segmented, so every question of those papers appeared
twice in the tools. A pair is the same paper when both covers print the same
Pearson reference (P75820A ...), read in data/analysis/all_topic_audit/
paper_covers.json.

Of each pair the plain name is kept (the site's naming for every other year),
unless it serves fewer questions than its twin: Biology 2023 Jan "1" serves 7
cuts taken from Paper 2R, while "1B" serves the real 10.

Hiding = pages.is_question false on the copy's rows. Both tools and the MCP
question search filter on is_question, so the copy disappears from them; the
rows, their URLs and the papers row stay, so saved tests and the past-paper
download pages are untouched. Undo: set is_question back to true for the ids
in the backup.

    python scripts/hide_duplicate_live_papers_20261010.py            # dry run
    python scripts/hide_duplicate_live_papers_20261010.py --execute
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.live_paper_sources import ROOT, fetch_rows, supabase_client  # noqa: E402

COVERS = ROOT / "data" / "analysis" / "all_topic_audit" / "paper_covers.json"
SUBJECTS = ("4CH1", "4BI1")
TWIN_LETTER = {"4CH1": "C", "4BI1": "B"}
BACKUP_DIR = ROOT / "data" / "backups"
BATCH = 100


def label(paper: dict) -> str:
    return f"{paper['year']}_{paper['season']}_{paper['paper_number']}"


def is_plain(paper: dict) -> bool:
    return TWIN_LETTER[paper["code"]] not in paper["paper_number"]


def served_rows(sb, paper_ids: list[str]) -> dict[str, list[dict]]:
    rows: dict[str, list[dict]] = defaultdict(list)
    for i in range(0, len(paper_ids), BATCH):
        part = paper_ids[i:i + BATCH]
        for row in fetch_rows(lambda o, part=part: sb.table("pages")
                              .select("id,paper_id,is_question,qp_page_url")
                              .in_("paper_id", part).range(o, o + 999)):
            if row["is_question"] and row["qp_page_url"]:
                rows[row["paper_id"]].append(row)
    return rows


def build_plan(sb) -> list[dict]:
    papers = [p for p in json.loads(COVERS.read_text(encoding="utf-8"))
              if p["code"] in SUBJECTS and p.get("ref")]
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for paper in papers:
        groups[(paper["code"], paper["ref"])].append(paper)
    pairs = [g for g in groups.values() if len(g) == 2]
    rows = served_rows(sb, [p["id"] for g in pairs for p in g])

    plan = []
    for pair in pairs:
        if not all(rows.get(p["id"]) for p in pair):
            continue  # only one copy reaches the tools: nothing duplicated
        plain = [p for p in pair if is_plain(p)]
        keep = plain[0] if len(plain) == 1 else pair[0]
        other = next(p for p in pair if p is not keep)
        if len(rows[keep["id"]]) < len(rows[other["id"]]):
            keep, other = other, keep
        plan.append({"code": keep["code"], "ref": keep["ref"], "keep": label(keep),
                     "hide": label(other), "hide_paper_id": other["id"],
                     "page_ids": sorted(r["id"] for r in rows[other["id"]])})
    return sorted(plan, key=lambda p: (p["code"], p["hide"]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    sb = supabase_client()
    plan = build_plan(sb)
    ids = [i for p in plan for i in p["page_ids"]]
    for p in plan:
        print(f"  {p['code']} {p['ref']:9} keep {p['keep']:18} hide {p['hide']:18} ({len(p['page_ids'])} rows)")
    print(f"{len(plan)} duplicate papers, {len(ids)} question rows to hide")
    if not args.execute:
        print("Dry run only. Re-run with --execute to write.")
        return 0

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = BACKUP_DIR / f"hide_duplicate_papers_{stamp}.json"
    backup.write_text(json.dumps(plan, indent=1), encoding="utf-8")
    print(f"backup: {backup.relative_to(ROOT)}")
    for i in range(0, len(ids), BATCH):
        sb.table("pages").update({"is_question": False}).in_("id", ids[i:i + BATCH]).execute()

    still = []
    for i in range(0, len(ids), BATCH):
        still += [r["id"] for r in sb.table("pages").select("id,is_question")
                  .in_("id", ids[i:i + BATCH]).execute().data if r["is_question"]]
    print(f"hidden {len(ids) - len(still)} rows; still visible: {len(still)}")
    return 1 if still else 0


if __name__ == "__main__":
    sys.exit(main())
