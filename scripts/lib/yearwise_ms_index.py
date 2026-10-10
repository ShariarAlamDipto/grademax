"""
Where each question's answers begin in a mark scheme, so the question book can
print "Mark scheme: Q4 p. 212" and the reader lands on the right page.

A question's scheme ENDS where its per-question total is printed -- the same
markers the linkage audit uses:

    numbered   "Total for Question 4 = 8 marks"          (sciences)
    tallies    "Total 8 marks", in question order       (Maths B, FPM; read by
               ms_bands.find_tallies, which handles rotated pages)
    bare       "Total for question 8" -- the MARKS       (IAL practical units)
    paren      "(6 marks)"                              (IAL P1-P4)

So question q STARTS where question q-1 ended -- on the same page, unless that
total sits at the very foot of its page, in which case on the next one.
Question 1 starts on the first page of the scheme proper (after Pearson's
front matter). Unnumbered tallies are matched to questions by aligning their
marks to the paper's `(Total for Question n is m marks)` sequence (LCS), so a
tally the text layer lost shifts nothing.

Questions whose position cannot be read are simply absent from the result; the
book then prints the paper-level reference only for them.
"""

from __future__ import annotations

import re
from pathlib import Path

import fitz

from .ms_bands import find_numbered_rows, find_tallies

NUMBERED = re.compile(r"Total\s+for\s+[Qq]uestion\s+(\d+)\s*(?:=|is|:)?\s*(\d+)(?!\d)", re.I)
BARE = re.compile(r"Total\s+for\s+[Qq]uestion\s+(\d+)(?=\s+[A-Za-z(])")
PAREN = re.compile(r"\((\d{1,2})\s*marks\)", re.I)
# The scheme proper opens with a table header: "Question Number | Answer ..."
# / "Question | Working | Answer | Mark" / "Question | Scheme | Marks".
TABLE_HEAD = re.compile(r"Question\s*(?:Number|number)?\s*(?:Answer|Scheme|Working|Acceptable)", re.I)
FOOT_FRACTION = 0.88


def first_scheme_page(doc: fitz.Document) -> int:
    """The first page of the scheme proper: everything before is Pearson's
    front matter (cover, about Pearson, General Marking Guidance)."""
    for i, page in enumerate(doc):
        if TABLE_HEAD.search(re.sub(r"\s+", " ", page.get_text())):
            return i
    return min(3, doc.page_count - 1)


def _lcs_pairs(a: list[int], b: list[int]) -> list[tuple[int, int]]:
    """Index pairs (i, j) of one longest common subsequence of a and b."""
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            dp[i][j] = dp[i + 1][j + 1] + 1 if a[i] == b[j] else max(dp[i + 1][j], dp[i][j + 1])
    pairs, i, j = [], 0, 0
    while i < n and j < m:
        if a[i] == b[j]:
            pairs.append((i, j))
            i, j = i + 1, j + 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return pairs


def _ends_numbered(doc: fitz.Document) -> dict[int, tuple[int, float]]:
    """question -> (page, y fraction) of its numbered total."""
    ends: dict[int, tuple[int, float]] = {}
    for i, page in enumerate(doc):
        h = page.rect.height or 1
        for block in page.get_text("blocks"):
            text = re.sub(r"\s+", " ", block[4])
            for m in NUMBERED.finditer(text):
                ends.setdefault(int(m.group(1)), (i, block[3] / h))
    return ends


def _ends_sequence(doc: fitz.Document, path: Path, paper: list[tuple[int, int]]) -> dict[int, tuple[int, float]]:
    """question -> (page, y fraction) from unnumbered totals aligned by marks."""
    seq: list[tuple[int, int, float]] = []          # (marks, page, fraction)
    for t in find_tallies(path):
        h = doc[t.page].rect.height if t.axis == "y" else doc[t.page].rect.width
        seq.append((t.marks, t.page, t.hi / (h or 1)))
    if not seq:
        for rx in (BARE, PAREN):
            for i, page in enumerate(doc):
                h = page.rect.height or 1
                for block in page.get_text("blocks"):
                    for m in rx.finditer(re.sub(r"\s+", " ", block[4])):
                        seq.append((int(m.group(1)), i, block[3] / h))
            if len(seq) >= 3:
                break
            seq = []
    marks = [m for _, m in paper]
    pairs = _lcs_pairs(marks, [s[0] for s in seq])
    ends = {}
    for k, (i, j) in enumerate(pairs):
        # Maths B prints alternative methods AFTER a question's main answer,
        # each closing with its own "Total n marks" -- the same n. Those
        # unmatched tallies are still this question's, so its end moves to the
        # last of them; otherwise the next question would "start" mid-ALT.
        nxt = pairs[k + 1][1] if k + 1 < len(pairs) else len(seq)
        last = j
        for jj in range(j + 1, nxt):
            if seq[jj][0] == marks[i]:
                last = jj
            else:
                break
        ends[paper[i][0]] = (seq[last][1], seq[last][2])
    return ends


def question_start_pages(ms_path: Path, paper_totals: list[tuple[int, int]]) -> dict[int, int]:
    """question -> 0-based page index in the scheme where its answers begin."""
    doc = fitz.open(ms_path)
    try:
        first = first_scheme_page(doc)
        ends = _ends_numbered(doc)
        if len(ends) < max(2, len(paper_totals) // 3):
            ends = _ends_sequence(doc, ms_path, paper_totals)
        starts: dict[int, int] = {}
        previous: tuple[int, float] | None = (first, 0.0)
        for q, _ in paper_totals:
            if previous is not None:
                page, frac = previous
                starts[q] = page + 1 if frac > FOOT_FRACTION and q != paper_totals[0][0] else page
            previous = ends.get(q)
        if len(starts) < len(paper_totals):
            _fill_from_rows(ms_path, paper_totals, starts, first)
        _refine_with_rows(ms_path, paper_totals, starts, first)
        return _monotonic(paper_totals, starts)
    finally:
        doc.close()


def _refine_with_rows(ms_path: Path, paper_totals: list[tuple[int, int]],
                      starts: dict[int, int], first: int) -> None:
    """
    A total says where a question ENDS, not where the next begins: Maths B
    prints alternative methods after a question's total, often with no total
    of their own (Jun 2026 P2: Q5's ALT 1 and ALT 2 fill two pages before Q6).
    Where the question-number column prints q LATER than the totals put it --
    but before the following question's located start -- the printed number
    wins. Bounded both ways, so a stray digit cannot drag a question far.
    """
    rows = [(r.page, r.question) for r in find_numbered_rows(ms_path) if r.page >= first]
    # The margin label is often "11(a)" rather than a bare "11", which the row
    # reader (standalone integers only) does not return.
    with fitz.open(ms_path) as doc:
        for i in range(first, doc.page_count):
            for m in re.finditer(r"(?m)^\s*(\d{1,2})\s*\(\s*[a-z]\s*\)", doc[i].get_text()):
                rows.append((i, int(m.group(1))))
    order = [q for q, _ in paper_totals]
    for k, q in enumerate(order):
        if q not in starts:
            continue
        nxt = next((starts[o] for o in order[k + 1:] if o in starts), None)
        limit = nxt if nxt is not None else starts[q] + 3
        later = [page for page, num in rows if num == q and starts[q] < page <= limit]
        if later and not any(num == q and page == starts[q] for page, num in rows):
            starts[q] = min(later)


def _monotonic(paper_totals: list[tuple[int, int]], starts: dict[int, int]) -> dict[int, int]:
    """
    A scheme runs in question order, so a located page earlier than an earlier
    question's is a misreading (Maths B Jan 2020 P1's rotated pages put Q26
    after Q27). A wrong page is worse than none: such entries are dropped and
    those questions fall back to the paper-level reference. The later of the
    two is kept only if it agrees with the next question's page.
    """
    order = [q for q, _ in paper_totals if q in starts]
    keep: dict[int, int] = {}
    floor = -1
    for i, q in enumerate(order):
        page = starts[q]
        nxt = starts[order[i + 1]] if i + 1 < len(order) else None
        if page < floor or (nxt is not None and page > nxt):
            continue
        keep[q], floor = page, page
    return keep


def _fill_from_rows(ms_path: Path, paper_totals: list[tuple[int, int]],
                    starts: dict[int, int], first: int) -> None:
    """
    Schemes with no per-question totals (Maths B 2018-19, Physics P2 Jun 2019)
    still print the question number in the table's first column. The first
    numbered row for q, at or after the page q-1 was found on, is where q's
    answers begin. Rows come back in block order, so the search only moves
    forward -- a stray "3" in a later answer cannot drag question 3 backwards.
    """
    rows = [r for r in find_numbered_rows(ms_path) if r.page >= first]
    floor, cursor = first, 0
    for q, _ in paper_totals:
        if q in starts:
            floor = max(floor, starts[q])
            continue
        for k in range(cursor, len(rows)):
            if rows[k].question == q and rows[k].page >= floor:
                starts[q], floor, cursor = rows[k].page, rows[k].page, k + 1
                break
