"""
Check a finished yearwise workbook against the papers it was built from.

Shared by the per-unit audit scripts.

The only audit worth running is the one that could fail. Counting pages cannot:
a book that dropped a question's figure, or clipped the mark fence off every
sheet, or numbered its contents one page short, has exactly the page count it
was supposed to have. So this reads the finished PDF and takes nothing from the
code that wrote it.

  1. NOTHING BUT BLANK SPACE WAS DROPPED. Every source page absent from the
     book must be one that carried no question content at all -- checked
     against the source, not against the builder's own decision.

  2. EVERY MARK TARIFF SURVIVED. `(Total for Question 4 is 12 marks)` is what
     tells a student what the question is worth, and on most questions it sits
     alone at the foot of an otherwise blank page, which is exactly the kind of
     page the book drops. Every one of them has to be in the finished file.

  3. NOTHING WAS CLIPPED OR COVERED. Every word on a page the book kept has to
     be on the book's version of it -- and, because a white rectangle hides
     text without removing it from the text layer, every page is ALSO compared
     as rendered ink. See the note above `ink_bands` for why that second pass
     is not redundant and why it is not a pixel comparison.

  4. THE CONTENTS IS TRUE. Each entry is read back off the contents page and
     the page it names is opened: the paper's first sheet must be that paper's
     cover, and each question's page must be the sheet that question starts on.

  5. THE MARK SCHEMES ARE COMPLETE. They are read, not written on, so every
     page of every scheme has to be there.

"""

from __future__ import annotations

import json
import re
from pathlib import Path

import fitz
import numpy as np

from dataclasses import dataclass

from .m1_paper_pages import read_paper, strip_furniture
# (the comparison window is stated below; the book's own bands are not used here)

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Volumes:
    """Where one unit's finished interiors and their index live."""
    slug: str
    token: str
    name: str

    @property
    def out_dir(self) -> Path:
        return ROOT / "data" / "workbook" / f"{self.slug}_yearwise"

    @property
    def index(self) -> Path:
        return self.out_dir / "print_index.json"

    @property
    def audit(self) -> Path:
        return ROOT / "data" / "analysis" / f"{self.slug}_yearwise_source_audit.json"

    @property
    def questions(self) -> Path:
        return self.out_dir / f"{self.token}_Yearwise_Questions_interior.pdf"

    @property
    def mark_schemes(self) -> Path:
        return self.out_dir / f"{self.token}_Yearwise_MarkSchemes_interior.pdf"

TOTAL_ANY = re.compile(r"\(\s*Total\s+(?:for\s+Question\s+\d{1,2}\s+(?:is|=)\s+)?\d{1,3}\s+marks?\s*\)",
                       re.I)
WORD = re.compile(r"[A-Za-z]{3,}")
A4 = (595.0, 842.0)
SIZE_TOLERANCE = 1.5


def source_paths(vol: Volumes) -> dict[tuple[int, str], tuple[Path, Path]]:
    rows = json.loads(vol.audit.read_text(encoding="utf-8"))
    out: dict[tuple[int, str], dict[str, Path]] = {}
    for r in rows:
        if r["path"] == "-":
            continue
        out.setdefault((r["year"], r["season"]), {})[r["kind"]] = ROOT / r["path"]
    return {k: (v["QP"], v["MS"]) for k, v in out.items() if "QP" in v and "MS" in v}


def words(text: str) -> set[str]:
    return set(WORD.findall(strip_furniture(text).lower()))


# The window both the source page and the book's copy of it are read through.
#
# Comparing whole pages does not work, and not because of a bug: the book
# replaces the board's header and footer with its own, so a book page carries
# words its source page never had, while the source carries a barcode and a
# printed page number the book deliberately covered. Worse, covering is all a
# white rectangle does -- the hidden strings are still in the text layer -- so
# the difference does not go away by itself.
#
# The window is stated in absolute points rather than derived from each page,
# because the two differ by 0.11pt (the papers are 841.89 tall, the book's
# sheets 842.0) and a window measured from the bottom edge therefore falls in a
# different place on each, which put `Pearson Education Ltd.` inside one and
# outside the other on all three 2023 covers. It sits just inside Edexcel's
# frame, whose top edge is never above y=36.5 and whose bottom is never below
# y=794.1 across the twenty papers.
WINDOW_TOP = 36.0
WINDOW_BOTTOM = 792.0


# --- the rendered-ink check -------------------------------------------------
#
# Text comparison cannot see a page that has been COVERED. Painting a white
# rectangle is how the book removes the board's footer, and a rectangle only
# hides: the strings stay in the text layer, so a band set 150pt too deep --
# straight through the first four lines of a question -- reads as a perfect
# match on every text test there is. That was not a hypothesis; it was a
# deliberately broken build that this audit passed.
#
# So the last check looks at the ink. Both pages are rendered through the same
# window and compared band by band: wherever the source page has ink, the book's
# copy must still have it.
#
# Counting differing PIXELS does not work. The book's sheets are 842.0pt tall
# and the papers 841.89, so every row of type lands a fraction of a pixel off
# and a dense cover page differs in 1% of its pixels while being perfectly
# correct. What a covering destroys is not pixel equality but ink: the band goes
# empty. Comparing the ink in a band is immune to the shift, and a run of bands
# is required before it counts, because one sparse band of ruled lines can lose
# a quarter of its ink to that same fraction of a pixel.
INK_DPI = 72
INK_BAND_PT = 12.0
INK_FLOOR = 40          # ink in a source band before it is worth comparing
INK_LOSS = 0.25         # the book keeping less than this share is a loss
INK_RUN = 3             # consecutive lost bands before it is called a defect


def ink_bands(page: fitz.Page) -> "np.ndarray":
    clip = fitz.Rect(0, WINDOW_TOP, page.rect.width, WINDOW_BOTTOM)
    pixmap = page.get_pixmap(dpi=INK_DPI, clip=clip, colorspace=fitz.csGRAY)
    grey = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
        pixmap.height, pixmap.width)
    rows = max(1, round(INK_BAND_PT * INK_DPI / 72))
    dark = (grey < 160).sum(axis=1)
    usable = (len(dark) // rows) * rows
    return dark[:usable].reshape(-1, rows).sum(axis=1)


def lost_ink(source: fitz.Page, book: fitz.Page) -> int:
    """The longest run of bands where the source has ink and the book does not."""
    a, b = ink_bands(source), ink_bands(book)
    n = min(len(a), len(b))
    longest = run = 0
    for i in range(n):
        if a[i] >= INK_FLOOR and b[i] < a[i] * INK_LOSS:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return longest


def live_words(page: fitz.Page) -> set[str]:
    """
    The words inside the frame, which is the part of the sheet the book keeps.

    Deliberately NOT furniture-stripped. The audit needs to tell one page from
    another, and a blank continuation sheet has nothing on it BUT furniture --
    strip that and every blank side in a paper reads the same, so the alignment
    cannot say which of them was dropped, and the last page of three papers got
    reported missing when it was there all along. `Question 4 continued` and
    `TOTAL FOR PAPER` are exactly the identifying marks it needs.
    """
    clip = fitz.Rect(0, WINDOW_TOP, page.rect.width, WINDOW_BOTTOM)
    return set(WORD.findall(page.get_text("text", clip=clip).lower()))


def check_questions(vol: Volumes, problems: list[str]) -> dict:
    report = json.loads(vol.index.read_text(encoding="utf-8"))["volumes"]["questions"]
    entries = report["entries"]
    book = fitz.open(vol.questions)
    paths = source_paths(vol)
    offset = report["front_matter"]

    stats = {"papers": 0, "pages_checked": 0, "tariffs": 0, "dropped": 0,
             "ink_checked": 0}

    for entry in entries:
        key = (entry["year"], entry["season"])
        qp, _ = paths[key]
        paper = read_paper(qp)
        source = fitz.open(qp)
        name = f"{entry['year']} {entry['season']}"
        stats["papers"] += 1

        kept = [p for p in paper.pages if p.role != "space"]
        kept_indices = {p.index for p in kept}

        # The builder keeps some blank sides too; work out which by matching the
        # book's own pages back to the source, so the audit never consults the
        # builder's decision -- only the finished file.
        first = entry["page"] + offset - 1          # 0-based in the book
        book_pages = list(range(first, first + entry["book_pages"]))
        if book_pages[-1] >= book.page_count:
            problems.append(f"{name}: runs past the end of the book")
            continue

        source_texts = [live_words(source[i]) for i in range(source.page_count)]
        book_texts = [live_words(book[i]) for i in book_pages]

        # --- 1 + 3: align the book's pages to the source's, in order ---------
        # The book never reorders, so its pages are a subsequence of the
        # paper's. Walking both at once says which source pages were dropped
        # AND, for the ones kept, whether every word came through.
        si = 0
        matched: dict[int, int] = {}
        for bi, bw in enumerate(book_texts):
            while si < source.page_count and source_texts[si] != bw:
                si += 1
            if si >= source.page_count:
                problems.append(
                    f"{name}: book page {book_pages[bi] + 1} matches no source page; "
                    f"it reads {sorted(bw)[:6]}")
                si = 0
                continue
            matched[si] = book_pages[bi]
            run = lost_ink(source[si], book[book_pages[bi]])
            if run >= INK_RUN:
                problems.append(
                    f"{name}: book page {book_pages[bi] + 1} has lost the ink from "
                    f"{run * INK_BAND_PT:.0f}pt of source page {si + 1} -- covered?")
            stats["ink_checked"] += 1
            si += 1
            stats["pages_checked"] += 1

        for i in range(source.page_count):
            if i in matched:
                continue
            stats["dropped"] += 1
            if i in kept_indices:
                problems.append(
                    f"{name}: source page {i + 1} carries content but is not in the book "
                    f"({strip_furniture(source[i].get_text())[:60]!r})")

        # --- 2: every tariff survived ----------------------------------------
        source_tariffs = sorted(
            t for i in range(source.page_count)
            for t in TOTAL_ANY.findall(re.sub(r"\s+", " ", source[i].get_text())))
        book_tariffs = sorted(
            t for i in book_pages
            for t in TOTAL_ANY.findall(re.sub(r"\s+", " ", book[i].get_text())))
        if source_tariffs != book_tariffs:
            lost = [t for t in source_tariffs if t not in book_tariffs]
            problems.append(f"{name}: mark tariffs lost: {lost}")
        stats["tariffs"] += len(book_tariffs)

        # --- 4: the contents tells the truth ---------------------------------
        for qnum, page in entry["questions"]:
            at = page + offset - 1
            if not (0 <= at < book.page_count):
                problems.append(f"{name}: Q{qnum} points off the end of the book")
                continue
            expected = next((p for p in paper.questions if p.number == qnum), None)
            if expected is None:
                continue
            want = live_words(source[expected.pages[0].index])
            if live_words(book[at]) != want:
                problems.append(
                    f"{name}: contents sends Q{qnum} to book page {at + 1}, "
                    "which is not where that question starts")

        if live_words(book[first]) != live_words(source[0]):
            problems.append(f"{name}: the paper does not open on its own cover page")

        source.close()

    # Page geometry: a print shop should never have to ask which size is right.
    odd = [i + 1 for i in range(book.page_count)
           if abs(book[i].rect.width - A4[0]) > SIZE_TOLERANCE
           or abs(book[i].rect.height - A4[1]) > SIZE_TOLERANCE]
    if odd:
        problems.append(f"question volume: {len(odd)} pages are not A4 (first: {odd[0]})")

    numbered = sum(1 for i in range(1, book.page_count)
                   if re.search(r"GradeMax", book[i].get_text()))
    if numbered < book.page_count - 1:
        problems.append(f"question volume: {book.page_count - 1 - numbered} pages "
                        "carry no running footer")

    stats["book_pages"] = book.page_count
    book.close()
    return stats


def check_mark_schemes(vol: Volumes, problems: list[str]) -> dict:
    report = json.loads(vol.index.read_text(encoding="utf-8"))["volumes"]["markschemes"]
    book = fitz.open(vol.mark_schemes)
    paths = source_paths(vol)
    offset = report["front_matter"]
    stats = {"schemes": 0, "pages_checked": 0}

    for entry in report["entries"]:
        _, ms = paths[(entry["year"], entry["season"])]
        source = fitz.open(ms)
        name = f"{entry['year']} {entry['season']}"
        stats["schemes"] += 1
        if source.page_count != entry["book_pages"]:
            problems.append(f"{name}: mark scheme is {source.page_count} pages, "
                            f"book has {entry['book_pages']}")
        first = entry["page"] + offset - 1
        for i in range(source.page_count):
            at = first + i
            if at >= book.page_count:
                problems.append(f"{name}: mark scheme runs past the end of the book")
                break
            if not words(source[i].get_text()) <= words(book[at].get_text()):
                problems.append(f"{name}: scheme page {i + 1} does not match "
                                f"book page {at + 1}")
            stats["pages_checked"] += 1
        source.close()

    odd = [i + 1 for i in range(book.page_count)
           if abs(book[i].rect.width - A4[0]) > SIZE_TOLERANCE
           or abs(book[i].rect.height - A4[1]) > SIZE_TOLERANCE]
    if odd:
        problems.append(f"mark scheme volume: {len(odd)} pages are not A4 (first: {odd[0]})")

    stats["book_pages"] = book.page_count
    book.close()
    return stats


def audit(vol: Volumes) -> int:
    if not vol.index.exists():
        print(f"nothing built yet -- run scripts/build_{vol.slug}_yearwise_workbook.py --execute")
        return 1

    problems: list[str] = []
    print(f"{vol.name} question volume")
    q = check_questions(vol, problems)
    print(f"  {q['papers']} papers, {q['book_pages']} pages, "
          f"{q['pages_checked']} matched to their source page, "
          f"{q['tariffs']} mark tariffs present, {q['dropped']} blank sides dropped")
    print(f"  {q['ink_checked']} pages compared as rendered ink against their source")

    print(f"{vol.name} mark scheme volume")
    m = check_mark_schemes(vol, problems)
    print(f"  {m['schemes']} schemes, {m['book_pages']} pages, "
          f"{m['pages_checked']} matched to their source page")

    print()
    if problems:
        print(f"{len(problems)} problems:")
        for p in problems:
            print(f"  ! {p}")
        return 1
    print("no problems")
    return 0
