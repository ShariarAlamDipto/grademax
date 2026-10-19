#!/usr/bin/env python3
"""
Rebuild every live IAL Pure Mathematics 1 (WMA11) question + mark-scheme segment the
test builder and worksheet generator serve, from the whole-paper PDFs, and
PROVE each pair before it can be published.

    python scripts/rebuild_p1_live_segments.py            # build + verify (staging only)
    python scripts/rebuild_p1_live_segments.py --paper 2019_jan_P1
    python scripts/rebuild_p1_live_segments.py --render   # draw unproven pairs

Writes only to data/analysis/live_rebuild/WMA11/. Publishing is
publish_p1_live_segments.py. How documents are chosen, cut and proven:
lib/live_rebuild_ial.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.live_rebuild_ial import run  # noqa: E402

if __name__ == "__main__":
    sys.exit(run("WMA11", "P1"))
