"""
Covers, watermark and final audit for the Statistics S1 (WST01) chapterwise book.
The work is in lib/ial_workbook_finish.py.

    python scripts/finalize_s1_workbook_print.py             # paged edition
    python scripts/finalize_s1_workbook_print.py paged --part all
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.ial_workbook_finish import finalize_unit  # noqa: E402

if __name__ == "__main__":
    sys.exit(finalize_unit("s1", "WST01", "Statistics S1"))
