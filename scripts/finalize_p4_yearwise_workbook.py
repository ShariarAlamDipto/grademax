"""
Put the covers and the watermark on the Pure Mathematics P4 (WMA14) yearwise workbook.

The work is in `lib/yearwise_finish.py`, shared with the other units.

    python scripts/finalize_p4_yearwise_workbook.py
    python scripts/finalize_p4_yearwise_workbook.py --only questions
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.yearwise_finish import finish  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=("questions", "markschemes"), default=None)
    args = ap.parse_args()
    # The supplied cover, with its PAPERS INCLUDED list corrected to this book's
    # sessions by scripts/fix_yearwise_cover_lists.py.
    cover = (Path(__file__).resolve().parent.parent / "data" / "workbook"
             / "M1 S1 P4 cover" / "corrected" / "PureMaths_P4_WMA14_YearWise_QP.pdf")
    return finish(slug="p4", token="P4", name="Pure Mathematics P4", only=args.only, question_cover=cover)


if __name__ == "__main__":
    sys.exit(main())
