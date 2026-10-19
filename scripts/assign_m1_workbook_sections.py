"""
Settle the M1 (WME01) chapterwise book's sections and write its print order
(data/workbook/m1_book.json). The logic is in lib/ial_workbook_assign.py.

    python scripts/assign_m1_workbook_sections.py              # report
    python scripts/assign_m1_workbook_sections.py --disputes   # list them
    python scripts/assign_m1_workbook_sections.py --execute
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.ial_workbook_assign import settle  # noqa: E402

if __name__ == "__main__":
    sys.exit(settle("m1", "WME01", execute="--execute" in sys.argv,
                    show_disputes="--disputes" in sys.argv))
