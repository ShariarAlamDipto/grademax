"""
Print-ready Further Pure Maths chapterwise workbook: one book, one mark scheme.

This is the physical-print assembler, separate from build_fpm_workbook_pdf.py,
which produces per-chapter proofing PDFs. What the press needs and what a proof
needs are different documents:

  * ONE continuous book, so page numbers run 1..N and a contents page can point
    at them. Per-chapter files each restart at 1 and cannot be bound.
  * QUESTIONS ONLY. The mark schemes are a second, separate book -- a student
    working a chapter should not have the answers on the facing page. The
    DIGITAL edition keeps them linked; see print_index.json below.
  * Questions RENUMBERED 1..N within each section. A chapterwise workbook that
    prints "Question 10" as the seventh question of 9.4 is lying to the reader,
    so the paper's number is painted out and the book's own written in its place.
  * FIXED working space in three sizes by mark tariff, so the book has a steady
    rhythm rather than a different gap under every question.
  * GradeMax and nothing else. The trim already drops the exam board's footer,
    the item barcode and the subject code, so they are absent rather than
    covered -- seamless on white stock by construction.

DIGITAL LINKAGE
---------------
`print_index.json` maps every question slug to its printed identity: chapter,
section, the number as printed, the workbook page and the mark scheme page. The
web edition joins on the slug, so a student reading question 7 of 9.4 on paper
and on screen sees the same thing.

TWO PASSES, BECAUSE A CONTENTS PAGE IS SELF-REFERENTIAL
-------------------------------------------------------
Body first, recording where each chapter and section starts. Only then is the
front matter laid out -- and since the front matter shifts every body page, its
own length is added back before the contents are written. Getting this wrong
gives a book whose contents are off by exactly the length of its contents.

USAGE
-----
    python scripts/build_fpm_workbook_print.py                 # dry run
    python scripts/build_fpm_workbook_print.py --execute
    python scripts/build_fpm_workbook_print.py --execute --edition verbatim

TWO EDITIONS
------------
`trimmed` reduces each question to its printed content and gives it a fixed
block of working space, which cuts the book from about 1,780 sheets to 495.

`verbatim` assembles the papers exactly as the board printed them -- every page,
at full size, nothing dropped, no reflow. It is the larger book by far, and it
is the one to use when the pages must look like the exam a student will sit.
Both editions carry the same branding, the same per-section numbering and the
same contents; they differ only in what happens to the page in between.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import fitz
from dotenv import load_dotenv
from supabase import create_client

from lib.fpm_formulas import flow_blocks as formula_blocks
from lib.formula_render import render as render_formulas
from lib.workbook_ink import Band, content_layout, paper_box, question_number_box
from lib.workbook_layout import (
    INK, MARGIN, MUTED, NO_SPACE, PAGE_HEIGHT, PAGE_WIDTH, PRINT_POLICY, RULE,
    Flow, number_patch,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SEGMENT_DIR = REPO_ROOT / "data" / "workbook" / "fpm"
BOOK_DIR = SEGMENT_DIR / "print"

# How far in from a band's edge the hanging indent reaches.
NUMBER_ZONE = 30.0

# The paged edition's split: below this tariff a question gets one sheet, at or
# above it two.
PAGE_BREAK_MARKS = 5
# Report any question squeezed below this to fit its allocation.
SHRINK_WARN = 0.92

# The strip at the foot of every exam page carrying the board's page number,
# item barcode and subject code. Measured: the lowest real question content in
# the corpus ends at y=779, so this is safe to paint over.
FOOTER_BAND = 54.0

# Where to look for a question number on a page with no text layer: the hanging
# indent of the first line, relative to the paper box.
NUMBER_PROBE_TOP = 46.0
NUMBER_PROBE_BOTTOM = 96.0
NUMBER_PROBE_LEFT = 34.0
NUMBER_PROBE_RIGHT = 164.0

SUBJECT_CODE = "4PM1"
SUBJECT_TITLE = "Edexcel International GCSE"
SUBJECT_NAME = "Further Pure Mathematics"
SUBJECT_SUB = "Chapterwise Practice Workbook"
BRAND = "GradeMax"

SESSION_LABEL = {
    "jan": "January", "may-jun": "May/June",
    "oct-nov": "October/November", "specimen": "Specimen",
}

FONT_DIR = Path("C:/Windows/Fonts")
FORMULA_TOP = 118.0
FORMULA_GAP = 4.0
CHAPTER_GAP = 13.0

# End matter. The diary is what a student fills in each week; the blank sheets
# are for working that outgrew the space beside the question.
DIARY_PAGES = 2
BLANK_PAGES = 10
DIARY_ROWS = 16
DIARY_COLUMNS = ((0.13, "Date"), (0.30, "Chapter / section"),
                 (0.34, "Questions set"), (0.13, "Due"), (0.10, "Done"))

FOOTER_BASELINE = PAGE_HEIGHT - 26.0 + 12.0
CONTENTS_ROW = 20.0
CONTENTS_TOP = 132.0
CONTENTS_BOTTOM = PAGE_HEIGHT - 90.0


def formula_sheet(chapters: list[dict]) -> tuple[fitz.Document, list[str]]:
    """
    Every chapter's results, in the book's own order, before the questions.

    Rendered to a temporary PDF by lib.formula_render (matplotlib mathtext) and
    then read back in, because real mathematical typesetting is not something
    PyMuPDF's text drawing can do: no fraction bars, no radical vinculum, no
    limits above and below an integral.
    """
    titles = {c["number"]: c["title"] for c in chapters}
    target = BOOK_DIR / "_formula_sheet.pdf"
    target.parent.mkdir(parents=True, exist_ok=True)
    overflow = render_formulas(formula_blocks(titles), target)
    doc = fitz.open(target)
    sheet = fitz.open()
    sheet.insert_pdf(doc)
    doc.close()
    target.unlink(missing_ok=True)
    return sheet, overflow


def diary_page(doc: fitz.Document, index: int) -> None:
    """A week of homework, for the teacher to set and the student to tick off."""
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((MARGIN, 96), "Homework Record",
                     fontname="hebo", fontsize=19, color=INK)
    page.insert_text((PAGE_WIDTH - MARGIN - 52, 96), f"{index} of {DIARY_PAGES}",
                     fontname="helv", fontsize=9, color=MUTED)
    page.draw_line(fitz.Point(MARGIN, 108), fitz.Point(PAGE_WIDTH - MARGIN, 108),
                   color=RULE, width=0.8)

    width = PAGE_WIDTH - 2 * MARGIN
    top = 132.0
    row = (PAGE_HEIGHT - 90 - top) / DIARY_ROWS

    x = MARGIN
    for fraction, label in DIARY_COLUMNS:
        page.insert_text((x + 4, top - 8), label, fontname="hebo", fontsize=8, color=MUTED)
        x += width * fraction

    page.draw_rect(fitz.Rect(MARGIN, top, PAGE_WIDTH - MARGIN, top + row * DIARY_ROWS),
                   color=RULE, width=0.7)
    for line in range(1, DIARY_ROWS):
        y = top + row * line
        page.draw_line(fitz.Point(MARGIN, y), fitz.Point(PAGE_WIDTH - MARGIN, y),
                       color=RULE, width=0.5)
    x = MARGIN
    for fraction, _ in DIARY_COLUMNS[:-1]:
        x += width * fraction
        page.draw_line(fitz.Point(x, top), fitz.Point(x, top + row * DIARY_ROWS),
                       color=RULE, width=0.5)


def end_matter(doc: fitz.Document) -> None:
    """The diary, then blank sheets to work on."""
    for index in range(1, DIARY_PAGES + 1):
        diary_page(doc, index)
    for index in range(1, BLANK_PAGES + 1):
        page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        page.insert_text((MARGIN, 96), f"Working   ·   {index} of {BLANK_PAGES}",
                         fontname="helv", fontsize=9, color=MUTED)


def fetch_all(query_builder, page_size: int = 1000) -> list[dict]:
    """PostgREST caps a response at 1000 rows and says nothing about it."""
    rows: list[dict] = []
    page = 0
    while True:
        batch = query_builder().range(page * page_size,
                                      page * page_size + page_size - 1).execute().data
        rows.extend(batch)
        if len(batch) < page_size:
            return rows
        page += 1


def load_book(supabase, from_year: int = 0) -> tuple[list[dict], dict[str, list[dict]]]:
    subject_id = (supabase.table("subjects").select("id")
                  .eq("code", SUBJECT_CODE).single().execute().data["id"])

    chapters = (supabase.table("workbook_chapters").select("id, number, title")
                .eq("subject_id", subject_id).order("number").execute().data)
    sections = (supabase.table("workbook_sections")
                .select("id, chapter_id, number, title")
                .in_("chapter_id", [c["id"] for c in chapters]).execute().data)
    section_by_id = {s["id"]: s for s in sections}

    def question_query():
        return (supabase.table("workbook_questions")
                .select("id, slug, section_id, ordinal_in_chapter, marks, difficulty,"
                        " source_paper_key, source_question_number, verified_at, ms_pdf_url")
                .eq("subject_id", subject_id)
                .not_.is_("verified_at", "null")
                .order("ordinal_in_chapter"))

    by_chapter: dict[str, list[dict]] = defaultdict(list)
    for question in fetch_all(question_query):
        section = section_by_id.get(question["section_id"])
        if section is None:
            continue
        # The paper key leads with its year: 2019_may-jun_1.
        if from_year and int(question["source_paper_key"].split("_")[0]) < from_year:
            continue
        question["_section"] = section
        by_chapter[section["chapter_id"]].append(question)

    for rows in by_chapter.values():
        rows.sort(key=lambda q: (q["_section"]["number"], q["ordinal_in_chapter"]))
    return chapters, by_chapter


def segment_path(question: dict, kind: str) -> Path:
    folder = "questions" if kind == "qp" else "markschemes"
    return (SEGMENT_DIR / question["source_paper_key"] / folder
            / f"q{question['source_question_number']}.pdf")


def source_label(question: dict) -> str:
    year, season, paper = question["source_paper_key"].split("_")
    return (f"{year} {SESSION_LABEL.get(season, season.title())} "
            f"Paper {paper} Q{question['source_question_number']}")


def chapter_divider(doc: fitz.Document, chapter: dict, sections: list[tuple[int, str, int, int]]) -> None:
    """A right-hand opener for each chapter, listing its sections."""
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    y = 190.0
    page.insert_text((MARGIN, y), f"Chapter {chapter['number']}",
                     fontname="helv", fontsize=12, color=MUTED)
    y += 34
    page.insert_text((MARGIN, y), chapter["title"], fontname="hebo", fontsize=25, color=INK)
    y += 18
    page.draw_line(fitz.Point(MARGIN, y), fitz.Point(PAGE_WIDTH - MARGIN, y), color=RULE, width=1)
    y += 32

    for number, title, count, marks in sections:
        page.insert_text((MARGIN, y), f"{chapter['number']}.{number}",
                         fontname="hebo", fontsize=10, color=MUTED)
        page.insert_text((MARGIN + 44, y), title, fontname="helv", fontsize=10.5, color=INK)
        tail = f"{count} questions · {marks} marks"
        width = fitz.get_text_length(tail, fontname="helv", fontsize=9)
        page.insert_text((PAGE_WIDTH - MARGIN - width, y), tail,
                         fontname="helv", fontsize=9, color=MUTED)
        y += 22
        if y > CONTENTS_BOTTOM:
            break


def place_verbatim(doc: fitz.Document, source: fitz.Document, index: int,
                   footer: str, renumber: tuple[fitz.Rect | None, str] | None) -> None:
    """
    One source page, whole and at full size, on one A4 sheet.

    The verbatim edition changes nothing about the question: no trimming, no
    reflow, no page dropped. What it does change is the furniture GradeMax is
    replacing -- the board's footer strip is covered with white, which on white
    stock is seamless, and the book's own footer is written into the space that
    frees up.

    The page is clipped to its PAPER BOX rather than its media box, so the
    652x899 sheets contribute their A4 area at 1:1 and leave their bleed --
    including the printer's registration marks -- outside the book.
    """
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    box = paper_box(source[index])
    page.show_pdf_page(fitz.Rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT), source, index, clip=box)

    # The board's page number, item barcode and subject code all live in this
    # strip; the lowest real question content measured across the corpus ends at
    # y=779, so the strip is safe to paint over.
    page.draw_rect(fitz.Rect(0, PAGE_HEIGHT - FOOTER_BAND, PAGE_WIDTH, PAGE_HEIGHT),
                   color=None, fill=(1, 1, 1))
    page.insert_text((MARGIN, PAGE_HEIGHT - FOOTER_BAND + 22), footer,
                     fontname="helv", fontsize=7.6, color=MUTED)

    if renumber is not None and renumber[0] is not None:
        source_box, printed = renumber
        rect = fitz.Rect(source_box.x0 - box.x0, source_box.y0 - box.y0,
                         source_box.x1 - box.x0, source_box.y1 - box.y0)
        page.draw_rect(number_patch(rect) & page.rect, color=None, fill=(1, 1, 1))
        size = max(7.5, min(11.0, rect.height * 0.86))
        page.insert_text((rect.x0, rect.y1 - rect.height * 0.12), printed,
                         fontname="hebo", fontsize=size, color=INK)


def blank_sheet(doc: fitz.Document, footer: str) -> None:
    """An empty working sheet, carrying the book's footer like any other page."""
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((MARGIN, PAGE_HEIGHT - FOOTER_BAND + 22), footer,
                     fontname="helv", fontsize=7.6, color=MUTED)


def pages_to_keep(source: fitz.Document, bands, allowance: int) -> list[int]:
    """
    Which source pages this question prints.

    The allowance decides how many sheets a question gets, but it never decides
    whether a page of the QUESTION survives: a page carrying content is kept
    whatever the allowance says. Everything else is answer space, and answer
    space is what the allowance is rationing -- so the pages dropped are the
    blank continuation sheets at the end, which is exactly what "two pages for
    the longer questions" means.
    """
    content = sorted({band.page for band in bands}) or [0]
    keep = set(content) | set(range(min(allowance, source.page_count)))
    return sorted(keep)


def number_box_for(source: fitz.Document, number: int) -> fitz.Rect | None:
    """Where the paper printed its question number, text layer or not."""
    box = paper_box(source[0]) if source.page_count else None
    probe = None
    if box is not None:
        probe = Band(0, box.y0 + NUMBER_PROBE_TOP, box.y0 + NUMBER_PROBE_BOTTOM,
                     box.x0 + NUMBER_PROBE_LEFT, box.x0 + NUMBER_PROBE_RIGHT)
    return question_number_box(source, number, probe)


def build_body_verbatim(chapters: list[dict], by_chapter: dict[str, list[dict]],
                        kind: str,
                        allocate: bool = False) -> tuple[fitz.Document, list[dict], list[str]]:
    """
    Assemble the papers chapterwise, page for page, editing nothing out.

    There is no section heading page: adding 39 of them to a book whose premise
    is "nothing added, nothing removed" would be its own kind of edit, so the
    section is named in the footer of every sheet instead, and the contents
    carry the page numbers.
    """
    warnings: list[str] = []
    doc = fitz.open()
    entries: list[dict] = []

    for chapter in chapters:
        questions = by_chapter.get(chapter["id"], [])
        if not questions:
            continue

        grouped: dict[int, list[dict]] = defaultdict(list)
        for question in questions:
            grouped[question["_section"]["number"]].append(question)
        summary = [(number, grouped[number][0]["_section"]["title"], len(grouped[number]),
                    sum(q["marks"] for q in grouped[number]))
                   for number in sorted(grouped)]

        chapter_divider(doc, chapter, summary)
        entries.append({"level": "chapter", "number": chapter["number"],
                        "title": chapter["title"], "page": doc.page_count - 1,
                        "count": len(questions),
                        "marks": sum(q["marks"] for q in questions)})

        for number in sorted(grouped):
            rows = grouped[number]
            section = rows[0]["_section"]
            label = f"{chapter['number']}.{number}"
            entries.append({"level": "section", "number": label,
                            "title": section["title"], "page": doc.page_count,
                            "count": len(rows),
                            "marks": sum(r["marks"] for r in rows)})

            for printed, question in enumerate(rows, 1):
                question["_printed"] = printed
                question["_section_label"] = label
                path = segment_path(question, kind)
                if not path.is_file():
                    if kind == "qp":
                        warnings.append(f"{question['slug']}: missing {path.name}")
                    continue

                footer = (f"{BRAND}   ·   {SUBJECT_NAME}   ·   {label} {section['title']}"
                          f"   ·   Question {printed}")
                if kind == "ms":
                    footer += "   ·   Mark scheme"
                try:
                    with fitz.open(path) as source:
                        renumber = None
                        if kind == "qp":
                            box = number_box_for(source, question["source_question_number"])
                            renumber = (box, str(printed))

                        indices = list(range(source.page_count))
                        allowance = 0
                        if allocate and kind == "qp":
                            allowance = (1 if question["marks"] < PAGE_BREAK_MARKS else 2)
                            bands, _ = content_layout(source)
                            indices = pages_to_keep(source, bands, allowance)
                            if len(indices) > allowance:
                                warnings.append(
                                    f"{question['slug']}: {question['marks']} marks, question "
                                    f"content runs to {len(indices)} pages; kept over the "
                                    f"{allowance}-page allowance")

                        question[f"_page_{kind}"] = doc.page_count
                        for position, index in enumerate(indices):
                            # Only the first page carries the question number.
                            place_verbatim(doc, source, index, footer,
                                           renumber if position == 0 else None)
                        for _ in range(allowance - len(indices)):
                            blank_sheet(doc, footer)
                except Exception as error:  # noqa: BLE001
                    warnings.append(f"{question['slug']}: {error}")

    return doc, entries, warnings


def build_body(chapters: list[dict], by_chapter: dict[str, list[dict]],
               kind: str) -> tuple[fitz.Document, list[dict], list[str]]:
    """
    Lay out every chapter into one document.

    Returns the document, a flat list of contents entries carrying the page each
    one starts on (0-based within the body), and any warnings.
    """
    warnings: list[str] = []
    doc = fitz.open()
    entries: list[dict] = []
    policy = NO_SPACE if kind == "ms" else PRINT_POLICY

    for chapter in chapters:
        questions = by_chapter.get(chapter["id"], [])
        if not questions:
            continue

        grouped: dict[int, list[dict]] = defaultdict(list)
        for question in questions:
            grouped[question["_section"]["number"]].append(question)
        summary = [(number, grouped[number][0]["_section"]["title"], len(grouped[number]),
                    sum(q["marks"] for q in grouped[number]))
                   for number in sorted(grouped)]

        chapter_divider(doc, chapter, summary)
        entries.append({"level": "chapter", "number": chapter["number"],
                        "title": chapter["title"], "page": doc.page_count - 1,
                        "count": len(questions),
                        "marks": sum(q["marks"] for q in questions)})

        running = f"{BRAND}  ·  {SUBJECT_NAME}  ·  Chapter {chapter['number']}  {chapter['title']}"
        if kind == "ms":
            running += "  ·  Mark schemes"
        flow = Flow(doc, running, policy)

        for number in sorted(grouped):
            rows = grouped[number]
            section = rows[0]["_section"]
            flow.section_break(f"{chapter['number']}.{number}   {section['title']}")
            entries.append({"level": "section",
                            "number": f"{chapter['number']}.{number}",
                            "title": section["title"],
                            "page": doc.page_count - 1,
                            "count": len(rows),
                            "marks": sum(r["marks"] for r in rows)})

            # Numbering restarts at 1 in every section: that is what makes it a
            # chapterwise workbook rather than a reordered past paper.
            for printed, question in enumerate(rows, 1):
                question["_printed"] = printed
                question["_section_label"] = f"{chapter['number']}.{number}"
                path = segment_path(question, kind)
                if not path.is_file():
                    if kind == "qp":
                        warnings.append(f"{question['slug']}: missing {path.name}")
                    continue

                right = f"{question['marks']} marks   ·   {source_label(question)}"
                try:
                    with fitz.open(path) as source:
                        bands, masks = content_layout(source)
                        if not bands:
                            warnings.append(f"{question['slug']}: no content; printing whole pages")
                            bands = [Band(i, 0.0, source[i].rect.height,
                                          source[i].rect.x0, source[i].rect.x1)
                                     for i in range(source.page_count)]
                        # Replace the paper's number in place when we know
                        # exactly where it is AND it sits in the hanging indent.
                        # A box found further in is not the number, and painting
                        # over it would white out the question; on those, and on
                        # segments whose window already clips the number away,
                        # the book's number goes in the margin instead.
                        renumber = None
                        label = f"{printed}"
                        if kind == "qp":
                            box = question_number_box(
                                source, question["source_question_number"], bands[0])
                            if box is not None and box.x0 <= bands[0].x0 + NUMBER_ZONE:
                                renumber, label = (box, str(printed)), ""
                        flow.add(source, bands, label, right, question["marks"],
                                 False, renumber=renumber, masks=masks)
                        question[f"_page_{kind}"] = flow.last_start_page
                except Exception as error:  # noqa: BLE001
                    warnings.append(f"{question['slug']}: {error}")

    return doc, entries, warnings


def contents_pages(entries: list[dict], offset: int, kind: str) -> fitz.Document:
    """
    The front matter: a title page, then the contents.

    `offset` is how many pages sit in front of the body once this document is
    itself counted -- without it every entry points one contents-length too low.
    """
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    y = 250.0
    page.insert_text((MARGIN, y), BRAND, fontname="hebo", fontsize=13, color=MUTED)
    y += 46
    page.insert_text((MARGIN, y), SUBJECT_TITLE, fontname="helv", fontsize=13, color=MUTED)
    y += 36
    page.insert_text((MARGIN, y), SUBJECT_NAME, fontname="hebo", fontsize=30, color=INK)
    y += 30
    page.insert_text((MARGIN, y), f"({SUBJECT_CODE})", fontname="helv", fontsize=15, color=MUTED)
    y += 26
    page.draw_line(fitz.Point(MARGIN, y), fitz.Point(PAGE_WIDTH - MARGIN, y), color=RULE, width=1.2)
    y += 30
    subtitle = SUBJECT_SUB + ("  ·  Mark Schemes" if kind == "ms" else "")
    page.insert_text((MARGIN, y), subtitle, fontname="helv", fontsize=11.5, color=INK)

    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((MARGIN, 96), "Contents", fontname="hebo", fontsize=19, color=INK)
    page.draw_line(fitz.Point(MARGIN, 108), fitz.Point(PAGE_WIDTH - MARGIN, 108),
                   color=RULE, width=0.8)
    y = CONTENTS_TOP

    for entry in entries:
        if y > CONTENTS_BOTTOM:
            page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
            y = CONTENTS_TOP

        printed_page = entry["page"] + offset + 1
        if entry["level"] == "chapter":
            y += 8
            page.insert_text((MARGIN, y), f"{entry['number']}",
                             fontname="hebo", fontsize=11.5, color=MUTED)
            page.insert_text((MARGIN + 26, y), entry["title"],
                             fontname="hebo", fontsize=11.5, color=INK)
            font, size = "hebo", 11.5
        else:
            page.insert_text((MARGIN + 26, y), entry["number"],
                             fontname="helv", fontsize=10, color=MUTED)
            page.insert_text((MARGIN + 70, y), entry["title"],
                             fontname="helv", fontsize=10, color=INK)
            font, size = "helv", 10

        label = str(printed_page)
        width = fitz.get_text_length(label, fontname=font, fontsize=size)
        page.insert_text((PAGE_WIDTH - MARGIN - width, y), label,
                         fontname=font, fontsize=size, color=INK)
        y += CONTENTS_ROW

    return doc


def stamp_page_numbers(doc: fitz.Document, kind: str, tail: bool = True) -> None:
    """
    Number every sheet, so the contents can be trusted and a reader can be told
    "turn to page 148" without qualification.
    """
    running = f"{BRAND}  ·  {SUBJECT_NAME}" + ("  ·  Mark Schemes" if kind == "ms" else "")
    for number, page in enumerate(doc, 1):
        label = str(number)
        width = fitz.get_text_length(label, fontname="hebo", fontsize=9)
        page.insert_text(((PAGE_WIDTH - width) / 2, FOOTER_BASELINE), label,
                         fontname="hebo", fontsize=9, color=INK)
        if tail:
            page.insert_text((MARGIN, FOOTER_BASELINE), running,
                             fontname="helv", fontsize=7.4, color=MUTED)


def assemble(chapters, by_chapter, kind: str,
             edition: str = "trimmed") -> tuple[fitz.Document, int, list[str]]:
    """Returns the finished book, the front-matter length, and any warnings."""
    if edition in ("verbatim", "paged"):
        # The paged edition IS the verbatim edition, rationed. The question
        # paper's own formatting is the point, so nothing is reflowed and no
        # page carrying question content is dropped -- only the trailing blank
        # continuation sheets, until the allowance is met. Mark schemes are read
        # rather than written on and keep every page in both editions.
        body, entries, warnings = build_body_verbatim(
            chapters, by_chapter, kind, allocate=edition == "paged")
    else:
        body, entries, warnings = build_body(chapters, by_chapter, kind)

    # Only the question book carries the reference matter; a mark scheme needs
    # neither a formula sheet nor somewhere to record homework.
    formulas = None
    if kind == "qp":
        formulas, overflow = formula_sheet(chapters)
        warnings.extend(f"formula sheet: line too wide — {line}" for line in overflow)
        end_matter(body)

    # The contents shift the body, and their own length depends on the entry
    # count -- which is already known, so one pass settles it. Laying them out
    # once with a zero offset just measures how long they are. The formula sheet
    # sits between the two and shifts everything again, so its length is part of
    # the offset the contents are written with.
    probe = contents_pages(entries, 0, kind)
    contents_length = probe.page_count
    probe.close()
    offset = contents_length + (formulas.page_count if formulas else 0)

    front = contents_pages(entries, offset, kind)
    if front.page_count != contents_length:
        raise RuntimeError(
            f"contents length changed between passes ({contents_length} -> "
            f"{front.page_count}); every page reference in the book would be wrong")

    if formulas:
        front.insert_pdf(formulas)
        formulas.close()
    front.insert_pdf(body)
    body.close()
    # The verbatim edition writes its own richer footer on every question page
    # (chapter, section and question number), so a second line here would just
    # double up.
    stamp_page_numbers(front, kind, tail=edition not in ("verbatim", "paged"))
    return front, offset, warnings


def write_index(chapters, by_chapter, offsets: dict[str, int]) -> dict:
    index = {"subject": SUBJECT_CODE, "questions": []}
    for chapter in chapters:
        for question in by_chapter.get(chapter["id"], []):
            if "_printed" not in question:
                continue
            index["questions"].append({
                "slug": question["slug"],
                "chapter": chapter["number"],
                "chapter_title": chapter["title"],
                "section": question["_section_label"],
                "section_title": question["_section"]["title"],
                "printed_number": question["_printed"],
                "marks": question["marks"],
                "source": source_label(question),
                "workbook_page": question.get("_page_qp", 0) + offsets["qp"] + 1,
                "markscheme_page": (question["_page_ms"] + offsets["ms"] + 1
                                    if "_page_ms" in question else None),
            })
    return index


def main() -> int:
    load_dotenv(REPO_ROOT / ".env.local")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="write the PDFs")
    parser.add_argument("--from-year", type=int, default=2018,
                        help="earliest paper year to include (default 2018)")
    parser.add_argument("--edition", choices=("trimmed", "verbatim", "paged"),
                        default="trimmed",
                        help="trimmed: question plus fixed working space. "
                             "verbatim: the papers exactly as printed, nothing removed. "
                             "paged: one whole sheet per question under 5 marks, two above")
    args = parser.parse_args()
    verbatim = args.edition == "verbatim"
    paged = args.edition == "paged"

    supabase = create_client(os.environ["NEXT_PUBLIC_SUPABASE_URL"],
                             os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    chapters, by_chapter = load_book(supabase, args.from_year)
    total = sum(len(by_chapter.get(c["id"], [])) for c in chapters)

    print(f"{'=' * 74}\nFPM WORKBOOK — PRINT EDITION  "
          f"[{'EXECUTE' if args.execute else 'DRY RUN'}]\n{'=' * 74}")
    print(f"  edition            : {args.edition}")
    print(f"  papers             : {args.from_year} onwards")
    print(f"  verified questions : {total}")
    if verbatim:
        print(f"  pages              : every source page, at full size, nothing removed")
        print(f"  furniture          : board footer strip covered in white")
    elif paged:
        small = sum(1 for c in chapters
                    for q in by_chapter.get(c["id"], []) if q["marks"] < PAGE_BREAK_MARKS)
        print(f"  pages              : 1 sheet under {PAGE_BREAK_MARKS} marks, 2 sheets at or above")
        print(f"  split              : {small} questions on 1 sheet, "
              f"{total - small} on 2  ->  {small + (total - small) * 2} question sheets")
    else:
        print(f"  working space      : {PRINT_POLICY.describe()}")
    print(f"  numbering          : restarts at 1 in every section")
    print(f"  mark schemes       : separate book; linked digitally by slug")
    print(f"  front matter       : contents, then a formula sheet for every chapter")
    print(f"  end matter         : {DIARY_PAGES} homework pages, {BLANK_PAGES} blank")

    if total == 0:
        print("\n  Nothing verified to print.")
        return 0
    if not args.execute:
        print("\n  Dry run — nothing written. Re-run with --execute.")
        return 0

    BOOK_DIR.mkdir(parents=True, exist_ok=True)
    offsets: dict[str, int] = {}
    outputs: dict[str, Path] = {}
    all_warnings: list[str] = []

    suffix = {"verbatim": "_Verbatim", "paged": "_Paged"}.get(args.edition, "")
    for kind, name in (("qp", f"GradeMax_FPM_Workbook{suffix}.pdf"),
                       ("ms", f"GradeMax_FPM_Workbook_MarkSchemes{suffix}.pdf")):
        doc, offset, warnings = assemble(chapters, by_chapter, kind, args.edition)
        all_warnings.extend(warnings)
        target = BOOK_DIR / name
        doc.save(target, deflate=True, garbage=3)
        offsets[kind] = offset
        outputs[kind] = target
        print(f"\n  {name}\n      {doc.page_count} pages "
              f"({offset} front matter), {target.stat().st_size // 1024} KB")
        doc.close()

    index = write_index(chapters, by_chapter, offsets)
    index["edition"] = args.edition
    index_path = BOOK_DIR / f"print_index{suffix.lower()}.json"
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"\n  print_index.json   {len(index['questions'])} questions "
          f"(slug -> chapter, section, printed number, both page numbers)")

    if all_warnings:
        print(f"\n  {len(all_warnings)} warning(s):")
        for warning in all_warnings[:12]:
            print(f"    {warning}")
    else:
        print("\n  no warnings — every verified question placed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
