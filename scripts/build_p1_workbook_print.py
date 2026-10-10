"""
Print-ready Pure Mathematics P1 (WMA11) chapterwise workbook: question book + mark scheme
book. All the assembly is in lib/ial_workbook_print.py; this names the unit.

    python scripts/build_p1_workbook_print.py                     # dry run
    python scripts/build_p1_workbook_print.py --execute           # paged edition
    python scripts/build_p1_workbook_print.py --execute --part 1  # first volume of two
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import ial_workbook_print as book  # noqa: E402
from lib.p1_notes import flow_blocks  # noqa: E402

# --part splits the book before this chapter, for a two-volume set.
SPLIT_CHAPTER = 3

if __name__ == "__main__":
    book.configure("p1", "WMA11", "Pure Mathematics P1", flow_blocks, SPLIT_CHAPTER)
    sys.exit(book.main())
