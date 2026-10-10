"""
The furniture of a yearwise workbook: covers, title page, contents, and the
header and footer that go on every sheet. Shared by M1, S1 and P4.

WHY THE EXAM SHEET GETS A NEW HEADER AND FOOTER

The board's own strips cannot stay. At the foot of every page sit the item
barcode, the printed page number and, on the 2017-2019 papers, the footer the
scraper left behind; a book that reprints them tells the reader they are on
page 3 when they are on page 47, and carries a second set of numbers that
disagree with the contents. At the head sits our ingest stamp, which differs
between the two archives the papers come from -- the 2020+ files carry a
provenance line the older ones do not -- so leaving it makes the book look like
two books.

Both strips are paintable because Edexcel draws a frame round the live area of
every page and nothing of the question ever leaves it. Measured over all 46
papers of the three units, and re-measured per unit rather than assumed to
carry over: every page is 595x842, the frame's top edge never sits above
y=36.5 and its bottom edge never below y=791.1, while the barcode never starts
above y=799.4. So a band of 34pt at the head and 46pt at the foot removes every
piece of furniture and does not touch the frame, let alone the question.

The mark schemes get no bands. They are not framed, their content starts at
x=14, and a strip taken off the foot of one would cut into the table.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import fitz

from .workbook_layout import INK, MARGIN, MUTED, PAGE_HEIGHT, PAGE_WIDTH, RULE

BRAND = "GradeMax"
SUBJECT_TITLE = "Edexcel International Advanced Level"
SUBJECT_SUB = "Yearwise Practice Workbook"

# The bands described above.
HEADER_BAND = 34.0
FOOTER_BAND = 46.0
# Where our own lines sit inside them.
HEADER_BASELINE = 22.0
FOOTER_BASELINE = PAGE_HEIGHT - 18.0

CONTENTS_TOP = 132.0
CONTENTS_BOTTOM = PAGE_HEIGHT - 76.0
CONTENTS_ROW = 19.0
CONTENTS_SUBROW = 13.0
YEAR_GAP = 10.0

SEASON_LABEL = {"Jan": "January", "May-Jun": "May/June", "Oct-Nov": "October/November"}
SEASON_SHORT = {"Jan": "Jan", "May-Jun": "Jun", "Oct-Nov": "Oct"}


@dataclass(frozen=True)
class Book:
    """The unit a book is for, as the book prints it."""
    name: str            # Mechanics M1
    code: str            # WME01
    slug: str            # m1
    token: str           # M1, as the archive and the provenance line write it


@dataclass(frozen=True)
class Volume:
    """Which of a unit's two books is being built."""
    book: Book
    kind: str            # questions | markschemes

    @property
    def is_questions(self) -> bool:
        return self.kind == "questions"

    @property
    def title(self) -> str:
        return "Question Papers" if self.is_questions else "Mark Schemes"

    @property
    def running(self) -> str:
        tail = "" if self.is_questions else "  ·  Mark Schemes"
        return f"{BRAND}  ·  {self.book.name} ({self.book.code}){tail}"


def volumes(book: Book) -> tuple[Volume, Volume]:
    return Volume(book, "questions"), Volume(book, "markschemes")


def session_label(year: int, season: str) -> str:
    return f"{SEASON_LABEL[season]} {year}"


def clear_bands(page: fitz.Page) -> None:
    """Paint out the board's header and footer strips on a reprinted exam sheet."""
    page.draw_rect(fitz.Rect(0, 0, PAGE_WIDTH, HEADER_BAND), color=None, fill=(1, 1, 1))
    page.draw_rect(fitz.Rect(0, PAGE_HEIGHT - FOOTER_BAND, PAGE_WIDTH, PAGE_HEIGHT),
                   color=None, fill=(1, 1, 1))


def running_header(page: fitz.Page, left: str, right: str) -> None:
    page.insert_text((MARGIN, HEADER_BASELINE), left,
                     fontname="hebo", fontsize=8.5, color=INK)
    width = fitz.get_text_length(right, fontname="helv", fontsize=8.5)
    page.insert_text((PAGE_WIDTH - MARGIN - width, HEADER_BASELINE), right,
                     fontname="helv", fontsize=8.5, color=MUTED)
    page.draw_line(fitz.Point(MARGIN, HEADER_BASELINE + 5),
                   fitz.Point(PAGE_WIDTH - MARGIN, HEADER_BASELINE + 5),
                   color=RULE, width=0.5)


def stamp_page_numbers(doc: fitz.Document, volume: Volume) -> None:
    """
    Number every sheet, so the contents can be trusted and a reader can be told
    "turn to page 148" without qualification.

    EVERY sheet, including the title page. Leaving the title page unnumbered is
    the usual convention in trade publishing and it is the wrong one here: the
    contents counts that sheet, and the series' own press check requires each
    sheet to carry the number the contents would send a reader to. An unnumbered
    title page fails it, and rightly -- a book whose numbering starts on page 2
    is a book whose page 1 cannot be cited.
    """
    for number, page in enumerate(doc, 1):
        label = str(number)
        width = fitz.get_text_length(label, fontname="hebo", fontsize=9)
        page.insert_text(((PAGE_WIDTH - width) / 2, FOOTER_BASELINE), label,
                         fontname="hebo", fontsize=9, color=INK)
        page.insert_text((MARGIN, FOOTER_BASELINE), volume.running,
                         fontname="helv", fontsize=7.2, color=MUTED)


def title_page(doc: fitz.Document, volume: Volume, span: str, papers: int) -> None:
    book = volume.book
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    y = 150.0
    page.insert_text((MARGIN, y), BRAND, fontname="hebo", fontsize=13, color=MUTED)
    y += 26
    page.insert_text((MARGIN, y), SUBJECT_TITLE, fontname="helv", fontsize=13, color=MUTED)
    y += 40
    page.insert_text((MARGIN, y), book.name, fontname="hebo", fontsize=30, color=INK)
    y += 24
    page.insert_text((MARGIN, y), f"({book.code}/01)", fontname="helv",
                     fontsize=15, color=MUTED)
    y += 46
    page.insert_text((MARGIN, y), SUBJECT_SUB, fontname="helv", fontsize=11.5, color=INK)
    y += 20
    page.insert_text((MARGIN, y), volume.title, fontname="hebo", fontsize=11.5, color=INK)
    y += 34
    page.draw_line(fitz.Point(MARGIN, y), fitz.Point(PAGE_WIDTH - MARGIN, y),
                   color=RULE, width=0.7)
    y += 26
    page.insert_text((MARGIN, y), span, fontname="hebo", fontsize=13, color=INK)
    y += 18
    page.insert_text((MARGIN, y), f"{papers} past papers, complete and in order",
                     fontname="helv", fontsize=10, color=MUTED)


def contents_pages(doc: fitz.Document, entries: list[dict], volume: Volume,
                   offset: int) -> None:
    """
    The contents, grouped by year.

    One row per sitting: the session, its paper reference, and the page it
    starts on. Nothing finer. An earlier edition also printed every question's
    page under each session (`Q1 5  Q2 8  Q3 10 …`); it made the contents twice
    as long and buried the thing a reader actually comes here for, which is
    where a given year and session begins. The per-question page map is still
    recorded in `print_index.json`, where the audit checks it.

    `offset` is how many sheets stand in front of the body -- the title page and
    the contents itself. The contents has to count its OWN length, which is why
    the caller builds it twice: the first pass finds the length, the second
    writes the page numbers that length implies.
    """
    page = _new_contents_page(doc, volume)
    y = CONTENTS_TOP
    year = None

    for entry in entries:
        need = CONTENTS_ROW + (CONTENTS_SUBROW if entry.get("note") else 0) \
            + (YEAR_GAP if entry["year"] != year else 0)
        if y + need > CONTENTS_BOTTOM:
            page = _new_contents_page(doc, volume, continued=True)
            y, year = CONTENTS_TOP, None

        if entry["year"] != year:
            year = entry["year"]
            y += YEAR_GAP
            page.insert_text((MARGIN, y), str(year), fontname="hebo",
                             fontsize=12.5, color=INK)
            y += CONTENTS_ROW

        page.insert_text((MARGIN + 18, y), SEASON_LABEL[entry["season"]],
                         fontname="helv", fontsize=10.5, color=INK)
        page.insert_text((MARGIN + 160, y), entry["reference"],
                         fontname="helv", fontsize=9, color=MUTED)
        label = str(entry["page"] + offset)
        width = fitz.get_text_length(label, fontname="hebo", fontsize=10.5)
        page.insert_text((PAGE_WIDTH - MARGIN - width, y), label,
                         fontname="hebo", fontsize=10.5, color=INK)
        y += CONTENTS_ROW

        if entry.get("note"):
            page.insert_text((MARGIN + 18, y - 6), entry["note"],
                             fontname="helv", fontsize=7.6, color=MUTED)
            y += CONTENTS_SUBROW


def _new_contents_page(doc: fitz.Document, volume: Volume,
                       continued: bool = False) -> fitz.Page:
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    heading = "Contents" + (" (continued)" if continued else "")
    page.insert_text((MARGIN, 96), heading, fontname="hebo", fontsize=19, color=INK)
    width = fitz.get_text_length(volume.title, fontname="helv", fontsize=10)
    page.insert_text((PAGE_WIDTH - MARGIN - width, 96), volume.title,
                     fontname="helv", fontsize=10, color=MUTED)
    page.draw_line(fitz.Point(MARGIN, 110), fitz.Point(PAGE_WIDTH - MARGIN, 110),
                   color=RULE, width=0.7)
    return page


def make_cover(path, volume: Volume, span: str, lockup: Path | None = None) -> None:
    """
    A plain two-page cover, front and back, in the book's own type.

    The other workbooks are wrapped in commissioned artwork; there is none for
    M1, and `workbook_finish.assemble` requires a two-page cover document, so
    the book gets a typographic one built from the same constants as its
    interior. Drop a designed cover in its place and the rest of the finishing
    step is unchanged.

    `lockup` is the GradeMax artwork, placed white on the dark ground. It is on
    the cover because a cover should carry the mark, and it also satisfies the
    series' press check, which counts exactly one image on each cover -- the
    artwork alone, so that a watermark leaking onto the cover is caught as a
    second one. A cover set purely in type carries none and fails that check for
    a reason that is not a defect, which would leave the check permanently red
    and therefore worthless.
    """
    book = volume.book
    doc = fitz.open()
    front = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    front.draw_rect(front.rect, color=None, fill=INK)
    front.draw_rect(fitz.Rect(MARGIN, MARGIN, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - MARGIN),
                    color=(1, 1, 1), width=0.8)

    art = _white_lockup(lockup) if lockup else None
    xref = 0
    if art is not None:
        stream, aspect = art
        width = 168.0
        rect = fitz.Rect(MARGIN + 32, 120, MARGIN + 32 + width, 120 + width * aspect)
        xref = front.insert_image(rect, stream=stream)

    y = 250.0
    front.insert_text((MARGIN + 32, y), BRAND, fontname="hebo", fontsize=15,
                      color=(1, 1, 1))
    y += 30
    front.insert_text((MARGIN + 32, y), SUBJECT_TITLE, fontname="helv", fontsize=12,
                      color=(0.78, 0.80, 0.86))
    y += 58
    front.insert_text((MARGIN + 32, y), book.name, fontname="hebo", fontsize=40,
                      color=(1, 1, 1))
    y += 30
    front.insert_text((MARGIN + 32, y), f"({book.code}/01)", fontname="helv",
                      fontsize=17, color=(0.78, 0.80, 0.86))
    y += 64
    front.insert_text((MARGIN + 32, y), SUBJECT_SUB.upper(), fontname="hebo",
                      fontsize=13, color=(1, 1, 1))
    y += 22
    front.insert_text((MARGIN + 32, y), volume.title, fontname="helv", fontsize=13,
                      color=(0.78, 0.80, 0.86))
    y += 44
    front.insert_text((MARGIN + 32, y), span, fontname="helv", fontsize=12,
                      color=(0.78, 0.80, 0.86))

    back = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    back.draw_rect(back.rect, color=None, fill=INK)
    if art is not None:
        stream, aspect = art
        width = 120.0
        rect = fitz.Rect((PAGE_WIDTH - width) / 2, PAGE_HEIGHT / 2 - width * aspect / 2,
                         (PAGE_WIDTH + width) / 2, PAGE_HEIGHT / 2 + width * aspect / 2)
        back.insert_image(rect, stream=stream, xref=xref)
    back.insert_text((MARGIN + 32, PAGE_HEIGHT - 120), BRAND,
                     fontname="hebo", fontsize=13, color=(1, 1, 1))
    back.insert_text((MARGIN + 32, PAGE_HEIGHT - 100),
                     f"{book.name} ({book.code}/01)  ·  {span}",
                     fontname="helv", fontsize=9, color=(0.78, 0.80, 0.86))
    doc.save(path)
    doc.close()


def _white_lockup(path: Path) -> tuple[bytes, float] | None:
    """
    The GradeMax artwork as white glyphs, for the dark cover.

    The supplied PNG is 5184x1072 with the lockup on a 1729x519 island in the
    middle, so it is cropped to its own ink first -- without that, "168pt wide"
    would be sizing the empty margin and the mark would come out a third of the
    intended size. The colour is then taken to pure white while the alpha keeps
    the shape, which is the same trick the watermark uses in the other
    direction: the tone lives in the pixels, not in a soft mask a RIP may skip.
    """
    try:
        from PIL import Image
    except ImportError:
        return None
    if not Path(path).exists():
        return None

    art = Image.open(path).convert("RGBA")
    box = art.split()[3].getbbox()
    if box is None:
        return None
    art = art.crop(box)
    alpha = art.split()[3]
    white = Image.new("RGB", art.size, "white")
    white.putalpha(alpha)

    buffer = io.BytesIO()
    white.save(buffer, "PNG", optimize=True)
    return buffer.getvalue(), art.height / art.width
