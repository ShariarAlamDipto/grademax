"""
IAL mark-scheme blocks located by the QUESTION NUMBER the scheme prints and
verified by the TOTAL it prints.

Companion to `ial_ms_parse`, used before it. That module accepts a block only
when its summed M1/A1/B1 codes or "(n)" part tallies equal the question's marks,
which is sound but loses about 30% of IAL questions (measured 2026-10-06 over
P1/P2/S1: 96 blocks found and rejected on their sums, 26 never found):

* Alternative methods are printed in full, so a 10-mark question's codes sum to
  20 -- the block is right and its sum is double.
* The 2023+ layout writes the question cell as "1a", which ial_ms_parse's cell
  patterns do not accept, so two whole P1 papers found nothing.

THE EVIDENCE USED HERE, both printed by the scheme itself:

  where   the question's own number in the scheme's question column ("1a",
          "1(a)", "1.", "1"), on a page that repeats the table header. A block
          runs from its number to the next question's number. Numbers are
          taken in document order and must INCREASE -- a numeral that breaks
          the sequence is a value from the working, not a question cell.
  which   the "(N marks)" total most IAL Pure schemes print after each question.
          A block is accepted when the FIRST total inside it equals the marks
          the question paper's own fence states. Later totals in the block are
          the alternative methods repeating it.

A block with no printed total is left for `ial_ms_parse` to judge on its codes.
Nothing is accepted on position alone: a wrong mark scheme is worse than a
missing one (the rule `ial_ms_parse` states, and this module keeps).

Where question n+1 starts partway down the page question n ends on, the block
carries a y-band (`top` on its first page, `bottom` on its last) so the written
segment never shows the neighbour's scheme.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import fitz

from .ial_ms_parse import CODE_RE

#: The question column is located from this page's own header.
# "Qu" is how the S1 schemes abbreviate it.
# "Qu" (S1) and a bare "Q" (M1 2024+, "Q | Scheme | Marks | Notes") abbreviate it.
QNUM_HEADER_RE = re.compile(r"^(?:question|number|question\s+number|qu\.?|q\.?)$", re.I)
# "Mark Notes" when the two headers are set as one line (M1 2021 June).
MARKS_HEADER_RE = re.compile(r"^marks?(?:\s+notes)?$", re.I)
NOTES_HEADER_RE = re.compile(r"^notes$", re.I)
COLUMN_TOLERANCE = 25.0
HEADER_CLEARANCE = 4.0

#: A question cell: the number, then nothing, a dot, a bracketed part, or a
#: single part letter run on ("1a", "1a(i)"). "12 cm" and "5 marks" fail: after
#: the digits comes a space and a multi-letter word.
CELL_RE = re.compile(r"^(\d{1,2})(?:\s*\.|\s*\(\s*[a-h]\s*\)|[a-h](?![a-z])|\s+[a-h](?![a-z])|\s*$)")

#: A cell that is only a number, with no part marker.
BARE_RE = re.compile(r"^\d{1,2}\s*\.?\s*$")
#: How far below the header a bare-number cell may sit and still be a cell.
BARE_MAX_DROP = 80.0

#: The per-question total as a line of its own: "(5 marks)" (P1/P2) or
#: "Total 13" (S1).
TOTAL_RE = re.compile(r"^(?:\(\s*(\d{1,2})\s*marks?\s*\)|Total\s+(\d{1,2})(?:\s*marks?)?)$", re.I)
#: A line in the marks column ENDING in a part tally: "(3)", "A1 (4)".
TALLY_END_RE = re.compile(r"(?:^|\s)\((\d{1,2})\)\s*$")
#: Column headers other than Marks that show a page is a scheme table.
OTHER_HEADER_RE = re.compile(r"^(?:scheme|notes|solution)$", re.I)
#: A part tally "(3)" in the marks column.
TALLY_RE = re.compile(r"\((\d{1,2})\)")

#: Questions on a 75-mark IAL paper never exceed this.
MAX_QUESTION = 15

#: A band edge sits this far above the next question's cell.
PAD = 4.0


@dataclass(frozen=True)
class NumberedBlock:
    question: int
    first_page: int
    last_page: int
    top: float | None  # crop on first_page, None = whole page
    bottom: float | None  # crop on last_page, None = whole page
    printed_total: int | None
    verified_by: str  # "printed total"


def _lines(page: fitz.Page) -> list[tuple[str, float, float]]:
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = "".join(s["text"] for s in spans).strip()
            if text:
                out.append((text, line["bbox"][0], line["bbox"][1]))
    return out


def _read(page: fitz.Page, carried_column: float | None = None):
    """
    (question cells (y, n), totals (y, marks), part tallies (y, n), has header,
    column x).

    A page with no header row of its own still has its cells read, at the
    column found on the last page that did have one (`carried_column`) --
    but only cells that name a part ("9. (i)", "9(a)"); a bare number on such
    a page is never trusted. P1 2021 Jan prints its header at the foot of one
    page and question 9's table on the next; reading header pages only, q8's
    block swallowed q9.
    """
    lines = _lines(page)
    width = page.rect.width
    header = [(x, y) for t, x, y in lines if QNUM_HEADER_RE.match(t) and x < 120]
    # Only the header ROW counts: a bare "Q" is also a point label in the
    # working ("Q: 5g - T = 5a"), and taken as a header it dropped the floor
    # below the page's real cells (M1 2022 June q8, 2024 October q5).
    if header:
        top = min(y for _, y in header)
        header = [(x, y) for x, y in header if y <= top + 30.0]
    # The marks column, from this page's own header. A landscape M1 scheme
    # (2019 June) has its marks column at 53% of the width with a Notes column
    # beyond it, so a fixed fraction of the width misses every tally.
    marks_x = [x for t, x, _ in lines if MARKS_HEADER_RE.match(t) and x > width * 0.4]
    other_heads = any(OTHER_HEADER_RE.match(t) and x > 60 for t, x, _ in lines)
    has_marks = bool(marks_x) or other_heads
    column_floor = (min(marks_x) - 45.0) if marks_x else width * 0.45
    # ...and its right edge: a Notes column beyond it holds numbers from the
    # examiners' notes ("50", "55" on M1 2024 October), which are not tallies.
    notes_x = [x for t, x, _ in lines if NOTES_HEADER_RE.match(t) and marks_x and x > min(marks_x)]
    merged = any(MARKS_HEADER_RE.match(t) and "note" in t.lower() for t, _, _ in lines)
    if notes_x:
        column_ceiling = min(notes_x) - 3.0
    elif merged and marks_x:
        column_ceiling = min(marks_x) + 32.0
    else:
        column_ceiling = width
    totals = [(y, int(m.group(1) or m.group(2))) for t, x, y in lines
              if x > width * 0.45 and (m := TOTAL_RE.match(t))]
    # Part tallies end a line in the marks column: "(3)", "A1 (4)". The 2019
    # January M1 schemes print the question's total as a BARE number at the
    # foot of that column ("10"; "16" = 11 + 1 + 4), counted as a candidate
    # only -- it is accepted later solely when it equals the parts' sum or is
    # the block's only value.
    tallies = []
    codes = []  # (y, marks) from M1/A1/B1 codes in the marks column
    footer = page.rect.height - 70.0  # page number and our own stamp
    for t, x, y in lines:
        if x < column_floor or x >= column_ceiling or y > footer:
            continue
        worth = sum(int(d) for _, d in CODE_RE.findall(t))
        if worth:
            codes.append((y, worth))
        end = TALLY_END_RE.search(t)
        if end:
            tallies.append((y, int(end.group(1))))
        elif marks_x and BARE_RE.match(t):
            tallies.append((y, int(t.strip().rstrip("."))))
    has_header = bool(header) and has_marks
    if has_header:
        column = min(x for x, _ in header)
        floor = max(y for _, y in header) + HEADER_CLEARANCE
    elif carried_column is not None:
        column, floor = carried_column, 0.0
    else:
        return [], totals, tallies, False, None, codes
    # Formula fragments in the notes are bare numbers in the same column ("9",
    # "5" under a power or a coefficient). A real cell either names a part --
    # "8 (a)", "4(a)", "1a", "2." -- or is a bare number sitting FIRST under
    # the header. Measured on P1 2021 Jan and 2023 May-Jun, where a bare "9"
    # and "5" otherwise started the wrong blocks.
    in_column = sorted((y, text) for text, x, y in lines
                       if abs(x - column) <= COLUMN_TOLERANCE and y > floor)
    cells = []
    for position, (y, text) in enumerate(in_column):
        match = CELL_RE.match(text)
        if not match or not 1 <= int(match.group(1)) <= MAX_QUESTION:
            continue
        bare = BARE_RE.match(text) is not None
        if bare and not (has_header and position == 0 and y - floor <= BARE_MAX_DROP):
            continue
        cells.append((y, int(match.group(1))))
    return sorted(cells), totals, tallies, has_header, column, codes


def _increasing_starts(cells: list[tuple[int, float, int]]) -> list[tuple[int, float, int]]:
    """
    First appearance of each question number, keeping the longest strictly
    increasing run in document order. A part label like "1b" repeats its
    number and is skipped as a repeat; a stray numeral that breaks the
    sequence falls out of the run.
    """
    firsts: list[tuple[int, float, int]] = []
    seen: set[int] = set()
    for page, y, n in cells:
        if n not in seen:
            firsts.append((page, y, n))
            seen.add(n)
    # Longest strictly increasing subsequence on n (document order kept).
    best: list[list[tuple[int, float, int]]] = []
    for item in firsts:
        candidates = [run for run in best if run[-1][2] < item[2]]
        longest = max(candidates, key=len, default=[])
        best.append(longest + [item])
    return max(best, key=len, default=[])


def question_starts(ms_path: Path, expected: dict[int, int]) -> dict[int, tuple[int, float]]:
    """
    question -> (page, y) of its printed cell, for every question whose cell
    sits in the increasing run. Used to trim a block found by another route
    (lib/ial_ms_parse attaches whole pages) where the next question starts on
    a page the block shares.
    """
    cells = _collect(ms_path)[0]
    return {n: (page, y) for page, y, n in _increasing_starts(cells) if n in expected}


def _collect(ms_path: Path):
    cells: list[tuple[int, float, int]] = []
    totals: list[tuple[int, float, int]] = []
    tallies: list[tuple[int, float, int]] = []
    codes: list[tuple[int, float, int]] = []
    heights: list[float] = []
    with fitz.open(ms_path) as doc:
        started = False
        column: float | None = None
        for index, page in enumerate(doc):
            heights.append(page.rect.height)
            page_cells, page_totals, page_tallies, is_table, page_column, page_codes = _read(
                page, column if started else None)
            started = started or is_table
            if is_table:
                column = page_column
            if not started:
                continue
            cells += [(index, y, n) for y, n in page_cells]
            totals += [(index, y, m) for y, m in page_totals]
            tallies += [(index, y, m) for y, m in page_tallies]
            codes += [(index, y, m) for y, m in page_codes]
    return cells, totals, tallies, heights, codes


def extract_numbered_blocks(ms_path: Path, expected: dict[int, int]) -> dict[int, NumberedBlock]:
    """Blocks verified by their printed total; see the module docstring."""
    cells, totals, tallies, heights, codes = _collect(ms_path)
    starts = [s for s in _increasing_starts(cells) if s[2] in expected]
    out: dict[int, NumberedBlock] = {}
    for position, (page, y, n) in enumerate(starts):
        following = starts[position + 1] if position + 1 < len(starts) else None
        # If question n+1's cell was not found its scheme would be folded into
        # this block; only the FIRST total -- n's -- is read, so that cannot
        # verify a wrong block, but the block can run long. Such a block is
        # rejected unless n is the last question found.
        if following is not None and following[2] != n + 1:
            continue
        # Nothing after it was found, yet it is not the paper's last question:
        # its end is unknown, and running to the end of the scheme would carry
        # every later question (P1 2019 Jun q9 and Oct q10 did exactly that).
        if following is None and n != max(expected):
            continue
        end_page = following[0] if following else len(heights) - 1
        end_y = following[1] if following else None

        def within(p, ty):
            return (p, ty) > (page, y) and (end_y is None or (p, ty) < (end_page, end_y))

        inside = [m for p, ty, m in totals if within(p, ty)]
        if inside:
            # Alternative methods repeat the SAME total; a different value is
            # a neighbour's, so the block has run past its own question.
            if len(set(inside)) > 1:
                continue
            found, how = inside[0], "printed total"
        else:
            # M1's layout: part tallies (3) (1), then the question's total (4),
            # which is their sum. A tally equal to the sum of the tallies before
            # it is the printed total; a single tally is its own total.
            parts = [m for p, ty, m in tallies if within(p, ty)]
            # Every point where a value equals the sum of ALL values before it
            # is a printed total of what came before. Taking the first such
            # point was wrong: tallies (3) (3) (6) would read the second (3) as
            # the total. Among the printed totals, the question's is the one
            # equal to the QP's marks -- a value the scheme itself printed AND
            # summed, so this is not the QP's number read back.
            how = "summed part tallies"
            sums, running = [], 0
            for value in parts:
                if running and value == running:
                    sums.append(value)
                running += value
            if expected[n] in sums:
                found = expected[n]
            elif len(parts) == 1:
                found = parts[0]
            else:
                found = None
        if found != expected[n]:
            # Bounded by the scheme's own labels: it opens on n, the next
            # label is n+1 (or n is the paper's last question), and its codes
            # are worth AT LEAST the marks -- alternative methods only add
            # codes, a block missing part of its scheme would fall short.
            bounded = following is not None or n == max(expected)
            worth = sum(m for p, ty, m in codes if within(p, ty))
            if not (bounded and worth >= expected[n]):
                continue
            found, how = None, "bounded by printed numbers"

        # Whole pages unless the next question starts low on the end page.
        top = max(0.0, y - 18.0) if y > 140 else None
        if following is not None and end_y is not None and end_y <= 140:
            last_page, bottom = end_page - 1, None
        elif following is not None:
            last_page, bottom = end_page, end_y - PAD
        else:
            last_page, bottom = end_page, None
        if last_page < page:
            continue
        out[n] = NumberedBlock(n, page, last_page, top, bottom, found, how)
    return out
