#!/usr/bin/env python3
"""
Tag the new / changed WST01 questions after publish_s1_live_segments.py --execute.
See lib/rebuild_topics_apply.py.

    python scripts/apply_s1_rebuild_topics.py            # dry run
    python scripts/apply_s1_rebuild_topics.py --execute
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.rebuild_topics_apply import run  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    sys.exit(run("WST01", do_execute=parser.parse_args().execute))
