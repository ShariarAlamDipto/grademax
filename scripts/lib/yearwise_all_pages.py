"""
Label every sheet of an IGCSE / IAL question paper for the 2018-2026 yearwise
books: what is printed, what is dropped, and what is printed once per volume.

Built on `m1_paper_pages.read_paper`, which tiles a paper into questions by
their `(Total for Question n is m marks)` lines and labels each sheet front /
start / content / space / back. That module stays untouched -- M1, S1 and P4
are its regression test. What these books need on top:

    cover      page 1. Dropped: the book's contents names the sitting, and the
               running head on every sheet repeats it.
    reference  a formulae sheet, equation list, data sheet, periodic table or
               the appended Equation Booklet. IDENTICAL from paper to paper, so
               printed ONCE at the front of each volume, never per paper (user
               brief: "repetition of formula sheet is not required").
    blank      "BLANK PAGE" / "There are no questions printed on this page".
               Dropped wherever it falls, including between two questions --
               where `read_paper` would otherwise count it as answer space.
    insert     the paper's OWN insert -- the Unit 5 Scientific Article carries
               the paper's item code bare ("P67793A"). Different for every
               paper, needed to answer it, so it travels with the paper.
    start / content / space   as in read_paper; space is capped by the
               allowance in `pages_to_keep`.

Geometry (measured over every linked Maths B and Physics paper, 2,036 sheets):
595x842, or 652x899 = A4 + 28.5pt bleed each side. After trimming the bleed
the frame never sits above y=35.4 or below y=794.1 and every piece of board
furniture is above y=30.4 or below y=797.6 -- the M1 bands (34pt head, 46pt
foot) are safe here too.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import fitz

from .m1_paper_pages import Page, PaperPages, read_paper, strip_furniture

A4 = fitz.Rect(0, 0, 595.0, 842.0)
BLEED = 28.5

BLANK = re.compile(r"BLANK\s+PAGE|There\s+are\s+no\s+questions\s+(?:printed\s+)?on\s+this\s+page", re.I)
REFERENCE = re.compile(
    r"Formulae\s+sheet|FORMULAE\s+FOR|List\s+of\s+(?:data,\s*)?formulae|Equation\s+Booklet"
    r"|Do\s+not\s+return\s+this\s+Booklet|The\s+Periodic\s+Table|Mathematical\s+Formulae"
    r"|^\s*EQUATIONS\s*$|You\s+may\s+find\s+the\s+following\s+(?:equations|formulae)\s+useful",
    re.I | re.M)
# Below this many real characters (after the furniture strip) a front sheet
# holds nothing of the paper; above it, it is Question 1 opening early.
FRONT_CONTENT_CHARS = 60
ITEM = re.compile(r"\*?(P\d{5}R{0,2}A)\d{4}\*?")


@dataclass
class Sheet:
    index: int
    role: str                   # cover|reference|blank|insert|front|start|content|space|back
    question: int | None = None
    has_total: bool = False
    starts: list[int] = field(default_factory=list)   # questions that open on this sheet


@dataclass
class LabelledPaper:
    path: Path
    sheets: list[Sheet]
    base: PaperPages
    trim: fitz.Rect             # the A4 area to place (bleed removed)

    @property
    def problems(self) -> list[str]:
        return self.base.problems


def trim_box(page: fitz.Page) -> fitz.Rect:
    """The A4 trim of a sheet: the whole page, or the page less a 28.5pt bleed."""
    r = page.rect
    if abs(r.width - (A4.width + 2 * BLEED)) < 2 and abs(r.height - (A4.height + 2 * BLEED)) < 2:
        return fitz.Rect(BLEED, BLEED, r.width - BLEED, r.height - BLEED)
    return fitz.Rect(r)


def label_paper(path: Path, item_code: str | None) -> LabelledPaper:
    base = read_paper(path)
    # read_paper assumes M1's 75 marks; these papers state their own total.
    base.problems[:] = [p for p in base.problems if "not the paper's 75" not in p]
    doc = fitz.open(path)
    bare = re.compile(rf"\b{re.escape(item_code)}\b") if item_code else None
    first_start = next((p.index for p in base.pages if p.role == "start"), None)
    sheets: list[Sheet] = []
    for p in base.pages:
        text = doc[p.index].get_text()
        role = p.role
        if p.index == 0:
            role = "cover"
        elif BLANK.search(text) and len(strip_furniture(text)) < FRONT_CONTENT_CHARS:
            # Whatever read_paper called it: a BLANK PAGE right after question
            # n's total is otherwise taken as question n+1's OPENING sheet.
            role = "blank"
        elif REFERENCE.search(text) and p.role in ("front", "back"):
            role = "reference"
        elif (p.role == "back" and bare and bare.search(text) and not ITEM.search(text)):
            role = "insert"
        elif p.role == "back" and not text.strip():
            role = "blank"
        sheets.append(Sheet(index=p.index, role=role, question=p.question,
                            has_total=p.has_total))
    _recover_question_one(doc, sheets, base)
    _booklet_runs(sheets)
    for q in base.questions:
        # A question's own span, widened back to any sheet recovered for it.
        printed = ("start", "content", "space", "insert")
        own = [s.index for s in sheets if s.question == q.number and s.role in printed]
        span = [p.index for p in q.pages if sheets[p.index].role in printed]
        candidates = own + span
        if candidates:
            sheets[min(candidates)].starts.append(q.number)
    if not base.questions:
        _image_only_fallback(doc, sheets)
    else:
        _image_sheets(doc, sheets, base)
    trim = trim_box(doc[first_start or 0])
    doc.close()
    return LabelledPaper(path=path, sheets=sheets, base=base, trim=trim)


def _recover_question_one(doc: fitz.Document, sheets: list[Sheet], base: PaperPages) -> None:
    """
    `read_paper` opens Question 1 one sheet before its first "Question 1
    continued" -- and, with no such line, on the sheet its total sits on. An
    IGCSE Q1 often runs two sheets with no "continued" line, so its OPENING
    sheet came back as front matter and would have been dropped with the cover.
    Any front sheet with real text that is not a cover, blank or reference
    sheet is therefore Question 1's.
    """
    if not base.questions:
        return
    q1 = base.questions[0].number
    for s in sheets:
        if s.role != "front":
            continue
        body = strip_furniture(doc[s.index].get_text())
        if len(body) >= FRONT_CONTENT_CHARS:
            s.role, s.question = "content", q1


def _booklet_runs(sheets: list[Sheet]) -> None:
    """An appended booklet (Equation Booklet) prints the paper's item code bare
    on its inner pages, like an insert -- but everything after a reference
    sheet at the back is the booklet."""
    last_question = max((s.index for s in sheets if s.question is not None), default=len(sheets))
    in_booklet = False
    for s in sheets[last_question + 1:]:
        if s.role in ("back", "insert", "reference", "blank"):
            if s.role == "reference":
                in_booklet = True
            elif in_booklet:
                s.role = "reference"


def _image_sheets(doc: fitz.Document, sheets: list[Sheet], base: PaperPages) -> None:
    """
    An image-only sheet inside a text paper (Maths B Jan 2019 P1: Q8 and Q9 are
    a picture) hides its questions' totals, so the tiling hands the sheet to
    the NEXT readable question -- and the book would print "Mark scheme: Q10"
    over Q8 and Q9. A picture cannot prove where a question starts: its claimed
    starts move to the next printed sheet, and the question numbers missing
    from the text layer (the holes) are given to the picture instead.
    """
    printed = [s for s in sheets if s.role in ("start", "content", "space", "insert")]
    numbers = sorted(q.number for q in base.questions)
    holes = [n for n in range(1, numbers[-1] + 1) if n not in numbers]
    for k, s in enumerate(printed):
        text = strip_furniture(doc[s.index].get_text())
        if len(text) >= 25 or not doc[s.index].get_images():
            continue
        claimed, s.starts = s.starts, []
        if claimed and k + 1 < len(printed):
            printed[k + 1].starts = claimed + printed[k + 1].starts
        before = max((q for t in printed[:k] for q in t.starts), default=0)
        s.starts = [h for h in holes if h > before and (not claimed or h < min(claimed))]
        holes = [h for h in holes if h not in s.starts]


def _image_only_fallback(doc: fitz.Document, sheets: list[Sheet]) -> None:
    """
    No text layer, so no question can be found (4PH1 Jun 2019 P1, the WPH16 /
    WBI14 scans). Keep every sheet but the cover: an unreadable sheet cannot be
    proven blank, and a lost question is worse than a spare page.
    """
    for s in sheets[1:]:
        s.role = "content"


def pages_to_keep(paper: LabelledPaper, allowance: int) -> list[Sheet]:
    """
    Question sheets and inserts, less the blank answer sides over the allowance.

    The sheet carrying a question's total band is always kept (it is the mark
    tariff, usually alone on an otherwise blank side), and the allowance is
    filled from the EARLIEST blank sides, so a cut comes from the middle.
    """
    dropped: set[int] = set()
    by_index = {s.index: s for s in paper.sheets}
    for q in paper.base.questions:
        space = [by_index[p.index] for p in q.pages if by_index[p.index].role == "space"]
        if len(space) <= allowance:
            continue
        keep = [s for s in space if s.has_total]
        for s in space:
            if len(keep) >= allowance:
                break
            if s not in keep:
                keep.append(s)
        dropped |= {s.index for s in space if s not in keep}
    return [s for s in paper.sheets
            if s.role in ("start", "content", "space", "insert") and s.index not in dropped]


def reference_sheets(paper: LabelledPaper) -> list[int]:
    return [s.index for s in paper.sheets if s.role == "reference"]
