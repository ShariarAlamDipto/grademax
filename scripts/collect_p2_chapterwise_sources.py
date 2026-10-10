"""
Gather the verified source papers for the P2 (WMA12) chapterwise workbook
into data/workbook/ial_sources/p2/. All the work and the checks are in
lib/ial_chapterwise_sources.py.

    python scripts/collect_p2_chapterwise_sources.py            # report
    python scripts/collect_p2_chapterwise_sources.py --execute
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.ial_chapterwise_sources import ROOT, Unit, collect  # noqa: E402

UNIT = Unit(token="P2", code="WMA12", first=(2019, "oct-nov"),
            yearwise_audit=None,
            linkage=True,
            june_2025=("wma12-01-que-20250514", "wma12-01-rms-20250814"))

if __name__ == "__main__":
    sys.exit(collect(UNIT, execute="--execute" in sys.argv))
