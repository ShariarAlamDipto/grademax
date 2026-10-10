"""
Assemble a yearwise workbook: every paper of a unit, in order, in two volumes.

Shared by the per-unit build scripts. What is particular to a unit -- which
sittings it had, which slot the archive duplicates, what the contents should
say about a cancelled series -- is declared by the caller in a `Plan`.

WHAT MAKES THESE BOOKS DIFFERENT FROM THE CHAPTERWISE ONES

Those take a question out of its paper and give it a measured block of ruled
space. These reprint whole papers, so the exam is the unit and the board's own
layout is the point: the frame, the sidebars, the ruled lines, the mark fence
and the total band all stay exactly as they were set.

The single change is to the ANSWER SPACE. Edexcel gives a question as many as
five further sides of rules, because one printed paper must suit the largest
handwriting in the cohort. The allowance caps that, and the surplus sides are
dropped -- not shrunk. A kept page is the board's page at 1:1, and a dropped
page is simply not there, exactly as if the board had set a shorter paper.

WHICH BLANK SIDE GETS DROPPED

Not the last one. Edexcel prints `(Total for Question 4 is 12 marks)` at the
foot of a question's final page, which on most questions is otherwise blank --
so taking "the last two" would throw the tariff away on three questions in
four. A page carrying the total band is always kept, and the allowance is
filled from the earliest blank sides, so the cut comes out of the middle where
nothing is printed at all.

A continuation page carrying part (b) or a figure is content, not space, and is
never a candidate however little text is on it. See `lib/m1_paper_pages.py` for
how that distinction is drawn and why the obvious tests for it do not work.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import fitz

from .ial_formula_booklet import formula_pages
from .m1_paper_pages import Page, PaperPages, read_paper
from .workbook_layout import PAGE_HEIGHT, PAGE_WIDTH
from .yearwise_layout import (
    FOOTER_BAND, SEASON_SHORT, Book, Volume, clear_bands, contents_pages,
    make_cover, running_header, session_label, stamp_page_numbers, title_page,
    volumes)

ROOT = Path(__file__).resolve().parents[2]

# Blank answer sides a question may keep. 1 since 2026-10-06, on the user's
# instruction: "the question page, then one answer page, and at most one more
# page only if the question itself continues". The side carrying the
# "(Total ...)" band is always kept and counts as that answer page, so a
# question prints as its own content pages + ONE answer side. Measured under 2,
# most questions printed question page + 2 blank sides (S1 61/88, P4 53/92,
# M1 102/154), which the user found "way too much".
DEFAULT_ALLOWANCE = 1

# A mark scheme page may be landscape A4 or US Letter. Both are placed on the
# book's A4 sheet, landscape turned a quarter clockwise -- the fix that took
# 355pt of dead space off every page of the Maths B mark scheme volume.
LANDSCAPE_MIN_WIDTH = 800.0


@dataclass(frozen=True)
class Plan:
    book: Book
    audit_json: Path
    out_dir: Path
    lockup: Path
    # Slots the archive fills but the book must not print -- a cancelled series
    # whose paper was sat in a later one, which would otherwise appear twice.
    skip: frozenset = frozenset()
    # What the contents should say about a session that needs explaining.
    notes: dict = field(default_factory=dict)


@dataclass
class Paper:
    year: int
    season: str
    qp: Path
    ms: Path
    reference: str
    note: str | None = None
    pages: PaperPages | None = None
    kept: list[Page] = field(default_factory=list)

    @property
    def label(self) -> str:
        return session_label(self.year, self.season)

    @property
    def short(self) -> str:
        return f"{SEASON_SHORT[self.season]} {self.year}"


def load_papers(plan: Plan) -> list[Paper]:
    rows = json.loads(plan.audit_json.read_text(encoding="utf-8"))
    by_key = {(r["year"], r["season"], r["kind"]): r for r in rows}
    papers = []
    for (year, season, kind), row in sorted(by_key.items()):
        if kind != "QP" or (year, season) in plan.skip:
            continue
        ms = by_key.get((year, season, "MS"))
        if row["path"] == "-" or not ms or ms["path"] == "-":
            continue
        papers.append(Paper(
            year=year, season=season,
            qp=ROOT / row["path"], ms=ROOT / ms["path"],
            reference=f"{plan.book.code}/01  ·  {row['item_code']}",
            note=plan.notes.get((year, season))))
    return papers


def pages_to_keep(paper: PaperPages, allowance: int) -> list[Page]:
    """
    Every page of the paper except the blank answer sides over the allowance.

    A page carrying the total band is kept whatever the allowance, because that
    band is the question's mark tariff and on most questions it is the only
    thing printed on an otherwise blank final side. So `--allowance 0` means
    "no spare space", not "throw the mark tariffs away".
    """
    dropped: set[int] = set()
    for question in paper.questions:
        space = question.space
        if len(space) <= allowance:
            continue
        keep = [p for p in space if p.has_total]
        for p in space:
            if len(keep) >= allowance:
                break
            if p not in keep:
                keep.append(p)
        dropped |= {p.index for p in space if p not in keep}
    return [p for p in paper.pages if p.index not in dropped]


def place_exam_sheet(book: fitz.Document, source: fitz.Document, index: int,
                     left: str, right: str) -> None:
    """One exam page, 1:1 on its own A4 sheet, with our furniture for theirs."""
    page = book.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.show_pdf_page(fitz.Rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT), source, index)
    clear_bands(page)
    running_header(page, left, right)


def place_scheme_sheet(book: fitz.Document, source: fitz.Document, index: int,
                       left: str, right: str) -> None:
    """
    One mark scheme page, fitted to the sheet above the book's own footer.

    A mark scheme has no frame and no furniture strip, so nothing is painted out
    and nothing may be cropped: it is scaled to fit whole. A landscape sheet is
    turned a quarter clockwise rather than fitted to the width -- fitted, it
    would sit at scale 0.707 with a third of every page empty below it.
    """
    box = source[index].rect
    page = book.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    top = 26.0
    limit = PAGE_HEIGHT - FOOTER_BAND

    if box.width >= LANDSCAPE_MIN_WIDTH and box.width > box.height:
        scale = min(PAGE_WIDTH / box.height, (limit - top) / box.width)
        width, height = box.height * scale, box.width * scale
        target = fitz.Rect((PAGE_WIDTH - width) / 2, top,
                           (PAGE_WIDTH + width) / 2, top + height)
        page.show_pdf_page(target, source, index, rotate=270)
        return

    scale = min(PAGE_WIDTH / box.width, (limit - top) / box.height)
    width, height = box.width * scale, box.height * scale
    target = fitz.Rect((PAGE_WIDTH - width) / 2, top,
                       (PAGE_WIDTH + width) / 2, top + height)
    page.show_pdf_page(target, source, index)
    running_header(page, left, right)


def build_questions(papers: list[Paper], allowance: int) -> tuple[fitz.Document, list[dict]]:
    book = fitz.open()
    entries = []
    for paper in papers:
        paper.pages = read_paper(paper.qp)
        paper.kept = pages_to_keep(paper.pages, allowance)
        source = fitz.open(paper.qp)

        first = book.page_count + 1
        starts: dict[int, int] = {}
        for page in paper.kept:
            if page.role == "start" and page.question is not None:
                starts[page.question] = book.page_count + 1
            place_exam_sheet(book, source, page.index, paper.label, paper.reference)
        source.close()

        entries.append({
            "year": paper.year, "season": paper.season, "page": first,
            "reference": paper.reference, "note": paper.note,
            "questions": sorted(starts.items()),
            "source_pages": len(paper.pages.pages), "book_pages": len(paper.kept),
            "marks": paper.pages.total_marks,
            "problems": paper.pages.problems,
        })
    return book, entries


def build_mark_schemes(papers: list[Paper]) -> tuple[fitz.Document, list[dict]]:
    book = fitz.open()
    entries = []
    for paper in papers:
        source = fitz.open(paper.ms)
        first = book.page_count + 1
        for index in range(source.page_count):
            place_scheme_sheet(book, source, index, paper.label, paper.reference)
        entries.append({
            "year": paper.year, "season": paper.season, "page": first,
            "reference": paper.reference, "note": paper.note,
            "book_pages": source.page_count,
        })
        source.close()
    return book, entries


def assemble(body: fitz.Document, entries: list[dict], volume: Volume,
             span: str, reference: fitz.Document | None = None) -> fitz.Document:
    """
    Front matter, then the body, numbered straight through.

    The contents has to count its own length, so it is laid out twice: once to
    learn how many sheets it takes, and again with the page numbers that length
    implies. Without the second pass every entry points one contents short.

    `reference` (the question volume's official formula sheet) goes straight
    after the title page, and its length is part of the contents' offset.
    """
    extra = reference.page_count if reference else 0
    length = 0
    for _ in range(4):
        front = fitz.open()
        title_page(front, volume, span, len(entries))
        contents_pages(front, entries, volume, offset=1 + extra + length)
        if front.page_count - 1 == length:
            break
        length = front.page_count - 1
        front.close()

    if reference:
        front.insert_pdf(reference, start_at=1)
    book = fitz.open()
    book.insert_pdf(front)
    front.close()
    book.insert_pdf(body)
    stamp_page_numbers(book, volume)
    return book


def run(plan: Plan, allowance: int, only: str | None, execute: bool) -> int:
    papers = load_papers(plan)
    if not papers:
        print(f"no papers found -- run the {plan.book.slug} source audit first")
        return 1
    span = f"{papers[0].label} - {papers[-1].label}"
    questions, mark_schemes = volumes(plan.book)
    print(f"{plan.book.name} ({plan.book.code}): {len(papers)} papers, {span}\n")

    plan.out_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {"allowance": allowance, "span": span, "volumes": {}}
    prefix = f"{plan.book.token}_Yearwise"

    if only != "markschemes":
        body, entries = build_questions(papers, allowance)
        print(f"{'session':20} {'source':>7} {'book':>5} {'cut':>4} {'Q':>2} {'marks':>5}  page")
        cut = kept = source_total = 0
        for e in entries:
            drop = e["source_pages"] - e["book_pages"]
            cut += drop
            kept += e["book_pages"]
            source_total += e["source_pages"]
            print(f"{e['year']} {e['season']:14} {e['source_pages']:7} {e['book_pages']:5} "
                  f"{drop:4} {len(e['questions']):2} {e['marks']:5}  {e['page']}")
            for p in e["problems"]:
                print(f"{'':22}! {p}")
        print(f"\n  {source_total} source pages -> {kept} "
              f"({cut} blank sides dropped, {100 * cut / source_total:.0f}%)")

        # The board's formula sheet for the unit, after the title page
        # (user, 2026-10-09).
        reference = formula_pages(plan.book.token)
        book = assemble(body, entries, questions, span, reference)
        reference.close()
        report["volumes"]["questions"] = {
            "pages": book.page_count, "front_matter": book.page_count - kept,
            "source_pages": source_total, "dropped": cut, "entries": entries}
        out = plan.out_dir / f"{prefix}_Questions_interior.pdf"
        if execute:
            book.save(out)
            print(f"  wrote {out.relative_to(ROOT)}  ({book.page_count} pages)")
        else:
            print(f"  question volume would be {book.page_count} pages")
        book.close()
        body.close()

    if only != "questions":
        body, entries = build_mark_schemes(papers)
        total = sum(e["book_pages"] for e in entries)
        book = assemble(body, entries, mark_schemes, span)
        report["volumes"]["markschemes"] = {
            "pages": book.page_count, "front_matter": book.page_count - total,
            "entries": entries}
        out = plan.out_dir / f"{prefix}_MarkSchemes_interior.pdf"
        if execute:
            book.save(out)
            print(f"  wrote {out.relative_to(ROOT)}  ({book.page_count} pages)")
        else:
            print(f"  mark scheme volume would be {book.page_count} pages")
        book.close()
        body.close()

    if execute:
        make_cover(plan.out_dir / f"{prefix}_Questions_cover.pdf",
                   questions, span, plan.lockup)
        make_cover(plan.out_dir / f"{prefix}_MarkSchemes_cover.pdf",
                   mark_schemes, span, plan.lockup)
        index = plan.out_dir / "print_index.json"
        index.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"  wrote {index.relative_to(ROOT)}")
    else:
        print("\ndry run -- rerun with --execute to write the volumes")
    return 0
