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

from lib.workbook_ink import Band, content_layout, question_number_box
from lib.workbook_layout import (
    INK, MARGIN, MUTED, NO_SPACE, PAGE_HEIGHT, PAGE_WIDTH, PRINT_POLICY, RULE,
    Flow,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SEGMENT_DIR = REPO_ROOT / "data" / "workbook" / "fpm"
BOOK_DIR = SEGMENT_DIR / "print"

# How far in from a band's edge the hanging indent reaches.
NUMBER_ZONE = 30.0

SUBJECT_CODE = "4PM1"
SUBJECT_TITLE = "Edexcel International GCSE"
SUBJECT_NAME = "Further Pure Mathematics"
SUBJECT_SUB = "Chapterwise Practice Workbook  ·  2016–2022"
BRAND = "GradeMax"

SESSION_LABEL = {
    "jan": "January", "may-jun": "May/June",
    "oct-nov": "October/November", "specimen": "Specimen",
}

FOOTER_BASELINE = PAGE_HEIGHT - 26.0 + 12.0
CONTENTS_ROW = 20.0
CONTENTS_TOP = 132.0
CONTENTS_BOTTOM = PAGE_HEIGHT - 90.0


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


def load_book(supabase) -> tuple[list[dict], dict[str, list[dict]]]:
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


def stamp_page_numbers(doc: fitz.Document, kind: str) -> None:
    """
    Number every sheet, so the contents can be trusted and a reader can be told
    "turn to page 148" without qualification.
    """
    tail = f"{BRAND}  ·  {SUBJECT_NAME}" + ("  ·  Mark Schemes" if kind == "ms" else "")
    for number, page in enumerate(doc, 1):
        label = str(number)
        width = fitz.get_text_length(label, fontname="hebo", fontsize=9)
        page.insert_text(((PAGE_WIDTH - width) / 2, FOOTER_BASELINE), label,
                         fontname="hebo", fontsize=9, color=INK)
        page.insert_text((MARGIN, FOOTER_BASELINE), tail,
                         fontname="helv", fontsize=7.4, color=MUTED)


def assemble(chapters, by_chapter, kind: str) -> tuple[fitz.Document, int, list[str]]:
    """Returns the finished book, the front-matter length, and any warnings."""
    body, entries, warnings = build_body(chapters, by_chapter, kind)

    # The contents shift the body, and their own length depends on the entry
    # count -- which is already known, so one pass settles it. Laying them out
    # once with a zero offset just measures how long they are.
    probe = contents_pages(entries, 0, kind)
    offset = probe.page_count
    probe.close()

    front = contents_pages(entries, offset, kind)
    if front.page_count != offset:
        raise RuntimeError(
            f"contents length changed between passes ({offset} -> {front.page_count}); "
            "every page reference in the book would be wrong")

    front.insert_pdf(body)
    body.close()
    stamp_page_numbers(front, kind)
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
    args = parser.parse_args()

    supabase = create_client(os.environ["NEXT_PUBLIC_SUPABASE_URL"],
                             os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    chapters, by_chapter = load_book(supabase)
    total = sum(len(by_chapter.get(c["id"], [])) for c in chapters)

    print(f"{'=' * 74}\nFPM WORKBOOK — PRINT EDITION  "
          f"[{'EXECUTE' if args.execute else 'DRY RUN'}]\n{'=' * 74}")
    print(f"  verified questions : {total}")
    print(f"  working space      : {PRINT_POLICY.describe()}")
    print(f"  numbering          : restarts at 1 in every section")
    print(f"  mark schemes       : separate book; linked digitally by slug")

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

    for kind, name in (("qp", "GradeMax_FPM_Workbook.pdf"),
                       ("ms", "GradeMax_FPM_Workbook_MarkSchemes.pdf")):
        doc, offset, warnings = assemble(chapters, by_chapter, kind)
        all_warnings.extend(warnings)
        target = BOOK_DIR / name
        doc.save(target, deflate=True, garbage=3)
        offsets[kind] = offset
        outputs[kind] = target
        print(f"\n  {name}\n      {doc.page_count} pages "
              f"({offset} front matter), {target.stat().st_size // 1024} KB")
        doc.close()

    index = write_index(chapters, by_chapter, offsets)
    index_path = BOOK_DIR / "print_index.json"
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
