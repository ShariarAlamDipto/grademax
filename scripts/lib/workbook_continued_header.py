"""
Bring the "Question N continued" page headers in line with the workbook.

The companion of workbook_total_band. IAL papers head every overflow page of a
question with "Question N continued". The paged edition renumbers the question
(the 2025 January Q1 becomes question 6 of section 2.1) and the total band is
already redrawn to match, but the continuation header still read "Question 1
continued" under a question the sheet calls 6.

WHY THE REWRITE IS SAFE

A header is only rewritten when its number is the SOURCE number of the question
that owns the sheet (read off the index's "January 2025 Q1"). That is the
board's own statement that the page belongs to this question, so a header from a
neighbour can never be renumbered to the wrong question.

As with the bands, the old header is REDACTED (glyphs removed from the text
layer, images and line art untouched) and redrawn on its own baseline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import fitz

from .workbook_total_band import _page_questions

HEADER = re.compile(r"^\s*Question\s+(\d{1,2})\s+continued\s*$", re.I)
FONT = "hebo"
PAD = 1.2


@dataclass(frozen=True)
class Repair:
    page: int
    was: int
    now: int


def _source_number(question: dict) -> int:
    return int(question["source"].rsplit("Q", 1)[1])


def _headers(page: fitz.Page) -> list[dict]:
    found = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = [s for s in line["spans"] if s["text"].strip()]
            text = "".join(s["text"] for s in spans)
            match = HEADER.match(text)
            if not match or line["dir"] != (1.0, 0.0):
                continue
            first = spans[0]
            found.append({"number": int(match.group(1)), "bbox": fitz.Rect(line["bbox"]),
                          "origin": first["origin"], "size": first["size"],
                          "color": first["color"]})
    return found


def repair(interior: fitz.Document, questions: list[dict]) -> list[Repair]:
    """Rewrite every stale continuation header in the interior (page N = index N-1)."""
    pages = _page_questions(questions, interior.page_count)
    done: list[Repair] = []
    for index in range(interior.page_count):
        candidates = pages.get(index + 1)
        if not candidates:
            continue
        page = interior[index]
        pending = []
        for header in _headers(page):
            owners = [q for q in candidates if _source_number(q) == header["number"]]
            if len(owners) != 1 or owners[0]["printed_number"] == header["number"]:
                continue
            pending.append((header, owners[0]["printed_number"]))
        if not pending:
            continue
        for header, _ in pending:
            page.add_redact_annot(header["bbox"] + (-PAD, -PAD, PAD, PAD))
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                              graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                              text=fitz.PDF_REDACT_TEXT_REMOVE)
        for header, now in pending:
            colour = header["color"]
            ink = ((colour >> 16 & 255) / 255, (colour >> 8 & 255) / 255, (colour & 255) / 255)
            page.insert_text(header["origin"], f"Question {now} continued",
                             fontname=FONT, fontsize=header["size"], color=ink)
            done.append(Repair(index + 1, header["number"], now))
    return done


def verify(book: fitz.Document, questions: list[dict], offset: int = 1) -> list[str]:
    """No continuation header may name a number other than its question's."""
    pages = _page_questions(questions, book.page_count - 2 * offset)
    problems = []
    for printed, candidates in sorted(pages.items()):
        sheet = printed + offset - 1
        if not 0 <= sheet < book.page_count:
            continue
        numbers = {q["printed_number"] for q in candidates}
        for header in _headers(book[sheet]):
            if header["number"] not in numbers:
                problems.append(f"p{printed}: 'Question {header['number']} continued', "
                                f"workbook prints {sorted(numbers)}")
    return problems
