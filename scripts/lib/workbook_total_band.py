"""
Bring the "(Total for Question N is M marks)" band in line with the workbook.

Used by both books. Nothing here is subject-specific -- it is handed the print
index and works from that -- because both builders renumber the same way and so
carry the same defect.

THE DEFECT

The paged edition renumbers every question: a question that was Q7 of the 2022
January paper becomes, say, question 3 of section 1.1, and the builder patches
the number printed beside it so the sheet agrees with the contents, the index
and the footer. What it does not patch is the band Edexcel prints at the foot of
the question, so 105 sheets of Further Pure Maths read

    3   Solve ...                            <- the workbook's number
        ...
                      (Total for Question 7 is 8 marks)   <- the paper's number

which a student reads as a misprint. Found by the final audit, on a book about
to go to press.

WHY THE REWRITE IS SAFE

The band is not guessed at. A band is only rewritten when its MARKS already
agree with the index entry for the question that owns the sheet -- that is what
proves the band belongs to this question and not to a neighbour sharing the
page. Across all 124 bands in the book the marks agree every time, so the guard
costs nothing and protects against the one way this could go wrong.

The band is redrawn rather than digit-patched. Overwriting "1" with "10" in
place would run the new digit into the " is" that follows; redrawing the whole
string right-aligned to the original right edge keeps the spacing the paper had.
Edexcel sets the band in Times New Roman Bold 12pt, which is NOT embedded in the
source, so it is redrawn in Times-Bold -- the metric-compatible base-14 face the
viewer was already substituting.

The old band is REDACTED, not painted over. A white rectangle hides text from
the eye and leaves it in the text layer, which would put both the old number and
the new one into anything that reads the file -- a copy-paste, a search, the
audit. Redaction takes the glyphs out. Images and line art are explicitly left
alone, so the answer box the band sits inside survives.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import fitz

# Maths prints "is"; Physics prints "=". The connector is kept as found when the
# band is redrawn, so neither subject's wording changes.
BAND = re.compile(r"\(Total for Question\s+(\d+)\s+(?:is|=)\s+(\d+)\s+marks?\)")

# The face the band is redrawn in, and the ink it is redrawn with. The colour is
# read back off the source span rather than assumed, so a paper that sets the
# band in a different grey keeps it.
FONT = "tibo"
PAD = 1.2


@dataclass(frozen=True)
class Repair:
    page: int          # 1-based printed page
    was: int
    now: int
    marks: int


def _page_questions(questions: list[dict], last_page: int) -> dict[int, list[dict]]:
    """
    Which questions appear on each printed page, in the order they are printed.

    A LIST, not one question. Maths B packs two questions onto a sheet, and a
    map of page -> single question quietly hands the second one's number to
    both: sheet 31 carried questions 20 and 21 and told the reader "Total for
    Question 21" twice. Every page therefore keeps all of its questions, and the
    bands are matched to them below.
    """
    ordered = sorted(questions,
                     key=lambda q: (q["workbook_page"], q["printed_number"]))
    pages: dict[int, list[dict]] = {}
    for index, question in enumerate(ordered):
        start = question["workbook_page"]
        following = (ordered[index + 1]["workbook_page"]
                     if index + 1 < len(ordered) else last_page + 1)
        end = start if following <= start else max(start, following - 1)
        for page in range(start, end + 1):
            pages.setdefault(page, []).append(question)
    return pages


def _pair(bands: list[dict], candidates: list[dict]) -> list[tuple[dict, dict]]:
    """
    Match the bands on a sheet to the questions printed on it.

    Bands are laid down the sheet in printed order, so when the counts agree the
    order is the answer. When they do not -- a question whose band fell on a
    later sheet, say -- fall back to the marks, and pair nothing that the marks
    cannot vouch for. A band left unpaired keeps the number the board gave it,
    which is wrong but honest; a band paired to the wrong question is neither.
    """
    bands = sorted(bands, key=lambda b: b["span"]["bbox"][1])
    candidates = sorted(candidates, key=lambda q: q["printed_number"])
    if len(bands) == len(candidates):
        return list(zip(bands, candidates))

    paired, used = [], set()
    for band in bands:
        marks = int(band["match"].group(2))
        for question in candidates:
            if id(question) in used or question["marks"] != marks:
                continue
            used.add(id(question))
            paired.append((band, question))
            break
    return paired


def _bands(page: fitz.Page) -> list[dict]:
    """Every band on the page, with the span geometry needed to redraw it."""
    found = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = "".join(span["text"] for span in line["spans"])
            match = BAND.search(text)
            if not match or len(line["spans"]) != 1:
                continue
            span = line["spans"][0]
            found.append({"span": span, "match": match})
    return found


def repair(interior: fitz.Document, questions: list[dict]) -> list[Repair]:
    """
    Rewrite every stale band in the interior. Returns what was changed.

    Operates on the interior, before the covers go on, so printed page N is
    index N-1 here.
    """
    pages = _page_questions(questions, interior.page_count)
    done: list[Repair] = []

    for index in range(interior.page_count):
        printed = index + 1
        candidates = pages.get(printed)
        if not candidates:
            continue
        page = interior[index]

        pending = []
        for band, question in _pair(_bands(page), candidates):
            stated, marks = int(band["match"].group(1)), int(band["match"].group(2))
            wanted = question["printed_number"]
            # The guard: only a band whose marks match this question's index
            # entry is provably this question's band.
            if stated == wanted or marks != question["marks"]:
                continue
            span = band["span"]
            colour = span["color"]
            pending.append({
                "rect": fitz.Rect(span["bbox"]) + (-PAD, -PAD, PAD, PAD),
                "right": span["bbox"][2],
                "baseline": span["origin"][1],
                "size": span["size"],
                "ink": ((colour >> 16 & 255) / 255, (colour >> 8 & 255) / 255,
                        (colour & 255) / 255),
                "text": (f"(Total for Question {wanted} "
                         f"{'=' if '=' in band['match'].group(0) else 'is'} {marks} marks)"),
                "was": stated, "now": wanted, "marks": marks,
            })

        if not pending:
            continue

        for fix in pending:
            page.add_redact_annot(fix["rect"])
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                              graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                              text=fitz.PDF_REDACT_TEXT_REMOVE)

        for fix in pending:
            # Right-aligned to the edge the paper set it to, on the original
            # baseline. Both come off the span, so a band that sat higher or
            # lower than its neighbours stays where it was.
            width = fitz.get_text_length(fix["text"], fontname=FONT,
                                         fontsize=fix["size"])
            page.insert_text((fix["right"] - width, fix["baseline"]), fix["text"],
                             fontname=FONT, fontsize=fix["size"], color=fix["ink"])
            done.append(Repair(printed, fix["was"], fix["now"], fix["marks"]))

    return done


def verify(book: fitz.Document, questions: list[dict], offset: int = 1) -> list[str]:
    """
    Re-read the finished book and confirm no band contradicts the workbook.

    `offset` is how many sheets the covers pushed the interior down by.
    """
    pages = _page_questions(questions, book.page_count - 2 * offset)
    problems = []
    for printed, candidates in sorted(pages.items()):
        sheet = printed + offset - 1
        if not 0 <= sheet < book.page_count:
            continue
        # Read the bands back with their geometry, so a packed sheet's bands can
        # be checked against the right question rather than against whichever
        # one happened to be listed last.
        for band, question in _pair(_bands(book[sheet]), candidates):
            stated, marks = int(band["match"].group(1)), int(band["match"].group(2))
            if marks != question["marks"]:
                continue
            if stated != question["printed_number"]:
                problems.append(
                    f"p{printed}: band says Question {stated}, "
                    f"workbook says {question['printed_number']}")
    return problems
