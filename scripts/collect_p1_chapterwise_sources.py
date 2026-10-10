"""
Gather the verified source papers for the P1 (WMA11) chapterwise workbook
into data/workbook/ial_sources/p1/. All the work and the checks are in
lib/ial_chapterwise_sources.py.

    python scripts/collect_p1_chapterwise_sources.py            # report
    python scripts/collect_p1_chapterwise_sources.py --execute
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.ial_chapterwise_sources import ROOT, Unit, collect  # noqa: E402

UNIT = Unit(token="P1", code="WMA11", first=(2019, "jan"),
            yearwise_audit=None,
            linkage=True,
            june_2025=("wma11-01-que-20250509", "wma11-01-rms-20250814"))

if __name__ == "__main__":
    sys.exit(collect(UNIT, execute="--execute" in sys.argv))
