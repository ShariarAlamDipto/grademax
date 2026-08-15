"""
Lay questions down A4 sheets, DECIDING the answer space instead of inheriting it.

The previous engine treated a source page as the unit: each one was scaled to the
content width and stamped onto a fresh sheet. At 595pt wide scaled into 527pt, a
source page came out 746pt tall against 752pt of usable sheet -- so two source
pages could never share a sheet, and the flow that was supposed to pack short
questions together never once fired. 48 verified FPM questions filled 203 sheets.
The full book would have run past 2,800 pages, of which measurement says 90% is
white.

Here the unit is a BAND of real content (see workbook_ink), and the working space
is a policy: so many points per mark, floored and capped. That decouples the two
things that were fused together -- how much question there is, and how much room
the student gets -- so the book can be resized without touching the segments.

A question is never left stranded at the foot of a sheet with its working space
overleaf; ORPHAN_GUARD keeps a usable slice of the space with the question.
"""

from __future__ import annotations

from dataclasses import dataclass

import fitz

PAGE_WIDTH, PAGE_HEIGHT = fitz.paper_size("a4")
MARGIN = 34.0
HEADER_HEIGHT = 30.0
FOOTER_HEIGHT = 26.0

INK = (0.09, 0.11, 0.15)
MUTED = (0.42, 0.45, 0.52)
RULE = (0.80, 0.82, 0.86)
DRAFT = (0.72, 0.11, 0.11)

LABEL_HEIGHT = 20.0
QUESTION_GAP = 16.0
# Gap kept between two bands of the same question. The source may have separated
# them by half a page of answer space; the question reads the same without it.
BAND_GAP = 8.0
# Never start a question that cannot keep this much of its working space with it.
ORPHAN_GUARD = 96.0
# Section band plus the air beneath it.
SECTION_HEADING_HEIGHT = 38.0

# Patch size used when the paper's question number cannot be located, which
# happens only on the image-only scan. Sized to the widest two-digit number.
FALLBACK_NUMBER_WIDTH = 17.0
FALLBACK_NUMBER_HEIGHT = 14.0
NUMBER_PAD = 1.6
# The detected box hugs the ink, and on a scanned digit the ink is measured
# short -- which left the tail of the original "2" showing under the new "1".
# The hanging indent holds nothing but the number, so the patch is grown to a
# full line and a full digit width regardless of what was measured.
NUMBER_PATCH_MIN_HEIGHT = 16.0
NUMBER_PATCH_MIN_WIDTH = 14.0


def number_patch(rect: fitz.Rect) -> fitz.Rect:
    """The area to paint white so no trace of the paper's number survives."""
    height = max(rect.height, NUMBER_PATCH_MIN_HEIGHT)
    width = max(rect.width, NUMBER_PATCH_MIN_WIDTH)
    centre_y = (rect.y0 + rect.y1) / 2
    return fitz.Rect(rect.x0 - NUMBER_PAD,
                     centre_y - height / 2 - NUMBER_PAD,
                     rect.x0 + width + NUMBER_PAD,
                     centre_y + height / 2 + NUMBER_PAD)


@dataclass(frozen=True)
class SpacePolicy:
    """How much room a student gets to work, as a function of the marks."""

    name: str
    points_per_mark: float
    minimum: float
    maximum: float

    def space_for(self, marks: int | None) -> float:
        if not marks or marks <= 0:
            return self.minimum
        return max(self.minimum, min(self.maximum, marks * self.points_per_mark))


# Roughly: compact gives a 10-mark question a third of a page to work in,
# standard just over a quarter-page more, generous the best part of half a sheet.
# The cap stops a 15-mark question from claiming two blank pages on its own.
POLICIES: dict[str, SpacePolicy] = {
    "compact": SpacePolicy("compact", 13.0, 55.0, 300.0),
    "standard": SpacePolicy("standard", 21.0, 85.0, 470.0),
    "generous": SpacePolicy("generous", 30.0, 120.0, 700.0),
}
DEFAULT_POLICY = "standard"

# Mark schemes are read, not written on.
NO_SPACE = SpacePolicy("none", 0.0, 0.0, 0.0)


@dataclass(frozen=True)
class BandedSpacePolicy:
    """
    Three fixed sizes of working space, chosen by the mark tariff.

    The printed book wants a steady rhythm: a reader flicking through should see
    the same block of space again and again, not a different height on every
    question. Continuous points-per-mark packs tighter but reads as ragged on
    paper. Banding keeps the page predictable while still refusing to give a
    2-mark question the room a 15-mark one needs.
    """

    name: str
    tiers: tuple[tuple[int, float], ...]   # (inclusive mark ceiling, space)
    largest: float

    def space_for(self, marks: int | None) -> float:
        tariff = marks or 0
        for ceiling, space in self.tiers:
            if tariff <= ceiling:
                return space
        return self.largest

    def describe(self) -> str:
        parts = [f"<={c} marks {s:.0f}pt" for c, s in self.tiers]
        parts.append(f"more {self.largest:.0f}pt")
        return ", ".join(parts)


PRINT_POLICY = BandedSpacePolicy("print", ((5, 260.0), (10, 400.0)), 620.0)


class Flow:
    """Packs labelled question blocks and their working space down A4 sheets."""

    def __init__(self, doc: fitz.Document, running_header: str, policy: SpacePolicy) -> None:
        self.doc = doc
        self.running_header = running_header
        self.policy = policy
        self.page: fitz.Page | None = None
        self.cursor = 0.0
        self.last_start_page = 0
        self.content_top = MARGIN + HEADER_HEIGHT
        self.content_bottom = PAGE_HEIGHT - FOOTER_HEIGHT
        self.width = PAGE_WIDTH - 2 * MARGIN

    # -- sheet handling ----------------------------------------------------

    def _start_page(self) -> None:
        self.page = self.doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        self.page.insert_text(
            (MARGIN, MARGIN + 2), self.running_header,
            fontname="helv", fontsize=8, color=MUTED,
        )
        y = MARGIN + 9
        self.page.draw_line(fitz.Point(MARGIN, y), fitz.Point(PAGE_WIDTH - MARGIN, y),
                            color=RULE, width=0.6)
        self.cursor = self.content_top

    def _room(self) -> float:
        if self.page is None:
            return 0.0
        return self.content_bottom - self.cursor

    @property
    def _usable(self) -> float:
        return self.content_bottom - self.content_top

    # -- placement ---------------------------------------------------------

    def add(self, source: fitz.Document, bands, label: str, right: str,
            marks: int | None, draft: bool,
            renumber: tuple[fitz.Rect | None, str] | None = None,
            masks: dict[int, list[fitz.Rect]] | None = None) -> None:
        """
        Place one question: its content bands, then its working space.

        `bands` come from workbook_ink.content_bands(source). An empty list means
        the trim found nothing, which would silently drop the question -- so the
        caller is expected to fall back to whole pages rather than pass nothing.
        """
        # A band with no area cannot be drawn, and PyMuPDF raises rather than
        # ignoring it -- which cost 16 mark schemes their place in the book,
        # because the caller's error handler drops the whole question. Discard
        # the degenerate band instead and print everything else.
        bands = [b for b in bands if b.width > 0 and b.height > 0]
        if not bands:
            return

        space = self.policy.space_for(marks)
        first_height = self._scaled_height(source, bands[0])

        # Start the question on a fresh sheet rather than orphan its label, or
        # strand the question at the foot of a sheet away from its own space.
        needed = LABEL_HEIGHT + first_height + min(space, ORPHAN_GUARD)
        if self.page is None or needed > self._room():
            self._start_page()

        assert self.page is not None
        # Which sheet this question begins on. The caller cannot infer it from
        # the page count, because a question may open a new sheet or continue
        # the current one, and a contents entry that is one page out is worse
        # than no contents at all.
        self.last_start_page = self.doc.page_count - 1
        self._draw_label(label, right, draft)

        for index, band in enumerate(bands):
            height = self._scaled_height(source, band)
            if index and height + BAND_GAP > self._room():
                self._start_page()
            elif index:
                self.cursor += BAND_GAP

            scale = self._scale(source, band)
            width = band.width * scale
            target = fitz.Rect(MARGIN, self.cursor, MARGIN + width, self.cursor + height)
            self.page.show_pdf_page(
                target, source, band.page,
                clip=fitz.Rect(band.x0, band.y0, band.x1, band.y1),
            )
            if masks:
                self._paint_out(band, target, scale, masks.get(band.page, ()))
            if index == 0 and renumber is not None:
                self._replace_number(band, target, scale, *renumber)
            self.cursor += height

        self._reserve(space)
        self._separator()

    def add_paged(self, source: fitz.Document, bands, label: str, right: str,
                  pages: int, draft: bool,
                  renumber: tuple[fitz.Rect | None, str] | None = None,
                  masks: dict[int, list[fitz.Rect]] | None = None,
                  heading: str | None = None) -> tuple[int, float]:
        """
        Give this question exactly `pages` sheets, to itself.

        Nothing shares a sheet with it and nothing runs past its allocation: the
        question opens a fresh page, and blank sheets are added afterwards until
        the count is exact. Where the content cannot fit the allocation it is
        shrunk uniformly rather than allowed to spill, because the promise this
        edition makes -- one sheet under five marks, two above -- is the whole
        point of it. The shrink factor is returned so the caller can say which
        questions paid for that promise.
        """
        bands = [b for b in bands if b.width > 0 and b.height > 0]
        if not bands:
            return 0, 1.0

        self._start_page()
        first_page = self.doc.page_count - 1
        self.last_start_page = first_page

        # A section opens on the first question of that section rather than on a
        # sheet of its own: 39 near-blank pages in an 871-page book read as a
        # binding fault, not as structure. The heading comes out of this
        # question's allocation, which costs it about 6% of one sheet.
        heading_height = 0.0
        if heading:
            self._draw_heading(heading)
            heading_height = SECTION_HEADING_HEIGHT

        self._draw_label(label, right, draft)

        shrink = self._fit(source, bands, pages, heading_height)

        for index, band in enumerate(bands):
            scale = self._scale(source, band) * shrink
            height = band.height * scale
            if index and height + BAND_GAP > self._room():
                self._start_page()
            elif index:
                self.cursor += BAND_GAP

            assert self.page is not None
            width = band.width * scale
            target = fitz.Rect(MARGIN, self.cursor, MARGIN + width, self.cursor + height)
            self.page.show_pdf_page(
                target, source, band.page,
                clip=fitz.Rect(band.x0, band.y0, band.x1, band.y1),
            )
            if masks:
                self._paint_out(band, target, scale, masks.get(band.page, ()))
            if index == 0 and renumber is not None:
                self._replace_number(band, target, scale, *renumber)
            self.cursor += height

        used = self.doc.page_count - first_page
        while used < pages:
            self._start_page()
            used += 1
        return used, shrink

    def _fit(self, source: fitz.Document, bands, pages: int,
             heading: float = 0.0) -> float:
        """How much the content must shrink to sit inside `pages` sheets."""
        budget = (pages * self._usable - LABEL_HEIGHT - heading
                  - BAND_GAP * max(0, len(bands) - 1))
        natural = sum(self._scaled_height(source, band) for band in bands)
        if natural <= 0 or natural <= budget:
            return 1.0
        return budget / natural

    def _scale(self, source: fitz.Document, band) -> float:
        scale = min(self.width / band.width, 1.0) if band.width > 0 else 1.0
        # A band taller than a whole sheet is scaled down until it fits one.
        if band.height * scale > self._usable:
            scale = self._usable / band.height
        return scale

    def _scaled_height(self, source: fitz.Document, band) -> float:
        return band.height * self._scale(source, band)

    def _map(self, band, target: fitz.Rect, scale: float, rect: fitz.Rect) -> fitz.Rect:
        """A rectangle in source-page coordinates, placed on the output sheet."""
        return fitz.Rect(
            target.x0 + (rect.x0 - band.x0) * scale,
            target.y0 + (rect.y0 - band.y0) * scale,
            target.x0 + (rect.x1 - band.x0) * scale,
            target.y0 + (rect.y1 - band.y0) * scale,
        )

    def _paint_out(self, band, target: fitz.Rect, scale: float, boxes) -> None:
        """
        Cover furniture that shares a band with real content.

        Leaving it out of the band is not enough. A band is drawn by clipping the
        source page, so a footer on the same rows as the last line of a question
        is carried along with it -- which is how "Turn over" and the subject code
        reached six pages of a book that had supposedly removed them. Painting
        white over the exact rectangle is seamless on white stock.
        """
        assert self.page is not None
        band_rect = fitz.Rect(band.x0, band.y0, band.x1, band.y1)
        for box in boxes:
            if not box.intersects(band_rect):
                continue
            patch = self._map(band, target, scale, box & band_rect) & self.page.rect
            if not patch.is_empty:
                self.page.draw_rect(patch, color=None, fill=(1, 1, 1))

    def _replace_number(self, band, target: fitz.Rect, scale: float,
                        source_box: fitz.Rect | None, printed: str) -> None:
        """
        Paint out the exam paper's question number and write the book's own.

        A chapterwise section runs 1..N, so the number the paper printed is
        actively wrong here -- the seventh question of 9.4 is not "Question 10".
        Writing the new number beside the old one would leave two, so the old one
        is covered: it is part of the page image, not text we control.

        `source_box` is None for the image-only scanned paper, which has no text
        layer to locate it in. There the number still sits in the hanging indent
        at the head of the first band, so a small patch at that corner covers it.
        """
        assert self.page is not None
        if source_box is not None:
            mapped = self._map(band, target, scale, source_box)
            x0, y0, x1, y1 = mapped.x0, mapped.y0, mapped.x1, mapped.y1
        else:
            x0, y0 = target.x0, target.y0
            x1, y1 = x0 + FALLBACK_NUMBER_WIDTH, y0 + FALLBACK_NUMBER_HEIGHT

        patch = number_patch(fitz.Rect(x0, y0, x1, y1)) & self.page.rect
        if not patch.is_empty:
            self.page.draw_rect(patch, color=None, fill=(1, 1, 1))

        size = max(7.5, min(11.0, (y1 - y0) * 0.86))
        self.page.insert_text((x0, y1 - (y1 - y0) * 0.12), printed,
                              fontname="hebo", fontsize=size, color=INK)

    def _draw_label(self, label: str, right: str, draft: bool) -> None:
        assert self.page is not None
        self.page.insert_text((MARGIN, self.cursor + 10), label,
                              fontname="hebo", fontsize=9, color=INK)
        if right:
            tail = fitz.get_text_length(right, fontname="helv", fontsize=7.6)
            self.page.insert_text(
                (PAGE_WIDTH - MARGIN - tail, self.cursor + 10), right,
                fontname="helv", fontsize=7.6, color=DRAFT if draft else MUTED,
            )
        self.cursor += LABEL_HEIGHT

    def _reserve(self, space: float) -> None:
        """Leave `space` points blank, continuing onto further sheets if needed."""
        remaining = space
        while remaining > self._room():
            remaining -= self._room()
            self._start_page()
        self.cursor += remaining

    def _separator(self) -> None:
        if self.page is None or self._room() <= QUESTION_GAP:
            return
        y = self.cursor + QUESTION_GAP / 2
        self.page.draw_line(fitz.Point(MARGIN + 60, y), fitz.Point(PAGE_WIDTH - MARGIN - 60, y),
                            color=RULE, width=0.5)
        self.cursor += QUESTION_GAP

    def _draw_heading(self, title: str) -> None:
        """The section band, drawn wherever the cursor currently sits."""
        assert self.page is not None
        self.page.draw_rect(
            fitz.Rect(MARGIN, self.cursor, PAGE_WIDTH - MARGIN, self.cursor + 26),
            color=None, fill=(0.95, 0.96, 0.97),
        )
        self.page.insert_text((MARGIN + 8, self.cursor + 17), title,
                              fontname="hebo", fontsize=10.5, color=INK)
        self.cursor += SECTION_HEADING_HEIGHT

    def section_break(self, title: str, force_page: bool = False) -> None:
        """
        Open a section with its own heading, so a student can find "6.3 Circle
        theorems" by flicking rather than by consulting the contents page.

        `force_page` starts a fresh sheet for it. The paged edition needs that:
        there, the sheet still open is the previous question's working space,
        and dropping a section heading into the middle of it both defaces that
        space and misplaces the section. Only 10 of 39 headings got a page of
        their own without this.
        """
        if force_page or self.page is None or 44.0 + 90 > self._room():
            self._start_page()
        else:
            self.cursor += 10

        assert self.page is not None
        self.page.draw_rect(
            fitz.Rect(MARGIN, self.cursor, PAGE_WIDTH - MARGIN, self.cursor + 26),
            color=None, fill=(0.95, 0.96, 0.97),
        )
        self.page.insert_text((MARGIN + 8, self.cursor + 17), title,
                              fontname="hebo", fontsize=10.5, color=INK)
        self.cursor += 26 + 12


def add_page_numbers(doc: fitz.Document, footer: str) -> None:
    for number, page in enumerate(doc, 1):
        label = f"{footer}   ·   {number}"
        width = fitz.get_text_length(label, fontname="helv", fontsize=8)
        page.insert_text(
            ((PAGE_WIDTH - width) / 2, PAGE_HEIGHT - FOOTER_HEIGHT + 12),
            label, fontname="helv", fontsize=8, color=MUTED,
        )
