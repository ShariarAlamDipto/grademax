"""
Furniture for the 2018-2026 yearwise books: title page, contents, page
numbers, covers, and the sheet placement with cross-references.

TYPE IS EMBEDDED, AND THE SEPARATOR IS ASCII. The first pilot set its heads and
feet in PDF base-14 Helvetica, which is NOT embedded: every viewer substitutes
its own font, and in the user's viewer the middle dot separator ("·") came out
as a summation sign (in PyMuPDF's renderer it was a bullet, in a serif face).
A print book cannot leave its type to the printer's substitution either. So
all our own text is Arial, embedded from the system fonts, and items are
separated by a plain "|" that every font has.

Self-contained on purpose: `yearwise_layout` still serves the finished M1, S1
and P4 books, and their regression test pins its output, so nothing there
changes. Only the board-strip geometry (bands) and the lockup recolouring are
shared.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import fitz

from .workbook_layout import INK, MARGIN, MUTED, PAGE_HEIGHT, PAGE_WIDTH, RULE
from .yearwise_layout import (
    BRAND, FOOTER_BAND, FOOTER_BASELINE, HEADER_BASELINE, SEASON_LABEL, _white_lockup,
    clear_bands)

FONT_DIR = Path("C:/Windows/Fonts")
REGULAR = FONT_DIR / "arial.ttf"
BOLD = FONT_DIR / "arialbd.ttf"
_FONTS = {False: fitz.Font(fontfile=str(REGULAR)), True: fitz.Font(fontfile=str(BOLD))}
SEP = "  |  "

QUALIFICATION = {"IGCSE": "Pearson Edexcel International GCSE",
                 "IAL": "Pearson Edexcel International Advanced Level"}
SUB = "Yearwise Past Paper Workbook"
LANDSCAPE_MIN_WIDTH = 800.0
A4 = fitz.Rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT)
CONTENTS_TOP, CONTENTS_BOTTOM, CONTENTS_ROW, YEAR_GAP = 132.0, PAGE_HEIGHT - 76.0, 19.0, 10.0


@dataclass(frozen=True)
class Volume:
    """One bound book."""
    subject: str          # "Mathematics B"
    code: str             # "4MB1"
    level: str            # IGCSE | IAL
    kind: str             # questions | markschemes
    number: int
    of: int
    span: str

    @property
    def is_questions(self) -> bool:
        return self.kind == "questions"

    @property
    def title(self) -> str:
        return "Question Papers" if self.is_questions else "Mark Schemes"

    @property
    def running(self) -> str:
        return SEP.join([BRAND, f"{self.subject} ({self.code})", self.title, f"Volume {self.number}"])


def width(text: str, size: float, bold: bool = False) -> float:
    return _FONTS[bold].text_length(text, fontsize=size)


def put(page: fitz.Page, x: float, y: float, text: str, size: float,
        bold: bool = False, color=INK) -> None:
    """Our own text, always in embedded Arial."""
    page.insert_text((x, y), text, fontsize=size, color=color,
                     fontname="ArialBold" if bold else "Arial",
                     fontfile=str(BOLD if bold else REGULAR))


def title_page(doc: fitz.Document, v: Volume, papers: int, partner: str) -> None:
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    y = 150.0
    put(page, MARGIN, y, BRAND, 13, True, MUTED); y += 26
    put(page, MARGIN, y, QUALIFICATION[v.level], 13, color=MUTED); y += 40
    put(page, MARGIN, y, v.subject, 30, True); y += 24
    put(page, MARGIN, y, f"({v.code})", 15, color=MUTED); y += 46
    put(page, MARGIN, y, SUB, 11.5); y += 20
    put(page, MARGIN, y, f"{v.title}{SEP}Volume {v.number} of {v.of}", 11.5, True); y += 34
    page.draw_line(fitz.Point(MARGIN, y), fitz.Point(PAGE_WIDTH - MARGIN, y), color=RULE, width=0.7)
    y += 26
    put(page, MARGIN, y, v.span, 13, True); y += 18
    put(page, MARGIN, y, f"{papers} papers, complete and in order", 10, color=MUTED); y += 30
    for line in partner.split("\n"):
        put(page, MARGIN, y, line, 9.5, color=MUTED)
        y += 14


def _contents_page(doc: fitz.Document, v: Volume, continued: bool) -> fitz.Page:
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    put(page, MARGIN, 96, "Contents" + (" (continued)" if continued else ""), 19, True)
    put(page, PAGE_WIDTH - MARGIN - width(v.title, 10), 96, v.title, 10, color=MUTED)
    page.draw_line(fitz.Point(MARGIN, 110), fitz.Point(PAGE_WIDTH - MARGIN, 110), color=RULE, width=0.7)
    return page


def contents_pages(doc: fitz.Document, entries: list[dict], v: Volume) -> None:
    """One row per paper: session, paper and item code, first page; grouped by year."""
    page = _contents_page(doc, v, False)
    y, year = CONTENTS_TOP, None
    for e in entries:
        need = CONTENTS_ROW + (YEAR_GAP + CONTENTS_ROW if e["year"] != year else 0)
        if y + need > CONTENTS_BOTTOM:
            page, y, year = _contents_page(doc, v, True), CONTENTS_TOP, None
        if e["year"] != year:
            year = e["year"]
            y += YEAR_GAP
            put(page, MARGIN, y, str(year), 12.5, True)
            y += CONTENTS_ROW
        put(page, MARGIN + 18, y, SEASON_LABEL[e["season"]], 10.5)
        put(page, MARGIN + 160, y, e["reference"], 9, color=MUTED)
        label = str(e["page"])
        put(page, PAGE_WIDTH - MARGIN - width(label, 10.5, True), y, label, 10.5, True)
        y += CONTENTS_ROW


def stamp_page_numbers(doc: fitz.Document, v: Volume) -> None:
    """Every sheet numbered (title page included -- the contents counts it)."""
    for number, page in enumerate(doc, 1):
        label = str(number)
        put(page, (PAGE_WIDTH - width(label, 9, True)) / 2, FOOTER_BASELINE, label, 9, True)
        put(page, MARGIN, FOOTER_BASELINE, v.running, 7.2, color=MUTED)


def section_page(doc: fitz.Document, heading: str, lines: list[str]) -> None:
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    put(page, MARGIN, 96, heading, 19, True)
    page.draw_line(fitz.Point(MARGIN, 110), fitz.Point(PAGE_WIDTH - MARGIN, 110), color=RULE, width=0.7)
    y = 140.0
    for line in lines:
        put(page, MARGIN, y, line, 10.5)
        y += 17


def header(page: fitz.Page, left: str, right: str) -> None:
    """Running head; the right side carries the cross-reference and may be long."""
    put(page, MARGIN, HEADER_BASELINE, left, 8.5, True)
    size = 8.5
    while width(right, size) > PAGE_WIDTH * 0.58 and size > 6:
        size -= 0.25
    put(page, PAGE_WIDTH - MARGIN - width(right, size), HEADER_BASELINE, right, size, color=MUTED)
    page.draw_line(fitz.Point(MARGIN, HEADER_BASELINE + 5),
                   fitz.Point(PAGE_WIDTH - MARGIN, HEADER_BASELINE + 5), color=RULE, width=0.5)


def place_exam(book: fitz.Document, src: fitz.Document, index: int, trim: fitz.Rect,
               left: str, right: str) -> None:
    """One exam sheet at 1:1 on A4, bleed trimmed, the board's strips painted out.
    `src` must come from clean_source()."""
    page = book.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.show_pdf_page(A4, src, index, clip=trim)
    clear_bands(page)
    header(page, left, right)


# Our site's upload stamps on every source PDF: "GradeMax" top right, the
# provenance line "Mathematics B · 2020 · Jan · Paper 1 · MS" and the older
# "4MB1 | 2019 | May/June | Paper 2 | GradeMax". Set in non-embedded base-14
# type -- the middot renders as a summation sign in some viewers. Exam sheets
# lose them under the painted bands; a scheme sheet has no bands, so they are
# redacted. Only these exact shapes: a "|" in an answer (|x|) is never touched.
STAMP_SPAN = re.compile(r"GradeMax|·.*\b(?:QP|MS)\b|\|\s*20\d\d\s*\|")


def _strip_ingest_stamps(page: fitz.Page) -> None:
    hit = False
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = "".join(s["text"] for s in line["spans"])
            if STAMP_SPAN.search(text):
                page.add_redact_annot(fitz.Rect(line["bbox"]), fill=None)
                hit = True
    if hit:
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                              graphics=fitz.PDF_REDACT_LINE_ART_NONE)


def clean_source(path: Path) -> fitz.Document:
    """
    A source paper or scheme, opened ONCE and readied for placing: our upload
    stamps redacted (visible on scheme sheets, hidden text under the painted
    strips on exam sheets) and any /Rotate baked in -- show_pdf_page clips a
    rotated page (Maths B Jan 2020 P1 lost its Question column).

    Done per DOCUMENT, never per page: placing each sheet through its own
    one-page copy stops PyMuPDF sharing fonts, images and metadata between
    sheets, and a 14MB volume came out at 128MB.
    """
    doc = fitz.open(path)
    for page in doc:
        if page.rotation:
            page.remove_rotation()
        _strip_ingest_stamps(page)
    return doc


def place_scheme(book: fitz.Document, src: fitz.Document, index: int, left: str, right: str) -> None:
    """A mark scheme sheet scaled whole above the footer; landscape turned a quarter.

    A source page carrying a /Rotate flag (Maths B Jan 2020 P1 is portrait
    MediaBox + /Rotate 90) loses its leftmost columns -- the QUESTION NUMBERS --
    through show_pdf_page; `src` must come from clean_source(), which bakes
    the rotation in.
    """
    box = src[index].rect
    page = book.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    top, limit = 30.0, PAGE_HEIGHT - FOOTER_BAND
    if box.width >= LANDSCAPE_MIN_WIDTH and box.width > box.height:
        scale = min(PAGE_WIDTH / box.height, (limit - top) / box.width)
        w, h = box.height * scale, box.width * scale
        page.show_pdf_page(fitz.Rect((PAGE_WIDTH - w) / 2, top, (PAGE_WIDTH + w) / 2, top + h),
                           src, index, rotate=270)
    else:
        scale = min(PAGE_WIDTH / box.width, (limit - top) / box.height)
        w, h = box.width * scale, box.height * scale
        page.show_pdf_page(fitz.Rect((PAGE_WIDTH - w) / 2, top, (PAGE_WIDTH + w) / 2, top + h),
                           src, index)
    page.draw_rect(fitz.Rect(0, 0, PAGE_WIDTH, top - 1), color=None, fill=(1, 1, 1))
    header(page, left, right)


def make_cover(path: Path, v: Volume, lockup: Path | None) -> None:
    """Typographic front + back cover carrying the GradeMax lockup (one image each)."""
    doc = fitz.open()
    front = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    front.draw_rect(front.rect, color=None, fill=INK)
    front.draw_rect(fitz.Rect(MARGIN, MARGIN, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - MARGIN),
                    color=(1, 1, 1), width=0.8)
    art = _white_lockup(lockup) if lockup and Path(lockup).exists() else None
    xref = 0
    if art:
        stream, aspect = art
        xref = front.insert_image(fitz.Rect(MARGIN + 32, 120, MARGIN + 200, 120 + 168 * aspect), stream=stream)
    pale = (0.78, 0.80, 0.86)
    y = 250.0
    for text, size, bold, color, gap in (
            (BRAND, 15, True, (1, 1, 1), 30), (QUALIFICATION[v.level], 12, False, pale, 58),
            (v.subject, 40, True, (1, 1, 1), 30), (f"({v.code})", 17, False, pale, 64),
            (SUB.upper(), 13, True, (1, 1, 1), 22), (f"{v.title}{SEP}Volume {v.number}", 13, False, pale, 44),
            (v.span, 12, False, pale, 0)):
        put(front, MARGIN + 32, y, text, size, bold, color)
        y += gap
    back = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    back.draw_rect(back.rect, color=None, fill=INK)
    if art:
        stream, aspect = art
        w = 120.0
        back.insert_image(fitz.Rect((PAGE_WIDTH - w) / 2, PAGE_HEIGHT / 2 - w * aspect / 2,
                                    (PAGE_WIDTH + w) / 2, PAGE_HEIGHT / 2 + w * aspect / 2),
                          stream=stream, xref=xref)
    put(back, MARGIN + 32, PAGE_HEIGHT - 120, BRAND, 13, True, (1, 1, 1))
    put(back, MARGIN + 32, PAGE_HEIGHT - 100,
        SEP.join([f"{v.subject} ({v.code})", f"{v.title} Volume {v.number}", v.span]), 9, False, pale)
    doc.save(path, garbage=3, deflate=True)
    doc.close()
