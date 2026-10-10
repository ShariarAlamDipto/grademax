"""
Recover the Maths B mark schemes the segmenter could not read.

103 of 742 verified questions reached the printed book with no mark scheme, and
the reason recorded at segmentation time -- "the tables are image-only, it needs
OCR" -- is wrong. Opening the sources shows ordinary PDF pages carrying a
perfectly legible `Question | Scheme | Mark | Notes` table, 700 to 1,000
characters of text a page, and the question number printed in the leftmost
column of every row.

What defeated the segmenter is that this is a THIRD layout. It knows Format A
(each question boxed, closing with `Total N marks`) and Format B (one continuous
table with a per-question mark in the far-right column). These papers have
neither: no per-question tally to align on, and no mark column to confirm
against. Both readers came away with nothing, and a paper that produced no
blocks at all was recorded as needing OCR rather than as unparsed.

THE MAPPING THIS USES INSTEAD
-----------------------------
Nothing is inferred from marks. Every table page names the questions it holds,
in its own Question column, so the page is read for its numbers and a question
is given the pages that carry it:

    p5  -> 1        p9  -> 20, 21, 22
    p6  -> 9,10,11  p10 -> 23
    p7  -> 13, 14   p11 -> 25
    p8  -> 17, 18   p12 -> 26

A question that runs past the foot of a page prints its number once, at the top
of its row, so it is given every page up to the one that opens a LATER question.

The column is located per page from the header word "Question" rather than from
a fixed x, because the tables are not laid out identically across sessions. On
the papers measured, the column sits at x=78-87 and no scheme content starts
before x=139, so the separation is wide.

WHAT IS EMITTED
---------------
A BAND, not a page. This script used to attach a shared page to every question
on it, on the grounds that the Paper 1 mark schemes already made that trade --
and they did, which is exactly what turned out to be wrong with them. A table
page here holds up to four questions, so `q20.pdf` opened on question 20's row
and carried 21 and 22 underneath it with nothing marking where one ended.

The rows already state their own boundaries: each question's band runs from its
own numbered row to the next question's. Both ends are read off the page, and a
band is cut with `show_pdf_page`, whose clip is in the same coordinate space
`get_text` reports. Nothing is rendered to an image; the result stays sharp and
selectable, and the audit can read it back.

Pages whose text is not written left-to-right are left whole rather than cut on
a coordinate that means something else there -- see scripts/lib/ms_bands.py.

SAFETY
------
Existing mark scheme segments are NEVER touched -- only the gaps are filled, so
this can be re-run and cannot damage a paper the segmenter did read. A paper
whose numbers do not come out in non-decreasing order is rejected whole and
reported, rather than half-written.

USAGE
-----
    python scripts/recover_mathsb_markscheme_pages.py            # dry run
    python scripts/recover_mathsb_markscheme_pages.py --execute
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import fitz

from lib import ms_bands

REPO_ROOT = Path(__file__).resolve().parent.parent
SEGMENT_DIR = REPO_ROOT / "data" / "workbook" / "mathsb"
SOURCE_DIR = REPO_ROOT / "data" / "Ultimate Final IGCSE" / "Mathematics_B"

SESSION_FOLDER = {"jan": "Jan", "may-jun": "May-Jun", "oct-nov": "Oct-Nov"}

# A table page names its columns in a header row, but not in one wording. Three
# appear across 2016-2022, and a paper may use more than one:
#     Question | Scheme  | Mark   | Notes
#     Question | Working | Answer | Mark  | Notes
#     Question | Working | Answer | Mark  | Notes | Total
# So the header is recognised by "Question" plus ANY of the others, never by a
# fixed row of words.
HEADER_ANCHOR = "Question"
HEADER_COMPANIONS = ("Scheme", "Working", "Answer")
# The window around the measured column. Row numbers are left-aligned but their
# indent varies by a few points down a page; the nearest scheme content is 45pt
# further right, so this is wide enough to catch the column and nowhere near
# wide enough to reach the next one.
COLUMN_LEFT_SLACK = 12.0
COLUMN_RIGHT_SLACK = 22.0
# The row number, with the part letter some layouts print beside it: a page
# opening "1(a) (i) 6.3" is question 1's, and matching bare digits alone missed
# every such page and mistook it for a continuation.
QUESTION_NUMBER_RE = re.compile(r"^(\d{1,2})\s*(?:\([a-z]\))?$", re.IGNORECASE)
# How far the question count may jump in one step. A paper that prints no
# scheme for one question still advances by two; anything larger is a stray
# numeral, not a row number.
ALLOWED_GAP = 1

# Guidance pages at the front of every mark scheme carry no table.
MAX_QUESTION_NUMBER = 40


def paper_source(paper_key: str) -> Path | None:
    """`2018_jan_1R` -> the archive's mark scheme PDF for that paper."""
    year, season, paper = paper_key.split("_")
    folder = SESSION_FOLDER.get(season)
    if folder is None:
        return None
    path = (SOURCE_DIR / year / folder
            / f"Mathematics_B_{year}_{folder}_Paper_{paper}_MS.pdf")
    return path if path.is_file() else None


def _has_header(words) -> bool:
    """Whether this page opens a mark scheme table."""
    text = " ".join(word[4] for word in words[:14])
    return HEADER_ANCHOR in text and any(t in text for t in HEADER_COMPANIONS)


def _candidates(words):
    """(value, x, y) for every word that could be a row number."""
    out = []
    for word in words:
        match = QUESTION_NUMBER_RE.fullmatch(word[4].strip())
        if match is None:
            continue
        value = int(match.group(1))
        if 1 <= value <= MAX_QUESTION_NUMBER:
            out.append((value, word[0], word[1]))
    return out


def _number_column(doc: fitz.Document, start: int) -> tuple[float, float] | None:
    """
    Where the row numbers actually sit, measured rather than taken from the header.

    Two things defeat reading the column off the header word "Question":

      * it is not always aligned with the numbers beneath it. In 2019 January
        Paper 2 the numbers sit ONE POINT to its left, so a window anchored on
        the header missed every one of them and the whole paper read as
        continuation pages.
      * a window wide enough to be safe about that is wide enough to reach into
        the Scheme column. In 2020 October/November Paper 1 that swept up
        numerals out of the working -- "30", "1", "2" -- and the page then
        claimed to open questions it does not hold.

    So the column is found from the numbers themselves: the leftmost x that
    recurs often enough to be a column rather than a coincidence. Measured, the
    real numbers cluster within about 9 points of each other while the nearest
    scheme content is 45 or more away, so the window is comfortably inside the
    gap.
    """
    counts: Counter[int] = Counter()
    for index in range(start, doc.page_count):
        for _, x, _y in _candidates(doc[index].get_text("words")):
            counts[round(x)] += 1
    if not counts:
        return None
    floor = max(3, max(counts.values()) // 4)
    columns = [x for x, n in counts.items() if n >= floor]
    if not columns:
        return None
    base = float(min(columns))
    return base - COLUMN_LEFT_SLACK, base + COLUMN_RIGHT_SLACK


def _numbers_in_column(words, column: tuple[float, float]) -> list[tuple[int, float]]:
    """(value, y) for the row numbers on this page, in reading order down it."""
    low, high = column
    seen: set[int] = set()
    rows: list[tuple[int, float]] = []
    for value, x, y in sorted(_candidates(words), key=lambda c: c[2]):
        if low <= x <= high and value not in seen:
            seen.add(value)
            rows.append((value, y))
    return rows


def table_pages(doc: fitz.Document) -> list[tuple[int, list[tuple[int, float]]]]:
    """
    Every page that carries a mark scheme table, with the questions it opens.

    The column is fixed by the FIRST header seen and then reused, because some
    papers print the header once and let the table run over the following pages
    without repeating it. Those pages carry row numbers in the same column and
    would otherwise read as empty continuations, stranding every question on
    them. Scanning starts at the first header page, which is what excludes the
    four or five pages of marking guidance at the front.

    Returns (page index, [(question number, y it opens at), ...]) in page
    order. The y is what lets each question be cut to its own band instead of
    taking the whole page.
    """
    start = None
    for index in range(doc.page_count):
        if _has_header(doc[index].get_text("words")):
            start = index
            break
    if start is None:
        return []

    column = _number_column(doc, start)
    if column is None:
        return []

    # A mark scheme runs 1..N in order, so the true row numbers are an
    # INCREASING run down the document and a stray numeral is whatever will not
    # fit in one. Taking the longest increasing subsequence settles that without
    # a rule about how far the count may step: a fixed "may advance by one"
    # filter looked reasonable and threw away nine of 2018 January Paper 1R's
    # questions, because a page legitimately opens at 9 when the previous one
    # ended at 8 and the next jumps to 13.
    ordered: list[tuple[int, int, float]] = []   # (page index, value, y)
    for index in range(start, doc.page_count):
        for value, y in _numbers_in_column(doc[index].get_text("words"), column):
            ordered.append((index, value, y))

    keep = _longest_increasing(ordered)
    found: list[tuple[int, list[tuple[int, float]]]] = []
    for index in range(start, doc.page_count):
        found.append(
            (index, [(value, y) for page, value, y in keep if page == index])
        )
    # Trim trailing pages that carry no table at all.
    while found and not found[-1][1]:
        found.pop()
    return found


def _longest_increasing(
    rows: list[tuple[int, int, float]]
) -> list[tuple[int, int, float]]:
    """
    The longest strictly increasing run of values, in document order.

    Quadratic, which is irrelevant here -- a mark scheme offers a few hundred
    candidates at most -- and far easier to be sure of than the patience-sorting
    version.
    """
    if not rows:
        return []
    best = [1] * len(rows)
    prev = [-1] * len(rows)
    for i in range(len(rows)):
        for j in range(i):
            if rows[j][1] < rows[i][1] and best[j] + 1 > best[i]:
                best[i] = best[j] + 1
                prev[i] = j
    end = max(range(len(rows)), key=lambda i: best[i])
    chain: list[tuple[int, int, float]] = []
    while end != -1:
        chain.append(rows[end])
        end = prev[end]
    return chain[::-1]


def _row_rules(page: fitz.Page) -> list[float]:
    """
    The y of every horizontal rule long enough to be a table row boundary.

    The rule is the row's TRUE edge, and it does not coincide with the row
    number's bounding box: on 2018 Jan Paper 1R page 8 the rule sits at y=251.5
    while question 21's "21" reports a box from 250.2, because the box carries
    the line's leading above the glyph. Cutting on the box therefore leaves a
    sliver of the answer above -- question 21 opened on the descenders of
    "4.5 (metres)". Cutting on the rule does not, and still keeps the row
    number whole, since its glyphs are drawn below the rule.
    """
    found: list[float] = []
    try:
        drawings = page.get_drawings()
    except Exception:  # noqa: BLE001 - a damaged page must not stop the run
        return found

    for drawing in drawings:
        for item in drawing["items"]:
            if item[0] == "l":
                start, end = item[1], item[2]
                if abs(start.y - end.y) < 0.6 and abs(end.x - start.x) > 100:
                    found.append(start.y)
            elif item[0] == "re":
                rect = item[1]
                if rect.height < 0.8 and rect.width > 100:
                    found.append(rect.y0)
    return sorted(found)


def _snap_to_rule(rules: list[float], y: float, reach: float = 6.0) -> float:
    """`y` moved to the nearest row rule within `reach`, or left where it is."""
    nearest = min(rules, key=lambda r: abs(r - y), default=None)
    if nearest is None or abs(nearest - y) > reach:
        return y
    return nearest


def bands_for(
    pages: list[tuple[int, list[tuple[int, float]]]], doc: fitz.Document
) -> dict[int, ms_bands.Band]:
    """
    Which slice of the mark scheme carries each question.

    A question's band opens at its own numbered row and closes just above the
    next question's, wherever that falls -- the next row down the same page, or
    the first row of a later page, in which case everything between belongs to
    this question. That is the continuation case the page-based version handled
    by giving a question every following page that opened nothing new; reading
    the rows directly says the same thing without needing the special case.

    The last question runs to the end of the last table page, because no later
    row bounds it.

    A page whose text is not written left-to-right is not banded: the column
    measurement above works in x, which means something else there. Such a paper
    returns nothing and keeps its whole pages.
    """
    # The rows of this layout sit directly under one another with no rule
    # between them, so a generous pad above a row reaches into the answer above
    # it -- question 21 opened on "4.5 (metres)", the tail of question 20. The
    # row number's own glyphs start at the row top, so two points is enough to
    # survive rounding without borrowing a line.
    row_pad = 2.0

    rows: list[tuple[int, int, float]] = []
    for index, numbers in pages:
        for value, y in numbers:
            rows.append((index, value, y))
    if not rows:
        return {}

    last_table_page = max(index for index, _ in pages)
    for index, _ in pages:
        if ms_bands.page_axis(doc[index]) != ms_bands.AXIS_Y:
            return {}

    rules = {index: _row_rules(doc[index]) for index, _ in pages}

    bands: dict[int, ms_bands.Band] = {}
    for position, (index, value, y) in enumerate(rows):
        if position + 1 < len(rows):
            next_index, _, next_y = rows[position + 1]
            end_page = next_index
            end_at = _snap_to_rule(rules.get(next_index, []), next_y) - row_pad
        else:
            end_page, end_at = last_table_page, None

        bands[value] = ms_bands.Band(
            start_page=index,
            start_at=max(0.0, _snap_to_rule(rules.get(index, []), y) - row_pad),
            end_page=max(index, end_page),
            end_at=end_at,
            axis=ms_bands.AXIS_Y,
        )
    return bands


def write_band(doc: fitz.Document, band: ms_bands.Band, target: Path) -> None:
    """Write `band` of `doc` to `target`, cropping only the pages it shares."""
    target.parent.mkdir(parents=True, exist_ok=True)
    extents = [page.rect.y1 for page in doc]
    regions = ms_bands.band_to_regions(band, _Region, extents)

    out = fitz.open()
    try:
        for region in regions:
            if region.top is None and region.bottom is None:
                out.insert_pdf(doc, from_page=region.page, to_page=region.page)
                continue
            rect = doc[region.page].rect
            top = rect.y0 if region.top is None else max(rect.y0, region.top)
            bottom = rect.y1 if region.bottom is None else min(rect.y1, region.bottom)
            if bottom - top < 20:
                out.insert_pdf(doc, from_page=region.page, to_page=region.page)
                continue
            clip = fitz.Rect(rect.x0, top, rect.x1, bottom)
            page = out.new_page(width=clip.width, height=clip.height)
            page.show_pdf_page(
                fitz.Rect(0, 0, clip.width, clip.height), doc, region.page, clip=clip
            )
        out.save(target)
    finally:
        out.close()


@dataclass(frozen=True)
class _Region:
    """The shape band_to_regions builds; only the vertical edges are used here."""

    page: int
    top: float | None = None
    bottom: float | None = None
    left: float | None = None
    right: float | None = None


def missing_questions(paper_dir: Path) -> list[int]:
    """Questions in this paper with a segment but no mark scheme."""
    questions = {int(path.stem[1:]) for path in (paper_dir / "questions").glob("q*.pdf")
                 if path.stem[1:].isdigit()}
    schemes = {int(path.stem[1:]) for path in (paper_dir / "markschemes").glob("q*.pdf")
               if path.stem[1:].isdigit()}
    return sorted(questions - schemes)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="write the segments")
    args = parser.parse_args()

    print(f"{'=' * 74}\nMATHS B — RECOVER UNREAD MARK SCHEMES  "
          f"[{'EXECUTE' if args.execute else 'DRY RUN'}]\n{'=' * 74}")

    total_missing = total_written = 0
    rejected: list[str] = []
    unmatched: list[str] = []

    for paper_dir in sorted(SEGMENT_DIR.iterdir()):
        if not paper_dir.is_dir() or paper_dir.name == "print":
            continue
        gaps = missing_questions(paper_dir)
        if not gaps:
            continue
        total_missing += len(gaps)

        source = paper_source(paper_dir.name)
        if source is None:
            rejected.append(f"{paper_dir.name}: no source mark scheme in the archive")
            continue

        with fitz.open(source) as doc:
            pages = table_pages(doc)
            if not pages:
                rejected.append(f"{paper_dir.name}: no mark scheme table found "
                                f"in {source.name}")
                continue

            # Continuation pages carry no number of their own and are skipped
            # here; the order check is about the pages that DO open a question.
            opening = [numbers[0][0] for _, numbers in pages if numbers]
            if opening != sorted(opening):
                rejected.append(f"{paper_dir.name}: question numbers out of order "
                                f"across pages ({opening}); not trusted")
                continue

            mapping = bands_for(pages, doc)
            if not mapping:
                rejected.append(
                    f"{paper_dir.name}: mark scheme pages are not written "
                    f"left-to-right, so the row column cannot be measured"
                )
                continue

            written = 0
            absent: list[int] = []
            for number in gaps:
                band = mapping.get(number)
                if band is None:
                    absent.append(number)
                    continue
                if args.execute:
                    write_band(
                        doc, band, paper_dir / "markschemes" / f"q{number}.pdf"
                    )
                written += 1
            total_written += written

            note = f"{written}/{len(gaps)} recovered"
            if absent:
                note += f", not on any page: {absent}"
                unmatched.append(f"{paper_dir.name}: {absent}")
            print(f"  {paper_dir.name:<22} {len(pages):>2} table pages   {note}")

    print(f"\n  {total_written} of {total_missing} missing mark schemes recovered")
    if rejected:
        print(f"\n  {len(rejected)} paper(s) rejected:")
        for line in rejected:
            print(f"    {line}")
    if unmatched:
        print(f"\n  questions whose number appears on no table page:")
        for line in unmatched:
            print(f"    {line}")
    if not args.execute:
        print("\n  Dry run — nothing written. Re-run with --execute.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
