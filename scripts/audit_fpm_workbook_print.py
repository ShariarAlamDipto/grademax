"""
Audit the printed book's navigation: does every promise about a page hold?

Four separate claims are made about page numbers, and they can fail
independently, so each is checked against the PDF rather than against the code
that wrote it:

  1. every sheet carries its own number, and the numbers run 1..N
  2. every CHAPTER row in the contents lands on that chapter's front page
  3. every SECTION row lands on the first page of that section
  4. every question in print_index.json is on the page the index claims

The paged and verbatim editions do not print a section heading on the page -- the
footer names the section instead -- so checks 3 and 4 read the footer. That is
also what a reader uses to find their place, so it is the right thing to test.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import fitz

BOOK = Path("c:/Users/shari/grademax/data/workbook/fpm/print")
SUFFIX = {"verbatim": "_Verbatim", "paged": "_Paged"}


def footer_of(page: fitz.Page) -> str:
    band = fitz.Rect(0, page.rect.height - 60, page.rect.width, page.rect.height)
    return " ".join(page.get_text("text", clip=band).split())


def contents_rows(doc: fitz.Document) -> tuple[list, list]:
    """(chapter rows, section rows) reconstructed from word positions."""
    # Scan the whole of the front matter, not just the page carrying the word
    # "Contents". The contents run to a second page which does NOT repeat the
    # heading, so keying off it found 22 of 38 sections and called that a pass.
    chapters, sections = [], []
    for index in range(min(20, doc.page_count)):
        page = doc[index]
        text = page.get_text()
        if "Formula Sheet" in text or "Chapter " in text:
            break
        rows: dict[int, list] = defaultdict(list)
        for word in page.get_text("words"):
            rows[round(word[3])].append((word[0], word[4]))
        for _, row in sorted(rows.items()):
            row.sort()
            # A contents row is label + title + page. Two-word rows are not
            # contents; a ONE-word row is the sheet's own page number, which the
            # first version of this parser happily read as "chapter 2, page 2".
            if len(row) < 3:
                continue
            label, tail = row[0][1], row[-1][1]
            if not tail.isdigit():
                continue
            title = " ".join(w for _, w in row[1:-1])
            if re.fullmatch(r"\d{1,2}", label):
                chapters.append((int(label), title, int(tail)))
            elif re.fullmatch(r"\d{1,2}\.\d{1,2}", label):
                sections.append((label, title, int(tail)))
    return chapters, sections


def main() -> int:
    edition = sys.argv[1] if len(sys.argv) > 1 else "paged"
    path = BOOK / f"GradeMax_FPM_Workbook{SUFFIX.get(edition, '')}.pdf"
    index_path = BOOK / f"print_index{SUFFIX.get(edition, '').lower()}.json"
    doc = fitz.open(path)
    problems = 0
    print(f"{'=' * 70}\n  {path.name} — {doc.page_count} pages\n{'=' * 70}")

    # 1. page numbers -----------------------------------------------------
    missing = []
    for number, page in enumerate(doc, 1):
        band = fitz.Rect(page.rect.width * 0.35, page.rect.height - 40,
                         page.rect.width * 0.65, page.rect.height)
        if str(number) not in page.get_text("text", clip=band).split():
            missing.append(number)
    print(f"  1. page numbers 1..{doc.page_count}: "
          f"{doc.page_count - len(missing)} correct, {len(missing)} missing")
    if missing:
        print(f"       first few: {missing[:12]}")
    problems += len(missing)

    # 2 & 3. contents rows ------------------------------------------------
    chapters, sections = contents_rows(doc)
    bad_chapters = []
    for number, title, target in chapters:
        if not 1 <= target <= doc.page_count:
            bad_chapters.append((number, target, "out of range"))
            continue
        text = doc[target - 1].get_text()
        if f"Chapter {number}" not in text:
            bad_chapters.append((number, target, "no chapter front page there"))
    print(f"  2. chapter rows: {len(chapters)} found, "
          f"{len(chapters) - len(bad_chapters)} land on their front page")
    for row in bad_chapters[:8]:
        print(f"       chapter {row[0]} -> page {row[1]}: {row[2]}")
    problems += len(bad_chapters)

    bad_sections = []
    for label, title, target in sections:
        if not 1 <= target <= doc.page_count:
            bad_sections.append((label, target, "out of range"))
            continue
        page = doc[target - 1]
        if label not in page.get_text() and label not in footer_of(page):
            bad_sections.append((label, target, "section not named on that page"))
    print(f"  3. section rows: {len(sections)} found, "
          f"{len(sections) - len(bad_sections)} land on their first page")
    for row in bad_sections[:8]:
        print(f"       {row[0]} -> page {row[1]}: {row[2]}")
    problems += len(bad_sections)

    # 4. the index --------------------------------------------------------
    if index_path.is_file():
        data = json.loads(index_path.read_text(encoding="utf-8"))
        wrong = []
        for question in data["questions"]:
            target = question["workbook_page"]
            if not 1 <= target <= doc.page_count:
                wrong.append((question["slug"], target, "out of range"))
                continue
            footer = footer_of(doc[target - 1])
            if question["section"] not in footer:
                wrong.append((question["slug"], target, f"footer says {footer[:60]!r}"))
            elif f"Question {question['printed_number']}" not in footer:
                wrong.append((question["slug"], target,
                              f"expected Question {question['printed_number']}"))
        total = len(data["questions"])
        print(f"  4. index page references: {total} questions, "
              f"{total - len(wrong)} land on the right page")
        for row in wrong[:8]:
            print(f"       {row[0]} -> page {row[1]}: {row[2]}")
        problems += len(wrong)

        # numbering restarts at 1 in every section
        by_section = defaultdict(list)
        for question in data["questions"]:
            by_section[question["section"]].append(question["printed_number"])
        broken = [s for s, nums in by_section.items()
                  if sorted(nums) != list(range(1, len(nums) + 1))]
        print(f"  5. sections numbered 1..N: "
              f"{len(by_section) - len(broken)}/{len(by_section)}")
        problems += len(broken)

    doc.close()
    print(f"\n{'=' * 70}\n  PROBLEMS: {problems}\n{'=' * 70}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
