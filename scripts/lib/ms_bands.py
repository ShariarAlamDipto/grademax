"""
Vertical bands for mark-scheme segments.

THE DEFECT THIS EXISTS TO FIX
-----------------------------
Every workbook segmenter cropped the question paper exactly and then emitted the
mark scheme as WHOLE PAGES. That was a deliberate choice at the time, recorded in
build_mathsb_workbook_segments.locate_ms_blocks: the mark scheme pages mix
portrait and landscape, some print their table cells as rotated text, and the
judgement was that their coordinates could not be trusted.

The cost of that choice turned out to be much higher than the note assumed. An
Edexcel Maths B Paper 1 mark scheme fits three questions on a page, so `q1.pdf`
opened on question 1's scheme followed by questions 2 and 3:

    data/workbook/mathsb/2016_jan_1/markschemes/q1.pdf
        Question Working Answer Mark Notes
        1   ...            Total 2 marks     <- the answer
        2   ...            Total 2 marks     <- someone else's
        3   ...            Total 2 marks     <- someone else's

In a printed workbook that is not a small imprecision: the student turns to the
answer for question 1 and is shown three, with nothing marking which is which.

WHY THE COORDINATES ARE ACTUALLY FINE
-------------------------------------
The original note conflated two different things. Reading the page *structurally*
-- "the row below this one", "the cell to the right" -- really is unreliable when
cells are rotated. But that is not what is needed here. A band needs one number:
the coordinate at which a block ends. Both mark scheme layouts state it in their
own text.

    Format A (boxed)      Each question closes with its own tally, "Total 2
                          marks". Block N runs from the tally that closed N-1
                          up to N's own tally. Both ends are read off the page.

    Format B (continuous) One table runs the length of the document with the
                          question number in the leftmost column. Block N runs
                          from N's own numbered row up to N+1's.

Neither needs to know what a cell is. What the original note was right about is
that a *guessed* coordinate is worse than a whole page. Nothing here is guessed:
every band edge is the bounding box of text matched by a regex, and a page whose
layout is not understood is handed back unbanded rather than cut on a guess.

THE ROTATED PAGES ARE REAL, AND THEY ARE NOT A y PROBLEM
--------------------------------------------------------
Some mark schemes -- 2020 Jan Paper 1 and 1R in Maths B -- set /Rotate 90 AND
write their text bottom-to-top, so PyMuPDF reports a writing direction of
(0, -1). On those pages every tally on the page shares one y range and the
blocks are separated along x instead:

    Total 1 marks   bbox x 131.4-144.7   y 72.1-143.8
    Total 2 marks   bbox x 174.3-187.6   y 72.1-143.8   <- same y, next x

Read as y bands these pages collapse: every band starts after its own tally, so
15 of 27 questions came out with no mark scheme inside them at all. So a band
carries the axis it was measured on, and a page is cut across whichever axis its
text actually runs down. Layouts other than these two (text written top-to-bottom
or right-to-left) are not guessed at -- `page_axis` returns None and the caller
keeps the whole page.

The tally scan works on the word stream rather than on assembled lines, because
"Total 6 marks" is sometimes broken across two lines by the typesetter. Measured
across the 82 Maths B mark schemes, the word-level scan agrees with a
whole-page regex count on every single paper; a line-level scan silently lost a
tally on 2016 Jan Paper 1 and swallowed question 26 into question 25's band.

WHAT THIS MODULE DOES NOT DO
----------------------------
It does not decide WHICH block belongs to which question -- that stays with the
caller, which has the question paper's fences and can align them. This module is
handed an anchor per question and turns it into a band. Keeping the two apart
means the alignment safeguards each segmenter already has are untouched.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

import fitz

# "Total 2 marks" -- the per-question tally that closes a boxed block.
TALLY_RE = re.compile(r"Total\s+(\d{1,3})\s+marks?", re.I)

# Blocks run down the page (normal text) or across it (text written
# bottom-to-top on a rotated page).
AXIS_Y = "y"
AXIS_X = "x"

# Keep the tally line itself inside the block it closes, and keep the question
# number from being clipped by a rounding error.
PAD_BEFORE = 6.0
PAD_AFTER = 8.0

# A band starts fractionally past the previous block's tally. The next block's
# table header sits ~28pt further on, so this never clips it.
GAP_AFTER_TALLY = 1.0

# Bands thinner than this are a bad coordinate rather than a real block, and the
# page is handed back whole instead.
MIN_BAND_EXTENT = 24.0


@dataclass(frozen=True)
class Tally:
    """One "Total N marks" line: the marks it states, and where it sits."""

    page: int
    marks: int
    lo: float  # low edge along the page's block axis
    hi: float  # high edge along the page's block axis
    axis: str


@dataclass(frozen=True)
class NumberedRow:
    """One question-number row of a continuous mark scheme table."""

    page: int
    question: int
    marks: int | None
    lo: float
    axis: str


@dataclass(frozen=True)
class Band:
    """
    A slice of a mark scheme, possibly spanning pages.

    `start_at` of None means the start of `start_page`; `end_at` of None means
    the end of `end_page`. Both are measured along `axis`.
    """

    start_page: int
    start_at: float | None
    end_page: int
    end_at: float | None
    axis: str

    @property
    def page_span(self) -> int:
        return self.end_page - self.start_page + 1


# ─────────────────────────────────────────────────────────────────────────────
# Which way does this page run?
# ─────────────────────────────────────────────────────────────────────────────


def page_axis(page: fitz.Page) -> str | None:
    """
    The axis this page's blocks run down, or None if the layout is not one we
    have established how to read.

    Decided from the dominant writing direction of the page's text lines, which
    PyMuPDF reports as a unit vector. Only the two directions actually present
    in the archive are accepted; returning None for anything else is what keeps
    a page from being cut on a guess.
    """
    directions: Counter[tuple[int, int]] = Counter()

    try:
        blocks = page.get_text("dict")["blocks"]
    except Exception:  # noqa: BLE001 - a damaged page must not stop the run
        return None

    for block in blocks:
        for line in block.get("lines", []):
            if not "".join(s["text"] for s in line.get("spans", [])).strip():
                continue
            directions[tuple(round(v) for v in line["dir"])] += 1

    if not directions:
        return None

    dominant = directions.most_common(1)[0][0]
    if dominant == (1, 0):
        return AXIS_Y
    if dominant == (0, -1):
        return AXIS_X
    return None


def _extent(bbox: Sequence[float], axis: str) -> tuple[float, float]:
    """The bbox's low and high edge along `axis`. bbox is (x0, y0, x1, y1)."""
    return (bbox[1], bbox[3]) if axis == AXIS_Y else (bbox[0], bbox[2])


def _page_extent(page: fitz.Page, axis: str) -> float:
    return page.rect.y1 if axis == AXIS_Y else page.rect.x1


def _cross_offset(bbox: Sequence[float], axis: str, page: fitz.Page) -> float:
    """
    How far this line sits from the margin the table's question numbers occupy,
    measured across the blocks' own axis.

    The margin is not simply "low coordinate". On an ordinary page the columns
    run left to right and the number column is at low x, so the offset is x0.
    On a page whose text is written bottom-to-top the columns run the other way:
    the Further Pure specimen mark schemes put Notes at y=98 and Question far
    down the page, because reading across the table means DECREASING y. Treating
    low y as the margin there found the Notes column and no headers at all,
    which cost those two papers their mark schemes entirely.
    """
    if axis == AXIS_Y:
        return bbox[0] - page.rect.x0
    return page.rect.y1 - bbox[3]


# ─────────────────────────────────────────────────────────────────────────────
# Reading the delimiters off the page
# ─────────────────────────────────────────────────────────────────────────────


def find_tallies(ms_path: Path) -> list[Tally]:
    """
    Every per-question tally in block order, with its extent along its page's
    axis.

    Scans the word stream rather than assembled lines. PyMuPDF returns words as
    (x0, y0, x1, y1, word, block, line, word_no) in reading order, so a tally
    broken across two lines is still three consecutive words and is still found.

    Pages whose axis is not understood contribute nothing, so a mark scheme that
    mixes a readable table with an unreadable one still yields the readable part
    and the caller's alignment decides whether that is enough.
    """
    found: list[Tally] = []

    with fitz.open(ms_path) as doc:
        for index, page in enumerate(doc):
            axis = page_axis(page)
            if axis is None:
                continue

            words = page.get_text("words")
            for position, word in enumerate(words):
                if word[4].lower().rstrip(":.") != "total":
                    continue
                window = words[position : position + 3]
                match = TALLY_RE.match(" ".join(item[4] for item in window))
                if match is None:
                    continue
                edges = [_extent(item[:4], axis) for item in window]
                found.append(
                    Tally(
                        page=index,
                        marks=int(match.group(1)),
                        lo=min(edge[0] for edge in edges),
                        hi=max(edge[1] for edge in edges),
                        axis=axis,
                    )
                )

    found.sort(key=lambda tally: (tally.page, tally.lo))
    return found


def find_numbered_rows(
    ms_path: Path,
    *,
    margin_fraction: float = 0.14,
    far_fraction: float = 0.55,
) -> list[NumberedRow]:
    """
    The question-number rows of a continuous mark scheme table, in block order,
    each with the coordinate at which it starts.

    A row is a standalone integer hard against the margin the table's numbers
    sit in; its mark is the standalone integer on the far side of the page at
    the same offset down the table. Both columns are located per page rather
    than hardcoded, because the layout shifts between portrait and landscape.
    """
    rows: list[NumberedRow] = []

    with fitz.open(ms_path) as doc:
        for index, page in enumerate(doc):
            axis = page_axis(page)
            if axis is None:
                continue

            # The columns run across the axis the blocks do NOT run down.
            cross = AXIS_X if axis == AXIS_Y else AXIS_Y
            span = _page_extent(page, cross)
            margin_limit = span * margin_fraction
            far_floor = span * far_fraction

            near: list[tuple[float, int]] = []
            far: list[tuple[float, int]] = []

            try:
                blocks = page.get_text("dict")["blocks"]
            except Exception:  # noqa: BLE001
                continue

            for block in blocks:
                for line in block.get("lines", []):
                    text = "".join(s["text"] for s in line.get("spans", [])).strip()
                    if not re.fullmatch(r"\d{1,2}", text):
                        continue
                    down = _extent(line["bbox"], axis)[0]
                    across = _cross_offset(line["bbox"], axis, page)
                    if across < margin_limit:
                        near.append((down, int(text)))
                    elif across > far_floor:
                        far.append((down, int(text)))

            for down, question in sorted(near):
                mark = next(
                    (value for other, value in sorted(far) if abs(other - down) <= 6),
                    None,
                )
                rows.append(
                    NumberedRow(
                        page=index, question=question, marks=mark, lo=down, axis=axis
                    )
                )

    return rows


@dataclass(frozen=True)
class BlockHeader:
    """
    One "Question number / Scheme / Marks" row: where a block opens, and the
    question number printed under it where there is one.

    `question` is None when the mark scheme opens a block without restating the
    number, which Edexcel does whenever a question runs on past a page break.
    The caller decides what to do about that; this module only reports it.
    """

    page: int
    lo: float
    question: int | None
    axis: str


# The row that opens a block in the Further Pure style of mark scheme, where
# there is no per-question tally to close one.
BLOCK_HEADER_RE = re.compile(r"^Question\b", re.I)

# Words that belong to the header row itself rather than to the block under it.
_HEADER_WORDS = {"number", "scheme", "marks", "question", "working", "answer", "notes"}


def find_block_headers(
    ms_path: Path,
    *,
    margin_fraction: float = 0.28,
    number_reach: float = 90.0,
    number_spread: float = 50.0,
) -> list[BlockHeader]:
    """
    Every block-opening header row, in document order.

    The question number is looked for in the SAME narrow column the header sits
    in, a little way below it. Anchoring on the header's own offset across the
    page is what makes this work: a fixed margin fraction wide enough to catch
    the number column also catches stray glyphs from the working column, and
    those were being read as the block's number.

    A header with no number under it yields `question=None` rather than a guess.
    """
    found: list[BlockHeader] = []

    with fitz.open(ms_path) as doc:
        for index, page in enumerate(doc):
            axis = page_axis(page)
            if axis is None:
                continue
            cross = AXIS_X if axis == AXIS_Y else AXIS_Y
            limit = _page_extent(page, cross) * margin_fraction

            try:
                blocks = page.get_text("dict")["blocks"]
            except Exception:  # noqa: BLE001
                continue

            lines: list[tuple[float, float, str]] = []
            for block in blocks:
                for line in block.get("lines", []):
                    text = "".join(s["text"] for s in line.get("spans", [])).strip()
                    if not text:
                        continue
                    down = _extent(line["bbox"], axis)[0]
                    across = _cross_offset(line["bbox"], axis, page)
                    if across < limit:
                        lines.append((down, across, text))
            lines.sort()

            for position, (down, across, text) in enumerate(lines):
                if not BLOCK_HEADER_RE.match(text):
                    continue
                question: int | None = None
                for other_down, other_across, other in lines[position + 1 :]:
                    if other_down - down > number_reach:
                        break
                    if other.strip().lower() in _HEADER_WORDS:
                        continue
                    if not (
                        across - 12 <= other_across <= across + number_spread
                    ):
                        continue
                    match = re.match(r"^(\d{1,2})\s*[.\(]?", other)
                    if match:
                        question = int(match.group(1))
                    break
                found.append(
                    BlockHeader(page=index, lo=down, question=question, axis=axis)
                )

    return found


# A question label in the number column: "4", "4(a)", "4 (a) (i)", "10  (a)",
# and the 2016-17 style "2." (a decimal like "2.5" still fails the tail).
# A bare digit followed by anything but a part bracket is working, not a label.
_LABEL_RE = re.compile(r"^(\d{1,2})\.?\s*(?:\(|$)")

# The header row's own words, including the truncated forms the typesetter
# leaves when the column is too narrow: "Questio" / "n", "Qu" / "numb".
_LEAD_IN_RE = re.compile(r"^(Qu\w*|Num\w*|num\w*|n)$")

# How far above a label its header row can sit and still be its own.
LEAD_IN_REACH = 45.0

# Where a label may sit relative to the "Question" heading's offset. Measured
# over FPM 2018-2022: labels print 0-26pt inward of the heading's left edge,
# while working in the Scheme column starts ~35pt or more inward.
LABEL_BEFORE_COLUMN = 15.0
LABEL_PAST_COLUMN = 30.0


def find_question_labels(
    ms_path: Path,
    *,
    margin_fraction: float = 0.28,
) -> list[BlockHeader]:
    """
    Every question-number label in the margin column, as a header-like anchor.

    `find_block_headers` needs a line reading "Question". Two things defeat it,
    and each costs a question its mark scheme while silently folding that
    scheme into the question above:

      a truncated header   the column is too narrow and the header prints as
                           "Questio" / "n" or "Qu" / "numb" (FPM 2020 Oct-Nov
                           Papers 1 and 2, 2019 Jan Paper 2);
      no header at all     the next question simply starts partway down the
                           page with "2(a)" in the number column (2018 May-Jun
                           Paper 2, 2019 May-Jun Paper 2).

    In both cases the question number itself is still printed in the number
    column. The anchor's `lo` is pulled back to the header row above the label
    when one sits within LEAD_IN_REACH, so the block keeps its column headings.

    This returns every label, noise included (a bare "2" under "ALT" is a
    label too); the caller must only ever look for a SPECIFIC missing number
    between two known neighbours.
    """
    found: list[BlockHeader] = []
    columns: list[float] = []
    pages: list[tuple[int, str, list[tuple[float, float, float, str]]]] = []

    with fitz.open(ms_path) as doc:
        for index, page in enumerate(doc):
            axis = page_axis(page)
            if axis is None:
                continue
            cross = AXIS_X if axis == AXIS_Y else AXIS_Y
            limit = _page_extent(page, cross) * margin_fraction

            try:
                blocks = page.get_text("dict")["blocks"]
            except Exception:  # noqa: BLE001
                continue

            # (down, down_end, across, text) for every line in the margin.
            lines: list[tuple[float, float, float, str]] = []
            for block in blocks:
                for line in block.get("lines", []):
                    text = "".join(s["text"] for s in line.get("spans", [])).strip()
                    across = _cross_offset(line["bbox"], axis, page)
                    if text and across < limit:
                        lo, hi = _extent(line["bbox"], axis)
                        lines.append((lo, hi, across, text))
            lines.sort()
            columns.extend(a for _, _, a, t in lines if t.startswith("Qu"))
            pages.append((index, axis, lines))

    # The number column sits under the "Question" heading. A digit elsewhere in
    # the margin band -- the superscript in "9² + 8²" -- is working, and taking
    # it for question 2 cut question 1's block down to nothing (2018 May-Jun P2).
    column = sorted(columns)[len(columns) // 2] if columns else None

    for index, axis, lines in pages:
        for down, down_end, across, text in lines:
            match = _LABEL_RE.match(text)
            if match is None:
                continue
            if column is not None and not (
                column - LABEL_BEFORE_COLUMN <= across <= column + LABEL_PAST_COLUMN
            ):
                continue
            # A label opens its row: nothing in the table sits further toward
            # the margin alongside it. Tested at the label's centre, because the
            # header line above ("Number") can overlap a label's box by a point;
            # and only against table text, because on the rotated specimen pages
            # the page footer runs across every row nearer the edge.
            middle = (down + down_end) / 2
            table_edge = -1.0 if column is None else column - LABEL_BEFORE_COLUMN
            if any(
                table_edge <= other_across < across - 1
                and other_lo < middle < other_hi
                for other_lo, other_hi, other_across, _ in lines
            ):
                continue
            lead_in = [
                other_down
                for other_down, _, _, other in lines
                if down - LEAD_IN_REACH <= other_down < down
                and _LEAD_IN_RE.match(other)
            ]
            found.append(
                BlockHeader(
                    page=index,
                    lo=min(lead_in) if lead_in else down,
                    question=int(match.group(1)),
                    axis=axis,
                )
            )

    return found


def position_between(
    anchor: BlockHeader,
    after: tuple[int, float] | None,
    before: tuple[int, float] | None,
) -> bool:
    """Whether `anchor` lies strictly after `after` and before `before`,
    both given as (page, coordinate) and either open-ended when None."""
    here = (anchor.page, anchor.lo)
    if after is not None and here <= after:
        return False
    if before is not None and here >= before:
        return False
    return True


def bands_from_headers(
    headers: Sequence[BlockHeader],
    assignment: dict[int, int],
    *,
    last_page: int,
    runs_to_end: int | None = None,
) -> dict[int, Band]:
    """
    Band each question whose opening header is known.

    `assignment` maps question number -> index into `headers`. A block runs from
    its own header to the header that opens the NEXT ASSIGNED block, which
    differs from a page range in two ways.

    Two blocks sharing a page are separated at the header between them, rather
    than both taking the whole page.

    And a header the caller did not assign to any question does not end a block.
    Edexcel prints a fresh header at the top of the notes page that carries on
    from the scheme above it, without restating the question number, so those
    notes stay with the question they belong to. Treating every header as a new
    block instead made each notes page look like the next question: in 2018 Jan
    Paper 2 question 8's "mark scheme" was really question 7's notes page, and
    the check that should have caught it passed anyway, because it read the
    whole page rather than the block.
    """
    bands: dict[int, Band] = {}
    assigned_indices = sorted(assignment.values())

    for question, index in assignment.items():
        if not 0 <= index < len(headers):
            continue
        header = headers[index]

        next_index = next((i for i in assigned_indices if i > index), None)
        if next_index is None and question != runs_to_end:
            # The last block we could assign, but not the paper's last question
            # -- so blocks for later questions are still down there, unassigned
            # because their number could not be read. Running to the end of the
            # document would swallow every one of them: 2017 May-Jun Paper 2
            # anchored only question 1, whose band then held questions 2, 3 and
            # 6 as well. Stop at the next header of any kind instead, which is
            # the nearest boundary the page itself states.
            next_index = index + 1 if index + 1 < len(headers) else None

        if next_index is not None:
            following = headers[next_index]
            if following.axis != header.axis:
                end_page, end_at = last_page, None
            elif following.page == header.page:
                end_page, end_at = header.page, following.lo - PAD_BEFORE
            else:
                end_page, end_at = following.page, following.lo - PAD_BEFORE
        else:
            end_page, end_at = last_page, None

        bands[question] = Band(
            start_page=header.page,
            start_at=max(0.0, header.lo - PAD_BEFORE),
            end_page=max(header.page, min(end_page, last_page)),
            end_at=end_at,
            axis=header.axis,
        )

    return bands


def band_text(ms_path: Path, band: Band) -> str:
    """
    The text inside `band`, as one normalised string.

    Used to verify a band against something the block states about itself -- a
    mark tally, usually. Reading the band rather than its pages is the whole
    point: on a shared page the page's text includes the neighbour's tally, and
    a check against it would pass for the wrong reason.
    """
    pieces: list[str] = []

    with fitz.open(ms_path) as doc:
        for page_index in range(band.start_page, min(band.end_page, doc.page_count - 1) + 1):
            page = doc[page_index]
            lo = band.start_at if page_index == band.start_page else None
            hi = band.end_at if page_index == band.end_page else None

            try:
                blocks = page.get_text("dict")["blocks"]
            except Exception:  # noqa: BLE001
                continue

            for block in blocks:
                for line in block.get("lines", []):
                    down = _extent(line["bbox"], band.axis)[0]
                    if lo is not None and down < lo:
                        continue
                    if hi is not None and down >= hi:
                        continue
                    pieces.append("".join(s["text"] for s in line.get("spans", [])))

    return re.sub(r"\s+", " ", " ".join(pieces))


# ─────────────────────────────────────────────────────────────────────────────
# Turning anchors into bands
# ─────────────────────────────────────────────────────────────────────────────


def _own_header_within(
    headers: Sequence[BlockHeader],
    question: int,
    start_page: int,
    start_at: float | None,
    tally: Tally,
) -> BlockHeader | None:
    """
    The FIRST header naming `question` that lies between a band's provisional
    start and the tally that closes it, or None if there is none.

    First, not last. The header being skipped past belongs to the PREVIOUS
    question -- its Guidance table, printed after its own tally -- and so
    carries the previous question's number, not this one's. Taking the last
    matching header instead would also skip past this question's own
    continuation headers, which restate its number partway through a long
    scheme, and would then cut off the beginning of its answer.
    """
    for header in headers:
        if header.question != question or header.axis != tally.axis:
            continue
        if header.page < start_page or header.page > tally.page:
            continue
        if header.page == start_page and start_at is not None and header.lo < start_at:
            continue
        if header.page == tally.page and header.lo >= tally.lo:
            continue
        return header

    return None


def bands_from_tallies(
    tallies: Sequence[Tally],
    assignment: dict[int, int],
    headers: Sequence[BlockHeader] | None = None,
) -> dict[int, Band]:
    """
    Band each question whose closing tally is known.

    `assignment` maps question number -> index into `tallies`.

    A block ends at its own tally and starts just past the tally that closed the
    previous block -- the one immediately before it in the document, not the one
    belonging to the previous *matched* question. Using the document neighbour
    is what keeps an unmatched question's scheme from being silently folded into
    a neighbour's band without anything noticing: the band grows, and
    `verify_band` then reports two tallies inside one band.

    The first tally in the document has no predecessor, so its block starts at
    the start of its own page. It deliberately does not reach back into earlier
    pages, which hold the general marking guidance rather than any question.

    Where `headers` is given, the start is then moved FORWARD to the header row
    that names this question, if one falls inside the band. A tally does not
    always close a question outright: several Further Pure mark schemes print
    the scheme, then its tally, then a separate Guidance table for the same
    question. The next question's band would otherwise open on its neighbour's
    guidance -- which is how 2021 May-Jun Paper 2 q5 came out holding the tail
    of question 4, while still passing a one-tally check.

    Only a header carrying this question's own number is used. Snapping to the
    last header of any kind would be wrong: a long question's scheme has
    continuation headers inside it, and starting at one would cut off the
    beginning of the question's own answer.

    A block whose two ends were measured on pages with different axes is not
    emitted: the two coordinates are not comparable, and a band built from them
    would be nonsense. The caller keeps the whole page for those.
    """
    bands: dict[int, Band] = {}

    for question, index in assignment.items():
        if not 0 <= index < len(tallies):
            continue
        tally = tallies[index]

        if index == 0:
            start_page, start_at = tally.page, None
        else:
            previous = tallies[index - 1]
            if previous.axis != tally.axis:
                continue
            start_page, start_at = previous.page, previous.hi + GAP_AFTER_TALLY

        if headers:
            opening = _own_header_within(
                headers, question, start_page, start_at, tally
            )
            if opening is not None:
                start_page, start_at = opening.page, max(0.0, opening.lo - PAD_BEFORE)

        bands[question] = Band(
            start_page=start_page,
            start_at=start_at,
            end_page=tally.page,
            end_at=tally.hi + PAD_AFTER,
            axis=tally.axis,
        )

    return bands


def bands_from_rows(
    rows: Sequence[NumberedRow],
    assignment: dict[int, int],
    *,
    last_page: int,
) -> dict[int, Band]:
    """
    Band each question whose opening row is known.

    `assignment` maps question number -> index into `rows`.

    A block starts at its own numbered row and ends just before the next block's
    row. The last block runs to the end of the document -- a continuous table
    has no closing delimiter of its own, so there is nothing else to stop at.
    """
    bands: dict[int, Band] = {}
    ordered = sorted(assignment.items(), key=lambda item: item[1])

    for position, (question, index) in enumerate(ordered):
        if not 0 <= index < len(rows):
            continue
        row = rows[index]
        end_page, end_at = last_page, None

        if position + 1 < len(ordered):
            following = rows[ordered[position + 1][1]]
            if following.axis != row.axis:
                continue
            if following.page == row.page:
                end_page, end_at = row.page, following.lo - PAD_BEFORE
            else:
                # The next block opens on a later page, so this one runs to the
                # end of the page before it -- not to the next block's own
                # coordinate, which is measured on a different page.
                end_page, end_at = following.page - 1, None
                if end_page < row.page:
                    end_page, end_at = row.page, None

        bands[question] = Band(
            start_page=row.page,
            start_at=max(0.0, row.lo - PAD_BEFORE),
            end_page=max(row.page, end_page),
            end_at=end_at,
            axis=row.axis,
        )

    return bands


def band_to_regions(
    band: Band,
    make_region: Callable[..., object],
    page_extents: Sequence[float],
) -> tuple[object, ...]:
    """
    Expand a band into one region per page, for the caller's own Region type.

    `make_region` is called with page=, top=, bottom= for a band that runs down
    the page and page=, left=, right= for one that runs across it, which is the
    signature every segmenter's Region dataclass has. A page the band owns
    outright is emitted uncropped so it is copied rather than redrawn, which
    preserves it exactly.

    `page_extents` is each page's size along the band's own axis. A slice
    thinner than MIN_BAND_EXTENT is a bad coordinate rather than a real block,
    so that page is dropped -- unless dropping it would leave nothing, in which
    case the whole page is emitted and the caller's audit can judge it.
    """
    regions: list[object] = []
    across = band.axis == AXIS_X

    for page in range(band.start_page, band.end_page + 1):
        start = band.start_at if page == band.start_page else None
        end = band.end_at if page == band.end_page else None

        if start is None and end is None:
            regions.append(make_region(page=page))
            continue

        extent = page_extents[page] if page < len(page_extents) else 0.0
        low = 0.0 if start is None else start
        high = extent if end is None else end
        if high - low < MIN_BAND_EXTENT:
            continue

        if across:
            regions.append(make_region(page=page, left=start, right=end))
        else:
            regions.append(make_region(page=page, top=start, bottom=end))

    if not regions:
        regions.append(make_region(page=band.start_page))

    return tuple(regions)


def page_extents_of(ms_path: Path, axis: str) -> list[float]:
    """Each page's size along `axis`."""
    with fitz.open(ms_path) as doc:
        return [_page_extent(page, axis) for page in doc]


# ─────────────────────────────────────────────────────────────────────────────
# Reading a band back
# ─────────────────────────────────────────────────────────────────────────────


def band_until(
    opening: BlockHeader,
    following: Band | None,
    *,
    last_page: int,
) -> Band:
    """
    A band from `opening` up to where the `following` band begins, or to the end
    of the document when there is no following band. Used to fill a question
    the primary method could not band, between two neighbours it could.
    """
    start_at = max(0.0, opening.lo - PAD_BEFORE)
    if following is None or following.axis != opening.axis:
        return Band(opening.page, start_at, last_page, None, opening.axis)
    if following.start_at is None:
        end_page, end_at = following.start_page - 1, None
    else:
        end_page, end_at = following.start_page, following.start_at
    if end_page < opening.page:
        end_page, end_at = opening.page, None
    return Band(opening.page, start_at, end_page, end_at, opening.axis)


def verify_band(source: Path | Sequence[Tally], band: Band) -> list[int]:
    """
    The marks stated by every tally that falls inside `band`, in order.

    This is the check that makes banding worth doing: a correct block closes
    with exactly one tally. Two means the band swallowed a neighbour, zero means
    it missed its own. The caller compares the single value against the question
    paper's fence marks.

    Takes either a mark scheme path or an already-read tally list. Pass the list
    when checking a whole paper: re-reading a 24-page mark scheme once per
    question turns a paper-wide check into a minute of work.
    """
    tallies = find_tallies(source) if isinstance(source, Path) else source
    inside: list[int] = []

    for tally in tallies:
        if tally.page < band.start_page or tally.page > band.end_page:
            continue
        if tally.axis != band.axis:
            continue
        if (
            tally.page == band.start_page
            and band.start_at is not None
            and tally.hi <= band.start_at
        ):
            continue
        if (
            tally.page == band.end_page
            and band.end_at is not None
            and tally.lo >= band.end_at
        ):
            continue
        inside.append(tally.marks)

    return inside
