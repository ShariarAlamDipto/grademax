"""
Turn a built workbook interior into the file that goes to the printer.

Three things happen here and nothing else: the front cover is put in front, the
back cover is put behind, and every sheet between them is watermarked. The
interior is not re-laid-out, not re-paginated and not re-compressed -- it is
copied through object for object, so a book that audited clean before this step
audits clean after it.

WHY THE WATERMARK IS BUILT THE WAY IT IS

The obvious way to draw a 10% watermark is to keep the artwork black and put the
10% in the alpha channel. That renders correctly in every PDF viewer and fails
catastrophically on the print floor: a RIP that ignores the soft mask paints
solid black over the question. So the opacity is composited into the COLOUR
instead -- the glyphs are stored as light grey on white, and the alpha channel
carries only the shape. The two failure modes are then:

    soft mask honoured  -> light grey glyphs, nothing else            (intended)
    soft mask ignored   -> light grey glyphs on a WHITE box           (harmless)

On white stock the second one is very nearly the first, which is the property
worth paying for when the file is leaving the building.

SIZE AND POSITION

The mark is centred, horizontal, and 55% of the page wide. Centred is the only
placement that cannot be cropped off, horizontal keeps it from cutting across
the ruled answer lines at an angle, and 55% is wide enough to read and far too
faint to write around -- measured against real question sheets from both books,
not chosen from a style guide.

It is drawn UNDER the page, not over it. That only works because neither book's
sheets paint an opaque white ground -- the reproduced exam pages are placed as
form XObjects that mark only where there is ink -- so an underlay still shows
through. The gain is that the question text, the ruled answer lines and the
board's furniture all stay crisp and unmixed, which is what a watermark should
never cost. Verified by rendering both books before changing it; if a future
edition starts painting its own background, the mark will vanish and this is the
first place to look.
"""

from __future__ import annotations

import io
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import fitz
from PIL import Image

# A4 at 1:1. Both books' interiors are already built to this; the covers are
# 595.92 x 841.92 and get normalised onto it.
PAGE_WIDTH = 595.0
PAGE_HEIGHT = 842.0

# The measured settings. See the module docstring for how they were arrived at.
WIDTH_FRACTION = 0.55
OPACITY = 0.10

# How far a page's size may drift from A4 before it is worth reporting.
SIZE_TOLERANCE = 1.5


@dataclass(frozen=True)
class Watermark:
    """The artwork, cropped to its ink and lightened, ready to embed once."""

    stream: bytes
    width_px: int
    height_px: int

    @property
    def aspect(self) -> float:
        return self.height_px / self.width_px

    def rect_on(self, page_rect: fitz.Rect) -> fitz.Rect:
        """Centred, WIDTH_FRACTION of the page wide, aspect preserved."""
        width = page_rect.width * WIDTH_FRACTION
        height = width * self.aspect
        x = (page_rect.width - width) / 2
        y = (page_rect.height - height) / 2
        return fitz.Rect(x, y, x + width, y + height)


def load_watermark(path: Path, opacity: float = OPACITY) -> Watermark:
    """
    Read the artwork, crop away its transparent margin, and lighten it.

    The supplied PNG is 5184x1072 with the lockup occupying a 1729x519 island in
    the middle. Cropping to the ink is what makes the placement below mean what
    it says -- without it, "55% of the page wide" would size the empty margin and
    the mark itself would come out a third of the intended size.
    """
    art = Image.open(path).convert("RGBA")
    box = art.split()[3].getbbox()
    if box is None:
        raise ValueError(f"watermark is fully transparent: {path}")
    art = art.crop(box)

    alpha = art.split()[3]
    # Flatten onto white to get the artwork's own colour, then mix that colour
    # back towards white by (1 - opacity). This is the step described in the
    # module docstring: the opacity ends up in the ink, not in the mask.
    on_white = Image.alpha_composite(Image.new("RGBA", art.size, "white"), art)
    lightened = Image.blend(Image.new("RGB", art.size, "white"),
                            on_white.convert("RGB"), opacity)
    lightened.putalpha(alpha)

    buffer = io.BytesIO()
    lightened.save(buffer, "PNG", optimize=True)
    return Watermark(buffer.getvalue(), art.width, art.height)


def stamp(page: fitz.Page, mark: Watermark, xref: int = 0) -> int:
    """
    Draw the watermark over one page, reusing the embedded image if we have it.

    The xref round-trip is not an optimisation detail -- a 713 page book that
    embeds the artwork once per sheet carries 713 copies of it, and the reuse is
    what keeps the finished file the same size as the one that went in.
    """
    return page.insert_image(mark.rect_on(page.rect), stream=mark.stream,
                             xref=xref, overlay=False)


def place_cover(doc: fitz.Document, cover: fitz.Document, index: int,
                at_end: bool) -> None:
    """
    Put one cover page on a fresh A4 sheet.

    The covers are 0.92pt wider and 0.08pt shorter than the interior. Mixed page
    sizes in one file are what makes a print shop ring up to ask which one is
    right, so the cover is fitted to the interior's A4 exactly. The 0.15%
    stretch that costs is below what any press can hold.
    """
    page = doc.new_page(-1 if at_end else 0, width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.show_pdf_page(page.rect, cover, index)


def locked(out_path: Path) -> bool:
    """
    Is the target open in something that will not let us replace it?

    Worth asking BEFORE spending two minutes assembling a 180MB book, and worth
    asking per volume rather than per run: a reader left open on one volume
    should not stop the other three from being rebuilt.
    """
    if not out_path.exists():
        return False
    try:
        with open(out_path, "r+b"):
            return False
    except OSError:
        return True


def assemble(interior_path: Path, cover_path: Path, watermark_path: Path,
             out_path: Path, repair: Callable[[fitz.Document], list] | None = None) -> dict:
    """
    Front cover + watermarked interior + back cover -> one print file.

    `repair` is handed the copied interior before the covers and the watermark
    go on, for corrections the audit turned up that are worth making on the way
    to the press. It never sees the covers, and what it returns is reported.
    """
    cover = fitz.open(cover_path)
    if cover.page_count != 2:
        raise ValueError(f"cover must be 2 pages (front, back), "
                         f"got {cover.page_count}: {cover_path}")

    mark = load_watermark(watermark_path)
    interior = fitz.open(interior_path)
    interior_pages = interior.page_count

    book = fitz.open()
    book.insert_pdf(interior)
    interior.close()

    repairs = repair(book) if repair is not None else []

    xref = 0
    for page in book:
        xref = stamp(page, mark, xref)

    place_cover(book, cover, 0, at_end=False)
    place_cover(book, cover, 1, at_end=True)
    cover.close()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Deliberately a plain save. Rewriting the object tree on a 180MB book of
    # scanned sheets costs hours and returns about two percent, and the interior
    # arrives already compressed.
    book.save(out_path)
    book.close()

    return {"interior_pages": interior_pages,
            "total_pages": interior_pages + 2,
            "watermark_px": (mark.width_px, mark.height_px),
            "repairs": repairs,
            "bytes": out_path.stat().st_size}


# ---------------------------------------------------------------------------
# Verification. Everything below reads the finished file and takes nothing on
# trust from the code that wrote it.
# ---------------------------------------------------------------------------


def _watermark_images(page: fitz.Page) -> list:
    return page.get_images(full=True)


def verify(out_path: Path, interior_path: Path, cover_path: Path,
           mark: Watermark, cover_tokens: tuple[str, str],
           repaired: set[int] | None = None) -> list[str]:
    """
    Check the finished book against the two files it was made from.

    `repaired` is the set of printed pages a repair pass was allowed to change.
    Those are excluded from the unchanged-text check -- and every OTHER page is
    then required to be byte-for-byte identical in its text, which turns the
    repair into something the audit proves rather than trusts.

    Returns a list of problems; empty means the file is fit to send.
    """
    repaired = repaired or set()
    problems: list[str] = []
    book = fitz.open(out_path)
    interior = fitz.open(interior_path)

    # 1. shape ------------------------------------------------------------
    expected = interior.page_count + 2
    if book.page_count != expected:
        problems.append(f"page count is {book.page_count}, expected {expected} "
                        f"({interior.page_count} interior + 2 covers)")

    # 2. every sheet is A4, upright ---------------------------------------
    odd_size = [i + 1 for i, p in enumerate(book)
                if abs(p.rect.width - PAGE_WIDTH) > SIZE_TOLERANCE
                or abs(p.rect.height - PAGE_HEIGHT) > SIZE_TOLERANCE]
    if odd_size:
        problems.append(f"{len(odd_size)} sheets are not A4: {odd_size[:8]}")
    rotated = [i + 1 for i, p in enumerate(book) if p.rotation]
    if rotated:
        problems.append(f"{len(rotated)} sheets are rotated: {rotated[:8]}")

    # 3. the covers are on, and the right way round ------------------------
    front_token, back_token = cover_tokens
    front_text = " ".join(book[0].get_text().split())
    back_text = " ".join(book[book.page_count - 1].get_text().split())
    if front_token not in front_text:
        problems.append(f"front cover missing {front_token!r} "
                        f"(page 1 reads {front_text[:70]!r})")
    if back_token not in back_text:
        problems.append(f"back cover missing {back_token!r} "
                        f"(last page reads {back_text[:70]!r})")

    # 4. the covers are NOT watermarked ------------------------------------
    #    The mark is a promotion for the book; on the cover it would read as a
    #    printing fault. A cover carries exactly its own artwork -- one image.
    #    Two would mean the watermark leaked onto it.
    for label, index in (("front", 0), ("back", book.page_count - 1)):
        count = len(_watermark_images(book[index]))
        if count != 1:
            problems.append(f"{label} cover carries {count} images, expected 1 "
                            f"(the cover artwork alone)")

    # 5. every interior sheet carries the watermark, at the right size ------
    target = mark.rect_on(fitz.Rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT))
    unmarked, misplaced, xrefs = [], [], set()
    for sheet in range(1, book.page_count - 1):
        page = book[sheet]
        found = None
        for info in _watermark_images(page):
            for rect in page.get_image_rects(info[0]):
                if abs(rect.width - target.width) < 1.0 and \
                   abs(rect.height - target.height) < 1.0:
                    found = (info[0], rect)
                    break
            if found:
                break
        if found is None:
            unmarked.append(sheet + 1)
            continue
        xrefs.add(found[0])
        rect = found[1]
        if abs(rect.x0 - target.x0) > 1.0 or abs(rect.y0 - target.y0) > 1.0:
            misplaced.append(sheet + 1)
    if unmarked:
        problems.append(f"{len(unmarked)} interior sheets have no watermark: "
                        f"{unmarked[:8]}")
    if misplaced:
        problems.append(f"{len(misplaced)} watermarks are off centre: "
                        f"{misplaced[:8]}")
    if len(xrefs) > 1:
        problems.append(f"watermark embedded {len(xrefs)} times instead of once "
                        f"-- the file is carrying duplicate copies of the art")

    # 6. the interior came through unchanged -------------------------------
    #    Compared page by page against the source, so a sheet silently dropped
    #    or reordered by the copy shows up here rather than on the press.
    changed, unrepaired = [], []
    for index in range(min(interior.page_count, book.page_count - 2)):
        before = " ".join(interior[index].get_text().split())
        after = " ".join(book[index + 1].get_text().split())
        if before == after:
            if index + 1 in repaired:
                unrepaired.append(index + 1)
        elif index + 1 not in repaired:
            changed.append(index + 1)
    if changed:
        problems.append(f"{len(changed)} interior sheets changed text without "
                        f"being repaired: {changed[:8]}")
    if unrepaired:
        problems.append(f"{len(unrepaired)} sheets were reported repaired but "
                        f"read back unchanged: {unrepaired[:8]}")

    # 7. the book's own page numbers still line up -------------------------
    #    After the cover goes on, printed page 1 is the SECOND sheet. Getting
    #    this wrong is how a book comes back with the contents off by one.
    misnumbered = []
    for printed in range(1, interior.page_count + 1):
        page = book[printed]  # printed page N is sheet index N
        band = fitz.Rect(page.rect.width * 0.35, page.rect.height - 40,
                         page.rect.width * 0.65, page.rect.height)
        if str(printed) not in page.get_text("text", clip=band).split():
            misnumbered.append(printed)
    if misnumbered:
        problems.append(f"{len(misnumbered)} sheets do not carry their printed "
                        f"page number: {misnumbered[:8]}")

    interior.close()
    book.close()
    return problems


def report(title: str, stats: dict, problems: list[str]) -> int:
    """Print one book's result. Returns the problem count."""
    print(f"\n{'=' * 74}")
    print(f"  {title}")
    print(f"{'=' * 74}")
    print(f"  sheets            : {stats['total_pages']} "
          f"({stats['interior_pages']} interior + front and back cover)")
    print(f"  watermark         : {WIDTH_FRACTION:.0%} of page width, "
          f"{OPACITY:.0%} ink, centred, embedded once")
    print(f"  size              : {stats['bytes'] / 1_048_576:.1f} MB")
    repairs = stats.get("repairs") or []
    if repairs:
        print(f"  repaired          : {len(repairs)} question-total bands "
              f"renumbered to match the workbook")
        for fix in repairs[:4]:
            print(f"                      p{fix.page}: "
                  f"Question {fix.was} -> {fix.now} ({fix.marks} marks)")
        if len(repairs) > 4:
            print(f"                      ... and {len(repairs) - 4} more")
    if problems:
        print(f"  PROBLEMS          : {len(problems)}")
        for problem in problems:
            print(f"     - {problem}")
    else:
        print(f"  problems          : 0")
    return len(problems)
