#!/usr/bin/env python3
"""
Publish the rebuilt, proven IGCSE Further Pure Maths (4PM1) question + mark-scheme
segments to the live test builder and worksheet generator.

    python scripts/publish_fpm_live_segments.py            # dry run
    python scripts/publish_fpm_live_segments.py --execute

Run rebuild_fpm_live_segments.py first (it writes the verdicts read here), then re-run
audit_fpm_live_ms_linkage.py afterwards as the gate.
See lib/live_segments_publish.py for exactly what is written and how to undo it.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.live_paper_sources import REBUILD_DIR  # noqa: E402
from lib.live_rebuild_common import PUBLISHABLE  # noqa: E402
from lib.live_segments_publish import run  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    sys.exit(run("4PM1", "subjects/Further_Pure_Mathematics", REBUILD_DIR / "4PM1", PUBLISHABLE,
                 do_execute=args.execute))
