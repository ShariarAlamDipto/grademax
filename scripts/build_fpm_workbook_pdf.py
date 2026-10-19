"""
Phase 5: assemble the Further Pure Maths chapterwise workbook into printable PDFs.

Reads the curated layer from the DATABASE -- not from the classification files --
because the database is where human verification lives. A question a reviewer
moved from 6.1 to 6.6 prints in chapter 6 section 6, and the JSON that proposed
6.1 is irrelevant by then.

OUTPUT
------
    data/workbook/fpm/book/00_Contents.pdf
    data/workbook/fpm/book/Chapter_09_Calculus.pdf
    data/workbook/fpm/book/Chapter_09_Calculus_MarkScheme.pdf
    ...

Questions and mark schemes are separate documents on purpose: a student works a
chapter, then checks it. Binding them together makes the answer one page-turn
from the question.

VERIFIED ONLY, BY DEFAULT
-------------------------
Only questions a human has signed off are printed. The whole point of Phase 4 is
that the classifier is roughly 70% right and confidently wrong the rest of the
time, so an unverified book would quietly file questions in chapters they do not
belong to -- and a student practising "Circle theorems" would meet a matrix
question with no way to know which of them was mistaken.

`--include-unverified` prints them anyway for proofing, and stamps every
unverified question DRAFT - UNVERIFIED so no such page can be mistaken for
finished work.

PAGE LAYOUT
-----------
The book decides the working space; it does not inherit it. An exam paper is
sized for the worst-case candidate writing large, so reprinting its pages
verbatim gives a book that measures 90% white -- 1,279 FPM source pages carrying
124 pages of actual question.

So each segment is reduced to its bands of real content (lib/workbook_ink), and
each question is then given room to work as a function of its marks
(lib/workbook_layout). `--space compact|standard|generous` moves that dial;
mark schemes get none, being read rather than written on.

USAGE
-----
    python scripts/build_fpm_workbook_pdf.py                     # dry run
    python scripts/build_fpm_workbook_pdf.py --execute
    python scripts/build_fpm_workbook_pdf.py --execute --include-unverified
    python scripts/build_fpm_workbook_pdf.py --execute --chapter 6
    python scripts/build_fpm_workbook_pdf.py --execute --space compact
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

import fitz
from dotenv import load_dotenv
from supabase import create_client

from lib.workbook_ink import Band, content_bands
from lib.workbook_layout import (
    DEFAULT_POLICY, DRAFT, INK, MARGIN, MUTED, NO_SPACE, PAGE_HEIGHT, PAGE_WIDTH,
    POLICIES, RULE, Flow, add_page_numbers,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SEGMENT_DIR = REPO_ROOT / "data" / "workbook" / "fpm"
BOOK_DIR = SEGMENT_DIR / "book"

SUBJECT_CODE = "4PM1"
SUBJECT_TITLE = "Edexcel International GCSE Further Pure Mathematics (4PM1)"

SESSION_LABEL = {
    "jan": "January",
    "may-jun": "May/June",
    "oct-nov": "October/November",
    "specimen": "Specimen",
}


def fetch_all(query_builder, page_size: int = 1000) -> list[dict]:
    """
    Page through a PostgREST query.

    PostgREST caps a response at 1000 rows and says nothing about it, so a plain
    .execute() on a table this size silently truncates -- which is exactly how
    46 questions nearly went missing from the review queue.
    """
    rows: list[dict] = []
    page = 0
    while True:
        batch = query_builder().range(page * page_size, page * page_size + page_size - 1).execute().data
        rows.extend(batch)
        if len(batch) < page_size:
            return rows
        page += 1


def load_book(supabase, include_unverified: bool) -> tuple[list[dict], dict[str, list[dict]]]:
    """Return (chapters, questions grouped by chapter id), in print order."""
    subject_id = (
        supabase.table("subjects").select("id").eq("code", SUBJECT_CODE).single().execute().data["id"]
    )

    chapters = (
        supabase.table("workbook_chapters")
        .select("id,number,title")
        .eq("subject_id", subject_id)
        .order("number")
        .execute()
        .data
    )
    chapter_ids = [c["id"] for c in chapters]

    sections = (
        supabase.table("workbook_sections")
        .select("id,chapter_id,number,title")
        .in_("chapter_id", chapter_ids)
        .execute()
        .data
    )
    section_by_id = {s["id"]: s for s in sections}

    def question_query():
        query = (
            supabase.table("workbook_questions")
            .select(
                "id,slug,section_id,ordinal_in_chapter,marks,difficulty,"
                "source_paper_key,source_question_number,verified_at,ms_pdf_url"
            )
            .eq("subject_id", subject_id)
            .order("ordinal_in_chapter")
        )
        if not include_unverified:
            query = query.not_.is_("verified_at", "null")
        return query

    questions = fetch_all(question_query)

    by_chapter: dict[str, list[dict]] = defaultdict(list)
    for question in questions:
        section = section_by_id.get(question["section_id"])
        if section is None:
            continue  # a section deleted under it; skip rather than misfile
        question["_section"] = section
        by_chapter[section["chapter_id"]].append(question)

    # Section order, then the ordinal the loader assigned (archetype cluster,
    # marks ascending, chronological). Sorting here keeps the book's order a
    # property of the data rather than of the row order the database returns.
    for rows in by_chapter.values():
        rows.sort(key=lambda q: (q["_section"]["number"], q["ordinal_in_chapter"]))

    return chapters, by_chapter


def segment_path(question: dict, kind: str) -> Path:
    folder = "questions" if kind == "qp" else "markschemes"
    return SEGMENT_DIR / question["source_paper_key"] / folder / f"q{question['source_question_number']}.pdf"


def source_label(question: dict) -> str:
    year, season, paper = question["source_paper_key"].split("_")
    return f"{year} {SESSION_LABEL.get(season, season.title())} Paper {paper} Q{question['source_question_number']}"


def title_page(doc: fitz.Document, chapter: dict, questions: list[dict],
               kind: str, draft_count: int) -> None:
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    y = 150.0

    page.insert_text((MARGIN, y), SUBJECT_TITLE, fontname="helv", fontsize=10, color=MUTED)
    y += 34
    page.insert_text((MARGIN, y), f"Chapter {chapter['number']}", fontname="helv", fontsize=13, color=MUTED)
    y += 30
    page.insert_text((MARGIN, y), chapter["title"], fontname="hebo", fontsize=23, color=INK)
    y += 16
    page.draw_line(fitz.Point(MARGIN, y), fitz.Point(PAGE_WIDTH - MARGIN, y), color=RULE, width=1)
    y += 26

    if kind == "ms":
        page.insert_text((MARGIN, y), "Mark schemes", fontname="hebo", fontsize=13, color=INK)
        y += 26

    by_section: dict[int, list[dict]] = defaultdict(list)
    for question in questions:
        by_section[question["_section"]["number"]].append(question)

    for number in sorted(by_section):
        rows = by_section[number]
        title = rows[0]["_section"]["title"]
        marks = sum(r["marks"] for r in rows)
        page.insert_text((MARGIN, y), f"{chapter['number']}.{number}", fontname="hebo", fontsize=10, color=MUTED)
        page.insert_text((MARGIN + 42, y), title, fontname="helv", fontsize=10.5, color=INK)
        tail = f"{len(rows)} questions · {marks} marks"
        width = fitz.get_text_length(tail, fontname="helv", fontsize=9)
        page.insert_text((PAGE_WIDTH - MARGIN - width, y), tail, fontname="helv", fontsize=9, color=MUTED)
        y += 21
        if y > PAGE_HEIGHT - 120:
            break

    total_marks = sum(q["marks"] for q in questions)
    y = PAGE_HEIGHT - 96
    page.draw_line(fitz.Point(MARGIN, y - 16), fitz.Point(PAGE_WIDTH - MARGIN, y - 16), color=RULE, width=0.6)
    page.insert_text(
        (MARGIN, y), f"{len(questions)} questions · {total_marks} marks",
        fontname="helv", fontsize=10, color=INK,
    )
    if draft_count:
        page.insert_text(
            (MARGIN, y + 17),
            f"DRAFT — {draft_count} question(s) not yet verified by a teacher",
            fontname="hebo", fontsize=9.5, color=DRAFT,
        )


def whole_pages(source: fitz.Document) -> list[Band]:
    """
    Last resort when the trim finds nothing to keep.

    Printing the untrimmed pages wastes paper; printing nothing loses the
    question. A question missing from the book is the worse failure, so the
    fallback is deliberately the wasteful one.
    """
    return [Band(index, 0.0, source[index].rect.height,
                 source[index].rect.x0, source[index].rect.x1)
            for index in range(source.page_count)]


def build_chapter(chapter: dict, questions: list[dict], kind: str,
                  policy) -> tuple[fitz.Document | None, int, list[str]]:
    """Assemble one chapter. Returns (document, questions placed, warnings)."""
    warnings: list[str] = []
    draft_count = sum(1 for q in questions if not q["verified_at"])

    doc = fitz.open()
    title_page(doc, chapter, questions, kind, draft_count)

    running = f"Chapter {chapter['number']}  ·  {chapter['title']}"
    if kind == "ms":
        running += "  ·  Mark schemes"
    # A mark scheme is read, not written on, so it gets no working space.
    flow = Flow(doc, running, NO_SPACE if kind == "ms" else policy)

    placed = 0
    current_section: int | None = None

    for question in questions:
        path = segment_path(question, kind)
        if not path.is_file():
            if kind == "qp":
                warnings.append(f"{question['slug']}: missing {path.name}")
            continue

        section = question["_section"]
        if section["number"] != current_section:
            current_section = section["number"]
            flow.section_break(f"{chapter['number']}.{section['number']}  {section['title']}")

        label = f"Q{question['ordinal_in_chapter']}"
        right = f"{question['marks']} marks  ·  {source_label(question)}"
        if not question["verified_at"]:
            right = f"DRAFT — UNVERIFIED  ·  {right}"

        try:
            with fitz.open(path) as source:
                bands = content_bands(source)
                if not bands:
                    warnings.append(f"{question['slug']}: no content found; printing whole pages")
                    bands = whole_pages(source)
                flow.add(source, bands, label, right, question["marks"], not question["verified_at"])
            placed += 1
        except Exception as error:  # noqa: BLE001 - one bad PDF must not lose the chapter
            warnings.append(f"{question['slug']}: {error}")

    if placed == 0:
        doc.close()
        return None, 0, warnings

    label = f"{SUBJECT_TITLE.split('(')[0].strip()} · Chapter {chapter['number']}"
    add_page_numbers(doc, label + ("  ·  Mark schemes" if kind == "ms" else ""))
    return doc, placed, warnings


def contents_page(chapters: list[dict], by_chapter: dict[str, list[dict]], draft: bool) -> fitz.Document:
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    y = 120.0

    page.insert_text((MARGIN, y), SUBJECT_TITLE, fontname="helv", fontsize=10, color=MUTED)
    y += 32
    page.insert_text((MARGIN, y), "Chapterwise Practice Workbook", fontname="hebo", fontsize=22, color=INK)
    y += 18
    page.insert_text((MARGIN, y), "2016 – 2022 past papers, arranged by topic",
                     fontname="helv", fontsize=10.5, color=MUTED)
    y += 14
    page.draw_line(fitz.Point(MARGIN, y), fitz.Point(PAGE_WIDTH - MARGIN, y), color=RULE, width=1)
    y += 30

    total = 0
    for chapter in chapters:
        rows = by_chapter.get(chapter["id"], [])
        if not rows:
            continue
        total += len(rows)
        marks = sum(r["marks"] for r in rows)
        page.insert_text((MARGIN, y), f"{chapter['number']:>2}", fontname="hebo", fontsize=11, color=MUTED)
        page.insert_text((MARGIN + 28, y), chapter["title"], fontname="helv", fontsize=11.5, color=INK)
        tail = f"{len(rows)} questions · {marks} marks"
        width = fitz.get_text_length(tail, fontname="helv", fontsize=9)
        page.insert_text((PAGE_WIDTH - MARGIN - width, y), tail, fontname="helv", fontsize=9, color=MUTED)
        y += 24

    y += 12
    page.draw_line(fitz.Point(MARGIN, y), fitz.Point(PAGE_WIDTH - MARGIN, y), color=RULE, width=0.6)
    y += 20
    page.insert_text((MARGIN, y), f"{total} questions in total", fontname="hebo", fontsize=11, color=INK)
    if draft:
        y += 20
        page.insert_text(
            (MARGIN, y),
            "DRAFT — includes questions whose chapter has not been verified by a teacher.",
            fontname="hebo", fontsize=9.5, color=DRAFT,
        )
    return doc


def main() -> int:
    load_dotenv(REPO_ROOT / ".env.local")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="write the PDFs")
    parser.add_argument("--include-unverified", action="store_true",
                        help="print unverified questions, stamped DRAFT")
    parser.add_argument("--chapter", type=int, help="build only this chapter number")
    parser.add_argument("--space", choices=sorted(POLICIES), default=DEFAULT_POLICY,
                        help="how much working space each question gets, per mark")
    args = parser.parse_args()

    policy = POLICIES[args.space]

    supabase = create_client(
        os.environ["NEXT_PUBLIC_SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    )
    chapters, by_chapter = load_book(supabase, args.include_unverified)

    if args.chapter:
        chapters = [c for c in chapters if c["number"] == args.chapter]

    total_questions = sum(len(by_chapter.get(c["id"], [])) for c in chapters)
    mode = "EXECUTE" if args.execute else "DRY RUN"
    scope = "verified + UNVERIFIED (draft)" if args.include_unverified else "verified only"

    print(f"{'=' * 74}\nFPM WORKBOOK — CHAPTER PDFs  [{mode}]\n{'=' * 74}")
    print(f"  source   : the database, so human verification decides the chapter")
    print(f"  scope    : {scope}")
    print(f"  questions: {total_questions}")
    print(f"  space    : {policy.name} — {policy.points_per_mark:.0f}pt per mark, "
          f"floor {policy.minimum:.0f}pt, cap {policy.maximum:.0f}pt")

    if total_questions == 0:
        print("\n  Nothing to print.")
        if not args.include_unverified:
            print("  No question has been verified yet. Re-run with --include-unverified")
            print("  for a draft, or sign questions off at /admin/workbook/verify.")
        return 0

    if args.execute:
        BOOK_DIR.mkdir(parents=True, exist_ok=True)

    all_warnings: list[str] = []
    written = 0

    for chapter in chapters:
        questions = by_chapter.get(chapter["id"], [])
        if not questions:
            continue

        drafts = sum(1 for q in questions if not q["verified_at"])
        marks = sum(q["marks"] for q in questions)
        flag = f"  ({drafts} draft)" if drafts else ""
        print(f"\n  Chapter {chapter['number']:>2}  {chapter['title'][:44]:<44} "
              f"{len(questions):>4} questions  {marks:>4} marks{flag}")

        if not args.execute:
            continue

        safe = "".join(ch if ch.isalnum() else "_" for ch in chapter["title"]).strip("_")
        for kind, suffix in (("qp", ""), ("ms", "_MarkScheme")):
            doc, placed, warnings = build_chapter(chapter, questions, kind, policy)
            all_warnings.extend(warnings)
            if doc is None:
                print(f"      {kind}: nothing to place")
                continue
            target = BOOK_DIR / f"Chapter_{chapter['number']:02d}_{safe}{suffix}.pdf"
            doc.save(target, deflate=True, garbage=3)
            doc.close()
            written += 1
            print(f"      {target.name}  ({placed} questions, {target.stat().st_size // 1024} KB)")

    if args.execute:
        contents = contents_page(chapters, by_chapter, args.include_unverified)
        target = BOOK_DIR / "00_Contents.pdf"
        contents.save(target, deflate=True, garbage=3)
        contents.close()
        written += 1
        print(f"\n  {target.name}")
        print(f"\n  files written: {written}  ->  {BOOK_DIR.relative_to(REPO_ROOT)}")
    else:
        print("\n  Dry run -- nothing written. Re-run with --execute.")

    if all_warnings:
        print(f"\n  {len(all_warnings)} warning(s):")
        for warning in all_warnings[:12]:
            print(f"    {warning}")
        if len(all_warnings) > 12:
            print(f"    ... and {len(all_warnings) - 12} more")

    return 0


if __name__ == "__main__":
    sys.exit(main())
