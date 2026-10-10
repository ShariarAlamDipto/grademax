#!/usr/bin/env python3
"""
Publish the rebuilt, proven 4HB1 question + mark-scheme segments to the live
test builder and worksheet generator (one copy of each paper; see
lib/igcse_science_publish.py). Run rebuild_humanbio_live_segments.py first and
re-run audit_humanbio_live_ms_linkage.py afterwards as the gate.

    python scripts/publish_humanbio_live_segments.py            # dry run
    python scripts/publish_humanbio_live_segments.py --execute
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.igcse_science_publish import run  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    sys.exit(run("4HB1", "subjects/Human_Biology", do_execute=parser.parse_args().execute))
