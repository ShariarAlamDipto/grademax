"""
Parsing primitives for Edexcel **IAL** question papers.

Subject-neutral on purpose: this module knows about the IAL *paper format*, not
about S1 or P4. Each subject keeps its own dedicated entry-point script (see
`build_s1_workbook_segments.py`, `build_p4_workbook_segments.py`); this is the
shared format layer they both sit on, the same way `workbook_ink` and
`workbook_layout` are shared by the FPM and Maths B book builders.

Measured over 42 unique IAL papers (28 WST01 + 14 WMA14) in September 2026.

WHY THIS DOES NOT WORK THE WAY THE IGCSE SEGMENTERS DO
-----------------------------------------------------
The FPM segmenter derives every boundary from the end-of-question fence, on the
principle that the label should come from the paper rather than from our
inference: `Total for Question 7 is 12 marks` states its own number.

**IAL papers before 2022 do not print that.** They print a bare
`(Total 12 marks)` carrying no question number at all, so the fence cannot
label anything. Of the 42 papers here, 26 are in that older era.

What IAL gives instead is better than what it takes away. Every page of an IAL
paper announces its own owner in the top-left corner:

    page 1   '1.\\t (a) Find the first 4 terms ...'      <- question 1 starts
    page 2   'Question 1 continued'                     <- question 1 owns this
    page 3   '2.'                                       <- question 2 starts
    page 4   'Question 2 continued'

So **page ownership is read directly off the printed page headers**, and the
question number is stated explicitly on every single page rather than inferred
from position. Measured: all 42 papers yield question starts numbering exactly
1..N with no gaps.

Marks then come from a separate signal, and there are two of them:

  * the fence -- `Total for Question N is M marks` (2022 onwards) or
    `(Total M marks)` (before that);
  * the **bold per-part tallies** in the right margin -- `(2)`, `(3)` -- which
    sum to the question total.

These are independent, and on every paper that prints both they agree exactly.
Five WST01 papers print no readable fence at all (2014 May-Jun, 2015 May-Jun,
2016 Jan, 2016 May-Jun, 2017 Jan); the tallies recover all five, each summing to
exactly 75. Requiring the two to agree where both exist is a real check, not a
circular one -- unlike aligning mark schemes by LCS on the mark values, which
guarantees the agreement it then reports.

THE +29 CMAP REPAIR MUST RUN BEFORE MATCHING, NOT AFTER
-------------------------------------------------------
In the FPM and Maths B pipelines the broken-CMap repair was an enricher concern,
because the stems were only ever classifier input. Here it changes segmentation
itself: several papers lose most of their fences to it and recover once spans
are repaired. Apply it **per span, never per page** -- one page mixes broken and
intact spans, and decoding wholesale turns `DO NOT WRITE IN THIS AREA` into
`al=klq=tofqb`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import fitz

# ─────────────────────────────────────────────────────────────────────────────
# Geometry, measured rather than guessed
# ─────────────────────────────────────────────────────────────────────────────

#: Page headers ('3.' / 'Question 3 continued') sit hard against the left
#: margin at x ~= 54.5, y ~= 58.5 on every paper measured.
HEADER_MAX_X = 80.0
HEADER_MAX_Y = 120.0

#: Per-part mark tallies sit in the right margin at x ~= 493-540.
TALLY_MIN_X = 450.0

#: Below this the page is footer furniture: the printed page number, the
#: barcode, 'Turn over'. A tally never appears there, but a page number does.
TALLY_MAX_Y = 790.0

# ─────────────────────────────────────────────────────────────────────────────
# Patterns
# ─────────────────────────────────────────────────────────────────────────────

#: '1.' / '12.' opening a page. The trailing dot is IAL house style and is what
#: separates a question marker from a stray numeral; IGCSE papers print a bare
#: number, which is why the FPM matcher does not port.
QUESTION_START_RE = re.compile(r"^(\d{1,2})\s*\.")

#: 'Question 7 continued' -- an explicit, unambiguous ownership statement.
QUESTION_CONT_RE = re.compile(r"^Question\s+(\d{1,2})\s+continued", re.I)

#: 2022 onwards. Carries the question number AND the marks.
FENCE_NUMBERED_RE = re.compile(
    r"Total\s+for\s+Question\s+(\d{1,2})\s*(?:is|=)\s*(\d{1,3})\s*marks?", re.I
)

#: Before 2022. Carries the marks only -- no question number.
FENCE_BARE_RE = re.compile(r"\(\s*Total\s+(\d{1,3})\s*marks?\s*\)", re.I)

#: A right-margin per-part tally: exactly '(3)', nothing else on the line.
TALLY_RE = re.compile(r"^\(\s*(\d{1,2})\s*\)$")


# ─────────────────────────────────────────────────────────────────────────────
# Text repair
# ─────────────────────────────────────────────────────────────────────────────


def repair_span(text: str) -> str:
    """
    Undo the +29 CMap shift on a single span.

    Every character code sits exactly 29 below its true Unicode value, so
    `W` -> `t` and `\\x03` -> space. Control characters in the ASCII range are
    the conclusive tell: no legitimate span contains them, and a span without
    them is left completely alone.

    Deliberately conservative. Broken and intact spans report identical font
    name, size and flags, so the text itself is the only usable evidence, and
    the cost of repairing an intact span is corrupted output.
    """
    if not any(0x01 <= ord(ch) <= 0x1F and ch not in "\t\n\r" for ch in text):
        return text
    return "".join(
        chr(ord(ch) + 29) if 0x01 <= ord(ch) <= 0x1F and ch not in "\t\n\r" else ch
        for ch in text
    )


# ─────────────────────────────────────────────────────────────────────────────
# Page model
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Line:
    """One assembled text line with the geometry the callers actually use."""

    text: str
    x0: float
    y0: float
    bold: bool


@dataclass(frozen=True)
class PageFacts:
    """Everything one page tells us about who owns it and what it is worth."""

    index: int
    starts: int | None  # question number that STARTS here, if any
    continues: int | None  # question number this page continues, if any
    tallies: tuple[int, ...]  # bold right-margin per-part marks
    numbered_fences: tuple[tuple[int, int], ...]  # (question, marks)
    bare_fences: tuple[int, ...]  # marks only

    @property
    def owner_hint(self) -> int | None:
        """The question this page announces itself as belonging to."""
        return self.starts if self.starts is not None else self.continues


def page_lines(page: fitz.Page) -> list[Line]:
    """
    Assemble a page's spans into lines, repairing each span as it is read.

    Repair happens per span here -- doing it on the joined line would let one
    broken span's control characters trigger a decode of its intact neighbours.
    """
    lines: list[Line] = []
    try:
        blocks = page.get_text("dict")["blocks"]
    except Exception:  # noqa: BLE001 - a bad page must not kill the paper
        return lines

    for block in blocks:
        for raw in block.get("lines", []):
            spans = raw.get("spans", [])
            if not spans:
                continue
            lines.append(
                Line(
                    text="".join(repair_span(span["text"]) for span in spans),
                    x0=min(span["bbox"][0] for span in spans),
                    y0=min(span["bbox"][1] for span in spans),
                    bold=any("Bold" in span.get("font", "") for span in spans),
                )
            )
    return lines


def read_page(index: int, page: fitz.Page) -> PageFacts:
    """Extract ownership, tallies and fences from one page."""
    lines = page_lines(page)

    starts: int | None = None
    continues: int | None = None
    best_y: float | None = None

    tallies: list[int] = []

    for line in lines:
        stripped = line.text.strip()

        # Ownership: the topmost header-band line wins, so a '2.' appearing
        # lower down in a formula cannot outrank the real page header.
        if line.x0 < HEADER_MAX_X and line.y0 < HEADER_MAX_Y:
            match = QUESTION_START_RE.match(stripped)
            if match and (best_y is None or line.y0 < best_y):
                starts, continues, best_y = int(match.group(1)), None, line.y0
            match = QUESTION_CONT_RE.match(stripped)
            if match and (best_y is None or line.y0 < best_y):
                starts, continues, best_y = None, int(match.group(1)), line.y0

        # Per-part tallies. Bold is required: the printed page number sits at
        # a similar x on some layouts and is not bold, and an unbolded '(2)'
        # inside a formula would otherwise be counted as marks.
        if line.x0 > TALLY_MIN_X and line.y0 < TALLY_MAX_Y and line.bold:
            match = TALLY_RE.match(stripped)
            if match:
                tallies.append(int(match.group(1)))

    flat = re.sub(r"\s+", " ", "\n".join(line.text for line in lines))
    numbered = tuple((int(q), int(m)) for q, m in FENCE_NUMBERED_RE.findall(flat))
    # Only look for the bare form where the numbered form is absent: the
    # numbered fence contains the substring 'Total ... marks' and would
    # otherwise be counted twice on 2022+ papers.
    bare = tuple(int(m) for m in FENCE_BARE_RE.findall(flat)) if not numbered else ()

    return PageFacts(
        index=index,
        starts=starts,
        continues=continues,
        tallies=tuple(tallies),
        numbered_fences=numbered,
        bare_fences=bare,
    )


def read_paper(pdf_path: Path) -> list[PageFacts]:
    """Read every page of a question paper."""
    with fitz.open(pdf_path) as doc:
        return [read_page(index, page) for index, page in enumerate(doc)]


# ─────────────────────────────────────────────────────────────────────────────
# Deriving questions
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Question:
    number: int
    marks: int
    pages: tuple[int, int]  # inclusive [start, end], 0-indexed
    mark_source: str  # 'fence+tally' | 'fence' | 'tally'


def derive_page_ranges(
    facts: list[PageFacts],
) -> tuple[dict[int, tuple[int, int]], list[str]]:
    """
    Assign every page to a question using only the printed page headers.

    A question owns the run of pages from its start header up to the page before
    the next question's start header. Continuation headers are not needed to
    define the run, but they are checked against it -- a page that says it
    continues question 4 while sitting inside question 5's run means the run is
    wrong, and that is worth failing over rather than shipping.
    """
    problems: list[str] = []

    starts = [(f.index, f.starts) for f in facts if f.starts is not None]
    if not starts:
        return {}, ["no question start headers found at all"]

    numbers = [q for _, q in starts]
    if numbers != list(range(1, len(numbers) + 1)):
        problems.append(f"question start headers are not 1..N in order: {numbers}")
        return {}, problems

    ranges: dict[int, tuple[int, int]] = {}
    for position, (page_index, question) in enumerate(starts):
        if position + 1 < len(starts):
            end = starts[position + 1][0] - 1
        else:
            # The last question runs to the last page carrying content it owns.
            trailing = [
                f.index
                for f in facts
                if f.index >= page_index
                and (f.continues == question or f.index == page_index or f.tallies or f.bare_fences or f.numbered_fences)
            ]
            end = max(trailing) if trailing else page_index
        if end < page_index:
            problems.append(f"question {question}: end page {end} precedes start {page_index}")
            continue
        ranges[question] = (page_index, end)

    for fact in facts:
        if fact.continues is None:
            continue
        owner = next(
            (q for q, (lo, hi) in ranges.items() if lo <= fact.index <= hi), None
        )
        if owner is not None and owner != fact.continues:
            problems.append(
                f"page {fact.index} says 'Question {fact.continues} continued' "
                f"but falls inside question {owner}'s page range"
            )

    return ranges, problems


def derive_marks(
    facts: list[PageFacts],
    ranges: dict[int, tuple[int, int]],
    paper_total: int,
) -> tuple[dict[int, tuple[int, str]], list[str]]:
    """
    Marks per question, from the fence and the tallies independently.

    Where both are readable they must agree. Where only one is, it is used and
    labelled, so the audit can report how much of the book rests on which
    signal. The paper total is the arithmetic backstop: an individually
    plausible but wrong set of marks will almost never still sum to 75.
    """
    problems: list[str] = []
    by_question: dict[int, tuple[int, str]] = {}

    numbered = {q: m for fact in facts for q, m in fact.numbered_fences}

    # Bare fences carry no number, so they are matched to whichever question's
    # page range they physically fall inside -- which the page headers already
    # told us, independently of the fence.
    bare: dict[int, int] = {}
    for fact in facts:
        for marks in fact.bare_fences:
            owner = next(
                (q for q, (lo, hi) in ranges.items() if lo <= fact.index <= hi), None
            )
            if owner is None:
                problems.append(f"page {fact.index}: '(Total {marks} marks)' owned by no question")
                continue
            if owner in bare:
                problems.append(f"question {owner} has more than one bare fence")
                continue
            bare[owner] = marks

    tallied: dict[int, int] = {}
    for question, (lo, hi) in ranges.items():
        total = sum(sum(f.tallies) for f in facts if lo <= f.index <= hi)
        if total:
            tallied[question] = total

    for question in sorted(ranges):
        fence = numbered.get(question, bare.get(question))
        tally = tallied.get(question)

        if fence is not None and tally is not None:
            if fence != tally:
                problems.append(
                    f"question {question}: fence says {fence} marks but the "
                    f"per-part tallies sum to {tally}"
                )
                continue
            by_question[question] = (fence, "fence+tally")
        elif fence is not None:
            by_question[question] = (fence, "fence")
        elif tally is not None:
            by_question[question] = (tally, "tally")
        else:
            problems.append(f"question {question}: no fence and no tallies -- marks unknown")

    total = sum(marks for marks, _ in by_question.values())
    if by_question and total != paper_total:
        problems.append(
            f"marks sum to {total}, not {paper_total} "
            f"({len(by_question)} of {len(ranges)} questions priced)"
        )

    return by_question, problems


def build_questions(
    facts: list[PageFacts], paper_total: int
) -> tuple[list[Question], list[str]]:
    """Full pipeline for one paper: ownership -> ranges -> marks."""
    ranges, problems = derive_page_ranges(facts)
    if not ranges:
        return [], problems

    marks, mark_problems = derive_marks(facts, ranges, paper_total)
    problems.extend(mark_problems)

    questions = [
        Question(number=q, marks=marks[q][0], pages=ranges[q], mark_source=marks[q][1])
        for q in sorted(ranges)
        if q in marks
    ]
    return questions, problems


# ─────────────────────────────────────────────────────────────────────────────
# Duplicate papers
# ─────────────────────────────────────────────────────────────────────────────

#: Session words appear in OUR OWN watermark on every page, so two identical
#: papers filed under different sessions differ only by these tokens. Stripping
#: them is what makes reused papers detectable at all -- a filename or
#: paper-code check will never find them.
_SESSION_TOKENS = re.compile(
    r"January|Jan|June|Jun|May|October|Oct|November|Nov|Summer|Winter", re.I
)


def content_fingerprint(pdf_path: Path) -> str:
    """
    A session-independent fingerprint of a paper's text.

    Two papers with the same fingerprint are the same paper. Measured: five
    such pairs across WST01 and WMA14, every one scoring a similarity ratio of
    exactly 1.0000 once the watermark's session token is removed -- the COVID
    paper-reuse pattern.
    """
    with fitz.open(pdf_path) as doc:
        text = "".join(page.get_text() for page in doc)
    text = re.sub(r"[^A-Za-z0-9]+", "", text)
    text = _SESSION_TOKENS.sub("", text)
    return re.sub(r"\d{4}", "", text)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2: stems and sub-parts
# ─────────────────────────────────────────────────────────────────────────────

#: '(a)' / '(b)' opening a line, the printed sub-part label.
SUBPART_RE = re.compile(r"^\(\s*([a-z])\s*\)")

#: Furniture that is on every page and is never part of a question stem.
#:
#: `Leave` and `blank` are listed SEPARATELY and not as the phrase. The words
#: sit stacked in the right-hand margin box, so the text layer emits them as two
#: independent lines; matching only `Leave\s*blank` left the pair in 125 of 179
#: WST01 stems, where they are the first thing a classifier would read.
_NOISE_RE = re.compile(
    r"^(?:_{5,}"
    r"|Question\s+\d{1,2}\s+continued"
    r"|Leave|blank|Leave\s*blank|DO NOT WRITE IN THIS AREA"
    r"|Turn over|\*[A-Z0-9]+\*"
    r"|Mathematics\s*[·.]\s*\d{4}.*"        # our own watermark
    r"|GradeMax"
    r"|\(\s*Total\s+\d+\s+marks?\s*\)"
    r"|Total\s+for\s+Question\s+\d+.*"
    r"|\d{1,3}"                              # bare page numbers
    r")\s*$",
    re.I,
)


@dataclass(frozen=True)
class SubPart:
    label: str  # 'a'
    marks: int | None


def _body_lines(doc: fitz.Document, pages: tuple[int, int]) -> list[Line]:
    lo, hi = pages
    out: list[Line] = []
    for index in range(lo, min(hi + 1, doc.page_count)):
        out.extend(page_lines(doc[index]))
    return out


def extract_stem(doc: fitz.Document, pages: tuple[int, int], question: int) -> str:
    """
    The readable text of a question, for classifier input only.

    The workbook prints the original PDF pages, never this text, so cosmetic
    residue (stray Symbol-font glyphs) is left alone rather than scrubbed at the
    risk of eating a real character.
    """
    kept: list[str] = []
    for line in _body_lines(doc, pages):
        text = line.text.strip()
        if not text or _NOISE_RE.match(text):
            continue
        # Drop the leading question number on the opening line: '1.\t(a) Find...'
        text = re.sub(rf"^{question}\s*\.\s*", "", text)
        if text:
            kept.append(text)
    return re.sub(r"\s+", " ", " ".join(kept)).strip()


def extract_subparts(doc: fitz.Document, pages: tuple[int, int]) -> list[SubPart]:
    """
    Sub-part labels and their marks, paired the way the page reads.

    Each bold right-margin tally closes the most recently opened sub-part, which
    is exactly how a candidate reads the paper. A question with no printed
    sub-parts returns an empty list rather than one synthetic part.
    """
    events: list[tuple[float, float, str, object]] = []
    lo, hi = pages

    for index in range(lo, min(hi + 1, doc.page_count)):
        for line in page_lines(doc[index]):
            text = line.text.strip()
            match = SUBPART_RE.match(text)
            if match and line.x0 < TALLY_MIN_X:
                events.append((index, line.y0, "part", match.group(1)))
            if line.x0 > TALLY_MIN_X and line.y0 < TALLY_MAX_Y and line.bold:
                tally = TALLY_RE.match(text)
                if tally:
                    events.append((index, line.y0, "marks", int(tally.group(1))))

    events.sort(key=lambda e: (e[0], e[1]))

    parts: list[list] = []
    for _, _, kind, value in events:
        if kind == "part":
            if not any(p[0] == value for p in parts):
                parts.append([value, None])
        elif parts and parts[-1][1] is None:
            parts[-1][1] = value

    return [SubPart(label=label, marks=marks) for label, marks in parts]


def difficulty_for(marks: int, easy_max: int, medium_max: int) -> str:
    """
    Band a question by its mark tariff.

    Bands are per-subject and must be derived from that subject's own measured
    distribution -- S1 questions run roughly twice the tariff of P4's, so one
    shared set of cut points would call almost every S1 question hard or almost
    every P4 question easy.
    """
    if marks <= easy_max:
        return "easy"
    if marks <= medium_max:
        return "medium"
    return "hard"
