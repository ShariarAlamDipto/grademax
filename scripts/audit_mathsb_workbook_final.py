"""
Final audit of the Maths B files that go to the printer.

Runs against data/workbook/mathsb/print/final/ -- the covered, watermarked
volumes -- not against the builder's output, so the two sheets the covers added
are part of what is being checked.

    python scripts/audit_mathsb_workbook_final.py
    python scripts/audit_mathsb_workbook_final.py paged 1     # two-part edition
    python scripts/audit_mathsb_workbook_final.py paged all
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fitz

from audit_mathsb_workbook_print import contents_rows, footer_of
from lib import workbook_total_band
from lib.workbook_finish import load_watermark
from lib.workbook_print_audit import (furniture, navigation, press_readiness,
                                       report)

ROOT = Path(__file__).resolve().parent.parent
PRINT = ROOT / "data" / "workbook" / "mathsb" / "print"
FINAL = PRINT / "final"

COVER_SHEETS = 1
SUFFIX = {"paged": "_Paged", "verbatim": "_Verbatim", "trimmed": ""}

ART = Path.home() / "OneDrive" / "Desktop" / "FPM cover" / "Final Cover"
WATERMARK = ART / "Final Water Mark" / "FINAL WATERMARK.png"
COVER_TOKENS = ("CHAPTERWISE WORKBOOK", "SIX STRANDS,")


def trimmed_check(question: dict, page: fitz.Page, footer_of) -> str | None:
    """
    The trimmed edition names the chapter in the header and the section in a
    heading band; a question sharing a sheet with the one before it carries
    neither, so what is checked is the SOURCE reference printed beside it.
    """
    marker = question["source"].split(" Q")[0]
    if marker not in " ".join(page.get_text().split()):
        return f"{question['slug']}: {marker!r} not on that page"
    return None


def paged_check(question: dict, page: fitz.Page, footer_of) -> str | None:
    """
    The paged edition prints the source in the running HEADER, abbreviated
    ("May/Jun" where the index says "May/June"), so the source string is not
    what to match on. The footer carries the section and the workbook's own
    question number, which is what a reader navigates by.

    A sheet holding two packed questions names a RANGE -- "Questions 20-21" --
    so the number is checked for membership, not for an exact string. Demanding
    "Question 20" failed 126 questions that were on exactly the page they
    claimed.
    """
    footer = footer_of(page)
    number = question["printed_number"]
    if question["section"] not in footer:
        return f"{question['slug']}: footer reads {footer[:50]!r}"

    span = re.search(r"Questions (\d+)\s*-\s*(\d+)", footer)
    if span:
        if int(span.group(1)) <= number <= int(span.group(2)):
            return None
    elif re.search(rf"Question {number}\b", footer):
        return None
    return (f"{question['slug']}: footer {footer[-28:]!r} does not cover "
            f"Question {number}")


def audit(edition: str, part: int | None, mark) -> int:
    """Both volumes of one part, or of the undivided book. Returns failures."""
    tag = "" if part is None else f"_Part{part}"
    # The index and the check both follow the edition. Reading the trimmed
    # index against a paged book fails all 742 questions at once, which looks
    # like a broken book and is a broken audit. The same is true across parts:
    # each renumbers its pages from one, so each has its own index.
    index_check = trimmed_check if edition == "trimmed" else paged_check
    index_path = PRINT / f"print_index{SUFFIX[edition].lower()}{tag.lower()}.json"
    if not index_path.is_file():
        print(f"missing index: {index_path}")
        return 1
    questions = json.loads(index_path.read_text(encoding="utf-8"))["questions"]

    suffix = " - Part {}".format(part) if part else ""
    volumes = (
        (f"Mathematics B 4MB1 - Question book{suffix}",
         FINAL / f"Mathematics_B_Workbook_PRINT{tag}.pdf", questions),
        (f"Mathematics B 4MB1 - Mark scheme book{suffix}",
         FINAL / f"Mathematics_B_MarkSchemes_PRINT{tag}.pdf", []),
    )

    problems = 0
    for title, path, index in volumes:
        if not path.is_file():
            print(f"\nnot finalised: {path}")
            problems += 1
            continue
        book = fitz.open(path)
        found = navigation(book, index, COVER_SHEETS, contents_rows, footer_of,
                           index_check) if index else []
        if index:
            found += workbook_total_band.verify(book, index, offset=COVER_SHEETS)
        physical = furniture(book, mark, COVER_TOKENS)
        press = press_readiness(book, COVER_SHEETS)
        problems += report(title, path, found, press, book.page_count, physical)
        book.close()
    return problems


def main() -> int:
    edition = sys.argv[1] if len(sys.argv) > 1 else "paged"
    if edition not in SUFFIX:
        print(f"unknown edition {edition!r}; expected one of {sorted(SUFFIX)}")
        return 2
    choice = sys.argv[2] if len(sys.argv) > 2 else None
    if choice not in (None, "1", "2", "all"):
        print(f"unknown part {choice!r}; expected 1, 2 or all")
        return 2
    parts: list[int | None] = ([1, 2] if choice == "all"
                               else [int(choice)] if choice else [None])

    mark = load_watermark(WATERMARK)
    problems = sum(audit(edition, part, mark) for part in parts)

    print(f"\n{'=' * 74}\n  FAILURES: {problems}\n{'=' * 74}")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
