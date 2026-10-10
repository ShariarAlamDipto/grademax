"""
Fill the one hole in the P4 (WMA14) archive.

  2023 May-Jun  QP   the slot holds the JANUARY 2023 paper

`P72871A` is filed under both 2023 slots, so the June session has been serving
January's exam. The copy's cover honestly says January, which is why no cover
or filename check finds it; the mark schemes are the tell, and the paper scores
0.331 against January's and 0.185 against June's.

Everything else P4 needs is already held and audits clean. In particular there
is nothing to fetch before October 2020, because nothing exists -- see the note
at the head of `audit_p4_yearwise_sources.py`.

    python scripts/repair_p4_missing_qps.py            # check only
    python scripts/repair_p4_missing_qps.py --commit
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_p4_yearwise_sources import P4  # noqa: E402
from lib.yearwise_repair import Wanted, run  # noqa: E402

NEW = ("https://qualifications.pearson.com/content/dam/pdf/"
       "International-Advanced-Level/Mathematics/2018/Exam-materials")

WANTED = (
    Wanted(2023, "May-Jun", "QP",
           f"{NEW}/wma14-01-que-20230610.pdf", "Pearson",
           "slot holds the January 2023 paper"),
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    return run(P4, "P4", WANTED, args.commit)


if __name__ == "__main__":
    sys.exit(main())
