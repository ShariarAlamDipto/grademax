#!/usr/bin/env python3
"""
Tag the Maths A (4MA1) tool questions after publish_mathsa_live_segments.py
--execute: spec-section topics from data/analysis/live_rebuild/4MA1/
topics_new.json (classify_mathsa_tool_topics.py) and difficulty from the
question's marks.

Difficulty bands are the ones measured for 4MA1 Higher in the workbook
(docs/workbook-mathsa-plan.md): <=3 marks easy, 4-5 medium, >=6 hard. Neither
the FPM nor the Maths B bands transfer -- 90% of Maths A questions are 3-6 marks.
The test builder filters on difficulty, so an untagged row would vanish from
every difficulty-filtered test.

    python scripts/apply_mathsa_rebuild_topics.py            # dry run
    python scripts/apply_mathsa_rebuild_topics.py --execute
"""

import argparse
import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.igcse_science_publish import load_topics  # noqa: E402
from lib.live_paper_sources import REBUILD_DIR, ROOT, fetch_rows, supabase_client  # noqa: E402
from classify_mathsa_tool_topics import validate_tags  # noqa: E402

CODE = "4MA1"


def difficulty(marks: int) -> str:
    if marks <= 3:
        return "easy"
    return "medium" if marks <= 5 else "hard"


def apply_published_metadata(rows: list[dict], topics: dict) -> None:
    """Verify complete live coverage, back up, then update only changed fields."""
    sb = supabase_client()
    paper_ids = sorted({r["paper_id"] for r in rows})
    pages = []
    for start in range(0, len(paper_ids), 50):
        part = paper_ids[start:start + 50]
        pages += fetch_rows(lambda o: sb.table("pages").select("*").in_("paper_id", part)
                            .eq("is_question", True).not_.is_("qp_page_url", "null")
                            .range(o, o + 999))
    indexed = {}
    for page in pages:
        key = (page["paper_id"], str(page["question_number"]))
        if key in indexed:
            raise ValueError(f"Duplicate published question: {key}")
        indexed[key] = page
    if set(indexed) != set(topics):
        raise ValueError("Published questions must exactly match the reviewed classification")
    ids = [p["id"] for p in pages]
    mirror, existing_tags = [], []
    for start in range(0, len(ids), 100):
        part = ids[start:start + 100]
        mirror += fetch_rows(lambda o: sb.table("questions").select("*").in_("id", part)
                             .range(o, o + 999))
        existing_tags += fetch_rows(lambda o: sb.table("question_tags").select("*")
                                    .in_("question_id", part).range(o, o + 999))
    mirror_by_id = {q["id"]: q for q in mirror}
    if set(mirror_by_id) != set(ids):
        raise ValueError("Published question mirrors are incomplete; repair publication first")
    folder = ROOT / "data/backups" / f"mathsa_metadata_{dt.datetime.now():%Y%m%d_%H%M%S}"
    folder.mkdir(parents=True, exist_ok=True)
    for table, values in (("pages", pages), ("questions", mirror), ("question_tags", existing_tags)):
        (folder / f"{table}.json").write_text(json.dumps(values, indent=1), encoding="utf-8")
    print(f"metadata backup: {folder}", flush=True)
    levels = {(r["paper_id"], str(r["question"])): difficulty(int(r["marks"])) for r in rows}
    desired_tags, changed_pages, changed_mirrors = set(), 0, 0
    mirror_groups = {}
    for key, page in indexed.items():
        codes, level = topics[key], levels[key]
        if page["topics"] != codes or page["difficulty"] != level:
            sb.table("pages").update({"topics": codes, "difficulty": level}).eq("id", page["id"]).execute()
            changed_pages += 1
        if mirror_by_id[page["id"]]["difficulty"] != level:
            mirror_groups.setdefault(level, []).append(page["id"])
        desired_tags.update((page["id"], code) for code in codes)
    for level, group in mirror_groups.items():
        for start in range(0, len(group), 100):
            part = group[start:start + 100]
            sb.table("questions").update({"difficulty": level}).in_("id", part).execute()
            changed_mirrors += len(part)
    current_tags = {(t["question_id"], t["topic"]) for t in existing_tags}
    stale = [t["id"] for t in existing_tags if (t["question_id"], t["topic"]) not in desired_tags]
    for start in range(0, len(stale), 100):
        sb.table("question_tags").delete().in_("id", stale[start:start + 100]).execute()
    added = [{"question_id": qid, "topic": code} for qid, code in sorted(desired_tags - current_tags)]
    for start in range(0, len(added), 500):
        sb.table("question_tags").upsert(added[start:start + 500], on_conflict="question_id,topic").execute()
        print(f"question tags: {min(start + 500, len(added))}/{len(added)}", flush=True)
    result = {"questions": len(pages), "tag_assignments": len(desired_tags),
              "changed_pages": changed_pages, "changed_mirrors": changed_mirrors,
              "added_tags": len(added), "removed_stale_tags": len(stale), "backup": str(folder)}
    (REBUILD_DIR / CODE / "metadata_apply.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    rows = json.loads((REBUILD_DIR / CODE / "verdicts.json").read_text(encoding="utf-8"))["rows"]
    raw = json.loads((REBUILD_DIR / CODE / "topics_new.json").read_text(encoding="utf-8"))
    validate_tags(raw, {f"{r['paper']}|{r['question']}" for r in rows})
    topics = load_topics(CODE, rows)
    untagged = [f"{r['paper']} q{r['question']}" for r in rows
                if (r["paper_id"], str(r["question"])) not in topics]
    print(f"{CODE}: {len(rows)} questions, {len(topics)} with topics, {len(untagged)} without")
    if untagged:
        print("  REFUSING while any question is untagged:", untagged[:20])
        return 1
    print("  difficulty:", dict(Counter(difficulty(int(r["marks"])) for r in rows)))
    if args.execute:
        apply_published_metadata(rows, topics)
    else:
        print("Dry run only. Re-run with --execute to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
