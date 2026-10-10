#!/usr/bin/env python3
"""
Apply the 2026-10-10 chapter re-tag of the live test-builder / worksheet subjects
other than Maths B (which has its own fix_mathsb_live_chapter_topics.py).

The plan, data/analysis/all_topic_audit/final_plan.json, lists every pages row
whose `topics` change, with the old and new values and where the new value came
from:
  * workbook          -- the row is a verified chapterwise-workbook question
                         (Physics, FPM, M1) and the live tag disagreed with it;
  * claude_corrected  -- no workbook question; Claude read the question and
                         corrected the tag (Chemistry, Biology, Human Biology and
                         the papers the workbooks do not cover).
The reading record behind it is data/analysis/all_topic_audit/corrections.txt.

Backs up every touched row first, writes pages.topics, mirrors question_tags for
rows that have a `questions` mirror, then re-reads to verify.

    python scripts/fix_live_chapter_topics_audit_20261010.py            # dry run
    python scripts/fix_live_chapter_topics_audit_20261010.py --execute
    python scripts/fix_live_chapter_topics_audit_20261010.py --execute --subject 4CH1
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.live_paper_sources import ROOT, supabase_client  # noqa: E402

PLAN = ROOT / "data" / "analysis" / "all_topic_audit" / "final_plan.json"
BACKUP_DIR = ROOT / "data" / "backups"
BATCH = 100


def current_topics(sb, ids: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for i in range(0, len(ids), BATCH):
        for row in sb.table("pages").select("id,topics").in_("id", ids[i:i + BATCH]).execute().data:
            out[row["id"]] = sorted(row["topics"] or [])
    return out


def mirrored_ids(sb, ids: list[str]) -> set[str]:
    found: set[str] = set()
    for i in range(0, len(ids), BATCH):
        found |= {r["id"] for r in sb.table("questions").select("id").in_("id", ids[i:i + BATCH]).execute().data}
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--subject", help="limit to one subject code, e.g. 4CH1")
    args = parser.parse_args()

    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    if args.subject:
        plan = [p for p in plan if p["code"] == args.subject]
    if not plan:
        print("Nothing to change.")
        return 0

    sb = supabase_client()
    ids = [p["id"] for p in plan]
    now = current_topics(sb, ids)
    stale = [p for p in plan if now.get(p["id"]) != p["old"]]
    print("changes by subject:", dict(Counter(p["code"] for p in plan)))
    print("by source:", dict(Counter(p["source"] for p in plan)))
    if stale:
        print(f"{len(stale)} row(s) changed since the plan was built -- nothing written. First few:")
        for p in stale[:10]:
            print(f"  {p['code']} {p['paper']} Q{p['q']}: plan old {p['old']} vs live {now.get(p['id'])}")
        return 1
    if not args.execute:
        print(f"Dry run: {len(plan)} pages rows would change. Re-run with --execute to write.")
        return 0

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = BACKUP_DIR / f"live_topics_audit_{stamp}.json"
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_text(json.dumps([{"id": i, "topics": now[i]} for i in ids], indent=1), encoding="utf-8")
    print(f"backup: {backup.relative_to(ROOT)}")

    groups: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for p in plan:
        groups[tuple(p["new"])].append(p["id"])
    for topics, group in groups.items():
        for i in range(0, len(group), BATCH):
            sb.table("pages").update({"topics": list(topics)}).in_("id", group[i:i + BATCH]).execute()

    mirrored = mirrored_ids(sb, ids)
    for p in plan:
        if p["id"] in mirrored:
            sb.table("question_tags").delete().eq("question_id", p["id"]).execute()
            sb.table("question_tags").insert([{"question_id": p["id"], "topic": t} for t in p["new"]]).execute()

    after = current_topics(sb, ids)
    wrong = [p for p in plan if after.get(p["id"]) != p["new"]]
    print(f"written {len(plan)} pages rows; question_tags mirrored for {len(mirrored)}; "
          f"verification mismatches: {len(wrong)}")
    return 0 if not wrong else 1


if __name__ == "__main__":
    sys.exit(main())
