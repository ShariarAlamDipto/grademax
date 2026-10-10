#!/usr/bin/env python3
"""
Tag the new / changed WMA14 questions after publish_p4_live_segments.py --execute.
See lib/rebuild_topics_apply.py.

    python scripts/apply_p4_rebuild_topics.py            # dry run
    python scripts/apply_p4_rebuild_topics.py --execute
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.rebuild_topics_apply import run  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    sys.exit(run("WMA14", do_execute=parser.parse_args().execute))
