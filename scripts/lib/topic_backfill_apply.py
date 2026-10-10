"""
Apply topic tags recorded in data/analysis/live_rebuild/<CODE>/topic_backfill.json
to live `pages` rows that still have none, mirroring them into question_tags.

Entries: "mapped" {id, topics, difficulty, classified_by} and "need"
{id, topic, classified_by}. Only empty rows are written, so it is safe to re-run.
"""

from __future__ import annotations

import json

from lib.live_paper_sources import REBUILD_DIR, supabase_client


def apply(code: str, *, execute: bool) -> int:
    data = json.loads((REBUILD_DIR / code / "topic_backfill.json").read_text(encoding="utf-8"))
    plan = [(m["id"], m["topics"], m.get("difficulty")) for m in data.get("mapped", [])]
    plan += [(n["id"], [n["topic"]], None) for n in data["need"] if n.get("topic")]
    sb = supabase_client()
    ids = [p[0] for p in plan]

    def untagged() -> set[str]:
        out = set()
        for i in range(0, len(ids), 100):
            for r in sb.table("pages").select("id,topics").in_("id", ids[i:i + 100]).execute().data:
                if not r["topics"]:
                    out.add(r["id"])
        return out

    todo = [p for p in plan if p[0] in untagged()]
    print(f"{code}: planned {len(plan)}; still untagged {len(todo)}")
    if not execute:
        print("Dry run only. Re-run with --execute to write.")
        return 0
    for page_id, topics, difficulty in todo:
        fields = {"topics": topics}
        if difficulty:
            fields["difficulty"] = difficulty
        sb.table("pages").update(fields).eq("id", page_id).execute()
        sb.table("question_tags").upsert([{"question_id": page_id, "topic": t} for t in topics],
                                         on_conflict="question_id,topic").execute()
    left = len(untagged())
    print(f"{code}: written {len(todo)}; untagged now {left}")
    return 0 if left == 0 else 1
