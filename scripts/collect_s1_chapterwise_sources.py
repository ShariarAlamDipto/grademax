"""
Gather the verified source papers for the S1 (WST01) chapterwise workbook
into data/workbook/ial_sources/s1/. All the work and the checks are in
lib/ial_chapterwise_sources.py.

    python scripts/collect_s1_chapterwise_sources.py            # report
    python scripts/collect_s1_chapterwise_sources.py --execute
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.ial_chapterwise_sources import ROOT, Unit, collect  # noqa: E402

UNIT = Unit(token="S1", code="WST01", first=(2019, "jan"),
            yearwise_audit=ROOT / "data" / "analysis" / "s1_yearwise_source_audit.json",
            linkage=False,
            june_2025=("wst01-01-que-20250521", "wst01-01-rms-20250814"))

if __name__ == "__main__":
    sys.exit(collect(UNIT, execute="--execute" in sys.argv))
