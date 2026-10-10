#!/usr/bin/env python3
"""
Give topic tags to the IGCSE Maths B (4MB1) questions the 2026-10-07 live
rebuild inserted untagged. Tags (spec section codes) were classified by Claude
reading each question's text; the record, with the text, is
data/analysis/live_rebuild/4MB1/topic_backfill.json.

    python scripts/backfill_mathsb_new_question_topics.py            # dry run
    python scripts/backfill_mathsb_new_question_topics.py --execute
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.topic_backfill_apply import apply  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    sys.exit(apply("4MB1", execute=parser.parse_args().execute))
