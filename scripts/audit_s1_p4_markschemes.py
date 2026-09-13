#!/usr/bin/env python3
"""
Independent audit of the mark schemes attached to the S1 and P4 workbook trees.

    python scripts/audit_s1_p4_markschemes.py

The segmenters already accept a mark-scheme block only when its marks reconcile
with the question paper's. This checks something different and genuinely
independent: open each written PDF and read whether its FIRST page announces the
question the filename claims.

WHAT THIS DOES AND DOES NOT PROVE
---------------------------------
It re-reads the written PDF with the SAME primitives the parser used and checks
the artifact says what the parser believed. That catches extraction and writing
faults -- a block written from the wrong page range, an off-by-one, a file
saved under the wrong name. It is NOT an independent opinion on whether the
block is the right one; the independent check is the marks reconciliation
against the question paper, which happens in `ial_ms_parse`.

FOUR HAND-WRITTEN PROBES WERE TRIED FIRST AND ALL FOUR LIED
-----------------------------------------------------------
Worth not repeating. A mark-scheme page's left column is dense with data values
and formula digits, and every naive reading of "the question number on this
page" picked one of those up:

1. Scanning lines in document order rather than top-down. PyMuPDF emits blocks
   in no particular vertical order, so the "first" left-column line was often
   from halfway down the page. It reported question 10's scheme as question 6's
   when the page plainly opens '10(a)'.
2. Matching any bare numeral in the left column -- "question 25", "question 32",
   "question 70", on papers that have at most eleven questions.
3. Requiring the cell to match in full. A real cell usually carries the scheme
   text with it, '2.(a) [pass for] 30', so a full match fell through to
   whatever numeral came next and flagged correct blocks as wrong.
4. Excluding a fixed header band by y. The table starts at a different height on
   different papers, so this dropped the real cell on some of them.

Every case any of those flagged and that was then checked by hand turned out to
be a parser success and a probe failure. The lesson is the one this project
keeps relearning: look at a real page before believing a probe.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.ial_ms_parse import _read_ruled, _read_unruled  # noqa: E402

sys.stdout = io.TextIOWrapper(
    sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def opening_question(pdf_path: Path) -> int | None:
    """
    The question the first page of this written PDF announces.

    Uses the parser's own readers rather than a fresh heuristic -- see the
    module docstring for why four fresh heuristics were discarded.
    """
    with fitz.open(pdf_path) as doc:
        if doc.page_count == 0:
            return None
        first = doc[0]
        for read in (_read_ruled, _read_unruled):
            result = read(first)
            if result.starts is not None:
                return result.starts
    return None


def main() -> int:
    failures = 0
    for unit in ("s1", "p4"):
        root = REPO_ROOT / "data" / "workbook" / unit
        checked = wrong = unreadable = overlaps = 0
        bad: list[tuple] = []

        for manifest_path in sorted(root.glob("*/manifest.json")):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            used: dict[int, int] = {}
            for entry in manifest["questions"]:
                if not entry["has_markscheme"]:
                    continue
                number = entry["question_number"]
                checked += 1

                lo, hi = entry["ms_pages"]
                for page in range(lo, hi + 1):
                    if page in used:
                        overlaps += 1
                    used[page] = number

                found = opening_question(manifest_path.parent / "markschemes" / f"q{number}.pdf")
                if found is None:
                    unreadable += 1
                elif found != number:
                    wrong += 1
                    bad.append((manifest["key"], number, found, entry["ms_extractor"]))

        total = sum(
            len(json.loads(p.read_text(encoding="utf-8"))["questions"])
            for p in sorted(root.glob("*/manifest.json"))
        )
        print(f"=== {unit.upper()}")
        print(f"  attached          : {checked}/{total} ({checked * 100 // max(total, 1)}%)")
        print(f"  opens on wrong q  : {wrong}")
        print(f"  cell unreadable   : {unreadable}")
        print(f"  page overlaps     : {overlaps}")
        for item in bad:
            print(f"      {item}")
        failures += wrong + overlaps

    print(f"\nGATE {'PASS' if failures == 0 else 'FAIL'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
