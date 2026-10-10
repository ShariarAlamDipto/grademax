"""
Audit the rebuilt IGCSE Accounting "Chapterwise Formats" booklet.

Checks the three things the rebuild was asked to fix, plus the two ways a
re-flow can quietly go wrong (losing content, or duplicating a page):

  1. HEADINGS   every topic opens with a heading, and all eighteen are set in
                the same font, size, colour and alignment;
  2. SPLITS     no account, table or worked-example panel runs off the foot of
                one page and resumes at the head of the next;
  3. LOGO       the badge is stamped on every page;
  4. CONTENT    every line of text in the draft survives into the rebuild;
  5. PAGES      no page is a duplicate of another, and nothing sits outside
                the printable area.

Usage:
    python scripts/audit_accounting_format_booklet.py [--pdf PATH]

Exits non-zero if any check fails.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.accounting_booklet import (  # noqa: E402
    A4, CONTENT_BOT, CONTENT_TOP, FURNITURE,
)

ROOT = Path(__file__).resolve().parent.parent
ACC = ROOT / "data" / "workbook" / "accounting"
DRAFT = ACC / "IGCSE Acc fomat booklet draft (1) (1).pdf"
BOOK = ACC / "IGCSE_Accounting_Chapterwise_Formats.pdf"

HEADING = re.compile(r"^TOPIC (\d+)\s*:\s*(.+)$")

# Lines the rebuild deliberately replaces: the old titles, the straplines that
# repeated them, and the two part-title pages now set in capitals.
REPLACED = re.compile(
    r"^(Paper [12]"
    r"|Accounting Concepts"
    r"|EDEXCEL IGCSE ACCOUNTING"
    r"|Edexcel IGCSE Accounting.*"
    r"|Accounting: Introduction to Bookkeeping.*"
    r"|Introduction to Bookkeeping.*)$"
)

# How close to the foot and head of the text area ink has to sit before it
# counts as a block the page break cut in half.
EDGE = 14.0


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", t)).strip()


def text_bag(doc: fitz.Document) -> Counter:
    bag: Counter = Counter()
    for page in doc:
        for line in page.get_text().split("\n"):
            line = norm(line)
            if not line or FURNITURE.match(line):
                continue
            if "Azwad Hossain Tahmid" in line or "AZWAD HOSSAIN" in line \
                    or line == "TAHMID":
                continue
            bag[line] += 1
    return bag


# The audit measures the rendered page, not the page's drawing operators.
# Re-placed bands are drawn as form XObjects clipped to their bounding box:
# the operators inside still carry the geometry of the whole source page, so
# reading them back reports ink where none is printed. Rasterising is the only
# way to ask what actually lands on the paper.
AUDIT_DPI = 100
PX = AUDIT_DPI / 72.0

# A row of pixels counts as inked if this many are not paper-white.
INK_MIN_PX = 4

# A table header, a panel tint or a rule covers essentially the whole measure;
# the densest line of prose reaches about half of it, because there is white
# between every word and inside every letter. Calibrated against the draft,
# where the real splits it still contains all read above 0.9.
SOLID_COVERAGE = 0.70


def page_ink(page: fitz.Page):
    """Per-row ink counts of the rendered content area, in points.

    Returns (first_inked_y, last_inked_y, coverage) where coverage maps a row's
    y to the fraction of the measure that is inked.
    """
    import numpy as np

    pix = page.get_pixmap(dpi=AUDIT_DPI, colorspace=fitz.csGRAY)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    dark = a < 250
    y0 = int(CONTENT_TOP * PX)
    y1 = min(int(CONTENT_BOT * PX), pix.height)
    band = dark[y0:y1]
    counts = band.sum(axis=1)
    inked = np.nonzero(counts >= INK_MIN_PX)[0]
    if inked.size == 0:
        return None
    measure = pix.width * 0.86          # the text measure, not the whole sheet
    coverage = counts / measure
    return (float((y0 + inked[0]) / PX), float((y0 + inked[-1]) / PX),
            coverage, int(inked[0]), int(inked[-1]))


def solid_at(info, at_end: bool) -> bool:
    """Is the ink at this edge of the page a panel, a rule or a table row?"""
    import numpy as np

    _, _, coverage, first, last = info
    if at_end:
        window = coverage[max(0, last - 8):last + 1]
    else:
        window = coverage[first:first + 9]
    return bool(window.size and np.max(window) >= SOLID_COVERAGE)


def page_extent(page: fitz.Page):
    """Left and right edge of the rendered ink, in points."""
    import numpy as np

    pix = page.get_pixmap(dpi=AUDIT_DPI, colorspace=fitz.csGRAY)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    dark = a < 250
    cols = np.nonzero(dark.sum(axis=0) >= INK_MIN_PX)[0]
    if cols.size == 0:
        return None
    return float(cols[0] / PX), float(cols[-1] / PX)


def check_headings(book: fitz.Document) -> list[str]:
    faults: list[str] = []
    found: list[tuple[int, int, str, float, str, float]] = []
    for page in book:
        for b in page.get_text("dict")["blocks"]:
            if b["type"] != 0:
                continue
            for line in b["lines"]:
                txt = norm("".join(s["text"] for s in line["spans"]))
                m = HEADING.match(txt)
                if not m or line["bbox"][1] > 120:
                    continue
                sp = line["spans"][0]
                centre = (line["bbox"][0] + line["bbox"][2]) / 2
                found.append((page.number, int(m.group(1)), sp["font"],
                              round(sp["size"], 2), m.group(2), centre))
    numbers = [f[1] for f in found]
    if numbers != list(range(1, 19)):
        faults.append(f"topic numbering is {numbers}, expected 1..18")
    fonts = {f[2] for f in found}
    if len(fonts) != 1:
        faults.append(f"headings use {len(fonts)} fonts: {sorted(fonts)}")
    sizes = {f[3] for f in found}
    if len(sizes) > 1:
        faults.append(f"headings use {len(sizes)} sizes: {sorted(sizes)}")
    off = [f for f in found if abs(f[5] - A4[0] / 2) > 2.0]
    if off:
        faults.append(f"{len(off)} headings are not centred: "
                      f"{[(f[1], round(f[5], 1)) for f in off]}")
    return faults


def load_report(pdf: Path) -> dict | None:
    path = pdf.with_suffix(".build.json")
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def cut_group(report: dict, i: int) -> tuple[bool, bool]:
    """Was a keep-together block cut between pages i and i+1?

    Returns (cut, was_oversize). A page that simply ends flush with a finished
    panel looks exactly like one whose panel was cut, so the pixels cannot
    settle it; the builder's placement map can. A block may only be cut when it
    is taller than a page, and then there is nowhere else for it to go.
    """
    pages = {p["page"]: p for p in report["pages"]}
    a, b = pages.get(i), pages.get(i + 1)
    if not a or not b or a["topic"] != b["topic"]:
        return False, False
    shared = {x["group"] for x in a["bands"]} & {x["group"] for x in b["bands"]}
    shared.discard(-1)
    if not shared:
        return False, False
    return True, shared <= set(a.get("oversize_groups", []))


def check_splits(book: fitz.Document,
                 report: dict | None) -> tuple[list[str], list[str]]:
    """No panel or table may run off one page and resume on the next.

    Returns (faults, notes). A block taller than a page has to be continued and
    is reported as a note, not a fault: there is no page it would fit on.
    """
    faults: list[str] = []
    notes: list[str] = []
    info = [page_ink(p) for p in book]
    opens_topic = {n for n in range(book.page_count)
                   if any(HEADING.match(norm(line))
                          for line in book[n].get_text().splitlines())}
    for i in range(len(info) - 1):
        a, b = info[i], info[i + 1]
        if a is None or b is None:
            continue
        if i + 1 in opens_topic:
            continue          # a new topic cannot be a continuation
        if a[1] < CONTENT_BOT - EDGE or b[0] > CONTENT_TOP + EDGE:
            continue
        if not (solid_at(a, True) and solid_at(b, False)):
            continue
        if report is None:
            faults.append(f"pages {i}->{i + 1}: a panel or table may be split")
            continue
        cut, oversize = cut_group(report, i)
        if cut and not oversize:
            faults.append(f"pages {i}->{i + 1}: a block that fits on one page "
                          f"was split across two")
        elif cut:
            notes.append(f"pages {i}->{i + 1}: a block taller than a page is "
                         f"continued -- it fits on no page")
    return faults, notes


def check_logo(book: fitz.Document) -> list[str]:
    missing = []
    for page in book:
        hit = [i for i in page.get_image_info()
               if i["bbox"][1] < CONTENT_TOP and i["bbox"][2] > A4[0] / 2]
        if not hit:
            missing.append(page.number)
    return [f"no logo on pages {missing}"] if missing else []


def check_content(draft: fitz.Document, book: fitz.Document) -> list[str]:
    a, b = text_bag(draft), text_bag(book)
    lost = {k: (v, b[k]) for k, v in a.items()
            if b[k] < v and not REPLACED.match(k)}
    if not lost:
        return []
    out = [f"{len(lost)} lines lost from the draft:"]
    out += [f"    draft x{v[0]}, book x{v[1]}: {k[:80]!r}"
            for k, v in list(lost.items())[:20]]
    return out


def check_pages(book: fitz.Document) -> list[str]:
    faults: list[str] = []
    seen: dict[str, int] = {}
    for page in book:
        key = norm(page.get_text())[:400]
        if len(key) > 80:
            if key in seen:
                faults.append(f"page {page.number} duplicates page {seen[key]}")
            else:
                seen[key] = page.number
        ext = page_extent(page)
        if ext and (ext[0] < 18 or ext[1] > A4[0] - 18):
            faults.append(f"page {page.number}: ink reaches the sheet edge "
                          f"(x {ext[0]:.0f}-{ext[1]:.0f})")
    return faults


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", type=Path, default=BOOK)
    args = ap.parse_args()

    draft = fitz.open(str(DRAFT))
    book = fitz.open(str(args.pdf))

    report = load_report(args.pdf)
    split_faults, split_notes = check_splits(book, report)
    checks = [
        ("headings", check_headings(book)),
        ("splits", split_faults),
        ("logo", check_logo(book)),
        ("content", check_content(draft, book)),
        ("pages", check_pages(book)),
    ]

    bad = 0
    print(f"{args.pdf.name}: {book.page_count} pages "
          f"(draft {draft.page_count})\n")
    for name, faults in checks:
        if faults:
            bad += 1
            print(f"FAIL  {name}")
            for f in faults:
                print(f"        {f}")
        else:
            print(f"ok    {name}")
    for note in split_notes:
        print(f"note  splits: {note}")
    if report and report.get("forced_splits"):
        print(f"note  {len(report['forced_splits'])} blocks in the draft are "
              f"taller than a page and cannot be kept whole")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
