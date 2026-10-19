"""
The last look at a workbook before it goes to the press.

This is deliberately NOT the same audit as the per-edition ones. Those check
that the book the builder produced says what the builder meant it to say. This
one checks the FILE THAT LEAVES THE BUILDING: the covers are on it, the covers
pushed every printed page down by one sheet and the contents still find their
targets, and the things a print shop will hand back are not in it.

The navigation checks are re-run rather than trusted, because adding two sheets
to the front of a book is exactly the operation that silently breaks them. The
per-subject parsers are passed in, so this module never learns the difference
between the two books.

WHAT THE PRESS-READINESS SECTION IS LOOKING FOR

  fonts     A face the file names but does not carry is a face the RIP will
            substitute. Times New Roman and Arial are on every RIP; Arial
            Narrow, Verdana and Trebuchet are not, and Arial Narrow substituted
            by Arial is WIDER, which is how a mark scheme table overflows its
            cell between the proof and the run.
  detail    Below about 200dpi a scanned exam sheet prints visibly soft. This
            reports what is there rather than fixing it -- the resolution was
            lost when the paper was scanned, long before this book.
  geometry  One page size, no rotation, and a CropBox that matches the
            MediaBox. A stray box is what makes a shop ring up to ask.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from pathlib import Path

import fitz

# Faces every RIP resolves without being given them: the PDF base-14, plus the
# two families that ship with essentially every press workflow.
SAFE_UNEMBEDDED = {
    "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique",
    "Courier", "Courier-Bold", "Courier-Oblique", "Symbol", "ZapfDingbats",
    "Times-Roman", "Times-Bold", "Times-Italic", "Times-BoldItalic",
}
COMMON_FAMILIES = ("TimesNewRoman", "Times New Roman", "Arial", "ArialMT",
                   "CourierNew")

SOFT_DPI = 200
WATERMARK_PX = (1729, 519)
PAGE_WIDTH, PAGE_HEIGHT = 595.0, 842.0


def _is_common(basefont: str) -> bool:
    name = basefont.split("+")[-1]
    if name in SAFE_UNEMBEDDED:
        return True
    return (any(name.startswith(f) for f in COMMON_FAMILIES)
            and "Narrow" not in name)


def navigation(book: fitz.Document, questions: list[dict], offset: int,
               contents_rows, footer_of, index_check) -> list[str]:
    """
    Re-run the book's own navigation promises against the finished file.

    `offset` is how many sheets the front cover added, so printed page N lives
    at index N - 1 + offset.
    """
    problems: list[str] = []
    last = book.page_count - offset  # last printed page

    def sheet(printed: int) -> fitz.Page | None:
        index = printed - 1 + offset
        return book[index] if 0 <= index < book.page_count else None

    # 1. every printed page carries its own number ------------------------
    missing = []
    for printed in range(1, last):
        page = sheet(printed)
        if page is None:
            continue
        band = fitz.Rect(page.rect.width * 0.35, page.rect.height - 40,
                         page.rect.width * 0.65, page.rect.height)
        if str(printed) not in page.get_text("text", clip=band).split():
            missing.append(printed)
    if missing:
        problems.append(f"{len(missing)} sheets do not carry their printed page "
                        f"number: {missing[:10]}")

    # 2 & 3. the contents still land where they point ---------------------
    # The parser is handed the INTERIOR's front matter, not the book's. Run it
    # over the whole file and it reads the front cover first, where the design
    # sets its chapter list letter-spaced -- "0 1  A R E A  U N D E R..." parses
    # as a contents row for chapter 0, and the audit fails on the cover being a
    # cover.
    front = fitz.open()
    front.insert_pdf(book, from_page=offset,
                     to_page=min(offset + 24, book.page_count - 1))
    chapters, sections = contents_rows(front)
    front.close()
    if not chapters:
        problems.append("no chapter rows found in the contents -- the parser "
                        "did not recognise the front matter")
    for number, _title, target in chapters:
        page = sheet(target)
        if page is None:
            problems.append(f"contents: chapter {number} -> page {target} is "
                            f"out of range")
        elif f"Chapter {number}" not in page.get_text():
            problems.append(f"contents: chapter {number} -> page {target} is "
                            f"not that chapter's front page")
    for label, _title, target in sections:
        page = sheet(target)
        if page is None:
            problems.append(f"contents: section {label} -> page {target} is "
                            f"out of range")
        elif label not in page.get_text() and label not in footer_of(page):
            problems.append(f"contents: section {label} -> page {target} does "
                            f"not name that section")

    # 4. the index still finds its questions -------------------------------
    wrong = []
    for question in questions:
        page = sheet(question["workbook_page"])
        if page is None:
            wrong.append(f"{question['slug']} -> page "
                         f"{question['workbook_page']} out of range")
            continue
        complaint = index_check(question, page, footer_of)
        if complaint:
            wrong.append(complaint)
    if wrong:
        problems.append(f"{len(wrong)} index references do not land: {wrong[:6]}")

    # 5. numbering restarts at 1 in every section --------------------------
    by_section = defaultdict(list)
    for question in questions:
        by_section[question["section"]].append(question["printed_number"])
    broken = [s for s, nums in by_section.items()
              if sorted(nums) != list(range(1, len(nums) + 1))]
    if broken:
        problems.append(f"{len(broken)} sections are not numbered 1..N: "
                        f"{broken[:6]}")

    return problems


def furniture(book: fitz.Document, mark, cover_tokens: tuple[str, str]) -> list[str]:
    """
    The covers and the watermark, checked on the SHIPPED file alone.

    The finishing step already proves these against the interior it was built
    from. This proves them again from nothing but the file that goes to the
    printer, because that is the artefact, and a correct build followed by a
    bad copy is a thing that happens.
    """
    problems: list[str] = []
    if book.page_count < 3:
        return [f"only {book.page_count} sheets -- not a finished book"]

    front_token, back_token = cover_tokens
    front = " ".join(book[0].get_text().split())
    back = " ".join(book[book.page_count - 1].get_text().split())
    if front_token not in front:
        problems.append(f"sheet 1 is not the front cover (no {front_token!r})")
    if back_token not in back:
        problems.append(f"last sheet is not the back cover (no {back_token!r})")
    # Bound the wrong way round is the failure this catches: both covers carry
    # the publisher's name, so only the front/back-specific tokens separate them.
    if back_token in front or front_token in back:
        problems.append("front and back cover text is crossed over -- check the "
                        "covers are not bound the wrong way round")

    for label, index in (("front", 0), ("back", book.page_count - 1)):
        if len(book[index].get_images(full=True)) != 1:
            problems.append(f"{label} cover carries "
                            f"{len(book[index].get_images(full=True))} images, "
                            f"expected 1 -- the watermark may have leaked onto it")

    target = mark.rect_on(fitz.Rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT))
    unmarked, misplaced, xrefs = [], [], set()
    for sheet in range(1, book.page_count - 1):
        page = book[sheet]
        found = None
        for info in page.get_images(full=True):
            for rect in page.get_image_rects(info[0]):
                if (abs(rect.width - target.width) < 1.0
                        and abs(rect.height - target.height) < 1.0):
                    found = (info[0], rect)
                    break
            if found:
                break
        if found is None:
            unmarked.append(sheet)
            continue
        xrefs.add(found[0])
        if (abs(found[1].x0 - target.x0) > 1.0
                or abs(found[1].y0 - target.y0) > 1.0):
            misplaced.append(sheet)
    if unmarked:
        problems.append(f"{len(unmarked)} interior sheets carry no watermark: "
                        f"{unmarked[:8]}")
    if misplaced:
        problems.append(f"{len(misplaced)} watermarks are off centre: "
                        f"{misplaced[:8]}")
    if len(xrefs) > 1:
        problems.append(f"the watermark is embedded {len(xrefs)} times instead "
                        f"of once -- duplicate copies of the artwork")
    return problems


def press_readiness(book: fitz.Document, offset: int) -> dict:
    """Measure the things a print shop reacts to. Reports; fixes nothing."""
    substituted: dict[str, set[int]] = defaultdict(set)
    risky: dict[str, set[int]] = defaultdict(set)
    dpis: list[float] = []
    soft: dict[int, list[int]] = defaultdict(list)
    sizes: set[tuple[int, int]] = set()
    rotated: list[int] = []
    cropped: list[int] = []

    for index in range(book.page_count):
        page = book[index]
        printed = index - offset + 1
        sizes.add((round(page.rect.width), round(page.rect.height)))
        if page.rotation:
            rotated.append(printed)
        if not page.cropbox.__eq__(page.mediabox):
            cropped.append(printed)

        # Only fonts the page actually DRAWS WITH count. A Word export declares
        # every font the source document mentioned in the page's resource
        # dictionary whether or not a glyph was ever set in it, and reporting
        # those as substitution risk sends a print shop hunting for a licence to
        # a face that never marks the paper. Verdana and Trebuchet in these
        # mark schemes are exactly that: declared on hundreds of pages, drawn
        # with on none.
        drawn = {span["font"].split("+")[-1]
                 for block in page.get_text("dict")["blocks"]
                 for line in block.get("lines", [])
                 for span in line["spans"] if span["text"].strip()}
        for font in page.get_fonts(full=True):
            embedded, basefont = font[1] not in ("n/a", ""), font[3]
            if embedded:
                continue
            name = basefont.split("+")[-1]
            if name not in drawn:
                continue
            substituted[name].add(printed)
            if not _is_common(basefont):
                risky[name].add(printed)

        seen = set()
        for info in page.get_images(full=True):
            xref, width, height = info[0], info[2], info[3]
            if (width, height) == WATERMARK_PX or width * height < 40_000:
                continue
            if xref in seen:
                continue
            seen.add(xref)
            rects = page.get_image_rects(xref)
            if not rects:
                continue
            box = max(rects, key=lambda r: r.get_area())
            if box.width <= 1 or box.height <= 1:
                continue
            # The page may be turned a quarter turn, in which case the image's
            # pixel WIDTH is spread over the rectangle's HEIGHT. Measuring only
            # the upright pairing reported a 300dpi mark scheme as 24dpi and
            # buried the genuinely soft pages in false alarms, so both pairings
            # are measured and the sane one wins.
            upright = min(width / (box.width / 72.0), height / (box.height / 72.0))
            turned = min(width / (box.height / 72.0), height / (box.width / 72.0))
            dpi = max(upright, turned)
            dpis.append(dpi)
            if dpi < SOFT_DPI:
                soft[round(dpi / 12) * 12].append(printed)

    return {
        "substituted": {k: sorted(v) for k, v in substituted.items()},
        "risky": {k: sorted(v) for k, v in risky.items()},
        "dpi": (min(dpis), statistics.median(dpis), max(dpis)) if dpis else None,
        "soft": {k: sorted(set(v)) for k, v in soft.items()},
        "sizes": sorted(sizes),
        "rotated": rotated,
        "cropped": cropped,
        "encrypted": book.is_encrypted,
    }


def report(title: str, path: Path, problems: list[str], press: dict,
           sheets: int = 0, physical: list[str] | None = None) -> int:
    """Print one volume's final audit. Returns the count of hard problems."""
    print(f"\n{'=' * 74}")
    print(f"  {title}")
    print(f"  {path.name}  —  {sheets} sheets, "
          f"{path.stat().st_size / 1_048_576:.1f} MB")
    print(f"{'=' * 74}")

    print("  COVERS AND WATERMARK")
    if physical:
        for problem in physical:
            print(f"     FAIL  {problem}")
    else:
        print("     ok    front cover on sheet 1, back cover last, neither "
              "watermarked;")
        print(f"           all {max(0, sheets - 2)} interior sheets watermarked, "
              "art embedded once")

    print("  NAVIGATION")
    if problems:
        for problem in problems:
            print(f"     FAIL  {problem}")
    else:
        print("     ok    page numbers, contents, sections and index all land")

    print("  PRESS READINESS")
    sizes = press["sizes"]
    if len(sizes) == 1:
        print(f"     ok    one page size throughout: {sizes[0][0]}x{sizes[0][1]}pt (A4)")
    else:
        print(f"     WARN  mixed page sizes: {sizes}")
    for label, pages in (("rotated pages", press["rotated"]),
                         ("CropBox differs from MediaBox", press["cropped"])):
        if pages:
            print(f"     WARN  {len(pages)} {label}: {pages[:8]}")
    if press["encrypted"]:
        print("     WARN  file is encrypted")

    risky = press["risky"]
    substituted = press["substituted"]
    if risky:
        total = sorted({p for pages in risky.values() for p in pages})
        print(f"     WARN  {len(risky)} uncommon fonts are NOT embedded, on "
              f"{len(total)} pages -- the RIP will substitute:")
        for name, pages in sorted(risky.items(), key=lambda kv: -len(kv[1])):
            print(f"             {name:<32} {len(pages)} pages")
    common = {k: v for k, v in substituted.items() if k not in risky}
    if common:
        pages = sorted({p for v in common.values() for p in v})
        print(f"     note  {len(common)} common faces also unembedded "
              f"({len(pages)} pages) -- Times/Arial/base-14, safe on any RIP")
    if not substituted:
        print("     ok    every font embedded")

    if press["dpi"]:
        low, mid, high = press["dpi"]
        print(f"     {'ok   ' if mid >= 250 else 'note '} image detail: "
              f"median {mid:.0f} dpi (range {low:.0f}-{high:.0f})")
        for band in sorted(press["soft"]):
            pages = press["soft"][band]
            print(f"             ~{band} dpi on {len(pages)} pages: {pages[:8]}")
    else:
        print("     ok    no raster images -- pages are vector text")

    return len(problems) + len(physical or [])
