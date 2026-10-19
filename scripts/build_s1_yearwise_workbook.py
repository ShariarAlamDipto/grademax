"""
Build the Statistics S1 (WST01) yearwise workbook: every paper from 2019 to 2023, in order.

Two volumes, as with Maths B and FPM -- a question book and a mark scheme book,
each with its own contents and its own page numbers from 1. The assembly lives
in `lib/yearwise_build.py`, shared with the other units; this file is what is
particular to S1.

    python scripts/build_s1_yearwise_workbook.py                 # dry run
    python scripts/build_s1_yearwise_workbook.py --execute
    python scripts/build_s1_yearwise_workbook.py --execute --allowance 1
    python scripts/build_s1_yearwise_workbook.py --execute --only questions
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.yearwise_build import DEFAULT_ALLOWANCE, Plan, run  # noqa: E402
from lib.yearwise_layout import Book  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
# The series artwork: white on the cover, and the watermark on every interior
# sheet once the finishing step runs.
LOCKUP = (Path.home() / "OneDrive" / "Desktop" / "FPM cover" / "Final Cover"
          / "Final Water Mark" / "FINAL WATERMARK.png")

PLAN = Plan(
    book=Book(name="Statistics S1", code="WST01", slug="s1", token="S1"),
    audit_json=ROOT / "data" / "analysis" / "s1_yearwise_source_audit.json",
    out_dir=ROOT / "data" / "workbook" / "s1_yearwise",
    lockup=LOCKUP,
    skip=frozenset({(2020, "May-Jun")}),
    notes={(2020, "Oct-Nov"):
           "paper set for June 2020; the summer series was cancelled"},
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--allowance", type=int, default=DEFAULT_ALLOWANCE,
                    help="blank answer sides a question may keep")
    ap.add_argument("--only", choices=("questions", "markschemes"), default=None)
    args = ap.parse_args()
    return run(PLAN, args.allowance, args.only, args.execute)


if __name__ == "__main__":
    sys.exit(main())
