"""
Final audit of the Further Pure Maths files that go to the printer.

Runs against data/workbook/fpm/print/final/ -- the covered, watermarked
volumes -- not against the builder's output, so the two sheets the covers added
are part of what is being checked.

    python scripts/audit_fpm_workbook_final.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fitz

from audit_fpm_workbook_print import contents_rows, footer_of
from lib import workbook_total_band
from lib.workbook_finish import load_watermark
from lib.workbook_print_audit import (furniture, navigation, press_readiness,
                                       report)

ROOT = Path(__file__).resolve().parent.parent
PRINT = ROOT / "data" / "workbook" / "fpm" / "print"
FINAL = PRINT / "final"

COVER_SHEETS = 1  # the front cover; the back cover does not shift anything

ART = Path.home() / "OneDrive" / "Desktop" / "FPM cover" / "Final Cover"
WATERMARK = ART / "Final Water Mark" / "FINAL WATERMARK.png"
COVER_TOKENS = ("CHAPTERWISE WORKBOOK", "TEN CHAPTERS,")


def index_check(question: dict, page: fitz.Page, footer_of) -> str | None:
    """The paged edition names the section and the number in the footer."""
    footer = footer_of(page)
    if question["section"] not in footer:
        return f"{question['slug']}: footer reads {footer[:50]!r}"
    if f"Question {question['printed_number']}" not in footer:
        return (f"{question['slug']}: footer does not say Question "
                f"{question['printed_number']}")
    return None


def main() -> int:
    index_path = PRINT / "print_index_paged.json"
    if not index_path.is_file():
        print(f"missing index: {index_path}")
        return 1
    questions = json.loads(index_path.read_text(encoding="utf-8"))["questions"]
    mark = load_watermark(WATERMARK)

    volumes = (
        ("Further Pure Mathematics 4PM1 - Question book",
         FINAL / "Further_Pure_Mathematics_Workbook_PRINT.pdf", questions),
        ("Further Pure Mathematics 4PM1 - Mark scheme book",
         FINAL / "Further_Pure_Mathematics_MarkSchemes_PRINT.pdf", []),
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

    print(f"\n{'=' * 74}\n  FAILURES: {problems}\n{'=' * 74}")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
