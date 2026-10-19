"""
Separate the printed question from the answer space Edexcel happened to allocate.

WHY
---
A workbook segment is a slice of the original exam paper, so it inherits the
paper's answer space verbatim -- and an exam paper is generous by design, sized
for the worst-case candidate writing large. Measured across the corpus:

    FPM (4PM1)   431 segments, 1308 source pages, 9.4% ink
                 -> 124 A4-pages of question, 1188 A4-pages of white
    Maths B      avg 1.56 pages per question, 17.9% ink

Reprinting that verbatim gives a ~2,800-page FPM book that is mostly blank. The
fix is to stop treating the source page as the unit: find the bands that carry
the actual question, and let the book decide how much room to leave for working.

WHAT COUNTS AS THE QUESTION
---------------------------
Everything except the furniture Edexcel prints around it:

  * the page frame -- a single ~525x758pt rectangle drawn on EVERY page. Left in,
    it makes a blank continuation page look like solid ink from top to bottom.
  * DO NOT WRITE IN THIS AREA sidebars, which alternate left/right by recto/verso
  * the header/footer band: page number, item barcode, "Turn over", GradeMax stamp
  * "Question 7 continued" continuation headers
  * "(Total for Question 7 is 12 marks)" -- the workbook header already prints the
    marks, and this line sits alone at the foot of the last page, dragging a whole
    empty page along with it
  * rows of answer dots

A dotted run is only furniture when it is dots and nothing else. Maths B prints
its answer lines as ".................... cm", where the unit is part of the
question -- so a run carrying any other character is kept.

FIGURES, GRIDS AND GRAPH PAPER SURVIVE AUTOMATICALLY, because they are drawings
and images rather than absences. A question that says "sketch the curve on the
grid below" keeps its grid; only genuinely empty space is reclaimed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import fitz

A4_WIDTH, A4_HEIGHT = 595.0, 842.0

# (y0, y1, x0, x1) of one surviving piece of content, before merging.
Span = tuple[float, float, float, float]

# Header/footer cut lines, calibrated against the real corpus: the highest real
# content sits at y=59.8 and the GradeMax stamp ends at y=27.7; the lowest real
# content ends at y=779 and the page number starts at y=797.9.
HEADER_CUT = 34.0
FOOTER_CUT = 46.0
SIDEBAR_CUT = 32.0
# The sidebar is a 12pt-wide vertical strip. Anything wider sitting in the margin
# is real content, not furniture.
MARGIN_STRIP_WIDTH = 30.0

# Those two cuts are only valid on a whole sheet. Maths B Paper 1 puts two or
# three questions on a page, so its segments are y-crops -- some only 262pt tall,
# where a blind 80pt of header and footer would amputate a third of the question.
# A crop taken from inside the page has no header or footer to remove.
FULL_PAGE_MIN_HEIGHT = 700.0

# The page frame hugs the sheet: it starts above any possible content and ends
# below it. Matching on position rather than on size alone matters, because a
# full-page graph grid is nearly as large -- but a grid always has a question
# line above it, so it never starts this high.
FRAME_TOP = 48.0
FRAME_WIDTH_FRACTION = 0.60
FRAME_HEIGHT_FRACTION = 0.70
# A frame drawn as four lines instead of one rectangle leaves two verticals that
# would otherwise register as content spanning the whole page.
RULE_THICKNESS = 3.5
# How close to the edge of the sheet a tall thin rule must sit to be a frame
# side rather than a mark scheme's table column.
FRAME_EDGE = 45.0
# How far outside the page a shape may stray before it is a printer's mark.
BLEED_TOLERANCE = 0.5

DOTTED_RE = re.compile(r"^[\s.·…_,]{8,}$")
CONTINUED_RE = re.compile(r"^\s*question\s+\d+\s+continued\s*$", re.I)
FENCE_RE = re.compile(r"total\s+for\s+question\s+\d+", re.I)
BARCODE_RE = re.compile(r"^\*[A-Z0-9]{8,}\*$")
STAMP_RE = re.compile(r"grademax", re.I)
PAPER_TOTAL_RE = re.compile(r"total\s+for\s+(paper|section)", re.I)
# The exam board's own footers. The workbook carries GradeMax branding only.
PUBLISHER_RE = re.compile(r"pearson education|©\s*pearson|edexcel limited", re.I)
# The spare grid. A past paper offers a second copy of a graph grid in case the
# candidate spoils the first; the workbook keeps one grid, so the offer and the
# grid it points at both go. Two phrasings, and they differ in WHERE the spare
# sits: "turn over for" puts it on the next page, "only use this grid" directly
# below the sentence.
SPARE_GRID_RE = re.compile(
    r"(spare grid|only use this grid|if you need to redraw your graph)", re.I)
SPARE_GRID_OVERLEAF_RE = re.compile(r"turn over for a spare", re.I)

# Instructions addressed to a candidate sitting the whole paper. "Answer ALL
# TWENTY EIGHT questions" is worse than noise in a chapterwise workbook.
RUBRIC_RE = re.compile(
    r"^(answer all\b.*|write your answers?\b.*spaces?\b.*|"
    r"you must write down all the stages\b.*|turn over\s*)\.?$", re.I)
# The stamp GradeMax adds along the top of every segmented page. Its separator is
# a private-use glyph in some papers and a middot in others, so it is matched by
# what it ends with: the document kind.
SUBJECT_STAMP_RE = re.compile("\\b(19|20)\\d{2}\\b.*\\bPaper\\b.*\\b(QP|MS)\\s*$", re.I)
# Graphics sitting at the same height as a line of furniture belong to it.
FURNITURE_OVERLAP = 4.0
# The stamp is a short line; a long one that happens to fit the shape is prose.
MAX_STAMP_LENGTH = 70
# A publisher footer is a short line, not a paragraph that mentions Pearson.
MAX_PUBLISHER_LENGTH = 120
# A run this long of one non-alphanumeric character is an answer rule.
MIN_RULE_REPEATS = 8
# A question number lives in the hanging indent; this far in, a bare number is
# part of the question rather than its label.
QUESTION_NUMBER_MAX_X = 56.0
# An image covering this much of the sheet, with no surviving text, is a scan.
SCAN_AREA_FRACTION = 0.55
# Shapes on one page, with no text at all, that mean the page is a traced scan.
VECTOR_SCAN_PRIMITIVES = 400
# More text blocks than this and the page has a working text layer, so an
# empty result means the page really is blank. The traced scan carries only
# our own two-line GradeMax stamp.
MAX_SCAN_TEXT_BLOCKS = 6
# Shape of the mark fence on a scanned page: one line tall, set well in.
FENCE_MAX_HEIGHT = 26.0
FENCE_MIN_INDENT = 0.30
# The fence merged with its rule spans most of the sheet.
FENCE_MIN_WIDTH = 0.50
# Clearance above the spare-grid sentence, so the sentence itself is cut too.
SPARE_GRID_PAD = 4.0
# Window searched for a scanned question number, and the blank gap that ends it.
NUMBER_SCAN_WIDTH = 130.0
NUMBER_SCAN_HEIGHT = 34.0
NUMBER_SCAN_DPI = 150
NUMBER_GAP_COLUMNS = 8
# A printed question number is between these widths; narrower is a rule.
MIN_NUMBER_WIDTH = 2.5
MAX_NUMBER_WIDTH = 22.0

# Two bands closer together than this read as one block of content.
MERGE_GAP = 9.0
# Ink thinner than this is a rule, not content -- used on scanned pages, where
# there is no text layer to recognise an answer line by its dots. Measured: a
# scanned answer rule renders about 6pt tall at 60 DPI and repeats on a 28pt
# pitch, while a line of 12pt maths covers 11-13pt.
MIN_BAND_HEIGHT = 8.5
BAND_PAD = 3.0

RASTER_DPI = 60
RASTER_INK_THRESHOLD = 205
RASTER_MIN_DARK = 3


@dataclass(frozen=True)
class Band:
    """
    A rectangle of one source page that carries question content.

    It carries its own x-window because a y-range alone still prints whatever
    sits beside the question -- the rotated DO NOT WRITE IN THIS AREA sidebar and
    the page frame's vertical rule, which arrive on a Maths B y-crop as debris
    reading "AREA" or "OT W" down the edge of the block.
    """

    page: int
    y0: float
    y1: float
    x0: float
    x1: float

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def width(self) -> float:
        return self.x1 - self.x0


def _is_answer_rule(stripped: str) -> bool:
    """
    A row of answer dots, whatever character the PDF happens to encode them as.

    Matching the dot itself is not enough. The 2016-2019 papers carry the broken
    CMap where every code sits 29 below its true value, so their answer rules
    arrive as 242 repetitions of U+0011 rather than of ".". Those pages printed a
    full page of dotted rules into the workbook because a dot-list never matched.

    What identifies a rule is that it is ONE character repeated, and that the
    character is not one you can write maths with.
    """
    solid = "".join(stripped.split())
    if len(solid) < MIN_RULE_REPEATS:
        return False
    first = solid[0]
    return first.isspace() is False and not first.isalnum() and solid == first * len(solid)


def _is_furniture_line(stripped: str) -> bool:
    if not stripped:
        return True
    if DOTTED_RE.match(stripped) or _is_answer_rule(stripped):
        return True
    if PAPER_TOTAL_RE.search(stripped) or RUBRIC_RE.match(stripped):
        return True
    if PUBLISHER_RE.search(stripped) and len(stripped) <= MAX_PUBLISHER_LENGTH:
        return True
    if CONTINUED_RE.match(stripped):
        return True
    if FENCE_RE.search(stripped):
        return True
    if BARCODE_RE.match(stripped):
        return True
    if SUBJECT_STAMP_RE.search(stripped) and len(stripped) <= MAX_STAMP_LENGTH:
        return True
    if STAMP_RE.search(stripped) and len(stripped) < 90:
        return True
    if stripped.lower().startswith("do not write in this area"):
        return True
    return False


def _is_furniture(text: str) -> bool:
    """
    Judge a block by its lines.

    Blocks are not clean units of furniture. The page number and the item
    barcode arrive glued together as "2\\n*P48381A0220*", which matches no
    whole-block pattern -- so that block survived, and its band dragged the
    GradeMax footer stamp into the printed page with it. A barcode is never
    adjacent to anything worth keeping, so one is enough to condemn the block;
    otherwise every line has to be furniture.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return True
    # One line is enough to condemn the block for these two. A barcode is never
    # adjacent to anything worth keeping, and neither is a publisher colophon --
    # which arrives split across lines ("Pearson Education Limited. Registered
    # company number 872828" / "with its registered office at 80 Strand"), so
    # requiring every line to match left it standing on 26 mark scheme pages.
    if any(BARCODE_RE.match(line) or PUBLISHER_RE.search(line) for line in lines):
        return True
    return all(_is_furniture_line(line) for line in lines)


def paper_box(page: fitz.Page) -> fitz.Rect:
    """
    Where the A4 sheet actually sits inside the PDF page.

    The 2020+ papers are 652x899 -- A4 plus 28.5pt of bleed on every side. Every
    cut line below is a distance from the edge of the PAPER, so measuring them
    from the raw page rect puts all of them 28.5pt out: the frame escapes the
    frame rule, the sidebar escapes the margin rule, and the page number escapes
    the footer rule. All three of those defects are the same arithmetic.
    """
    rect = page.rect
    target = (A4_WIDTH, A4_HEIGHT) if rect.height >= rect.width else (A4_HEIGHT, A4_WIDTH)
    dx = max(0.0, (rect.width - target[0]) / 2)
    dy = max(0.0, (rect.height - target[1]) / 2)
    return fitz.Rect(rect.x0 + dx, rect.y0 + dy, rect.x1 - dx, rect.y1 - dy)


def _outside_content_area(x0: float, x1: float, y0: float, y1: float,
                          box: fitz.Rect) -> bool:
    if box.height >= FULL_PAGE_MIN_HEIGHT:
        if y1 <= box.y0 + HEADER_CUT or y0 >= box.y1 - FOOTER_CUT:
            return True
    # A narrow strip pinned to a margin: the rotated sidebar, or an edge crop
    # mark. Width matters. Mark schemes carry no sidebar and no frame, and their
    # question-number column starts at x=14 -- a blind margin cut would slice it
    # off every mark scheme in the book.
    in_margin = x1 <= box.x0 + SIDEBAR_CUT or x0 >= box.x1 - SIDEBAR_CUT
    return in_margin and (x1 - x0) <= MARGIN_STRIP_WIDTH


def _is_page_frame(rect: fitz.Rect, box: fitz.Rect) -> bool:
    """The border Edexcel draws round every page, as a rectangle or as rules."""
    if rect.height < box.height * FRAME_HEIGHT_FRACTION:
        return False
    # A vertical side of a frame drawn as four separate lines -- but only at the
    # edge of the sheet. A mark scheme is a full-page TABLE, and its column rules
    # are just as tall and just as thin; treating one as a frame collapsed the
    # content window to a negative width and threw 16 mark schemes out of the
    # book with "rect must be finite and not empty".
    if rect.width <= RULE_THICKNESS:
        return rect.x1 <= box.x0 + FRAME_EDGE or rect.x0 >= box.x1 - FRAME_EDGE
    return rect.y0 <= box.y0 + FRAME_TOP and rect.width >= box.width * FRAME_WIDTH_FRACTION


def _is_frame_rectangle(rect: fitz.Rect, box: fitz.Rect) -> bool:
    """A frame with an interior, i.e. one the content window can be held inside."""
    return (rect.width >= box.width * FRAME_WIDTH_FRACTION
            and rect.height >= box.height * FRAME_HEIGHT_FRACTION)


def _is_bleed_mark(rect: fitz.Rect, width: float, height: float) -> bool:
    """
    A printer's registration mark, which runs off the edge of the sheet.

    The 652x899 papers carry two, at x[-1.8, 54.9]. Being 57pt wide they are too
    broad for the margin-strip rule and too thin for the frame rule, so they
    survived both -- widening the content window to the page edge (dragging the
    sidebar back in) and planting a phantom 3pt band at the foot of the sheet.
    Real content is never drawn outside the page.
    """
    return (rect.x0 < -BLEED_TOLERANCE or rect.y0 < -BLEED_TOLERANCE
            or rect.x1 > width + BLEED_TOLERANCE or rect.y1 > height + BLEED_TOLERANCE)


def _rides_with_furniture(rect: fitz.Rect, furniture: list[tuple[float, float]]) -> bool:
    """
    A graphic drawn at the same height as a line of furniture is part of it.

    The item barcode is the case that matters: it is a cluster of vector bars,
    invisible to every text rule, sitting directly on the "4MB0 | 2017 | January
    | Paper 1 | GradeMax" stamp. The stamp was correctly discarded and the bars
    were not, so the band they created reprinted both.
    """
    centre = (rect.y0 + rect.y1) / 2
    return any(y0 - FURNITURE_OVERLAP <= centre <= y1 + FURNITURE_OVERLAP
               for y0, y1 in furniture)


class PageScan:
    """What one source page yields: content, the frame, and what to paint out."""

    def __init__(self) -> None:
        self.spans: list[Span] = []
        self.frame: fitz.Rect | None = None
        self.masks: list[fitz.Rect] = []
        self.text_spans = 0
        self.text_blocks = 0
        self.image_area = 0.0
        self.spare_from: float | None = None
        self.spare_overleaf = False


def _text_bands(page: fitz.Page) -> PageScan:
    width, height = page.rect.width, page.rect.height
    box = paper_box(page)
    scan = PageScan()
    spans = scan.spans

    # BLOCK level, deliberately, not line level.
    #
    # Lines trim harder, but a band is re-stacked in the output with a fixed gap,
    # so anything laid out in two dimensions comes apart: a table's ruling lines
    # are drawings and its text is lines, and separating them into 73 bands
    # reassembles the rules and the figures they belong to in the wrong places.
    # A block is PyMuPDF's own grouping of what belongs together, which is
    # exactly the unit that survives being moved.
    furniture: list[tuple[float, float]] = []
    for block in page.get_text("blocks"):
        x0, y0, x1, y1, text = block[0], block[1], block[2], block[3], block[4]
        if text.strip():
            scan.text_blocks += 1
        if SPARE_GRID_RE.search(text):
            scan.spare_from = y0 if scan.spare_from is None else min(scan.spare_from, y0)
            if SPARE_GRID_OVERLEAF_RE.search(text):
                scan.spare_overleaf = True
        if _outside_content_area(x0, x1, y0, y1, box):
            continue
        if _is_furniture(text):
            furniture.append((y0, y1))
            # Kept as a rectangle too. Excluding furniture from the BANDS does
            # not stop it printing: a band is rendered by clipping the source
            # page, so a footer sharing a y-range with real content comes along
            # with it. "Turn over" and the subject code reached the printed book
            # exactly that way. Anything still inside a band gets painted out.
            scan.masks.append(fitz.Rect(x0, y0, x1, y1))
            continue
        scan.text_spans += 1
        spans.append((y0, y1, x0, x1))

    for drawing in page.get_drawings():
        rect = drawing["rect"]
        if rect.is_empty or rect.is_infinite:
            continue
        if _outside_content_area(rect.x0, rect.x1, rect.y0, rect.y1, box):
            continue
        if _is_page_frame(rect, box):
            # Remember it: excluding the frame from the BANDS is not enough,
            # because each band is rendered by clipping the source page, and a
            # window that reaches the frame reprints its vertical rules down the
            # edge of every block in the book. Only a frame with an interior is
            # worth remembering -- a bare vertical rule has none.
            if _is_frame_rectangle(rect, box) and (
                    scan.frame is None or rect.width > scan.frame.width):
                scan.frame = rect
            continue
        if _is_bleed_mark(rect, width, height) or _rides_with_furniture(rect, furniture):
            scan.masks.append(fitz.Rect(rect))
            continue
        spans.append((rect.y0, rect.y1, rect.x0, rect.x1))

    for image in page.get_images(full=True):
        try:
            rect = page.get_image_bbox(image)
        except Exception:  # noqa: BLE001 - a stale xref must not lose the page
            continue
        if rect.is_empty or rect.is_infinite:
            continue
        if _outside_content_area(rect.x0, rect.x1, rect.y0, rect.y1, box):
            continue
        if _rides_with_furniture(rect, furniture):
            scan.masks.append(fitz.Rect(rect))
            continue
        scan.image_area += rect.get_area()
        spans.append((rect.y0, rect.y1, rect.x0, rect.x1))

    return scan


def _raster_bands(page: fitz.Page) -> PageScan:
    """
    Row-scan fallback for the ~20 segments that are image-only scans.

    There is no text layer, so an answer line cannot be recognised by its dots.
    It is recognised by its thickness instead: MIN_BAND_HEIGHT drops any band too
    thin to be a line of maths.
    """
    pix = page.get_pixmap(dpi=RASTER_DPI, colorspace=fitz.csGRAY)
    w, h = pix.width, pix.height
    scan = PageScan()
    if not w or not h:
        return scan
    samples = pix.samples
    pt_per_row = page.rect.height / h

    box = paper_box(page)
    x0 = int(w * (box.x0 + SIDEBAR_CUT + 8) / page.rect.width)
    x1 = int(w * (box.x1 - SIDEBAR_CUT - 8) / page.rect.width)
    full_page = box.height >= FULL_PAGE_MIN_HEIGHT
    y0 = int((box.y0 + HEADER_CUT) / pt_per_row) if full_page else 0
    y1 = int((box.y1 - (FOOTER_CUT if full_page else 0)) / pt_per_row)

    pt_per_col = page.rect.width / w
    spans: list[Span] = []
    run_start: int | None = None
    run_left = w
    run_right = 0

    for y in range(y0, min(y1, h)):
        base = y * w
        first = last = -1
        dark = 0
        # The whole row is measured, not just enough of it to prove there is ink.
        # Per-band x-extents are what let the window hug the real content: taking
        # the scan bounds instead put it exactly on the page frame's vertical
        # rules, which then printed down the side of every scanned question.
        for x in range(x0, x1):
            if samples[base + x] < RASTER_INK_THRESHOLD:
                dark += 1
                if first < 0:
                    first = x
                last = x
        if dark >= RASTER_MIN_DARK:
            if run_start is None:
                run_start, run_left, run_right = y, first, last
            else:
                run_left, run_right = min(run_left, first), max(run_right, last)
        elif run_start is not None:
            spans.append((run_start * pt_per_row, y * pt_per_row,
                          run_left * pt_per_col, run_right * pt_per_col))
            run_start = None
    if run_start is not None:
        spans.append((run_start * pt_per_row, min(y1, h) * pt_per_row,
                      run_left * pt_per_col, run_right * pt_per_col))

    spans = [s for s in spans if s[1] - s[0] >= MIN_BAND_HEIGHT]

    # The mark fence, which on a scan cannot be read and rejected as text. It
    # names the ORIGINAL question number, so leaving it in contradicts the
    # renumbering the whole book depends on.
    #
    # Two shapes, because the row scan sees ink and not words. On a page of its
    # own the fence and the rule beneath it merge into a single 12pt run
    # spanning 509 of 595 points -- so it is not indented at all, and the
    # indent test alone missed it. A page whose entire content is one thin, wide
    # line is furniture; anywhere else, the fence is the trailing indented line.
    while spans:
        y_start, y_end, span_x0, span_x1 = spans[-1]
        if y_end - y_start > FENCE_MAX_HEIGHT:
            break
        alone_and_wide = (len(spans) == 1
                          and span_x1 - span_x0 >= box.width * FENCE_MIN_WIDTH)
        indented = span_x0 > box.x0 + box.width * FENCE_MIN_INDENT
        if not (alone_and_wide or indented):
            break
        spans.pop()

    scan.spans = spans
    return scan


def _merge(spans: Iterable[Span], limit: float) -> list[tuple[float, float]]:
    """Collapse the y-ranges; x is handled document-wide, not per band."""
    ordered = sorted((s[0], s[1]) for s in spans)
    if not ordered:
        return []
    merged = [list(ordered[0])]
    for y0, y1 in ordered[1:]:
        if y0 - merged[-1][1] <= limit:
            merged[-1][1] = max(merged[-1][1], y1)
        else:
            merged.append([y0, y1])
    return [(a, b) for a, b in merged]


X_PAD = 6.0
# Kept clear of the frame's stroke, which has width of its own.
FRAME_CLEARANCE = 2.5


def _window(spans: list[Span], width: float, frame: fitz.Rect | None) -> tuple[float, float]:
    """
    The horizontal slice worth printing, measured rather than assumed.

    A fixed inset cannot serve both document types. A question paper needs ~38pt
    cut to clear the sidebar and the frame; a mark scheme has neither and starts
    its question-number column at x=14, so the same cut would remove it. Taking
    the extent of the content that survived the filters gets both right, and is
    safe by construction: the window is derived FROM the kept spans, so it can
    only ever clip something already rejected as furniture.

    The frame is the exception, and it is why `frame` is passed in. Excluding it
    from the bands does not stop it printing: a band is rendered by clipping the
    source page, so a window that merely touches the frame reprints its vertical
    rules down the side of every block in the book. The window is held strictly
    inside it.

    It is deliberately never widened to some minimum. Widening past the content
    would reach back over the sidebar on a narrow Maths B crop and reprint the
    "AREA" debris this exists to remove. A narrow question simply prints at its
    original size -- the layout caps magnification at 1.0.
    """
    if not spans:
        return 0.0, width
    x0 = max(0.0, min(s[2] for s in spans) - X_PAD)
    x1 = min(width, max(s[3] for s in spans) + X_PAD)
    if frame is not None:
        clamped = (max(x0, frame.x0 + FRAME_CLEARANCE), min(x1, frame.x1 - FRAME_CLEARANCE))
        # Never let the clamp win if it would leave nothing to print. A window
        # that inverts does not degrade the page, it loses the question.
        if clamped[1] - clamped[0] > 0:
            x0, x1 = clamped
    return x0, x1


def _is_scanned(page: fitz.Page, scan: PageScan) -> bool:
    """
    A page whose content is one big picture rather than text.

    This is the check that decides whether to fall back to the row scan, and the
    obvious version of it -- "almost no text on the page" -- is wrong here. The
    scanned paper still carries text: OUR OWN GradeMax stamp, about fifteen words
    per page. So the fallback never fired, the scan's full-page image became a
    single band covering the whole sheet, and all eleven of those questions
    printed verbatim: answer rules, "Question 2 continued" headers and all.

    What identifies a scan is that nothing survived as TEXT, while the page
    plainly still has something on it.

    The first clause is the one that matters and the one I got wrong twice. On
    this paper `get_images` reports nothing at all -- the scan is embedded where
    the page's own image list does not reach -- so keying off image area alone
    still left these pages empty. If no span of any kind survived, there is
    nothing to print, and the row scan can only be an improvement.
    """
    if scan.text_spans:
        return False

    # A page that HAS a text layer and produced no content is not unreadable --
    # it is a blank continuation page, correctly reduced to nothing. Reading it
    # by eye instead put "Question 8 continued" back on 389 pages of the book.
    # The presence of text blocks, not of surviving ones, is what says the text
    # layer works.
    if scan.text_blocks > MAX_SCAN_TEXT_BLOCKS:
        return False

    # A traced scan: thousands of vector primitives and barely a word of text.
    # This paper stores its pages that way -- 5,472 shapes on a single sheet --
    # so it is neither an image page nor an empty one. A real figure is tens of
    # shapes; the only text is our own stamp.
    if len(scan.spans) >= VECTOR_SCAN_PRIMITIVES:
        return True
    if not scan.spans and scan.text_blocks == 0:
        return True
    box = paper_box(page)
    return box.get_area() > 0 and scan.image_area >= box.get_area() * SCAN_AREA_FRACTION


def _drop_spare_grids(scans: list[PageScan]) -> None:
    """
    Remove the spare grid, and the sentence that offers it.

    A past paper prints a second copy of a graph grid in case the candidate
    spoils the first. One grid is enough in the workbook -- but dropping only
    the sentence would leave an unexplained empty grid on the page, so whatever
    the sentence points at goes with it. Where it points depends on the wording:
    "turn over for a spare grid" means the next page is the spare, "only use
    this grid" means everything below the sentence on this one.
    """
    blank_next = False
    for scan in scans:
        if blank_next:
            scan.spans = []
            blank_next = False
            continue
        if scan.spare_from is None:
            continue
        cut = scan.spare_from - SPARE_GRID_PAD
        scan.spans = [s for s in scan.spans if s[1] <= cut]
        blank_next = scan.spare_overleaf


def content_layout(doc: fitz.Document) -> tuple[list[Band], dict[int, list[fitz.Rect]]]:
    """
    Bands of real content, plus the furniture rectangles to paint out.

    Masks are returned because exclusion alone is not enough: a band is drawn by
    clipping the source page, so any furniture sharing its y-range prints with
    it. Whatever the geometry cannot remove, the mask covers.
    """
    scans: list[PageScan] = []
    frame: fitz.Rect | None = None
    masks: dict[int, list[fitz.Rect]] = {}

    for index in range(doc.page_count):
        page = doc[index]
        scan = _text_bands(page)
        if _is_scanned(page, scan):
            scan = _raster_bands(page)
        if scan.frame is not None and (frame is None or scan.frame.width < frame.width):
            frame = scan.frame
        masks[index] = scan.masks
        scans.append(scan)

    _drop_spare_grids(scans)

    per_page: list[tuple[int, list[tuple[float, float]]]] = []
    widest: list[Span] = []
    for index, scan in enumerate(scans):
        per_page.append((index, _merge(scan.spans, MERGE_GAP)))
        widest.extend(scan.spans)

    # One window for the whole segment, so every band prints at the same scale.
    # A per-band window would magnify a lone short line and shrink the next.
    x0, x1 = _window(widest, doc[0].rect.width if doc.page_count else 0.0, frame)

    bands: list[Band] = []
    for index, merged in per_page:
        page = doc[index]
        for y0, y1 in merged:
            top = max(0.0, y0 - BAND_PAD)
            bottom = min(page.rect.height, y1 + BAND_PAD)
            if bottom - top >= 1.0:
                bands.append(Band(index, top, bottom,
                                  max(page.rect.x0, x0), min(page.rect.x1, x1)))
    return bands, masks


def content_bands(doc: fitz.Document) -> list[Band]:
    """Every band of real question content in this segment, in reading order."""
    return content_layout(doc)[0]


def ink_height(bands: list[Band]) -> float:
    return sum(band.height for band in bands)


def question_number_box(doc: fitz.Document, number: int,
                        first_band: Band | None = None) -> fitz.Rect | None:
    """
    Where the paper printed this question's number, so the book can replace it.

    A chapterwise workbook renumbers from 1 within each section, which means the
    original number has to go -- "10" at the head of the seventh question in 9.4
    is worse than no number at all. It is not enough to draw the new number
    beside it; the old one is part of the page image and has to be painted out.

    Matched by position as well as by text: exam papers print the number in a
    hanging indent at the far left of the first line, and a bare "10" somewhere
    inside the question body means something else entirely.

    Matched at WORD level, not block level: on the broken-CMap papers PyMuPDF
    groups the number into the same block as the stem ("10 The points A and B
    have coordinates..."), so no block ever equals the number on its own.
    """
    if not doc.page_count:
        return None
    page = doc[0]
    box = paper_box(page)
    wanted = str(number)
    best: fitz.Rect | None = None

    for word in page.get_text("words"):
        x0, y0, x1, y1, text = word[0], word[1], word[2], word[3], word[4]
        if text.strip() != wanted:
            continue
        if x0 > box.x0 + QUESTION_NUMBER_MAX_X:
            continue
        if best is None or y0 < best.y0:
            best = fitz.Rect(x0, y0, x1, y1)

    if best is None and first_band is not None:
        best = _number_box_by_ink(doc[first_band.page], first_band)
    return best


def _number_box_by_ink(page: fitz.Page, band) -> fitz.Rect | None:
    """
    Find the question number on a scanned page by looking for its ink.

    There is no text to match, and a fixed-size patch guessed at the corner is
    not good enough -- it left the tail of the original "2" showing beside the
    new "1", which reads as a printing fault. The number is the first cluster of
    ink on the first line, separated from the question text by the hanging
    indent, so it can be measured: scan columns until the gap.
    """
    clip = fitz.Rect(band.x0, band.y0,
                     min(band.x0 + NUMBER_SCAN_WIDTH, band.x1),
                     min(band.y0 + NUMBER_SCAN_HEIGHT, band.y1))
    if clip.is_empty:
        return None
    pix = page.get_pixmap(dpi=NUMBER_SCAN_DPI, colorspace=fitz.csGRAY, clip=clip)
    w, h = pix.width, pix.height
    if not w or not h:
        return None
    samples = pix.samples

    inky = [any(samples[y * w + x] < RASTER_INK_THRESHOLD for y in range(h))
            for x in range(w)]
    if not any(inky):
        return None

    # Every cluster of ink across the window, then the first one shaped like a
    # number. Taking simply the first cluster picked up the page frame's vertical
    # rule -- half a point wide -- on three of the eleven, so the new number was
    # drawn over the frame while the real digit stayed put.
    runs: list[tuple[int, int]] = []
    x = 0
    while x < w:
        if not inky[x]:
            x += 1
            continue
        start = x
        gap = 0
        end = x
        while x < w:
            if inky[x]:
                end, gap = x, 0
            else:
                gap += 1
                if gap >= NUMBER_GAP_COLUMNS:
                    break
            x += 1
        runs.append((start, end))

    scale = clip.width / w
    candidates = [(s, e) for s, e in runs
                  if MIN_NUMBER_WIDTH <= (e - s + 1) * scale <= MAX_NUMBER_WIDTH]
    if not candidates:
        return None
    start, end = candidates[0]

    rows = [y for y in range(h)
            if any(samples[y * w + x] < RASTER_INK_THRESHOLD for x in range(start, end + 1))]
    if not rows:
        return None

    sx = scale
    sy = clip.height / h
    return fitz.Rect(clip.x0 + start * sx, clip.y0 + rows[0] * sy,
                     clip.x0 + (end + 1) * sx, clip.y0 + (rows[-1] + 1) * sy)
