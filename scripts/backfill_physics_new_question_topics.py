#!/usr/bin/env python3
"""
Give topic tags to the 171 IGCSE Physics questions the 2026-10-07 live rebuild
added (they were inserted with topics [], so topic-filtered tools skipped them).

    python scripts/backfill_physics_new_question_topics.py            # dry run
    python scripts/backfill_physics_new_question_topics.py --execute

Live Physics topics are the spec's eight sections, codes "1".."8", which are
exactly the Physics workbook's chapters. Sources, recorded per row in
data/analysis/live_rebuild/4PH1/topic_backfill.json:
  * 82 questions in the workbook's 2018-2023 window: its classification
    (section -> chapter, secondaries included) and difficulty;
  * 89 others: read and classified by Claude from the question text.
Only rows whose topics are still empty are touched; question_tags (the
legacy mirror) gets the same tags.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.live_paper_sources import ROOT, supabase_client  # noqa: E402

DATA = ROOT / "data" / "analysis" / "live_rebuild" / "4PH1" / "topic_backfill.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    data = json.loads(DATA.read_text(encoding="utf-8"))
    plan = [(m["id"], m["topics"], m["difficulty"]) for m in data["mapped"]]
    plan += [(n["id"], [n["topic"]], None) for n in data["need"]]

    sb = supabase_client()
    ids = [p[0] for p in plan]
    current = {}
    for i in range(0, len(ids), 100):
        for r in sb.table("pages").select("id,topics").in_("id", ids[i:i + 100]).execute().data:
            current[r["id"]] = r["topics"]
    todo = [p for p in plan if not current.get(p[0])]
    print(f"planned {len(plan)}; still untagged {len(todo)}")
    if not args.execute:
        print("Dry run only. Re-run with --execute to write.")
        return 0
    for page_id, topics, difficulty in todo:
        fields = {"topics": topics}
        if difficulty:
            fields["difficulty"] = difficulty
        sb.table("pages").update(fields).eq("id", page_id).execute()
        sb.table("question_tags").upsert(
            [{"question_id": page_id, "topic": t} for t in topics],
            on_conflict="question_id,topic").execute()
    left = sum(1 for i in range(0, len(ids), 100)
               for r in sb.table("pages").select("topics").in_("id", ids[i:i + 100]).execute().data
               if not r["topics"])
    print(f"written {len(todo)}; untagged now {left}")
    return 0 if left == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
