"""
Set the chapter tags of rebuilt questions that are new or whose cut now holds
a different question than the live row did, after their publish. Tags come
from data/analysis/live_rebuild/<CODE>/topics_new.json: the verified
chapterwise workbook where it covers the question, else Claude's reading.
Run AFTER publish_<unit>_live_segments.py --execute (inserted rows exist then).
"""

from __future__ import annotations

import json

from lib.igcse_science_publish import apply_topics, load_topics
from lib.live_paper_sources import REBUILD_DIR


def run(code: str, *, do_execute: bool) -> int:
    rows = json.loads((REBUILD_DIR / code / "verdicts.json").read_text(encoding="utf-8"))["rows"]
    topics = load_topics(code, rows)
    print(f"{code}: {len(topics)} questions to tag")
    if do_execute:
        apply_topics(topics)
    else:
        print("Dry run only. Re-run with --execute to write.")
    return 0
