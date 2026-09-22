#!/usr/bin/env python3
"""
Independent check that each attached mark scheme is the right question's.

    python scripts/check_s1_p4_markscheme_matching.py
    python scripts/check_s1_p4_markscheme_matching.py --show 20

WHAT MAKES THIS INDEPENDENT
---------------------------
`ial_ms_parse` attaches a block only when its MARKS reconcile with the question
paper's, and it locates the question cell GEOMETRICALLY (column x, header y).

This reads the same ground truth -- the number the mark scheme prints at the top
of its first page -- from the FLAT text, with no geometry at all. Different
evidence from the marks, and a different implementation from the parser's, so
an error in either one shows up as a disagreement.

A CONTENT-OVERLAP CHECK WAS TRIED FIRST AND WAS WORTHLESS
----------------------------------------------------------
The first version of this script scored each scheme's vocabulary against every
question in its paper, on the theory that a mark scheme restates its question's
numbers and context. It reported 66 suspects. Every one inspected by hand was
correct.

The theory is simply false for maths and statistics: a mark scheme is almost
pure notation -- `B1 B1 B1 (4)` plus formulae -- around 1,400 characters against
a 9,000-character question. There is hardly any prose to match, so the score was
dominated by which question happened to be shortest. P4's median margin over the
runner-up was +0.008, i.e. no discrimination at all. Recorded because the
approach looks reasonable until measured.

TWO LAYOUT FACTS THIS DEPENDS ON
--------------------------------
* The cell is sometimes `5. (a)` and sometimes a bare `1` with no dot and no
  part letter. Requiring the dot or the bracket misses every P4 paper.
* The `Question / Number / Scheme / Marks` header is NOT always present above
  the cell. Seeking to it first skips past the real cell on the S1 papers that
  omit it, which is what produced the only three S1 disagreements in an earlier
  draft -- all three verified correct by hand.
* Several pages carry a session banner BEFORE the header ("January 2019 WST01
  STATISTICS 1 Mark Scheme Question Number Scheme Marks 1.(a)"), and one paper
  abbreviates the header to "Qu. No.".
* **PyMuPDF block order is not visual order.** On pages that mix a scheme table
  with marking notes, the flat text can begin with the notes even though the
  question cell sits at the top of the page. Four P4 schemes read as unreadable
  for this reason alone; every one was confirmed by eye to carry its own cell.
  So the fallback re-reads the page in visual order (topmost left-column token),
  which is still a different rule from the parser's column-x calibration.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

import fitz

sys.stdout = io.TextIOWrapper(
    sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
)

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Table furniture that precedes the cell when it is present at all.
HEADER_WORDS_RE = re.compile(
    r"^(?:\s*(?:Question|Number|Scheme|Marks?|Notes?|Working|Answer|AO)\b)+", re.I
)

#: '5. (a)', '5(a)', '5.', or a bare '5' -- all four occur.
CELL_RE = re.compile(r"^\s*(\d{1,2})\s*(?:\.|\(|\s|$)")

#: The same header words, found anywhere -- some pages print a session banner
#: first ("January 2019 WST01 STATISTICS 1 Mark Scheme Question Number ...").
#: "Qu. No." is one paper's abbreviation of the same thing.
HEADER_ANYWHERE_RE = re.compile(
    r"(?:Question\s*Number|Qu\.?\s*No\.?)\s*(?:Scheme)?\s*(?:Marks?)?", re.I
)


def printed_question_number(pdf_path: Path) -> int | None:
    """The question number the first page of this mark scheme prints."""
    if not pdf_path.exists():
        return None
    with fitz.open(pdf_path) as doc:
        if doc.page_count == 0:
            return None
        text = " ".join(doc[0].get_text().split())

    # 1. Flat read: strip a leading header, then take the first token.
    stripped = HEADER_WORDS_RE.sub("", text).strip()
    match = CELL_RE.match(stripped)
    if match:
        return int(match.group(1))

    # 2. Some pages put a session banner before the header, so look for the
    #    header anywhere rather than only at the start.
    anywhere = HEADER_ANYWHERE_RE.search(text)
    if anywhere:
        match = CELL_RE.match(text[anywhere.end():].strip())
        if match:
            return int(match.group(1))

    # 3. Visual fallback: the topmost token in the left column. Needed because
    #    block order is not visual order on pages mixing a table with notes.
    with fitz.open(pdf_path) as doc:
        candidates: list[tuple[float, int]] = []
        for block in doc[0].get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                x0 = min(s["bbox"][0] for s in spans)
                y0 = min(s["bbox"][1] for s in spans)
                token = "".join(s["text"] for s in spans).strip()
                if x0 < 110 and y0 > 90 and token:
                    hit = CELL_RE.match(token)
                    if hit:
                        candidates.append((y0, int(hit.group(1))))
    return min(candidates)[1] if candidates else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show", type=int, default=15)
    args = parser.parse_args()

    failures = 0

    for unit in ("s1", "p4"):
        root = REPO_ROOT / "data" / "workbook" / unit
        agree = disagree = unreadable = 0
        suspects: list[tuple] = []

        for manifest_path in sorted(root.glob("*/manifest.json")):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for entry in manifest["questions"]:
                if not entry["has_markscheme"]:
                    continue
                number = entry["question_number"]
                found = printed_question_number(
                    manifest_path.parent / "markschemes" / f"q{number}.pdf"
                )
                if found is None:
                    unreadable += 1
                elif found == number:
                    agree += 1
                else:
                    disagree += 1
                    suspects.append(
                        (manifest["key"], number, found, entry["ms_extractor"])
                    )

        total = agree + disagree + unreadable
        print(f"=== {unit.upper()}")
        print(f"  attached schemes    : {total}")
        print(f"  printed number agrees: {agree}")
        print(f"  DISAGREES            : {disagree}")
        print(f"  number unreadable    : {unreadable}")
        for key, number, found, extractor in suspects[: args.show]:
            print(f"      {key} q{number}: scheme prints {found}  [{extractor}]")
        failures += disagree

    print()
    print(f"GATE {'PASS' if failures == 0 else f'FAIL ({failures} disagreements)'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
