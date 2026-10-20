#!/usr/bin/env python3
"""
Publish the rebuilt, proven IGCSE Mathematics A (4MA1) question + mark-scheme
segments to the live test builder and worksheet generator.

    python scripts/publish_mathsa_live_segments.py            # dry run
    python scripts/publish_mathsa_live_segments.py --execute

Run rebuild_mathsa_live_segments.py first (it writes the verdicts read here).
Maths A has never been served, so there are no live rows to update or audit:
every rebuilt question is INSERTED, with its scheme only when the pair was
proven (else NULL = "mark scheme not available"). Then run
apply_mathsa_rebuild_topics.py --execute to tag them, and only then add 4MA1
to TOOL_SUBJECT_SLOTS (src/lib/toolSubjects.ts).
See lib/live_segments_publish.py for exactly what is written and how to undo it.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.live_paper_sources import REBUILD_DIR, r2_reader  # noqa: E402
from lib.live_rebuild_common import PUBLISHABLE  # noqa: E402
from lib.live_segments_publish import build_plan, execute  # noqa: E402
from classify_mathsa_tool_topics import validate_tags  # noqa: E402
from apply_mathsa_rebuild_topics import difficulty  # noqa: E402

CODE = "4MA1"
R2_FOLDER = "subjects/MathsA"
NO_LIVE_ROWS = {"rows": []}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--upload-workers", type=int, default=8)
    args = parser.parse_args()

    verdicts = json.loads((REBUILD_DIR / CODE / "verdicts.json").read_text(encoding="utf-8"))
    stage = REBUILD_DIR / CODE
    audit = json.loads((stage / "artifact_audit.json").read_text(encoding="utf-8"))
    topics = json.loads((stage / "topics_new.json").read_text(encoding="utf-8"))
    keys = {f"{r['paper']}|{r['question']}" for r in verdicts["rows"]}
    validate_tags(topics, keys)
    if (not audit.get("passed") or audit.get("questions") != len(keys)
            or set(topics) != keys or args.upload_workers < 1
            or any(r["verdict"] not in PUBLISHABLE for r in verdicts["rows"])):
        raise ValueError("Maths A artifacts and classification must pass before publication")
    _, prefix = r2_reader()
    plan, rows = build_plan(CODE, R2_FOLDER, verdicts, NO_LIVE_ROWS, PUBLISHABLE, prefix)
    if rows:
        print(f"REFUSING: 4MA1 already has {len(rows)} pages rows; this script is for the "
              f"first publish only -- review them and use the generic update path.")
        return 1
    tagged = {(r["paper_id"], str(r["question"])):
              (topics[f"{r['paper']}|{r['question']}"], difficulty(int(r["marks"])))
              for r in verdicts["rows"]}
    for row in plan.inserts:
        row["topics"], row["difficulty"] = tagged[(row["paper_id"], row["question_number"])]
    if "new question inserted (unclassified)" in plan.counts:
        plan.counts["new question inserted (classified)"] = plan.counts.pop(
            "new question inserted (unclassified)")
    print(f"=== {CODE} -> live pages  [{'EXECUTE' if args.execute else 'DRY RUN'}] ===")
    for name, n in sorted(plan.counts.items(), key=lambda kv: -kv[1]):
        print(f"  {n:5}  {name}")
    print(f"  uploads planned: {len({k for _, k in plan.uploads})}")
    if args.execute:
        execute(CODE, plan, rows, upload_workers=args.upload_workers)
    else:
        print("\nDry run only. Re-run with --execute to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
