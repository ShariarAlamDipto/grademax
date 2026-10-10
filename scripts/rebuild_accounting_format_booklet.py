"""
Rebuild the IGCSE Accounting "Chapterwise Formats" booklet.

Takes the stapled-together draft and produces a single consistent A4 book:

  * all eighteen topic headings re-set in one typeface, case and alignment,
    replacing the hand-patched white boxes and pasted "Topic N" labels;
  * worked examples re-flowed so an account and its caption never straddle a
    page break;
  * the Accounting by Tahmid badge stamped top-right on every page, in black
    and white, with a uniform running foot.

Usage:
    python scripts/rebuild_accounting_format_booklet.py [--out PATH] [--report]

See scripts/lib/accounting_booklet.py for why the re-flow is done by slicing
and re-placing source bands rather than by re-typesetting the content.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.accounting_booklet import (  # noqa: E402
    A4, BLUE, CONTENT_BOT, CONTENT_H, CONTENT_TOP, FOOTER_H, GREY, NAVY,
    Group, PASSTHROUGH_PAGES, build_groups, clean_source, section_atoms,
)

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "workbook" / "accounting" / "IGCSE Acc fomat booklet draft (1) (1).pdf"
LOGO = ROOT / "data" / "workbook" / "accounting" / "assets" / "logo_bw.png"
DEFAULT_OUT = ROOT / "data" / "workbook" / "accounting" / "IGCSE_Accounting_Chapterwise_Formats.pdf"

# The builder writes a placement map beside the PDF. The audit needs it to tell
# a page that merely ends flush with a panel from one where a panel was cut:
# those look identical on paper, and only the source coordinates of the bands
# either side of the break can separate them.
REPORT_SUFFIX = ".build.json"

# Inherited whitespace above a group is preserved so the book keeps its rhythm,
# but capped: a gap that only existed because the generator was padding out to
# a page break should not survive into a page where it means nothing.
MAX_LEAD_GAP = 22.0

# Logo plate in the top margin.
LOGO_H = 34.0
LOGO_TOP = 9.0
LOGO_RIGHT = 45.0

HEADING_BLOCK_H = 54.0      # topic title + rule + air beneath
HEADING_MAX_W = A4[0] - 130
HEADING_RULE_INSET = 64.0


@dataclass(frozen=True)
class Section:
    number: int
    title: str
    first: int
    last: int


# The eighteen topics, in the order the draft presents them. The numbering in
# the draft contradicts itself -- two topics are numbered 5, two are numbered
# 11, and the page headed "Topic 8 : Control Accounts" is in fact the trial
# balance -- so the numbers are assigned here from reading order.
SECTIONS = [
    Section(1, "Business Documentation", 1, 2),
    Section(2, "Books of Original Entry", 3, 14),
    Section(3, "Ledger Accounting", 15, 24),
    Section(4, "Depreciation", 25, 31),
    Section(5, "Trial Balance", 32, 37),
    Section(6, "Correction of Errors", 38, 45),
    Section(7, "Control Accounts", 46, 52),
    Section(8, "Bank Reconciliation Statement", 53, 59),
    Section(9, "Capital & Revenue Expenditure", 60, 64),
    Section(10, "Accounting Concepts", 65, 66),
    Section(11, "Irrecoverable Debts", 67, 76),
    Section(12, "Other Receivables & Other Payables", 77, 84),
    Section(13, "Financial Statements", 86, 96),
    Section(14, "Partnership Business", 97, 109),
    Section(15, "Ratio Analysis", 110, 123),
    Section(16, "Manufacturing Accounts", 124, 132),
    Section(17, "Incomplete Records", 133, 144),
    Section(18, "Adjustments to Financial Statements", 145, 156),
]

# Part-title pages in the draft, keyed by the topic they introduce.
DIVIDERS = {1: "Paper 1", 13: "Paper 2"}


# --------------------------------------------------------------------------
# placement
# --------------------------------------------------------------------------

@dataclass
class Placement:
    """One band of one source page, positioned on an output page."""
    src_page: int
    y0: float
    y1: float
    target_y: float
    group: int = -1        # index of the keep-together group it belongs to


@dataclass
class OutPage:
    section: Section | None
    placements: list
    shift: float = 0.0
    heading: bool = False
    divider: str | None = None
    passthrough: int | None = None


def flow_section(sec: Section, groups: list[Group], shift: float) -> list[OutPage]:
    """Pack a topic's groups onto pages, never splitting a group."""
    pages: list[OutPage] = []
    cur = OutPage(sec, [], shift, heading=True)
    y = CONTENT_TOP + HEADING_BLOCK_H
    emitted: set[int] = set()      # pass-through source pages already placed

    def new_page() -> float:
        nonlocal cur
        pages.append(cur)
        cur = OutPage(sec, [], shift)
        return CONTENT_TOP

    for gi, g in enumerate(groups):
        if g.passthrough:
            # A pass-through page yields several groups (its banner and each
            # of its cards); the page itself is still placed once.
            src_page = g.slices[0][0].page
            if src_page in emitted:
                continue
            emitted.add(src_page)
            if cur.placements or cur.heading:
                y = new_page()
            pages.append(OutPage(sec, [], shift, passthrough=src_page))
            cur = OutPage(sec, [], shift)
            y = CONTENT_TOP
            continue

        gap = 0.0 if not cur.placements else min(g.lead_gap, MAX_LEAD_GAP)

        if g.total > CONTENT_H:
            # Taller than any page can hold: lay its atoms out in order and
            # break between them. Only a full-page table can reach here.
            for atom, off in g.slices:
                if y + atom.height > CONTENT_BOT:
                    y = new_page()
                cur.placements.append(
                    Placement(atom.page, atom.y0, atom.y1, y, gi))
                y += atom.height + 6.0
            continue

        if y + gap + g.total > CONTENT_BOT:
            y = new_page()
            gap = 0.0

        top = y + gap
        for atom, off in g.slices:
            cur.placements.append(
                Placement(atom.page, atom.y0, atom.y1, top + off, gi))
        y = top + g.total

    if cur.placements or cur.heading:
        pages.append(cur)
    return pages


def coalesce(placements: list[Placement]) -> list[Placement]:
    """Merge neighbouring bands of the same source page that kept their spacing.

    Without this every paragraph becomes its own form XObject; with it a page
    that was not re-flowed at all is drawn in a single operation.
    """
    out: list[Placement] = []
    for p in placements:
        if out:
            q = out[-1]
            if q.src_page == p.src_page and \
                    abs((p.target_y - q.target_y) - (p.y0 - q.y0)) < 0.05:
                out[-1] = Placement(q.src_page, q.y0, p.y1, q.target_y)
                continue
        out.append(p)
    return out


# --------------------------------------------------------------------------
# furniture
# --------------------------------------------------------------------------

def draw_logo(page: fitz.Page, logo: bytes, aspect: float) -> None:
    w = LOGO_H * aspect
    x1 = A4[0] - LOGO_RIGHT
    page.insert_image(fitz.Rect(x1 - w, LOGO_TOP, x1, LOGO_TOP + LOGO_H),
                      stream=logo, keep_proportion=True)


def heading_text(sec: Section) -> str:
    return f"TOPIC {sec.number}  :  {sec.title.upper()}"


def heading_size(sections: list[Section]) -> float:
    """One size for all eighteen headings: the largest the longest title takes.

    Shrinking only the titles that overrun would leave the book with headings
    set at two sizes, which is the inconsistency this rebuild is removing.
    """
    longest = max((heading_text(s) for s in sections), key=len)
    size = 17.0
    while size > 11 and fitz.get_text_length(longest, "hebo", size) > HEADING_MAX_W:
        size -= 0.5
    return size


def draw_heading(page: fitz.Page, sec: Section, size: float) -> None:
    """The one heading style the whole book uses."""
    title = heading_text(sec)
    w = fitz.get_text_length(title, "hebo", size)
    base = CONTENT_TOP + 20.0
    page.insert_text(((A4[0] - w) / 2, base), title,
                     fontname="hebo", fontsize=size, color=NAVY)
    page.draw_line(fitz.Point(HEADING_RULE_INSET, base + 12.0),
                   fitz.Point(A4[0] - HEADING_RULE_INSET, base + 12.0),
                   color=NAVY, width=1.2)


def draw_footer(page: fitz.Page, sec: Section | None, folio: int) -> None:
    y = A4[1] - FOOTER_H + 16.0
    if sec is not None:
        page.insert_text((64, y), f"Topic {sec.number}  ·  {sec.title}",
                         fontname="helv", fontsize=8, color=GREY)
    num = str(folio)
    w = fitz.get_text_length(num, "helv", 8)
    page.insert_text((A4[0] - 64 - w, y), num,
                     fontname="helv", fontsize=8, color=GREY)


def draw_divider(page: fitz.Page, label: str) -> None:
    w = fitz.get_text_length(label.upper(), "hebo", 34)
    page.insert_text(((A4[0] - w) / 2, 330), label.upper(),
                     fontname="hebo", fontsize=34, color=NAVY)
    sub = "Chapterwise Formats"
    w2 = fitz.get_text_length(sub, "helv", 16)
    page.insert_text(((A4[0] - w2) / 2, 362), sub,
                     fontname="helv", fontsize=16, color=BLUE)
    page.draw_line(fitz.Point(200, 385), fitz.Point(A4[0] - 200, 385),
                   color=BLUE, width=1.0)


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------

def build(out_path: Path, report: bool) -> None:
    src = clean_source(str(SRC), {sec.first for sec in SECTIONS})
    logo = LOGO.read_bytes()
    from PIL import Image
    with Image.open(LOGO) as im:
        aspect = im.width / im.height

    out = fitz.open()
    title_size = heading_size(SECTIONS)
    folio = 0
    stats: list[tuple[Section, int, int]] = []
    placement_map: list[dict] = []
    forced: list[str] = []

    for sec in SECTIONS:
        atoms = section_atoms(src, sec.first, sec.last)
        if not atoms:
            continue

        body = [a for a in atoms if a.page not in PASSTHROUGH_PAGES]
        gaps = [b.y0 - a.y1 for a, b in zip(body, body[1:])
                if a.page == b.page and 0 < b.y0 - a.y1 < 40]
        median_gap = statistics.median(gaps) if gaps else 12.0

        groups = build_groups(src, atoms, median_gap)

        x0 = min(a.x0 for a in body) if body else 42.5
        x1 = max(a.x1 for a in body) if body else A4[0] - 42.5
        shift = (A4[0] - (x1 - x0)) / 2 - x0

        oversize = [g for g in groups if g.total > CONTENT_H and not g.passthrough]
        oversize_idx = {i for i, g in enumerate(groups)
                        if g.total > CONTENT_H and not g.passthrough}
        forced += [f"topic {sec.number}: {g.tag!r} is {g.total:.0f}pt, "
                   f"taller than a {CONTENT_H:.0f}pt page" for g in oversize]

        pages = flow_section(sec, groups, shift)

        if sec.number in DIVIDERS:
            page = out.new_page(width=A4[0], height=A4[1])
            draw_divider(page, DIVIDERS[sec.number])
            draw_logo(page, logo, aspect)

        for op in pages:
            page = out.new_page(width=A4[0], height=A4[1])
            folio += 1
            draw_logo(page, logo, aspect)
            if op.heading:
                draw_heading(page, sec, title_size)
            if op.passthrough is not None:
                # A full-bleed card page. It keeps its own design, scaled to
                # sit below the logo band rather than under the badge.
                sp = src[op.passthrough]
                avail_h = CONTENT_BOT - CONTENT_TOP
                scale = min(A4[0] / sp.rect.width, avail_h / sp.rect.height)
                w, h = sp.rect.width * scale, sp.rect.height * scale
                page.show_pdf_page(
                    fitz.Rect((A4[0] - w) / 2, CONTENT_TOP,
                              (A4[0] + w) / 2, CONTENT_TOP + h),
                    src, op.passthrough)
            for p in coalesce(op.placements):
                srcw = src[p.src_page].rect.width
                page.show_pdf_page(
                    fitz.Rect(op.shift, p.target_y,
                              op.shift + srcw, p.target_y + (p.y1 - p.y0)),
                    src, p.src_page,
                    clip=fitz.Rect(0, p.y0, srcw, p.y1))
            draw_footer(page, sec, folio)
            placement_map.append({
                "page": page.number,
                "topic": sec.number,
                "passthrough": op.passthrough,
                "bands": [{"src": p.src_page, "y0": round(p.y0, 2),
                           "y1": round(p.y1, 2), "at": round(p.target_y, 2),
                           "group": p.group}
                          for p in coalesce(op.placements)],
                "oversize_groups": sorted(oversize_idx),
            })

        stats.append((sec, sec.last - sec.first + 1, len(pages)))

    out.set_metadata({
        "title": "Edexcel IGCSE Accounting - Chapterwise Formats",
        "author": "Accounting by Tahmid - Tri Axis Education",
        "subject": "Edexcel IGCSE Accounting (4AC1) chapterwise formats booklet",
    })
    out.save(str(out_path), garbage=4, deflate=True)
    out.close()
    src.close()

    report_path = out_path.with_suffix(REPORT_SUFFIX)
    report_path.write_text(json.dumps(
        {"pages": placement_map, "forced_splits": forced}, indent=1),
        encoding="utf-8")

    if report:
        print(f"{'topic':<40}{'draft':>7}{'rebuilt':>9}")
        for sec, before, after in stats:
            print(f"{sec.number:>2}. {sec.title:<36}{before:>7}{after:>9}")
        print(f"{'':<40}{sum(s[1] for s in stats):>7}{sum(s[2] for s in stats):>9}")
        print()
        print(f"blocks too tall for one page ({len(forced)}):")
        for f in forced:
            print(f"    {f}")
    print(f"wrote {out_path}  ({fitz.open(str(out_path)).page_count} pages)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    build(args.out, args.report)


if __name__ == "__main__":
    main()
