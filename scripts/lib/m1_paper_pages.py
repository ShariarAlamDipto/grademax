"""
Read an M1 question paper as a sequence of labelled pages.

The yearwise workbook reprints the board's own sheets, so the only thing it has
to understand about a paper is what each SHEET is: front matter, the page a
question starts on, a continuation page carrying more of the question, or a
continuation page that is nothing but ruled answer space. That last kind is the
one there is too much of -- Edexcel hands a 6-mark question three further sides
of rules because one printed paper has to suit the largest handwriting in the
cohort.

HOW A PAGE GETS ITS OWNER

Off the board's own furniture, which is more reliable than any layout analysis:

    (Total 9 marks)                 + a `Q1` label in the margin   (to 2022)
    (Total for Question 1 is 7 marks)                              (2023 on)
    Question 1 continued                                           (both)

The totals are the load-bearing marker. There is exactly one per question, it
sits on that question's LAST page, and they run in order, so they tile the
paper end to end: question n occupies everything after question n-1's total up
to and including its own. `Question n continued` then says where question 1
begins -- one page before its first continuation -- which is the only boundary
the totals leave open, and the front matter is whatever precedes it.

What is NOT used, and why:

  * The opening `4.` is missing from the text layer altogether on the 2023+
    template, and on every template a question that opens with a figure
    extracts its number as a line of its own, so a pattern demanding text after
    the dot matches nothing at all.
  * `(Total 9 marks)` alone does not name its question. The number is in a
    `Q4` label set separately in the margin, several hundred characters away in
    the extraction order -- a pattern that expects them adjacent silently
    matches nothing on six years of papers.

EMPTY IS NOT THE SAME AS BLANK

A page of answer space is not empty. It carries the running head, the item
barcode, the page number, three rotated `DO NOT WRITE IN THIS AREA` sidebars,
the `Leave blank` box, our own stamp, the board's footer and forty ruled lines.
Deciding whether any of the QUESTION is on it means removing all of that and
asking whether words are left -- and also whether a figure is drawn, because a
continuation sheet carrying part (c)'s diagram has almost no text on it and
must never be mistaken for space.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from statistics import median
from pathlib import Path

import fitz

# --- the board's own markers ------------------------------------------------
CONTINUED = re.compile(r"Question\s+(\d{1,2})\s+continued", re.I)
# 2023 onwards: the question number is in the sentence.
TOTAL_MODERN = re.compile(
    # \s* around "=": 4PH1 Oct 2020 P2 prints "(Total for Question 7 =10 marks)".
    r"\(\s*Total\s+for\s+Question\s+(\d{1,2})\s*(?:is|=)\s*(\d{1,3})\s+marks?\s*\)", re.I)
# To 2022: the marks are in the body, the question number in a margin label.
TOTAL_LEGACY = re.compile(r"\(\s*Total\s+(\d{1,3})\s+marks?\s*\)", re.I)
Q_LABEL = re.compile(r"(?m)^\s*Q\s?(\d{1,2})\s*$")

# --- furniture that is on every page and means nothing ----------------------
FURNITURE = re.compile(
    r"DO\s*NOT\s*WRITE\s*IN\s*THIS\s*AREA"
    r"|Leave\s*blank"
    r"|Turn\s*over"
    r"|GradeMax"
    r"|BLANK\s*PAGE"
    r"|TOTAL\s+FOR\s+PAPER\s*:?\s*\d+\s*MARKS?"
    r"|\bEND\b"
    r"|Question\s+\d{1,2}\s+continued"
    r"|\bP\d{5}R?A\d{4}\b"
    r"|\bWME01\b|\bWME\d{2}\b"
    r"|^\s*Q\s?\d{1,2}\s*$"
    r"|^\s*\d{1,3}\s*$",
    re.I | re.M)
# The PMT-derived footer, `WME01 | 2017 | January | Paper 1 | GradeMax`, and our
# own middot line, `Mathematics - 2023 - May/Jun - M1 - QP`.
STAMP_LINE = re.compile(
    r"[\w/]+(?:\s*\|\s*[\w/ ]+){2,}"
    r"|\w[\w ]* · \d{4} · [\w/]+ · [\w ]+ · (?:QP|MS)")
# A ruled answer line is ONE non-alphanumeric character repeated. Matching the
# character itself does not work: the 2016-2019 papers have a broken CMap that
# encodes `.` as U+0011, so a dot list matches nothing and every ruled page
# reads as full of content. Repetition is the property that survives.
RULE = re.compile(r"([^\w\s])\1{7,}")

# Below this many real characters a page is answer space, not content. A part
# label and a few words -- "(b) Find the speed of P." -- clears it comfortably;
# the punctuation the furniture strip leaves behind does not.
CONTENT_CHARS = 25
# How many drawings above a paper's own blank-page baseline count as a figure.
#
# Measuring a figure by its SIZE does not work here. The obvious test -- a
# drawing with both dimensions over ~24pt -- fires on every page in the book,
# because every page carries a 522x755pt frame rectangle: 79% of the sheet,
# larger than any figure will ever be. Take the frame out and a real figure is
# no longer one drawing at all but a scatter of short strokes, none of which
# passes a size test either. What does separate them is how MANY strokes there
# are, judged against the same paper's own empty pages, since the baseline
# moves with the template.
#
# Across the nineteen papers this is belt and braces: of 370 pages that are
# empty of text once the furniture is stripped, exactly three carry extra
# drawings, and all three are a paper's last page, where the extra strokes are
# the `TOTAL FOR PAPER: 75 MARKS` box. None is a figure. The guard stays
# because a paper added later may not be so tidy, and the cost of it being
# wrong is a question in the book missing its diagram.
FIGURE_DRAWING_MARGIN = 3


@dataclass
class Page:
    index: int                 # 0-based, as in the PDF
    number: int                # 1-based, as printed
    question: int | None
    role: str                  # front | start | content | space | back
    has_total: bool
    text_chars: int            # real characters left after the furniture strip
    has_figure: bool
    sample: str = ""


@dataclass
class Question:
    number: int
    marks: int | None
    pages: list[Page]

    @property
    def space(self) -> list[Page]:
        return [p for p in self.pages if p.role == "space"]


@dataclass
class PaperPages:
    path: Path
    pages: list[Page]
    questions: list[Question] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def front(self) -> list[Page]:
        return [p for p in self.pages if p.role == "front"]

    @property
    def back(self) -> list[Page]:
        return [p for p in self.pages if p.role == "back"]

    @property
    def total_marks(self) -> int:
        return sum(q.marks or 0 for q in self.questions)


def strip_furniture(text: str) -> str:
    text = STAMP_LINE.sub(" ", text)
    text = TOTAL_MODERN.sub(" ", text)
    text = TOTAL_LEGACY.sub(" ", text)
    text = FURNITURE.sub(" ", text)
    text = RULE.sub(" ", text)
    return re.sub(r"[\s·_.*|]+", " ", text).strip()


# Every page places one 24 x 762pt image: the rotated `DO NOT WRITE IN THIS
# AREA` sidebar. An "is there an image on this page" test therefore answers yes
# for the whole book. A real figure is not a ribbon, so both dimensions have to
# be substantial and the aspect ratio has to be sane.
MIN_FIGURE_SIDE = 40.0
MAX_FIGURE_ASPECT = 5.0


def _has_image(page: fitz.Page) -> bool:
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 1:
            continue
        x0, y0, x1, y1 = block["bbox"]
        w, h = x1 - x0, y1 - y0
        if min(w, h) < MIN_FIGURE_SIDE:
            continue
        if max(w, h) / min(w, h) > MAX_FIGURE_ASPECT:
            continue
        return True
    return False


def _ends_and_marks(texts: list[str]) -> tuple[dict[int, int], dict[int, int]]:
    """Map question -> the page index its total sits on, and -> its marks."""
    ends: dict[int, int] = {}
    marks: dict[int, int] = {}

    for i, text in enumerate(texts):
        for m in TOTAL_MODERN.finditer(text):
            q = int(m.group(1))
            ends[q], marks[q] = i, int(m.group(2))

    if ends:
        return ends, marks

    # Legacy template: the marks and the question label are set separately, so
    # they are paired by being on the same page. Pages carrying a total but no
    # label are numbered by their order, which is what the label would have said.
    pending: list[tuple[int, int | None, int]] = []
    for i, text in enumerate(texts):
        total = TOTAL_LEGACY.search(text)
        if not total:
            continue
        label = Q_LABEL.search(text)
        pending.append((i, int(label.group(1)) if label else None, int(total.group(1))))
    for order, (i, label, mk) in enumerate(pending, start=1):
        q = label if label is not None else order
        ends[q], marks[q] = i, mk
    return ends, marks


def read_paper(path: Path) -> PaperPages:
    doc = fitz.open(path)
    texts = [doc[i].get_text() for i in range(doc.page_count)]

    ends, marks = _ends_and_marks(texts)
    continued: dict[int, list[int]] = {}
    for i, text in enumerate(texts):
        m = CONTINUED.search(text)
        if m:
            continued.setdefault(int(m.group(1)), []).append(i)

    problems: list[str] = []
    numbers = sorted(ends)
    if numbers and numbers != list(range(1, len(numbers) + 1)):
        problems.append(f"questions do not run 1..n: {numbers}")

    spans: dict[int, tuple[int, int]] = {}
    previous_end = None
    for q in numbers:
        end = ends[q]
        if previous_end is None:
            # Question 1 opens one page before its first continuation sheet; a
            # question with no continuation opens on the page it ends.
            start = min(continued[q]) - 1 if continued.get(q) else end
        else:
            start = previous_end + 1
        if start > end:
            problems.append(f"question {q}: start p{start + 1} is after end p{end + 1}")
            start = end
        spans[q] = (start, end)
        previous_end = end

    first = min((s for s, _ in spans.values()), default=len(texts))
    last = max((e for _, e in spans.values()), default=-1)

    owner: dict[int, int] = {}
    for q, (start, end) in spans.items():
        for i in range(start, end + 1):
            owner[i] = q

    bodies = [strip_furniture(t) for t in texts]
    strokes = [len(doc[i].get_drawings()) for i in range(len(texts))]
    # The paper's own empty-page baseline, so the figure guard travels with the
    # template rather than with a number chosen on one year's papers.
    empty = [strokes[i] for i, b in enumerate(bodies) if len(b) < CONTENT_CHARS]
    baseline = median(empty) if empty else 0.0

    pages: list[Page] = []
    for i, text in enumerate(texts):
        body = bodies[i]
        figure = strokes[i] > baseline + FIGURE_DRAWING_MARGIN or _has_image(doc[i])
        q = owner.get(i)
        carries_total = bool(TOTAL_MODERN.search(text) or TOTAL_LEGACY.search(text))

        if i < first:
            role, q = "front", None
        elif i > last:
            role, q = "back", None
        elif q is not None and i == spans[q][0]:
            role = "start"
        elif len(body) >= CONTENT_CHARS or figure:
            role = "content"
        else:
            role = "space"

        pages.append(Page(index=i, number=i + 1, question=q, role=role,
                          has_total=carries_total, text_chars=len(body),
                          has_figure=figure, sample=body[:90]))

    doc.close()

    questions = [Question(number=q, marks=marks.get(q),
                          pages=[pages[i] for i in range(*(spans[q][0], spans[q][1] + 1))])
                 for q in numbers]
    paper = PaperPages(path=path, pages=pages, questions=questions, problems=problems)

    if paper.total_marks and paper.total_marks != 75:
        paper.problems.append(
            f"question marks sum to {paper.total_marks}, not the paper's 75")
    return paper
