#!/usr/bin/env python3
"""
Independent check that each attached mark scheme is the right question's.

Covers every IAL workbook unit: S1, P1, P2, P3, P4.

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
#: A page number sitting in front of the table header.
LEADING_PAGE_RE = re.compile(
    r"^\s*\d{1,3}\s+(?=(?:Question|Qu\.?\s*No))", re.I
)

#: The largest question number any 75-mark IAL paper in this archive carries is
#: 11; 15 is a generous bound. It is NOT the expected number for this block --
#: that would be circular -- just a property of the papers, and it is what
#: separates a real cell from a page number like "17 (a)" or "22 (i)".
MAX_QUESTION_NUMBER = 15

#: Cases where the reader disagrees but the attachment was CHECKED BY HAND and
#: is correct. Recorded so the gate flags only NEW cases instead of crying wolf
#: -- this is a verification result, not a suppression.
#:
#: Each of these pages prints something between the header and the cell that
#: looks like a number: a page number, or the question's own equation whose
#: exponents read as bare digits. Evidence for each, from reading the question
#: paper and the scheme side by side:
#:
#:   p1 2019_jan q9      QP "3x + 5 = -2x + c"     MS "...= -2x + c  9. Multiplies through by x"
#:   p1 2019_oct-nov q11 QP "11. A curve y = f(x)" MS "17 (a) Uses gradient of 5 at P(4, 32/3)"
#:   p1 2021_jan q9      QP "9. (i) Find integral" MS "22 (i) Attempts to multiply out the numerator"
#:   p2 2023_oct-nov q4  QP "4. ..."               MS "...f(x) = 4x^3 + ax^2 - 29x + b  4.(a) Sets f(-1/2) = 0"
#:   p2 2023_oct-nov q9  QP "9. P(9, 40) ..."      MS "...y = x^2 - 9x + 13/3  9 (a) dy/dx = 4x - 9"
#:   p3 2024_may-jun q4  QP "4. f(x) = 8 sin x cos x + 4 cos 2x - 3"
#:                                                 MS "...8sin cos 4cos 3  4(a) States sin 2x = 2 sin x cos x"
HAND_VERIFIED: dict[tuple[str, str, int], int] = {
    ("p1", "2019_jan", 9): 3,
    ("p1", "2019_oct-nov", 11): 17,
    ("p1", "2021_jan", 9): 22,
    ("p2", "2023_oct-nov", 4): 3,
    ("p2", "2023_oct-nov", 9): 2,
    ("p3", "2024_may-jun", 4): 2,
}

#: A cell WITH its punctuation: "4.", "9 (a)", "4.(a)", "7 (i)". Requiring the
#: dot or the bracket is what distinguishes the cell from a bare numeral, and
#: several layouts print the question's EQUATION between the header and the
#: cell -- "Scheme Marks 3 2 f(x) = 4x^3 + ax^2 ... 4.(a)" -- so a bare-number
#: match lands on an exponent.
PUNCTUATED_CELL_RE = re.compile(
    r"\b(\d{1,2})\s*\.?\s*\(\s*[a-z]\s*\)|\b(\d{1,2})\s*\.(?=\s)"
)


def first_cell_after_header(tail: str) -> int | None:
    """
    The first punctuated cell in the text following a table header.

    Scans in order and takes the first candidate within MAX_QUESTION_NUMBER, so
    a page number printed before the table is skipped rather than returned.
    Where a block starts on a continuation page there is no cell at all and this
    returns None -- honestly unreadable rather than a false disagreement.
    """
    for match in PUNCTUATED_CELL_RE.finditer(tail):
        number = int(match.group(1) or match.group(2))
        if 1 <= number <= MAX_QUESTION_NUMBER:
            return number
    return None


#: A single header cell token, matched on its own line.
HEADER_TOKEN_RE = re.compile(r"^(?:Question|Number|Scheme|Marks?|Notes?|Working|Answer|AO)\b", re.I)

HEADER_ANYWHERE_RE = re.compile(
    r"(?:Question\s*Number|Qu\.?\s*No\.?)\s*(?:Scheme)?\s*(?:Marks?)?", re.I
)


def printed_question_number(pdf_path: Path) -> int | None:
    """
    The question number the first page of this mark scheme prints.

    Priority order, arrived at by measuring each alternative on all five units:

    1. **After the table header**, wherever that header sits. This handles a
       session banner and a page number in front of the table uniformly -- both
       just become text before the header -- and it is authoritative because the
       cell immediately follows the header by construction.
    2. Header at the very start, stripped, then the first token.
    3. Visual: topmost left-column token. Last resort only.

    A VISUAL-FIRST version was tried and was measurably worse: P4 dropped from
    89/89 to 72/89 and S1 from 127/127 to 122/127, because scheme content puts
    formula digits in the left column just below the header. Flat text is better
    here precisely because the cell leads the text stream in most layouts.
    """
    if not pdf_path.exists():
        return None
    with fitz.open(pdf_path) as doc:
        if doc.page_count == 0:
            return None
        text = " ".join(doc[0].get_text().split())

        # 1. The cell after the header, wherever the header is.
        #
        #    The plain match comes first because several layouts print a BARE
        #    number as the cell ("Marks 1 Volume = ..."), and requiring
        #    punctuation misses every one of them -- measured: P4 drops from
        #    89/89 to 76/89.
        #
        #    It is only when that plain match returns an impossible question
        #    number that the page is printing something else first -- a page
        #    number like "17 (a)" or "22 (i)" -- and the punctuated scan is used
        #    to look past it. If that finds nothing either, the page genuinely
        #    does not state a number and None is the honest answer.
        anywhere = HEADER_ANYWHERE_RE.search(text)
        if anywhere:
            tail = text[anywhere.end():].strip()
            plain = CELL_RE.match(tail)
            if plain:
                number = int(plain.group(1))
                if number <= MAX_QUESTION_NUMBER:
                    return number
                return first_cell_after_header(tail)
            found = first_cell_after_header(tail)
            if found is not None:
                return found

        # 2. Header at the start (some layouts print no "Number" word at all).
        stripped = HEADER_WORDS_RE.sub("", text).strip()
        match = CELL_RE.match(stripped)
        if match:
            return int(match.group(1))

        # 3. Visual last resort, for pages with no header at all.
        candidates: list[tuple[float, int]] = []
        for block in doc[0].get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                x0 = min(s["bbox"][0] for s in spans)
                y0 = min(s["bbox"][1] for s in spans)
                token = "".join(s["text"] for s in spans).strip()
                if x0 < 110 and y0 > 25 and token:
                    hit = CELL_RE.match(token)
                    if hit:
                        candidates.append((y0, int(hit.group(1))))
        if candidates:
            return min(candidates)[1]
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show", type=int, default=15)
    parser.add_argument(
        "--units",
        default="s1,p1,p2,p3,p4",
        help="comma-separated unit directories under data/workbook",
    )
    args = parser.parse_args()

    failures = 0

    for unit in [u.strip() for u in args.units.split(",") if u.strip()]:
        root = REPO_ROOT / "data" / "workbook" / unit
        if not root.exists():
            print(f"=== {unit.upper()}: no segment tree, skipped")
            continue
        agree = disagree = unreadable = hand_checked = 0
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
                elif HAND_VERIFIED.get((unit, manifest["key"], number)) == found:
                    hand_checked += 1
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
        if hand_checked:
            print(
                f"  reader artifact      : {hand_checked} "
                f"(hand-verified correct; see HAND_VERIFIED)"
            )
        for key, number, found, extractor in suspects[: args.show]:
            print(f"      {key} q{number}: scheme prints {found}  [{extractor}]")
        failures += disagree

    print()
    print(f"GATE {'PASS' if failures == 0 else f'FAIL ({failures} disagreements)'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
