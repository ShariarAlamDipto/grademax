"""
The official formula sheet for an IAL Mathematics unit, for the front of a book.

Source: Pearson Edexcel IAS/IAL Mathematics, Further Mathematics and Pure
Mathematics -- Mathematical Formulae and Statistical Tables, Issue 2 (January
2021), the booklet candidates are given in the exam. Downloaded from Pearson's
own catalogue (qualifications.pearson.com, found through its Algolia index):

    data/workbook/ial_formulae/IAL-Mathematics-Formula-Book.pdf

WHAT EACH UNIT GETS

The booklet is arranged by unit, and each unit's section says which earlier
sections a candidate may also need ("Candidates sitting S1 may also require
those formulae listed under Pure Mathematics P1 and P2"). A book carries its
own unit's section first, then exactly the sections that note names -- the
same pages the candidate has on the desk, nothing invented.

    P1  P1                      P2  P2, P1
    P3  P3, P1, P2              P4  P4, P1, P2, P3
    S1  S1 (with the Normal tables), P1, P2
    M1  M1, P1, P2              (the booklet gives no M1 formulae of its own)

HOW IT IS SET

Sections are cut from the booklet by their printed headings and laid onto A4
sheets at 1:1 (the booklet is A4 too), stacked while they fit. The booklet's
own footer is left out because it carries the booklet's page number, which
would contradict the book's; a credit line takes its place on every sheet.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz

from .workbook_layout import MUTED, PAGE_HEIGHT, PAGE_WIDTH

ROOT = Path(__file__).resolve().parents[2]
BOOKLET = ROOT / "data" / "workbook" / "ial_formulae" / "IAL-Mathematics-Formula-Book.pdf"

CREDIT = ("Pearson Edexcel IAS/IAL Mathematics - Mathematical Formulae and Statistical "
          "Tables, Issue 2 (January 2021)  ·  © Pearson Education Limited 2021")

# Where the booklet sets its content: below the top margin, above its footer.
CONTENT_TOP = 40.0
CONTENT_BOTTOM = 785.0
# Room kept on a book sheet for the credit line and the book's page number.
SHEET_TOP = 40.0
SHEET_BOTTOM = PAGE_HEIGHT - 50.0
GAP = 14.0
LEAD = 10.0  # space kept above a heading so its rule and padding survive


@dataclass(frozen=True)
class Cut:
    page: int                # 0-based booklet page
    start: str | None        # heading the cut opens at (None: top of content)
    stop: str | None         # heading the cut ends before (None: foot of content)


# Each unit's section, by the headings the booklet prints. P3 and S1 run over
# more than one booklet page, so they are several cuts.
SECTIONS: dict[str, list[Cut]] = {
    "P1": [Cut(8, "Pure Mathematics P1", "Pure Mathematics P2")],
    "P2": [Cut(8, "Pure Mathematics P2", None)],
    "P3": [Cut(9, "Pure Mathematics P3", None), Cut(10, None, "Pure Mathematics P4")],
    "P4": [Cut(10, "Pure Mathematics P4", None)],
    "M1": [Cut(18, "Mechanics M1", "Mechanics M2")],
    "S1": [Cut(19, "Statistics S1", None), Cut(20, None, None),
           Cut(21, None, None), Cut(22, None, None)],
}

# A unit's own section first, then the ones its section says it may need.
UNITS: dict[str, list[str]] = {
    "P1": ["P1"],
    "P2": ["P2", "P1"],
    "P3": ["P3", "P1", "P2"],
    "P4": ["P4", "P1", "P2", "P3"],
    "S1": ["S1", "P1", "P2"],
    "M1": ["M1", "P1", "P2"],
}


def _heading_top(page: fitz.Page, heading: str) -> float:
    """The top of a printed heading; the heading must be on the page."""
    hits = page.search_for(heading)
    if not hits:
        raise ValueError(f"heading {heading!r} not on booklet page {page.number + 1}")
    return min(hit.y0 for hit in hits)


def _clip(booklet: fitz.Document, cut: Cut) -> fitz.Rect:
    page = booklet[cut.page]
    top = CONTENT_TOP if cut.start is None else _heading_top(page, cut.start) - LEAD
    bottom = CONTENT_BOTTOM if cut.stop is None else _heading_top(page, cut.stop) - LEAD
    # Trim the clip to the ink inside it, so a short section does not carry a
    # page's worth of white below it onto the sheet.
    ink = [fitz.Rect(b[:4]) for b in page.get_text("blocks")
           if b[1] >= top - 1 and b[3] <= bottom + 1]
    ink += [d["rect"] for d in page.get_drawings()
            if d["rect"].y0 >= top - 1 and d["rect"].y1 <= bottom + 1]
    if ink:
        bottom = min(bottom, max(r.y1 for r in ink) + 6.0)
    return fitz.Rect(page.rect.x0, top, page.rect.x1, bottom)


def formula_pages(unit: str) -> fitz.Document:
    """The unit's formula sheet as finished A4 sheets, ready for a book's front."""
    if unit.upper() not in UNITS:
        raise KeyError(f"no formula sheet defined for {unit!r}")
    if not BOOKLET.is_file():
        raise FileNotFoundError(f"formula booklet missing: {BOOKLET}")
    booklet = fitz.open(BOOKLET)
    cuts = [(cut, _clip(booklet, cut)) for name in UNITS[unit.upper()]
            for cut in SECTIONS[name]]

    out = fitz.open()
    sheet, y = None, SHEET_BOTTOM
    for cut, clip in cuts:
        if sheet is None or y + clip.height > SHEET_BOTTOM:
            sheet, y = _new_sheet(out), SHEET_TOP
        target = fitz.Rect(0, y, PAGE_WIDTH, y + clip.height)
        sheet.show_pdf_page(target, booklet, cut.page, clip=clip)
        y += clip.height + GAP
    booklet.close()
    return out


def _new_sheet(doc: fitz.Document) -> fitz.Page:
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    size = 6.8
    width = fitz.get_text_length(CREDIT, fontname="helv", fontsize=size)
    page.insert_text(((PAGE_WIDTH - width) / 2, PAGE_HEIGHT - 34), CREDIT,
                     fontname="helv", fontsize=size, color=MUTED)
    return page
