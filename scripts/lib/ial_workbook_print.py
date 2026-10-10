"""
Print-ready IAL chapterwise workbooks (P1, P2, S1, M1): one question book and
one mark scheme book per unit, like the FPM / Maths B / Physics books.

Generalised from build_physics_workbook_print.py; each unit has a thin entry
script (build_<unit>_workbook_print.py) that calls `configure()` then `main()`.

What carries over unchanged: one continuous book with real page numbers,
questions renumbered 1..N within each section, the paper's own pages kept 1:1
(the paged edition), the mark scheme book laid out FIRST so every question
prints its answer's page ("mark scheme p. 214"), and every answer in the mark
scheme book labelled with its section, number and source paper.

WHAT IS PARTICULAR TO IAL: ANSWER SPACE
---------------------------------------
Edexcel IAL papers follow a question with several ruled answer sides. The rule
(user, 2026-10-06): the question's own page(s), ONE answer page, and a further
page only when the question itself continues onto it. So a question keeps:

  * every page carrying question content (text or a figure);
  * plus exactly one answer page -- the page bearing the "(Total ...)" line if
    that page is otherwise blank (so the question's total still prints),
    otherwise the first blank page after the question's content.

Source labels read "January 2019 Q7": an IAL paper key is "2019_jan".
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import fitz

from lib.formula_render import render as render_formulas
from lib.ial_formula_booklet import formula_pages
from lib.workbook_ink import Band, content_layout, paper_box, question_number_box
from lib.workbook_layout import (
    INK, MARGIN, MUTED, NO_SPACE, PAGE_HEIGHT, PAGE_WIDTH, RULE,
    BandedSpacePolicy, Flow, number_patch,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
# Set per unit by configure().
SEGMENT_DIR = REPO_ROOT / "data" / "workbook" / "UNSET"
BOOK_SOURCE = REPO_ROOT / "data" / "workbook" / "UNSET_book.json"
TOKEN = "UNSET"
reference_blocks = None  # the unit's notes module flow_blocks
BOOK_DIR = SEGMENT_DIR / "print"
TOTAL_LINE_RE = re.compile(r"\(\s*Total\s+(?:for\s+Question\s+\d+\s+(?:is|=)\s+)?\d+\s+marks?\s*\)", re.I)

# Working space for the TRIMMED edition, banded by mark tariff. Physics runs
# 3-18 marks (median 9), and the board's own ruled answer lines are stripped
# by the trim as furniture, so a band has to hold several lines of written
# explanation, not a line of algebra.
SPACE_POLICIES: dict[str, BandedSpacePolicy] = {
    "compact": BandedSpacePolicy(
        "compact", ((4, 110.0), (7, 170.0), (10, 230.0), (13, 300.0)), 380.0),
    "standard": BandedSpacePolicy(
        "standard", ((4, 150.0), (7, 230.0), (10, 320.0), (13, 410.0)), 520.0),
    "generous": BandedSpacePolicy(
        "generous", ((4, 200.0), (7, 300.0), (10, 420.0), (13, 540.0)), 680.0),
}
DEFAULT_SPACE = "standard"

# Height of the label strip above each answer in the mark scheme book.
TAG_STRIP = 18.0

# How far in from a band's edge the hanging indent reaches.
NUMBER_ZONE = 30.0

# The paged edition's split. Higher than FPM's 5 because the tariffs are
# smaller: at 5 the split would be 68/32 and two thirds of the book would be
# one-sheet questions carrying 2 marks.
PAGE_BREAK_MARKS = 10
# Report any question squeezed below this to fit its allocation.
SHRINK_WARN = 0.92

# The strip at the foot of a full exam page carrying the board's page number,
# item barcode and subject code. Only ever painted over a WHOLE page -- on a
# cropped band this band of the sheet is blank paper, and on the segment itself
# it would be the middle of the question.
FOOTER_BAND = 54.0

# Object deduplication at save time. FPM saves with garbage=3 and is fine; on
# the Maths B mark scheme book that setting is catastrophic, because the one
# scanned paper contributes tens of thousands of image objects and the pass is
# super-linear in their number. Measured on the finished 584-page book:
#
#     garbage=0, no deflate       3.2s   158 MB
#     garbage=0, deflate         31.2s   159 MB
#     garbage=1, deflate         30.9s   159 MB
#     garbage=2, deflate         28.4s   159 MB
#     garbage=3, deflate       8008.0s   155 MB      <- two hours and thirteen
#                                                       minutes, to save 2%
#
# It is not a hang and it does finish, which is what made it hard to read: two
# builds were killed believing it wedged. Deflate is kept even though it does
# nothing for this book (the content is already-compressed scan imagery, and it
# comes out a megabyte LARGER) because it does compress the question book's text
# and vector drawing, and one setting for both books is worth a megabyte.
GARBAGE_LEVEL = 0

# A page holding at least this many embedded images is a scan stored glyph by
# glyph, and rasterising it to find its content costs minutes. See
# trimmed_layout. A normal page in this corpus carries fewer than ten.
IMAGE_DENSE_PAGE = 300

# Below this a segment page is a y-cropped band out of a shared page rather
# than a sheet of its own. The shortest whole page in the corpus is 842pt and
# the tallest crop 775pt.
FULL_SHEET_MIN_HEIGHT = 800.0

# Where to look for a question number on a page with no text layer: the hanging
# indent of the first line. On a whole sheet that is below the page header; on a
# crop the question opens at the top of the band.
NUMBER_PROBE_TOP = 46.0
NUMBER_PROBE_BOTTOM = 96.0
NUMBER_PROBE_LEFT = 34.0
NUMBER_PROBE_RIGHT = 164.0
CROP_PROBE_HEIGHT = 44.0

SUBJECT_CODE = "UNSET"
SUBJECT_TITLE = "Edexcel International Advanced Level"
SUBJECT_NAME = "UNSET"
SUBJECT_SUB = "Chapterwise Practice Workbook"
BRAND = "GradeMax"

# THE TWO-PART SPLIT
# ------------------
# Optional (--part). Cut at chapter 4, so Part One is Forces, Electricity and
# Waves and Part Two is Energy onwards -- about half the questions each, and no
# chapter is broken across volumes.
PART_SPLIT_CHAPTER = 4
PART_LABEL = {1: "Part One", 2: "Part Two"}

SESSION_LABEL = {
    "jan": "January", "may-jun": "May/June",
    "oct-nov": "October/November", "specimen": "Specimen",
}

CHAPTER_GAP = 13.0

# End matter. The diary is what a student fills in each week; the blank sheets
# are for working that outgrew the space beside the question.
DIARY_PAGES = 2
BLANK_PAGES = 10
DIARY_ROWS = 16
DIARY_COLUMNS = ((0.13, "Date"), (0.30, "Chapter / section"),
                 (0.34, "Questions set"), (0.13, "Due"), (0.10, "Done"))

FOOTER_BASELINE = PAGE_HEIGHT - 26.0 + 12.0
CONTENTS_ROW = 20.0
CONTENTS_TOP = 132.0
CONTENTS_BOTTOM = PAGE_HEIGHT - 90.0


def configure(unit: str, code: str, name: str, notes_blocks, split_chapter: int) -> None:
    """Point the module at one unit's segments, book file and notes."""
    global SEGMENT_DIR, BOOK_SOURCE, BOOK_DIR, TOKEN, SUBJECT_CODE, SUBJECT_NAME
    global reference_blocks, PART_SPLIT_CHAPTER
    SEGMENT_DIR = REPO_ROOT / "data" / "workbook" / unit
    BOOK_SOURCE = REPO_ROOT / "data" / "workbook" / f"{unit}_book.json"
    BOOK_DIR = SEGMENT_DIR / "print"
    TOKEN = unit.upper()
    SUBJECT_CODE = code
    SUBJECT_NAME = name
    reference_blocks = notes_blocks
    PART_SPLIT_CHAPTER = split_chapter


def is_whole_sheet(page: fitz.Page) -> bool:
    """True for a page that is an exam sheet, false for a y-cropped band."""
    return page.rect.height >= FULL_SHEET_MIN_HEIGHT


def chapters_in_part(chapters: list[dict], part: int | None) -> list[dict]:
    """The chapters one volume carries. `None` is the undivided book."""
    if part is None:
        return chapters
    if part == 1:
        return [c for c in chapters if c["number"] < PART_SPLIT_CHAPTER]
    return [c for c in chapters if c["number"] >= PART_SPLIT_CHAPTER]


def part_suffix(part: int | None) -> str:
    return "" if part is None else f"_Part{part}"


def formula_sheet(chapters: list[dict]) -> tuple[fitz.Document, list[str]]:
    """
    The Summary and Formulae section: every chapter and every section of it,
    in the book's own order, before the questions.

    Each section gets a short summary of what the topic asks and how the standard
    question is answered, and then its results. A list of formulae alone tells a
    reader what to write down but not when, and the sections where this subject
    loses marks -- reverse percentages, bounds, the ambiguous case, probability
    without replacement -- are the ones where the method is the difficulty.

    Rendered to a temporary PDF by lib.formula_render (matplotlib mathtext) and
    then read back in, because real mathematical typesetting is not something
    PyMuPDF's text drawing can do -- and on this subject that includes the 2x2
    matrices of chapter 5, which are set with \\genfrac.
    """
    titles = {c["number"]: c["title"] for c in chapters}
    target = BOOK_DIR / "_formula_sheet.pdf"
    target.parent.mkdir(parents=True, exist_ok=True)
    overflow = render_formulas(reference_blocks(titles, set(titles)), target,
                               title="Summary and Formulae")
    doc = fitz.open(target)
    sheet = fitz.open()
    sheet.insert_pdf(doc)
    doc.close()
    target.unlink(missing_ok=True)
    return sheet, overflow


def diary_page(doc: fitz.Document, index: int) -> None:
    """A week of homework, for the teacher to set and the student to tick off."""
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((MARGIN, 96), "Homework Record",
                     fontname="hebo", fontsize=19, color=INK)
    page.insert_text((PAGE_WIDTH - MARGIN - 52, 96), f"{index} of {DIARY_PAGES}",
                     fontname="helv", fontsize=9, color=MUTED)
    page.draw_line(fitz.Point(MARGIN, 108), fitz.Point(PAGE_WIDTH - MARGIN, 108),
                   color=RULE, width=0.8)

    width = PAGE_WIDTH - 2 * MARGIN
    top = 132.0
    row = (PAGE_HEIGHT - 90 - top) / DIARY_ROWS

    x = MARGIN
    for fraction, label in DIARY_COLUMNS:
        page.insert_text((x + 4, top - 8), label, fontname="hebo", fontsize=8, color=MUTED)
        x += width * fraction

    page.draw_rect(fitz.Rect(MARGIN, top, PAGE_WIDTH - MARGIN, top + row * DIARY_ROWS),
                   color=RULE, width=0.7)
    for line in range(1, DIARY_ROWS):
        y = top + row * line
        page.draw_line(fitz.Point(MARGIN, y), fitz.Point(PAGE_WIDTH - MARGIN, y),
                       color=RULE, width=0.5)
    x = MARGIN
    for fraction, _ in DIARY_COLUMNS[:-1]:
        x += width * fraction
        page.draw_line(fitz.Point(x, top), fitz.Point(x, top + row * DIARY_ROWS),
                       color=RULE, width=0.5)


def end_matter(doc: fitz.Document) -> None:
    """The diary, then blank sheets to work on."""
    for index in range(1, DIARY_PAGES + 1):
        diary_page(doc, index)
    for index in range(1, BLANK_PAGES + 1):
        page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        page.insert_text((MARGIN, 96), f"Working   ·   {index} of {BLANK_PAGES}",
                         fontname="helv", fontsize=9, color=MUTED)


def load_book(from_year: int = 0) -> tuple[list[dict], dict[str, list[dict]]]:
    """
    Chapters and their questions from the unit's book file (BOOK_SOURCE).

    Rows arrive in print order (section, then the order the assignment step
    chose); `ordinal` is kept so a re-run prints the same book.
    """
    if not BOOK_SOURCE.is_file():
        raise SystemExit(
            f"{BOOK_SOURCE} not found -- run assign_{TOKEN.lower()}_workbook_sections.py first")
    book = json.loads(BOOK_SOURCE.read_text(encoding="utf-8"))

    chapters = [{"id": str(c["number"]), "number": c["number"], "title": c["title"]}
                for c in book["chapters"]]
    sections = {
        f"{s['chapter']}.{s['number']}": {
            "id": f"{s['chapter']}.{s['number']}", "chapter_id": str(s["chapter"]),
            "number": s["number"], "title": s["title"],
        }
        for s in book["sections"]
    }

    by_chapter: dict[str, list[dict]] = defaultdict(list)
    for question in book["questions"]:
        section = sections.get(question["section"])
        if section is None:
            raise SystemExit(f"{question['slug']}: unknown section {question['section']}")
        if from_year and int(question["source_paper_key"].split("_")[0]) < from_year:
            continue
        by_chapter[section["chapter_id"]].append({**question, "_section": section})

    for rows in by_chapter.values():
        rows.sort(key=lambda q: (q["_section"]["number"], q["ordinal"]))
    return chapters, by_chapter


def segment_path(question: dict, kind: str) -> Path:
    folder = "questions" if kind == "qp" else "markschemes"
    return (SEGMENT_DIR / question["source_paper_key"] / folder
            / f"q{question['source_question_number']}.pdf")


def open_segment(path: Path) -> fitz.Document:
    """
    Open a segment WITHOUT holding an operating-system file handle.

    `show_pdf_page` and `insert_pdf` graft the source into the book, and the
    book keeps that graft alive until it is saved -- so closing the source at
    the end of its `with` block does not give the handle back. FPM's 316
    questions stayed under the descriptor limit and never showed this; Maths B
    opens 742 of them in one pass and MuPDF stops with "Too many open files"
    part-way through, which surfaced later and misleadingly as a failure to
    reopen the formula sheet.

    Reading the bytes first closes the handle immediately and leaves the graft
    holding memory instead, which is the resource there is plenty of: the whole
    2016-2022 question corpus is 196 MB.
    """
    return fitz.open(stream=path.read_bytes(), filetype="pdf")


def whole_page_bands(source: fitz.Document) -> list[Band]:
    """Every page entire, for a segment the trim should not be asked to read."""
    return [Band(index, 0.0, source[index].rect.height,
                 source[index].rect.x0, source[index].rect.x1)
            for index in range(source.page_count)]


def trimmed_layout(source: fitz.Document) -> tuple[list[Band], dict]:
    """
    Content bands, unless the segment is one the trim cannot afford to scan.

    ONE paper defeats it: the 2020 October/November Paper 1 mark scheme is an
    image-only scan that stores each glyph as its own embedded image, 2,000 to
    2,800 to a page. The ink trim has no text layer to read, so it falls back to
    rasterising -- and rasterising a page means compositing every one of those
    images. Measured: 310 seconds for a two-page segment against 0.02s for a
    normal one, across 18 segments. It was the whole of a two-hour build.

    A mark scheme is read rather than written on and gets no working space, so
    the trim buys almost nothing on one -- it drops furniture, and a scanned
    page has little. Printing those pages whole costs a little white space and
    saves ninety minutes, so an image-dense page is placed as it is.

    The threshold is nowhere near anything legitimate: a normal segment page in
    this corpus carries fewer than ten images.
    """
    if any(len(source[index].get_images(full=False)) >= IMAGE_DENSE_PAGE
           for index in range(source.page_count)):
        return whole_page_bands(source), {}
    return content_layout(source)


def source_label(question: dict) -> str:
    year, season = question["source_paper_key"].split("_")[:2]
    return (f"{SESSION_LABEL.get(season, season.title())} {year} "
            f"Q{question['source_question_number']}")


def markscheme_ref(question: dict) -> str:
    """The link from a question to its answer, once the mark scheme book exists."""
    page = question.get("_ms_book_page")
    if page:
        return f"   ·   Mark scheme p. {page}"
    # No verified mark scheme block: say exactly where the answer is instead.
    return f"   ·   Mark scheme: {source_label(question)} (grademax.me)"


def fit_size(text: str, font: str, size: float, width: float) -> float:
    """The largest size up to `size` at which `text` fits in `width`."""
    return min(size, size * width / max(fitz.get_text_length(text, fontname=font, fontsize=size), 1.0))


def chapter_divider(doc: fitz.Document, chapter: dict,
                    sections: list[tuple[int, str, int, int]]) -> None:
    """A right-hand opener for each chapter, listing its sections."""
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    y = 190.0
    page.insert_text((MARGIN, y), f"Chapter {chapter['number']}",
                     fontname="helv", fontsize=12, color=MUTED)
    y += 34
    page.insert_text((MARGIN, y), chapter["title"], fontname="hebo",
                     fontsize=fit_size(chapter["title"], "hebo", 25, PAGE_WIDTH - 2 * MARGIN),
                     color=INK)
    y += 18
    page.draw_line(fitz.Point(MARGIN, y), fitz.Point(PAGE_WIDTH - MARGIN, y), color=RULE, width=1)
    y += 32

    for number, title, count, marks in sections:
        page.insert_text((MARGIN, y), f"{chapter['number']}.{number}",
                         fontname="hebo", fontsize=10, color=MUTED)
        page.insert_text((MARGIN + 44, y), title, fontname="helv", fontsize=10.5, color=INK)
        tail = f"{count} questions · {marks} marks"
        width = fitz.get_text_length(tail, fontname="helv", fontsize=9)
        page.insert_text((PAGE_WIDTH - MARGIN - width, y), tail,
                         fontname="helv", fontsize=9, color=MUTED)
        y += 22
        if y > CONTENTS_BOTTOM:
            break


# The board's page furniture, as it appears INSIDE a cropped band: the item
# barcode's printed code, the "Turn over" cue, and the GradeMax stamp added at
# ingest. On a whole sheet all of this lives in the footer strip and is painted
# out; a crop taken to the foot of a page carries it into the middle of the
# book, which packing then puts between two questions.
# "DO NOT WRITE IN THIS AREA" is the margin label down the side strip. It is
# furniture, and it has to be named as such: it is set rotated, so its bounding
# box is hundreds of points tall and reaches BELOW the barcode. Counted as real
# content it drags the last-real-line marker past the furniture and vetoes the
# cut, which left the barcode showing on 60 sheets.
BOARD_FURNITURE = re.compile(
    r"\*P\d{4,6}A\d{3,6}\*|Turn over|\|\s*GradeMax\s*$|DO NOT WRITE IN THIS AREA")
# The board also prints a bare page number beside the barcode. It carries no
# question content, but it is not matched by the pattern above, and counting it
# as real content is what blocked the cut on the first attempt -- the barcode
# then printed between two packed questions.
BARE_NUMBER = re.compile(r"^\d{1,3}$")


def _is_furniture(text: str) -> bool:
    """
    Is this line the board's page furniture rather than the question?

    The last case is the printer's colour registration marks, which sit beside
    the barcode and are set as PRIVATE USE AREA glyphs -- characters with no
    meaning outside the font that drew them. They read as content to every
    pattern above, and being the lowest thing on the page they were what kept
    the barcode on 60 sheets after the obvious cases were handled. A line made
    up entirely of private-use glyphs is never something a student reads.
    """
    if BOARD_FURNITURE.search(text) or BARE_NUMBER.match(text):
        return True
    stripped = text.strip()
    return bool(stripped) and all("" <= ch <= "" for ch in stripped)


def trim_board_furniture(page: fitz.Page, box: fitz.Rect) -> fitz.Rect:
    """
    Shorten a crop so it stops above the board's page furniture.

    The cut is never made on position alone. The last line of REAL content is
    found first, and only furniture BELOW that is cut, so a band whose question
    happens to mention "Turn over" keeps everything the student has to read.
    A band with no text layer is left exactly as it is.
    """
    lines = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = "".join(span["text"] for span in line["spans"]).strip()
            if text:
                lines.append((line["bbox"], text))
    if not lines:
        return box

    real = [bbox for bbox, text in lines if not _is_furniture(text)]
    if not real:
        return box
    real_bottom = max(bbox[3] for bbox in real)

    # Text only. Taking drawings into account as well seems safer and is not:
    # the rule the board draws directly under "(Total for Question N...)" starts
    # a point or two below that text, so it became the cut, which then fell
    # inside the question and the whole trim was abandoned. The barcode needs no
    # help from the drawings anyway -- it is set in a barcode FONT, so its glyph
    # box is 34pt tall and cutting above the printed code removes the bars too.
    cuts = [bbox[1] for bbox, text in lines
            if _is_furniture(text) and bbox[1] >= real_bottom]
    if not cuts:
        return box

    cut = min(cuts) - 2.0
    if cut <= real_bottom or cut >= box.y1 - 4.0:
        return box
    return fitz.Rect(box.x0, box.y0, box.x1, cut)


# How much of a question's own answer box has to survive the squeeze, by mark
# tariff. These are the trimmed edition's measured Maths B allowances (see
# SPACE_POLICY) -- the same numbers, because they were derived from this
# subject's own mark distribution and nothing about that changed.
#
# The smallest gap worth cutting. Below this the saving is not worth a seam.
SQUEEZE_MIN_RUN = 24.0

# OFF. The squeeze works on a single sheet -- an 842pt page with a 592pt empty
# answer box comes down to 380pt with the question, the box borders, the ruled
# answer line and the total band all intact, and the seam is invisible because
# the borders it cuts are vertical.
#
# It is not switched on because on a PACKED sheet it lays the second band over
# the first: two questions both start at the top of the page, headers and side
# strips printed on top of each other. Set by --squeeze so the work is reachable
# while that is chased down; the default build does not use it.
#
# It also earns much less than it looks like it should. Measured over the book:
# 933 -> 921 sheets. The squeeze makes each band shorter but rarely short enough
# for TWO to share a sheet, so the space it reclaims from the middle of a page
# mostly reappears at the bottom of the same page.
SQUEEZE_ENABLED = False
# How far in from the box edge to look when deciding a row is blank. Wide enough
# to miss the side strips and the box's own vertical borders, which run the full
# height of the sheet and would make every row look occupied.
SQUEEZE_INSET = 0.16


def blank_runs(page: fitz.Page, box: fitz.Rect) -> list[tuple[float, float]]:
    """
    The vertical stretches of a sheet with nothing printed across its middle.

    Occupancy is judged only between SQUEEZE_INSET of either edge. The exam
    sheet's box borders and its "do not write in this area" strips run the whole
    height of the page, so measuring edge to edge reports every row as occupied
    and finds nothing.
    """
    left = box.x0 + box.width * SQUEEZE_INSET
    right = box.x1 - box.width * SQUEEZE_INSET
    spans: list[tuple[float, float]] = []

    def note(rect) -> None:
        if rect[2] > left and rect[0] < right:
            spans.append((rect[1], rect[3]))

    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            if "".join(s["text"] for s in line["spans"]).strip():
                note(line["bbox"])

    for drawing in page.get_drawings():
        # A drawing's bounding box is the wrong thing to ask. The answer box on
        # an exam sheet is ONE stroked rectangle running the height of the page,
        # so its bounding box reports every row as occupied and no gap is ever
        # found -- which is exactly what happened on the first attempt.
        #
        # What actually occupies a row is the ink: a stroked rectangle marks its
        # top and bottom edges only. Its VERTICAL edges are ignored altogether,
        # because a vertical line cut across and rejoined is seamless -- that is
        # the property the whole squeeze rests on.
        outline = drawing.get("type") == "s"
        pen = max(1.0, drawing.get("width") or 1.0)
        for item in drawing["items"]:
            shape = item[0]
            if shape == "l":
                (x0, y0), (x1, y1) = item[1], item[2]
                if abs(y1 - y0) <= 2.0:                      # a horizontal rule
                    note((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
            elif shape == "re":
                rect = item[1]
                if outline:
                    note((rect.x0, rect.y0, rect.x1, rect.y0 + pen))
                    note((rect.x0, rect.y1 - pen, rect.x1, rect.y1))
                else:
                    note((rect.x0, rect.y0, rect.x1, rect.y1))
            else:                                            # curves and quads
                note(drawing["rect"])

    for info in page.get_images(full=True):
        for rect in page.get_image_rects(info[0]):
            note(rect)

    spans.sort()
    runs, cursor = [], box.y0
    for start, end in spans:
        if start - cursor >= SQUEEZE_MIN_RUN:
            runs.append((cursor, start))
        cursor = max(cursor, end)
    if box.y1 - cursor >= SQUEEZE_MIN_RUN:
        runs.append((cursor, box.y1))
    return runs


def squeeze(page: fitz.Page, box: fitz.Rect,
            allowance: float) -> list[tuple[float, float]]:
    """
    The slices of a sheet to keep so its blank space comes to `allowance`.

    A whole exam sheet hands a three-mark question 599pt of empty answer box on
    an 842pt page -- 71% of it white, because on the board's own paper that
    question shared the sheet with two others. Placed one to a sheet here, that
    is the emptiness the book was criticised for.

    Rather than crop the sheet (which loses the total band) or scale it (which
    shrinks the type), the blank is taken out of the MIDDLE and the two parts
    are laid back edge to edge. The box's borders and the side strips are
    vertical, so they rejoin without a visible seam, and the question, the ruled
    answer line and the "(Total for Question N)" band all survive.

    Only stretches with nothing printed across them are ever removed, so a
    diagram or a table sitting in the answer area keeps every point of its room.
    """
    runs = [r for r in blank_runs(page, box) if r[0] > box.y0 + 8]
    total = sum(end - start for start, end in runs)
    excess = total - allowance
    if excess <= SQUEEZE_MIN_RUN or not runs:
        return [(box.y0, box.y1)]

    # Take it from the largest gaps first: one big cut is less visible than
    # several small ones, and the largest gap is the answer box itself.
    order = sorted(range(len(runs)), key=lambda i: runs[i][0] - runs[i][1])
    cuts: dict[int, tuple[float, float]] = {}
    for index in order:
        if excess <= 0:
            break
        start, end = runs[index]
        take = min(excess, (end - start) - SQUEEZE_MIN_RUN)
        if take <= 0:
            continue
        cuts[index] = (end - take, end)
        excess -= take

    keep, cursor = [], box.y0
    for index in sorted(cuts):
        cut_start, cut_end = cuts[index]
        if cut_start > cursor:
            keep.append((cursor, cut_start))
        cursor = cut_end
    if cursor < box.y1:
        keep.append((cursor, box.y1))
    return keep


# Packing geometry. The gutter is what separates two questions sharing a sheet;
# the board sets its own questions about this far apart on a shared Paper 1 page,
# so it reads as the original rather than as two things pushed together.
BAND_GUTTER = 18.0
BAND_TOP = 6.0


class SheetPacker:
    """
    Lays source pages onto sheets -- several cropped bands to a sheet.

    WHY PACK AT ALL

    Placing one cropped band per sheet left 40-70% of those sheets empty: a
    3-mark question owning a whole A4 with nothing under it. A band is a slice
    out of a page that PAPER 1 ALREADY SHARED between two or three questions, so
    putting two or three back on one sheet is not a compression of the book --
    it is the layout the board printed, and the band carries its own answer
    space with it.

    WHAT IS NEVER PACKED

    A whole exam sheet always gets a sheet to itself. That is the thing the
    paged edition exists to preserve, and it arrives already full.

    A sheet also never spans two sections. It costs at most one part-used sheet
    per section, and it buys a footer that can name one section honestly, a
    contents entry that lands, and an audit that can check both.

    LANDSCAPE PAGES ARE TURNED, NOT SHRUNK

    Edexcel sets the Maths B mark schemes in LANDSCAPE A4 -- 842x595 -- and 82%
    of the mark scheme pages are that shape. `is_whole_sheet` tests height, so a
    landscape page failed it, was treated as a cropped band, and got fitted to
    the sheet's WIDTH: 842pt of content squeezed into 595, a scale of 0.707,
    sitting at the top of the sheet with 355pt of nothing under it. That was the
    single largest source of empty space in either book -- nearly every page of a
    1200 page volume -- and it made the mark schemes small as well as sparse.

    Turned a quarter turn, a landscape A4 IS a portrait A4. It goes on at 0.936
    (only the book's own footer band is held back), which is 32% larger than it
    was, and the sheet is full. The reader turns the book clockwise, which is
    what the board's own landscape pages ask for when they are printed.
    """

    def __init__(self, doc: fitz.Document, kind: str) -> None:
        self.doc = doc
        self.kind = kind
        self.page: fitz.Page | None = None
        self.cursor = 0.0
        self.numbers: list[int] = []
        # (printed number, mark scheme page) for the questions on this sheet.
        self.links: list[tuple[int, int]] = []
        self.context: tuple[str, str] | None = None

    def flush(self) -> None:
        """Close the open sheet, writing the footer for what ended up on it."""
        if self.page is None:
            return
        label, title = self.context
        if len(self.numbers) > 1:
            tail = f"Questions {self.numbers[0]}-{self.numbers[-1]}"
        else:
            tail = f"Question {self.numbers[0]}" if self.numbers else "Working"
        if self.kind == "qp" and self.links:
            def ref(number, page):
                where = (f"mark scheme p. {page}" if isinstance(page, int)
                         else f"mark scheme: {page} (grademax.me)")
                return where if len(self.links) == 1 else f"Q{number} {where}"
            tail += "   ·   " + ", ".join(ref(n, p) for n, p in self.links)
        footer = (f"{BRAND}   ·   {SUBJECT_NAME}   ·   {label} {title}"
                  f"   ·   {tail}")
        if self.kind == "ms":
            footer += "   ·   Mark scheme"
        # A long section title would push the mark scheme link off the sheet.
        self.page.insert_text((MARGIN, PAGE_HEIGHT - FOOTER_BAND + 22), footer,
                              fontname="helv",
                              fontsize=fit_size(footer, "helv", 7.6, PAGE_WIDTH - 2 * MARGIN),
                              color=MUTED)
        self.page = None
        self.numbers = []
        self.links = []

    def _tag(self, text: str, top: float) -> None:
        """Name one answer on a mark scheme sheet: a sheet can carry two, and
        the page-range footer alone does not say where one stops."""
        self.page.draw_rect(fitz.Rect(MARGIN, top + 2, PAGE_WIDTH - MARGIN, top + 16),
                            color=None, fill=(0.93, 0.95, 0.97))
        self.page.insert_text((MARGIN + 5, top + 12.5), text,
                              fontname="hebo", fontsize=8.5, color=INK)

    def _open(self, context: tuple[str, str]) -> int:
        self.flush()
        self.page = self.doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        self.cursor = BAND_TOP
        self.context = context
        return self.doc.page_count - 1

    def place(self, source: fitz.Document, index: int, context: tuple[str, str],
              printed: int,
              renumber: tuple[fitz.Rect | None, str] | None,
              allowance: float | None = None,
              tag: str | None = None,
              link: int | None = None) -> int:
        """
        Put one source page on a sheet. Returns the sheet's 0-based index.

        With an `allowance`, a whole exam sheet is squeezed to that much blank
        answer space and becomes a band like any other -- which is what lets it
        share a sheet.
        """
        box = paper_box(source[index])
        whole = is_whole_sheet(source[index])
        # A landscape SHEET, not merely a box wider than it is tall: a cropped
        # band is the page's full width and only a few hundred points tall, so
        # "width > height" alone turned short question bands on their side.
        landscape = box.width >= FULL_SHEET_MIN_HEIGHT and box.width > box.height
        limit = PAGE_HEIGHT - FOOTER_BAND
        rotate = 0

        if landscape:
            # A quarter turn clockwise: the source's height becomes the page's
            # width. Held back from the footer band so the book's own footer
            # stays readable the normal way up.
            sheet = self._open(context)
            rotate = 270
            scale = min(PAGE_WIDTH / box.height, limit / box.width)
            width, height = box.height * scale, box.width * scale
            target = fitz.Rect((PAGE_WIDTH - width) / 2, 0,
                               (PAGE_WIDTH + width) / 2, height)
            self.cursor = limit
        elif whole and allowance is None:
            sheet = self._open(context)
            target = fitz.Rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT)
            self.cursor = limit  # nothing else joins a whole sheet
            self.page.show_pdf_page(target, source, index, clip=box)
            # The board's page number, item barcode and subject code all live in
            # this strip; the lowest real question content measured across the
            # corpus ends above it, so the strip is safe to paint over.
            self.page.draw_rect(
                fitz.Rect(0, PAGE_HEIGHT - FOOTER_BAND, PAGE_WIDTH, PAGE_HEIGHT),
                color=None, fill=(1, 1, 1))
        else:
            box = trim_board_furniture(source[index], box)
            slices = (squeeze(source[index], box, allowance)
                      if allowance is not None else [(box.y0, box.y1)])
            # Fit the width, keep the aspect ratio, and stay clear of the footer.
            content = sum(end - start for start, end in slices)
            # An answer's label gets a strip of its own above the band, so it
            # never sits on the scheme's table header.
            strip = TAG_STRIP if tag else 0.0
            scale = min(PAGE_WIDTH / box.width, (limit - strip) / content, 1.0)
            width, height = box.width * scale, content * scale
            if (self.page is None or self.context != context
                    or self.cursor + strip + height > limit):
                sheet = self._open(context)
            else:
                sheet = self.doc.page_count - 1
            if tag:
                self._tag(tag, self.cursor)
                self.cursor += strip
            target = fitz.Rect(0, self.cursor, width, self.cursor + height)

            # The slices go down the sheet edge to edge; the clip keeps each one
            # to its own stretch of the source.
            y = self.cursor
            for start, end in slices:
                tall = (end - start) * scale
                self.page.show_pdf_page(
                    fitz.Rect(0, y, width, y + tall), source, index,
                    clip=fitz.Rect(box.x0, start, box.x1, end))
                y += tall
            self.cursor += height + BAND_GUTTER

        if landscape:
            self.page.show_pdf_page(target, source, index, clip=box, rotate=rotate)

        if printed not in self.numbers:
            self.numbers.append(printed)
            if link:
                self.links.append((printed, link))

        # Whole sheets and turned sheets have no strip to label in; their
        # label goes in the top margin, which the board leaves empty.
        if tag and (whole or landscape) and allowance is None:
            self._tag(tag, 4.0)

        # The number patch maps source coordinates straight onto the sheet, so
        # it has no meaning on a turned page. Question papers are never
        # landscape, so this only ever skips a patch that was never asked for.
        if renumber is not None and renumber[0] is not None and not rotate:
            source_box, label = renumber
            scale = target.width / box.width
            rect = fitz.Rect(target.x0 + (source_box.x0 - box.x0) * scale,
                             target.y0 + (source_box.y0 - box.y0) * scale,
                             target.x0 + (source_box.x1 - box.x0) * scale,
                             target.y0 + (source_box.y1 - box.y0) * scale)
            self.page.draw_rect(number_patch(rect) & self.page.rect,
                                color=None, fill=(1, 1, 1))
            size = max(7.5, min(11.0, rect.height * 0.86))
            self.page.insert_text((rect.x0, rect.y1 - rect.height * 0.12), label,
                                  fontname="hebo", fontsize=size, color=INK)
        return sheet


def pages_to_keep(source: fitz.Document, bands, allowance: int) -> list[int]:
    """
    The question's content pages plus ONE answer page (see the module docstring).

    `allowance` is ignored for IAL; the rule is fixed by the user's instruction.
    A page is content when the ink trim found a band on it. The total line is
    trimmed as furniture, so a page carrying only "(Total ...)" reads as blank
    -- it is the preferred answer page, because keeping it keeps the total.
    """
    content = sorted({band.page for band in bands}) or [0]
    last = max(content)
    blank_after = [i for i in range(last + 1, source.page_count)]
    totals = [i for i in blank_after
              if TOTAL_LINE_RE.search(" ".join(source[i].get_text().split()))]
    answer = totals[:1] or blank_after[:1]
    return sorted(set(content) | set(answer))


def number_box_for(source: fitz.Document, number: int) -> fitz.Rect | None:
    """
    Where the paper printed its question number, text layer or not.

    The ink probe has to be aimed differently at the two kinds of page: on a
    whole sheet the first line sits below the page header, while a cropped band
    opens on the question itself.
    """
    if not source.page_count:
        return None
    page = source[0]
    box = paper_box(page)
    if is_whole_sheet(page):
        probe = Band(0, box.y0 + NUMBER_PROBE_TOP, box.y0 + NUMBER_PROBE_BOTTOM,
                     box.x0 + NUMBER_PROBE_LEFT, box.x0 + NUMBER_PROBE_RIGHT)
    else:
        probe = Band(0, box.y0, min(box.y0 + CROP_PROBE_HEIGHT, box.y1),
                     box.x0, box.x0 + NUMBER_PROBE_RIGHT)
    return question_number_box(source, number, probe)


def build_body_verbatim(chapters: list[dict], by_chapter: dict[str, list[dict]],
                        kind: str, allocate: bool = False,
                        policy: BandedSpacePolicy | None = None,
                        ) -> tuple[fitz.Document, list[dict], list[str]]:
    """
    Assemble the papers chapterwise, page for page, editing nothing out.

    There is no section heading page: adding 49 of them to a book whose premise
    is "nothing added, nothing removed" would be its own kind of edit, so the
    section is named in the footer of every sheet instead, and the contents
    carry the page numbers.
    """
    warnings: list[str] = []
    doc = fitz.open()
    entries: list[dict] = []
    packer = SheetPacker(doc, kind)

    for chapter in chapters:
        questions = by_chapter.get(chapter["id"], [])
        if not questions:
            continue
        packer.flush()

        grouped: dict[int, list[dict]] = defaultdict(list)
        for question in questions:
            grouped[question["_section"]["number"]].append(question)
        summary = [(number, grouped[number][0]["_section"]["title"], len(grouped[number]),
                    sum(q["marks"] for q in grouped[number]))
                   for number in sorted(grouped)]

        chapter_divider(doc, chapter, summary)
        entries.append({"level": "chapter", "number": chapter["number"],
                        "title": chapter["title"], "page": doc.page_count - 1,
                        "count": len(questions),
                        "marks": sum(q["marks"] for q in questions)})

        for number in sorted(grouped):
            rows = grouped[number]
            section = rows[0]["_section"]
            label = f"{chapter['number']}.{number}"
            # A sheet never spans two sections, so the contents entry can be
            # taken before the section's first sheet exists and still land.
            packer.flush()
            entries.append({"level": "section", "number": label,
                            "title": section["title"], "page": doc.page_count,
                            "count": len(rows),
                            "marks": sum(r["marks"] for r in rows)})
            context = (label, section["title"])

            for printed, question in enumerate(rows, 1):
                question["_printed"] = printed
                question["_section_label"] = label
                path = segment_path(question, kind)
                if not path.is_file():
                    if kind == "qp":
                        warnings.append(f"{question['slug']}: missing {path.name}")
                    continue

                try:
                    with open_segment(path) as source:
                        renumber = None
                        if kind == "qp":
                            box = number_box_for(source, question["source_question_number"])
                            renumber = (box, str(printed))

                        indices = list(range(source.page_count))
                        allowance = 0
                        if allocate and kind == "qp":
                            allowance = (1 if question["marks"] < PAGE_BREAK_MARKS else 2)
                            bands, _ = trimmed_layout(source)
                            indices = pages_to_keep(source, bands, allowance)
                            # Not reported when the content runs past the
                            # allowance: Physics questions routinely do (2.2
                            # pages on average), and every content page is
                            # kept by design.

                        # Only the question book is squeezed. A mark scheme has
                        # no answer space to reclaim -- nobody writes on it.
                        allowance = (policy.space_for(question["marks"])
                                     if policy is not None and kind == "qp"
                                     else None)
                        for position, index in enumerate(indices):
                            # Only the first page carries the question number.
                            first = position == 0
                            sheet = packer.place(
                                source, index, context, printed,
                                renumber if first else None,
                                allowance=allowance,
                                tag=(f"{label} Q{printed}  ·  {source_label(question)}"
                                     if first and kind == "ms" else None),
                                link=((question.get("_ms_book_page")
                                       or source_label(question))
                                      if first and kind == "qp" else None))
                            if position == 0:
                                question[f"_page_{kind}"] = sheet
                        # No blank padding. A question whose content fitted its
                        # sheets does not need an empty one appended: the band
                        # already carries the paper's own answer space, and the
                        # end matter has blank working sheets for what outgrows
                        # it. Padding is what produced 11 sheets carrying
                        # nothing but a footer.
                except Exception as error:  # noqa: BLE001
                    warnings.append(f"{question['slug']}: {error}")

    packer.flush()
    return doc, entries, warnings


def build_body(chapters: list[dict], by_chapter: dict[str, list[dict]],
               kind: str, policy: BandedSpacePolicy,
               report=None) -> tuple[fitz.Document, list[dict], list[str]]:
    """
    Lay every chapter into one document.

    Returns the document, a flat list of contents entries carrying the page each
    one starts on (0-based within the body), and any warnings.
    """
    warnings: list[str] = []
    doc = fitz.open()
    entries: list[dict] = []
    space = NO_SPACE if kind == "ms" else policy

    for chapter in chapters:
        questions = by_chapter.get(chapter["id"], [])
        if not questions:
            continue
        started = time.perf_counter()
        pages_before = doc.page_count

        grouped: dict[int, list[dict]] = defaultdict(list)
        for question in questions:
            grouped[question["_section"]["number"]].append(question)
        summary = [(number, grouped[number][0]["_section"]["title"], len(grouped[number]),
                    sum(q["marks"] for q in grouped[number]))
                   for number in sorted(grouped)]

        chapter_divider(doc, chapter, summary)
        entries.append({"level": "chapter", "number": chapter["number"],
                        "title": chapter["title"], "page": doc.page_count - 1,
                        "count": len(questions),
                        "marks": sum(q["marks"] for q in questions)})

        running = (f"{BRAND}  ·  {SUBJECT_NAME}  ·  "
                   f"Chapter {chapter['number']}  {chapter['title']}")
        if kind == "ms":
            running += "  ·  Mark schemes"
        flow = Flow(doc, running, space)

        for number in sorted(grouped):
            rows = grouped[number]
            section = rows[0]["_section"]
            flow.section_break(f"{chapter['number']}.{number}   {section['title']}")
            entries.append({"level": "section",
                            "number": f"{chapter['number']}.{number}",
                            "title": section["title"],
                            "page": doc.page_count - 1,
                            "count": len(rows),
                            "marks": sum(r["marks"] for r in rows)})

            # Numbering restarts at 1 in every section: that is what makes it a
            # chapterwise workbook rather than a reordered past paper.
            for printed, question in enumerate(rows, 1):
                question["_printed"] = printed
                question["_section_label"] = f"{chapter['number']}.{number}"
                path = segment_path(question, kind)
                if not path.is_file():
                    if kind == "qp":
                        warnings.append(f"{question['slug']}: missing {path.name}")
                    continue

                right = f"{question['marks']} marks   ·   {source_label(question)}"
                if kind == "qp":
                    right += markscheme_ref(question)
                try:
                    with open_segment(path) as source:
                        bands, masks = trimmed_layout(source)
                        if not bands:
                            warnings.append(
                                f"{question['slug']}: no content; printing whole pages")
                            bands = whole_page_bands(source)
                        # Replace the paper's number in place when we know
                        # exactly where it is AND it sits in the hanging indent.
                        # A box found further in is not the number, and painting
                        # over it would white out the question; on those, and on
                        # segments whose window already clips the number away,
                        # the book's number goes in the margin instead.
                        renumber = None
                        label = f"{printed}"
                        if kind == "qp":
                            box = question_number_box(
                                source, question["source_question_number"], bands[0])
                            if box is not None and box.x0 <= bands[0].x0 + NUMBER_ZONE:
                                renumber, label = (box, str(printed)), ""
                        flow.add(source, bands, label, right, question["marks"],
                                 False, renumber=renumber, masks=masks)
                        question[f"_page_{kind}"] = flow.last_start_page
                except Exception as error:  # noqa: BLE001
                    warnings.append(f"{question['slug']}: {error}")

        if report:
            report(f"      chapter {chapter['number']:>2} "
                   f"{chapter['title'][:34]:<34} {len(questions):>4} questions  "
                   f"{doc.page_count - pages_before:>4} pages  "
                   f"{time.perf_counter() - started:6.1f}s")

    return doc, entries, warnings


def contents_pages(entries: list[dict], offset: int, kind: str,
                   part: int | None = None) -> fitz.Document:
    """
    The front matter: a title page, then the contents.

    `offset` is how many pages sit in front of the body once this document is
    itself counted -- without it every entry points one contents-length too low.

    `part` names the volume on the title page and under the contents heading. A
    reader has to be able to tell two spiral-bound books apart with the covers
    face down, and the contents of Part 2 listing chapters 6 to 11 with no other
    explanation reads as a book missing its first five chapters.
    """
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    y = 250.0
    page.insert_text((MARGIN, y), BRAND, fontname="hebo", fontsize=13, color=MUTED)
    y += 46
    page.insert_text((MARGIN, y), SUBJECT_TITLE, fontname="helv", fontsize=13, color=MUTED)
    y += 36
    page.insert_text((MARGIN, y), SUBJECT_NAME, fontname="hebo", fontsize=30, color=INK)
    y += 30
    page.insert_text((MARGIN, y), f"({SUBJECT_CODE})", fontname="helv", fontsize=15, color=MUTED)
    y += 26
    page.draw_line(fitz.Point(MARGIN, y), fitz.Point(PAGE_WIDTH - MARGIN, y), color=RULE, width=1.2)
    y += 30
    subtitle = SUBJECT_SUB + ("  ·  Mark Schemes" if kind == "ms" else "")
    page.insert_text((MARGIN, y), subtitle, fontname="helv", fontsize=11.5, color=INK)

    chapters = [e for e in entries if e["level"] == "chapter"]
    span = ""
    if part is not None and chapters:
        first, last = chapters[0]["number"], chapters[-1]["number"]
        span = f"{PART_LABEL[part]}  ·  Chapters {first}–{last}"
        y += 34
        page.insert_text((MARGIN, y), span, fontname="hebo", fontsize=13, color=INK)
        y += 20
        page.insert_text((MARGIN, y),
                         f"Of two volumes. {chapters[0]['title']} to {chapters[-1]['title']}.",
                         fontname="helv", fontsize=10, color=MUTED)

    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((MARGIN, 96), "Contents", fontname="hebo", fontsize=19, color=INK)
    if span:
        width = fitz.get_text_length(span, fontname="helv", fontsize=9.5)
        page.insert_text((PAGE_WIDTH - MARGIN - width, 96), span,
                         fontname="helv", fontsize=9.5, color=MUTED)
    page.draw_line(fitz.Point(MARGIN, 108), fitz.Point(PAGE_WIDTH - MARGIN, 108),
                   color=RULE, width=0.8)
    y = CONTENTS_TOP

    for entry in entries:
        if y > CONTENTS_BOTTOM:
            page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
            y = CONTENTS_TOP

        printed_page = entry["page"] + offset + 1
        if entry["level"] == "chapter":
            y += 8
            page.insert_text((MARGIN, y), f"{entry['number']}",
                             fontname="hebo", fontsize=11.5, color=MUTED)
            page.insert_text((MARGIN + 26, y), entry["title"],
                             fontname="hebo", fontsize=11.5, color=INK)
            font, size = "hebo", 11.5
        else:
            page.insert_text((MARGIN + 26, y), entry["number"],
                             fontname="helv", fontsize=10, color=MUTED)
            page.insert_text((MARGIN + 70, y), entry["title"],
                             fontname="helv", fontsize=10, color=INK)
            font, size = "helv", 10

        label = str(printed_page)
        width = fitz.get_text_length(label, fontname=font, fontsize=size)
        page.insert_text((PAGE_WIDTH - MARGIN - width, y), label,
                         fontname=font, fontsize=size, color=INK)
        y += CONTENTS_ROW

    return doc


def stamp_page_numbers(doc: fitz.Document, kind: str, tail: bool = True) -> None:
    """
    Number every sheet, so the contents can be trusted and a reader can be told
    "turn to page 148" without qualification.
    """
    running = f"{BRAND}  ·  {SUBJECT_NAME}" + ("  ·  Mark Schemes" if kind == "ms" else "")
    for number, page in enumerate(doc, 1):
        label = str(number)
        width = fitz.get_text_length(label, fontname="hebo", fontsize=9)
        page.insert_text(((PAGE_WIDTH - width) / 2, FOOTER_BASELINE), label,
                         fontname="hebo", fontsize=9, color=INK)
        if tail:
            page.insert_text((MARGIN, FOOTER_BASELINE), running,
                             fontname="helv", fontsize=7.4, color=MUTED)


def assemble(chapters, by_chapter, kind: str, edition: str,
             policy: BandedSpacePolicy,
             report=None, part: int | None = None) -> tuple[fitz.Document, int, list[str]]:
    """Returns the finished book, the front-matter length, and any warnings."""
    if edition in ("verbatim", "paged"):
        # The paged edition IS the verbatim edition, rationed. The question
        # paper's own formatting is the point, so nothing is reflowed and no
        # page carrying question content is dropped -- only the trailing blank
        # continuation sheets, until the allowance is met. Mark schemes are read
        # rather than written on and keep every page in both editions.
        # --squeeze additionally takes the blank out of each sheet's answer box
        # down to the policy's allowance. OFF by default: see `squeeze` for what
        # it does and the module docstring for why it is not the default.
        body, entries, warnings = build_body_verbatim(
            chapters, by_chapter, kind, allocate=edition == "paged",
            policy=policy if (edition == "paged" and SQUEEZE_ENABLED) else None)
    else:
        body, entries, warnings = build_body(chapters, by_chapter, kind, policy, report)

    # Only the question book carries the reference matter; a mark scheme needs
    # neither a formula sheet nor somewhere to record homework.
    formulas = None
    if kind == "qp":
        formulas, overflow = formula_sheet(chapters)
        warnings.extend(f"formula sheet: line too wide — {line}" for line in overflow)
        end_matter(body)

    # The contents shift the body, and their own length depends on the entry
    # count -- which is already known, so one pass settles it. Laying them out
    # once with a zero offset just measures how long they are. The formula sheet
    # sits between the two and shifts everything again, so its length is part of
    # the offset the contents are written with.
    # The board's own formula sheet for the unit opens the question book, right
    # after the title page (user, 2026-10-09): the pages the candidate is handed
    # in the exam. It shifts the body like everything else in front of it.
    official = formula_pages(TOKEN) if kind == "qp" else None

    probe = contents_pages(entries, 0, kind, part)
    contents_length = probe.page_count
    probe.close()
    offset = (contents_length + (formulas.page_count if formulas else 0)
              + (official.page_count if official else 0))

    front = contents_pages(entries, offset, kind, part)
    if front.page_count != contents_length:
        raise RuntimeError(
            f"contents length changed between passes ({contents_length} -> "
            f"{front.page_count}); every page reference in the book would be wrong")

    if official:
        front.insert_pdf(official, start_at=1)
        official.close()
    if formulas:
        front.insert_pdf(formulas)
        formulas.close()
    front.insert_pdf(body)
    body.close()
    # The verbatim edition writes its own richer footer on every question page
    # (chapter, section and question number), so a second line here would just
    # double up.
    stamp_page_numbers(front, kind, tail=edition not in ("verbatim", "paged"))
    return front, offset, warnings


def write_index(chapters, by_chapter, offsets: dict[str, int]) -> dict:
    index = {"subject": SUBJECT_CODE, "source": BOOK_SOURCE.name, "questions": []}
    for chapter in chapters:
        for question in by_chapter.get(chapter["id"], []):
            if "_printed" not in question:
                continue
            index["questions"].append({
                "slug": question["slug"],
                "chapter": chapter["number"],
                "chapter_title": chapter["title"],
                "section": question["_section_label"],
                "section_title": question["_section"]["title"],
                "printed_number": question["_printed"],
                "marks": question["marks"],
                "source": source_label(question),
                "workbook_page": question.get("_page_qp", 0) + offsets["qp"] + 1,
                "markscheme_page": (question["_page_ms"] + offsets["ms"] + 1
                                    if "_page_ms" in question else None),
            })
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="write the PDFs")
    parser.add_argument("--from-year", type=int, default=0,
                        help="earliest paper year to include (default 2018)")
    parser.add_argument("--edition", choices=("trimmed", "verbatim", "paged"),
                        default="paged",
                        help="trimmed: question plus fixed working space. "
                             "verbatim: the questions exactly as printed. "
                             "paged: one whole sheet per question under "
                             f"{PAGE_BREAK_MARKS} marks, two at or above")
    parser.add_argument("--squeeze", action="store_true",
                        help="take the blank out of each sheet's answer box "
                             "(experimental; overlaps bands on packed sheets)")
    parser.add_argument("--space", choices=tuple(SPACE_POLICIES), default=DEFAULT_SPACE,
                        help="how much room a question gets to work in "
                             f"(default {DEFAULT_SPACE}; trimmed edition only)")
    parser.add_argument("--part", choices=("all", "1", "2"), default="all",
                        help="build one volume of the two-part print set: "
                             f"1 is chapters 1-{PART_SPLIT_CHAPTER - 1}, 2 is "
                             f"{PART_SPLIT_CHAPTER} onwards (Geometry). Each "
                             "part is a complete book -- its own contents, "
                             "reference section, page numbers and index. "
                             "'all' builds the single undivided volume")
    parser.add_argument("--only", choices=("both", "qp", "ms"), default="both",
                        help="build just one of the two books. The question book "
                             "and the mark scheme book are independent, so a "
                             "problem in one need not cost a rebuild of the other")
    parser.add_argument("--progress", action="store_true",
                        help="report each chapter as it is laid out, and time the "
                             "save separately, so a slow run can be located")
    args = parser.parse_args()
    global SQUEEZE_ENABLED
    SQUEEZE_ENABLED = bool(getattr(args, "squeeze", False))
    policy = SPACE_POLICIES[args.space]
    verbatim = args.edition == "verbatim"
    paged = args.edition == "paged"

    part = None if args.part == "all" else int(args.part)

    chapters, by_chapter = load_book(args.from_year)
    chapters = chapters_in_part(chapters, part)
    total = sum(len(by_chapter.get(c["id"], [])) for c in chapters)

    print(f"{'=' * 74}\n{SUBJECT_NAME.upper()} WORKBOOK — PRINT EDITION  "
          f"[{'EXECUTE' if args.execute else 'DRY RUN'}]\n{'=' * 74}")
    print(f"  edition            : {args.edition}")
    if part is None:
        print("  volume             : one book, chapters 1 onwards")
    else:
        print(f"  volume             : {PART_LABEL[part]} of two — chapters "
              f"{chapters[0]['number']}–{chapters[-1]['number']} "
              f"({chapters[0]['title']} to {chapters[-1]['title']})")
    print(f"  papers             : {args.from_year} onwards")
    print(f"  questions          : {total}  (from {BOOK_SOURCE.name})")
    if verbatim:
        print("  pages              : every source page, at the size it was printed")
        print("  furniture          : board footer strip covered on whole sheets;")
        print("                       cropped bands placed at natural size, untouched")
    elif paged:
        small = sum(1 for c in chapters
                    for q in by_chapter.get(c["id"], []) if q["marks"] < PAGE_BREAK_MARKS)
        print(f"  pages              : 1 sheet under {PAGE_BREAK_MARKS} marks, "
              f"2 sheets at or above")
        print("  answer space       : question pages + one answer page "
              "(IAL rule, user 2026-10-06)")
    else:
        print(f"  working space      : {args.space} — {policy.describe()}")
        allocation = sum(policy.space_for(q["marks"]) for c in chapters
                         for q in by_chapter.get(c["id"], []))
        print(f"  space allocated    : {allocation / 752:.0f} sheets' worth "
              f"of blank working, across {total} questions")
    print("  numbering          : restarts at 1 in every section")
    print("  mark schemes       : separate book; every question prints its "
          "mark scheme page")
    print("  front matter       : official formula sheet (questions), contents, "
          "then a summary for every chapter")
    print(f"  end matter         : {DIARY_PAGES} homework pages, {BLANK_PAGES} blank")

    if total == 0:
        print("\n  Nothing verified to print.")
        return 0
    if not args.execute:
        print("\n  Dry run — nothing written. Re-run with --execute.")
        return 0

    BOOK_DIR.mkdir(parents=True, exist_ok=True)
    offsets: dict[str, int] = {}
    all_warnings: list[str] = []

    report = print if args.progress else None
    suffix = {"verbatim": "_Verbatim", "paged": "_Paged"}.get(args.edition, "")
    suffix += part_suffix(part)
    # Mark schemes FIRST: the question book prints each answer's page number,
    # so those numbers have to exist before it is laid out.
    books = (("ms", f"GradeMax_{TOKEN}_Workbook_MarkSchemes{suffix}.pdf"),
             ("qp", f"GradeMax_{TOKEN}_Workbook{suffix}.pdf"))
    if args.only == "qp":
        raise SystemExit("--only qp would print no mark scheme page numbers; "
                         "build both books")
    for kind, name in books:
        if args.only != "both" and args.only != kind:
            continue
        print(f"\n  {name}")
        doc, offset, warnings = assemble(chapters, by_chapter, kind, args.edition,
                                         policy, report, part)
        all_warnings.extend(warnings)
        target = BOOK_DIR / name
        started = time.perf_counter()
        doc.save(target, deflate=True, garbage=GARBAGE_LEVEL)
        elapsed = time.perf_counter() - started
        offsets[kind] = offset
        if kind == "ms":
            for chapter in chapters:
                for question in by_chapter.get(chapter["id"], []):
                    if "_page_ms" in question:
                        question["_ms_book_page"] = question["_page_ms"] + offset + 1
        print(f"      {doc.page_count} pages ({offset} front matter), "
              f"{target.stat().st_size // 1024} KB, saved in {elapsed:.1f}s")
        doc.close()

    # The index names a page in both books, so it can only be written when both
    # have been laid out. Rebuilding one alone leaves the existing index alone
    # rather than writing one with half its page numbers invented.
    if args.only != "both":
        print(f"\n  --only {args.only}: print_index.json left as it was; "
              f"it needs both books' page numbers.")
        return 0

    index = write_index(chapters, by_chapter, offsets)
    index["edition"] = args.edition
    if part is not None:
        index["part"] = part
        index["chapters"] = [chapters[0]["number"], chapters[-1]["number"]]
    index_path = BOOK_DIR / f"print_index{suffix.lower()}.json"
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"\n  print_index.json   {len(index['questions'])} questions "
          f"(slug -> chapter, section, printed number, both page numbers)")

    if all_warnings:
        print(f"\n  {len(all_warnings)} warning(s):")
        for warning in all_warnings[:12]:
            print(f"    {warning}")
    else:
        print("\n  no warnings — every question placed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
