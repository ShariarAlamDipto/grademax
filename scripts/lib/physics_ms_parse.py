"""Parse Edexcel IGCSE Physics mark scheme PDFs into per-part answer points.

An Edexcel mark scheme is a four-column table: question number, answer, notes,
marks. Flattening the page with get_text() interleaves those columns and makes
the notes read as if they were part of the answer, so the columns are recovered
from the table's own drawn vertical rules and the words are bucketed by x.

Every parsed question is checked against the paper's printed
"Total for Question N = M marks" footer. That footer is the awarding body's own
arithmetic, so it is a genuine ground truth: a question whose parsed marks do
not sum to it was mis-parsed and is reported rather than silently used.
"""
from __future__ import annotations

import collections
import re
from dataclasses import dataclass, field
from pathlib import Path

import fitz

# Sessions vary the separator between "Total for question 3" and its tariff:
# most use "=", the January 2023 papers use ":".
TOTAL_RE = re.compile(r"Total\s+for\s+[Qq]uestion\s+(\d+)\s*[=:]\s*(\d+)\s*marks?", re.I)
QNUM_RE = re.compile(r"^\*?\s*(\d{1,2})\b")
ALPHA_RE = re.compile(r"\(?\b([a-h])\)")
ROMAN_RE = re.compile(r"\((i{1,3}|iv|v|vi{1,3})\)")

# Page furniture stamped on every archived paper, plus Edexcel's own sidebars and
# the registered-office boilerplate that runs along the foot of the legacy papers.
_CHROME = re.compile(
    r"GradeMax|DO NOT WRITE|^4PH[01]\s*\||Physics\s*[·|]\s*\d{4}|Pearson|Edexcel"
    r"|Strand, London|WC2R|Registered company|Rewarding Learning|VAT Reg"
    r"|United Kingdom|Lloyds Court|[·|]\s*(MS|QP|Paper)\b",
    re.I,
)

# The four-column header is reprinted at the top of every mark scheme page. Left in,
# the word "Answer" is appended to whichever question was running across the break.
_HEADER = re.compile(r"^(Question|number|Answer|Notes|Marks|Total)$", re.I)

# Edexcel typesets operators and Greek letters in the Symbol font, which extracts
# as private-use codepoints. Left alone, "power = current × voltage" comes out as
# "power = current  voltage" -- a formula with its operator silently deleted.
SYMBOL_PUA = {
    0xF020: " ", 0xF02D: "−", 0xF061: "α", 0xF062: "β",
    0xF063: "χ", 0xF064: "δ", 0xF065: "ε", 0xF066: "φ",
    0xF067: "γ", 0xF068: "η", 0xF06C: "λ", 0xF06D: "μ",
    0xF06E: "ν", 0xF070: "π", 0xF071: "θ", 0xF072: "ρ",
    0xF073: "σ", 0xF074: "τ", 0xF077: "ω", 0xF044: "Δ",
    0xF057: "Ω", 0xF053: "Σ", 0xF0A3: "≤", 0xF0A5: "∞",
    0xF0AE: "→", 0xF0B0: "°", 0xF0B1: "±", 0xF0B3: "≥",
    0xF0B4: "×", 0xF0B8: "÷", 0xF0B9: "≠", 0xF0BB: "≈",
    0xF0D6: "√", 0xF0D7: "⋅", 0xF0E5: "Σ", 0xF0A2: "",
    0xF0B7: "•", 0xF02B: "+", 0xF03D: "=", 0xF0AC: "←",
}


def demojibake(text: str) -> str:
    """Restore Symbol-font operators and Greek letters lost to private-use mapping."""
    return text.translate(SYMBOL_PUA)


@dataclass
class Part:
    """One creditable step of a mark scheme: an answer cell and its marks."""

    paper_id: str
    q: int
    part: str
    answer: str
    notes: str
    marks: int | None

    @property
    def ref(self) -> str:
        return f"{self.q}{self.part}"


@dataclass
class ParsedPaper:
    paper_id: str
    parts: list[Part] = field(default_factory=list)
    totals: dict[int, int] = field(default_factory=dict)

    def marks_by_question(self) -> dict[int, int]:
        out: dict[int, int] = collections.defaultdict(int)
        for p in self.parts:
            out[p.q] += p.marks or 0
        return dict(out)

    def check(self) -> tuple[int, int, list[str]]:
        """Return (questions_agreeing, questions_checked, mismatch descriptions)."""
        parsed = self.marks_by_question()
        ok = 0
        problems = []
        for q, total in sorted(self.totals.items()):
            got = parsed.get(q, 0)
            if got == total:
                ok += 1
            else:
                problems.append(f"{self.paper_id} Q{q}: parsed {got} vs printed {total}")
        return ok, len(self.totals), problems


def _column_edges(page: fitz.Page) -> list[float] | None:
    """Recover the mark scheme table's column boundaries from its drawn rules."""
    xs: collections.Counter = collections.Counter()
    for drawing in page.get_drawings():
        for item in drawing["items"]:
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                if abs(p1.x - p2.x) < 1.5 and abs(p1.y - p2.y) > 20:
                    xs[round(p1.x)] += 1
            elif item[0] == "re":
                rect = item[1]
                if rect.width < 2.5 and rect.height > 20:
                    xs[round(rect.x0)] += 1
    # Some sessions draw the table with doubled borders a few points apart, which
    # would otherwise be read as extra columns. The narrowest genuine column is
    # "Marks" at roughly 26pt, so anything closer than that is the same rule.
    edges = sorted(x for x, n in xs.items() if n >= 2)
    merged: list[float] = []
    for x in edges:
        if not merged or x - merged[-1] > 12:
            merged.append(float(x))
    return merged if len(merged) >= 5 else None


def _visual_lines(words: list[tuple], tolerance: float = 4.0) -> list[list[tuple]]:
    """Group words into visual lines by vertical proximity.

    Rounding y onto a fixed grid looks equivalent but is not: a Symbol-font glyph
    sits on a slightly different baseline from the text around it, so "momentum =
    mass x velocity" puts its multiplication sign 0.6pt below the rest of the line.
    On a fixed grid that lands in the next bucket, the operator is orphaned from its
    formula and then dropped as a stray fragment -- printing the formula to a student
    with the multiplication sign silently missing.
    """
    lines: list[list[tuple]] = []
    anchors: list[float] = []
    for word in sorted(words, key=lambda w: (w[1], w[0])):
        if lines and abs(word[1] - anchors[-1]) <= tolerance:
            lines[-1].append(word)
        else:
            lines.append([word])
            anchors.append(word[1])
    return lines


def _rows(page: fitz.Page, edges: list[float]) -> list[tuple[str, str, str, str]]:
    """Bucket the page's words into (question, answer, notes, marks) by column."""
    rows = []
    for line in _visual_lines(page.get_text("words")):
        words = sorted(line, key=lambda w: w[0])
        cells = ["", "", "", ""]
        for col, (lo, hi) in enumerate(zip(edges[:4], edges[1:5])):
            text = " ".join(w[4] for w in words if lo - 4 <= w[0] < hi)
            cell = demojibake(text).strip()
            cells[col] = "" if _HEADER.match(cell) else cell
        if any(cells) and not _CHROME.search(" ".join(cells)):
            rows.append(tuple(cells))
    return rows


def _tariff(cell: str) -> int | None:
    """Read the marks column. Text bleeding in from the notes column can leave
    several numbers in the cell, so take the first plausible tariff only: no
    single part of an IGCSE Physics paper is worth more than six marks.
    """
    for token in cell.split():
        if token.isdigit() and 1 <= int(token) <= 6:
            return int(token)
    return None


def _labels(cell: str) -> tuple[int | None, str | None, str | None]:
    """Read a question number, a letter part and a roman sub-part off column one."""
    cell = cell.replace("‑", "-").strip()
    qnum = QNUM_RE.match(cell)
    q = int(qnum.group(1)) if qnum else None
    rest = cell[qnum.end():] if qnum else cell

    roman = ROMAN_RE.search(rest)
    sub = f"({roman.group(1)})" if roman else None
    if roman:
        rest = rest[: roman.start()]

    alpha = ALPHA_RE.search(rest)
    letter = f"({alpha.group(1)})" if alpha else None
    return q, letter, sub


def _fallback_edges(per_page: list[list[float] | None]) -> list[float] | None:
    """A paper's table geometry barely moves between pages, so pages whose rules
    were not drawn as strokes can borrow the median geometry of the rest. Without
    this the last page of a question -- often the extended-response grid -- is
    dropped and the question's marks come out short.
    """
    found = [e[:5] for e in per_page if e]
    if not found:
        return None
    return [sorted(col)[len(col) // 2] for col in zip(*found)]


def parse_ms(path: Path, paper_id: str) -> ParsedPaper:
    """Read one mark scheme PDF into its creditable parts."""
    paper = ParsedPaper(paper_id=paper_id)
    current: Part | None = None
    q_now, letter_now = 0, ""

    with fitz.open(path) as doc:
        per_page = [_column_edges(page) for page in doc]
        fallback = _fallback_edges(per_page)

        for page, page_edges in zip(doc, per_page):
            for q, total in TOTAL_RE.findall(page.get_text()):
                paper.totals[int(q)] = int(total)

            edges = page_edges or fallback
            if not edges:
                continue

            for qcell, answer, notes, marks in _rows(page, edges):
                if TOTAL_RE.search(answer) or TOTAL_RE.search(notes):
                    current = None
                    continue

                q, letter, sub = _labels(qcell)
                starts_part = bool(q or letter or sub)
                if starts_part:
                    if q:
                        q_now = q
                        if letter or sub:
                            letter_now = letter or ""
                    if letter:
                        letter_now = letter
                    part = (letter or letter_now) + (sub or "")
                    current = Part(paper_id, q_now, part, "", "", None)
                    paper.parts.append(current)

                if current is None:
                    current = Part(paper_id, q_now, letter_now, "", "", None)
                    paper.parts.append(current)

                if answer:
                    current.answer = f"{current.answer} {answer}".strip()
                if notes:
                    current.notes = f"{current.notes} {notes}".strip()
                if marks and current.marks is None:
                    current.marks = _tariff(marks)

    paper.parts = [p for p in paper.parts if p.answer or p.marks]
    return paper
