#!/usr/bin/env python3
"""
Re-cut the Chemistry live papers whose question segments are wrong (2026-10-10 audit).
See scripts/lib/igcse_science_recut.py for what is wrong and how it is fixed.

    python scripts/recut_chemistry_live_papers.py --stage     # cut locally + contact sheets only
    python scripts/recut_chemistry_live_papers.py             # dry run against the live rows
    python scripts/recut_chemistry_live_papers.py --execute
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.igcse_science_recut import STAGE_ROOT, PaperSpec, run  # noqa: E402

CODE = "4CH1"
R2_FOLDER = "subjects/Chemistry"
PAPERS = [
    PaperSpec(CODE, R2_FOLDER, 2016, "jan", "1", "2016_Jan_1"),       # held 2015 Jan P1
    PaperSpec(CODE, R2_FOLDER, 2022, "may-jun", "1", "2022_May-Jun_1"),  # held 2022 May-Jun P2R
]
TOPICS = STAGE_ROOT / CODE / "topics.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--stage", action="store_true")
    args = parser.parse_args()
    return run(CODE, PAPERS, TOPICS, do_execute=args.execute, stage_only=args.stage)


if __name__ == "__main__":
    sys.exit(main())
