"""
Mark-scheme parsing for Edexcel **IAL** papers.

Subject-neutral, like `ial_qp_parse`. Each subject keeps its own entry-point
script; this is the shared format layer.

THE RULE THAT GOVERNS THIS MODULE
---------------------------------
**A wrong mark scheme is worse than a missing one.** A student who opens a
blank slot knows to go and find the answer; a student who opens the wrong
question's scheme is actively misled, and nothing in the workbook would flag it.

So every block this module returns has been checked against a number the mark
scheme did not supply: the question's marks, derived independently from the
question paper in `ial_qp_parse`. A block whose marks do not reconcile is
**dropped, not attached**. Coverage below 100% is the expected, correct outcome.

This is deliberately unlike aligning by longest-common-subsequence on the mark
values, which was used for 4MB1: LCS *aligns on* the marks, so agreement is
guaranteed and the check reports nothing.

TWO EXTRACTORS, BECAUSE THERE ARE TWO LAYOUTS
---------------------------------------------
Measured across 39 IAL mark schemes, neither approach covers the archive alone:

* **Ruled** (roughly 2015-2022): the scheme is a real bordered table, and
  PyMuPDF's `find_tables()` reads it cleanly -- question number in column 0,
  the marks column last. On these papers it verifies most papers outright
  (7/7, 6/6, 7/7 ...).
* **Unruled** (roughly 2023-2025, and some older ones): no table borders, so
  `find_tables()` returns nothing at all and every block sums to zero. These
  have to be read geometrically, from the x position of the column.

Running both and keeping whatever reconciles is safe precisely because of the
verification rule above: a block is accepted on the strength of the QP's marks,
never on the strength of which extractor produced it. The two are therefore
complementary rather than competing, and their union is what this module
returns.

WHAT IS NOT A PROBLEM HERE
--------------------------
* **Nothing is rotated.** Every line reports `dir=(1.0, 0.0)`. An earlier guess
  that the number column was rotated or unmapped was wrong; the failures were
  all in the reader's own filters.
* **The numbered guidance pages are the trap.** Every mark scheme opens with
  "1. The total number of marks for the paper is 75", "2. The Edexcel
  Mathematics mark schemes use the following types of mark ...". Those look
  exactly like question cells in the left column, and matching them silently
  anchors question 1 to a page several before the table starts, which wrecks
  every subsequent block. Both extractors therefore refuse to look at a page
  until the table itself has started.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import fitz

# ─────────────────────────────────────────────────────────────────────────────
# Geometry and patterns
# ─────────────────────────────────────────────────────────────────────────────

#: How far from the printed 'Question / Number' header a cell may sit and still
#: be that column. The column is located PER PAGE from the header rather than
#: by a fixed x, because the left margin moves between papers -- measured at
#: x = 26 on WST01 2024 Jan and x = 61 on WMA14 2021 Jan. A fixed threshold
#: either loses one layout's cells or swallows the scheme column's own
#: numerals, which sit at x = 81-98 on the very same pages.
QNUM_COLUMN_TOLERANCE = 25.0

#: Fallback when a page repeats no header: the widest left column seen.
QNUM_MAX_X = 100.0

#: The marks column, as a fraction of page width. Measured at 0.79-0.93.
MARKS_MIN_X_RATIO = 0.78

#: A cell must sit below the header row, but only just: on WST01 2024 Jan the
#: header is at y = 71-84 and question 1's cell at y = 97. An earlier cutoff of
#: 120 discarded every real cell on that paper and kept only scheme numerals
#: from lower down, which is how it scored 0 of 8 on a paper whose blocks are
#: in fact perfectly readable.
HEADER_CLEARANCE = 6.0

#: Our own watermark is a 53x14pt two-cell table on every page. Any real
#: scheme table is orders of magnitude larger.
MIN_TABLE_AREA = 20_000.0

TALLY_RE = re.compile(r"\(\s*(\d{1,2})\s*\)")

#: An individual mark code in the marks column: M1, A1, B2, dM1, A1ft ...
#: The digit is the number of marks that code is worth.
#:
#: This is the SECOND way a mark scheme states its marks, and it is not
#: redundant: the 2023-2025 papers largely stop printing per-part '(n)' tallies
#: and give only the codes, so a reader that sums tallies alone scores zero on
#: them. Summing the codes recovers exactly those papers.
CODE_RE = re.compile(r"\b[dD]?([MAB])(\d)(?!\d)")

#: The two extractors need DIFFERENT cell patterns, and conflating them was
#: worth 16 percentage points.
#:
#: A ruled cell has already been isolated by the table, so whatever follows the
#: number is the rest of that cell -- often every sub-part merged into one
#: string, '1.(a) (b) (c) (d)'. A prefix match is correct and an end-anchor
#: would reject most of them.
QCELL_RULED_RE = re.compile(r"^(\d{1,2})\s*\.?\s*(?:\(\s*[a-z]\s*\)|$|\s)")

#: An unruled "cell" is just a line that happens to sit in the left column, so
#: it must match the WHOLE line. Allowing a trailing space here matched '5
#: marks' and '12 cm' as question starts, fragmenting blocks into pieces that
#: could never reconcile.
QCELL_UNRULED_RE = re.compile(r"^(\d{1,2})\s*\.?\s*(?:\(\s*[a-z]\s*\)\s*)?$")
HEADER_RE = re.compile(r"question", re.I)
MARKS_HEADER_RE = re.compile(r"^marks?$", re.I)
QNUM_HEADER_RE = re.compile(r"^(?:question|number)$", re.I)


@dataclass(frozen=True)
class MarkSchemeBlock:
    question: int
    pages: tuple[int, int]  # inclusive, 0-indexed
    tally_marks: int
    code_marks: int
    extractor: str  # 'ruled' | 'unruled'

    def reconciles(self, expected: int) -> bool:
        """Either statement of the marks agreeing is enough."""
        return expected in (self.tally_marks, self.code_marks)


@dataclass(frozen=True)
class _PageRead:
    """
    One page's contribution to a block.

    Two mark totals, not one. They are alternative statements of the same
    quantity, and a block is accepted if EITHER reconciles with the question
    paper -- which layout a paper uses is not something worth predicting.
    """

    starts: int | None  # question whose block starts on this page
    tally_marks: int  # from per-part '(n)' totals
    code_marks: int  # from individual M1/A1/B1 codes
    is_table: bool


def _lines(page: fitz.Page) -> list[tuple[str, float, float]]:
    out: list[tuple[str, float, float]] = []
    try:
        blocks = page.get_text("dict")["blocks"]
    except Exception:  # noqa: BLE001
        return out
    for block in blocks:
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = "".join(span["text"] for span in spans).strip()
            if not text:
                continue
            out.append(
                (
                    text,
                    min(span["bbox"][0] for span in spans),
                    min(span["bbox"][1] for span in spans),
                )
            )
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Extractor 1: ruled tables
# ─────────────────────────────────────────────────────────────────────────────


def _read_ruled(page: fitz.Page) -> _PageRead:
    try:
        tables = list(page.find_tables())
    except Exception:  # noqa: BLE001
        return _PageRead(None, 0, 0, False)

    best = None
    for table in tables:
        if table.col_count < 3:
            continue
        area = (table.bbox[2] - table.bbox[0]) * (table.bbox[3] - table.bbox[1])
        if area < MIN_TABLE_AREA:
            continue
        if best is None or area > best[0]:
            best = (area, table)
    if best is None:
        return _PageRead(None, 0, 0, False)

    rows = best[1].extract()
    data = [r for r in rows if not (r and r[0] and HEADER_RE.search(r[0] or ""))]

    # NOTE: the unruled reader requires a repeated header before a page may
    # start a question; this one deliberately does NOT. Requiring it here was
    # measured and reverted -- it cost 12 correct WST01 blocks and fixed
    # nothing, because a ruled table's column 0 is already an isolated cell.
    starts = None
    for row in data:
        match = QCELL_RULED_RE.match((row[0] or "").strip())
        if match:
            starts = int(match.group(1))
            break

    tally_marks = 0
    code_marks = 0
    for row in data:
        column = row[-1] or ""
        for value in TALLY_RE.findall(column):
            tally_marks += int(value)
        for _, value in CODE_RE.findall(column):
            code_marks += int(value)

    return _PageRead(starts, tally_marks, code_marks, True)


# ─────────────────────────────────────────────────────────────────────────────
# Extractor 2: unruled pages, read geometrically
# ─────────────────────────────────────────────────────────────────────────────


def _read_unruled(page: fitz.Page) -> _PageRead:
    width = page.rect.width
    lines = _lines(page)

    is_table = any(
        MARKS_HEADER_RE.match(text) and x0 > width * MARKS_MIN_X_RATIO
        for text, x0, _ in lines
    )

    # Locate the question column from the printed header on THIS page.
    header = [
        (x0, y0) for text, x0, y0 in lines
        if QNUM_HEADER_RE.match(text) and x0 < QNUM_MAX_X
    ]
    if header:
        column_x = min(x for x, _ in header)
        header_bottom = max(y for _, y in header)
    else:
        column_x, header_bottom = None, 0.0

    tally_marks = 0
    code_marks = 0
    candidates: list[tuple[float, int]] = []

    for text, x0, y0 in lines:
        if x0 > width * MARKS_MIN_X_RATIO:
            for value in TALLY_RE.findall(text):
                tally_marks += int(value)
            for _, value in CODE_RE.findall(text):
                code_marks += int(value)
            continue

        # A page with no repeated 'Question / Number' header cannot START a
        # question: it is a notes or continuation page. Falling back to a bare
        # x threshold here let formula numerals at x = 43-82 register as
        # question cells, which began two P4 blocks on a notes page whose
        # marks then happened to reconcile -- the one failure mode this
        # module exists to prevent.
        in_column = (
            column_x is not None
            and abs(x0 - column_x) <= QNUM_COLUMN_TOLERANCE
        )
        if in_column and y0 > header_bottom + HEADER_CLEARANCE:
            match = QCELL_UNRULED_RE.match(text)
            if match:
                candidates.append((y0, int(match.group(1))))

    # The page belongs to whichever question appears highest on it.
    starts = min(candidates)[1] if candidates else None

    return _PageRead(starts, tally_marks, code_marks, is_table)


# ─────────────────────────────────────────────────────────────────────────────
# Blocks
# ─────────────────────────────────────────────────────────────────────────────


def _blocks_from(reads: list[_PageRead], label: str) -> dict[int, MarkSchemeBlock]:
    """
    Turn per-page reads into one page range per question.

    Pages before the table starts are ignored outright -- that is what keeps the
    numbered guidance list ("1. The total number of marks ...") from anchoring
    question 1 to a page several before the scheme begins.
    """
    table_pages = [i for i, r in enumerate(reads) if r.is_table]
    if not table_pages:
        return {}
    first = min(table_pages)

    firsts: dict[int, int] = {}
    for index in range(first, len(reads)):
        question = reads[index].starts
        if question is not None:
            firsts.setdefault(question, index)

    ordered = sorted(firsts)
    out: dict[int, MarkSchemeBlock] = {}
    for position, question in enumerate(ordered):
        lo = firsts[question]
        hi = firsts[ordered[position + 1]] - 1 if position + 1 < len(ordered) else len(reads) - 1
        hi = max(lo, hi)
        out[question] = MarkSchemeBlock(
            question,
            (lo, hi),
            sum(reads[i].tally_marks for i in range(lo, hi + 1)),
            sum(reads[i].code_marks for i in range(lo, hi + 1)),
            label,
        )
    return out


def extract_blocks(
    ms_path: Path, expected_marks: dict[int, int]
) -> tuple[dict[int, MarkSchemeBlock], dict[str, int]]:
    """
    Mark-scheme page ranges for the questions whose marks reconcile.

    `expected_marks` maps question number -> marks, and must come from the
    QUESTION paper. It is the whole basis on which a block is trusted; passing
    anything derived from the mark scheme itself would make the check circular
    and worthless.

    Returns the accepted blocks plus a per-extractor tally, so a caller can
    report which layout carried which paper instead of guessing.
    """
    with fitz.open(ms_path) as doc:
        ruled = _blocks_from([_read_ruled(page) for page in doc], "ruled")
        unruled = _blocks_from([_read_unruled(page) for page in doc], "unruled")

    accepted: dict[int, MarkSchemeBlock] = {}
    stats: dict[str, int] = {"ruled": 0, "unruled": 0, "rejected": 0}

    for question, expected in expected_marks.items():
        for candidate in (ruled.get(question), unruled.get(question)):
            if candidate is not None and candidate.reconciles(expected):
                accepted[question] = candidate
                stats[candidate.extractor] += 1
                break
        else:
            stats["rejected"] += 1

    return accepted, stats
