"""Parse Edexcel IGCSE Physics question papers into per-part question stems.

The mark scheme says what earns the marks but not what was asked, so an answer
on its own ("substitution; evaluation;") is meaningless to a student. This module
recovers the stem for each part so it can be joined to the mark scheme on the
same (question, part) reference.

Edexcel lays a question paper out on a fixed left-margin ladder: the question
number sits furthest left, then the (a) part, then the (i) sub-part, with the
prose indented past all three and the mark tariff right-aligned as "(2)".
The "DO NOT WRITE IN THIS AREA" rails down both edges are set as rotated text,
which is how they are told apart from the question itself.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import fitz

from .physics_ms_parse import demojibake

TARIFF_X = 430.0     # mark tariffs are right-aligned well past the prose
DEFAULT_ALPHA_X = 80.0

QNUM_RE = re.compile(r"^\*?(\d{1,2})\s+(?=[A-Z(])")
ALPHA_RE = re.compile(r"^\*?\(([a-h])\)\s*")
ROMAN_RE = re.compile(r"^\((i{1,3}|iv|v|vi{1,3})\)\s*")
TARIFF_RE = re.compile(r"\((\d)\)\s*$")

_NOISE = re.compile(
    r"BLANK PAGE|Turn over|GradeMax|^4PH[01]\s*\||Physics\s*[·|]\s*\d{4}"
    r"|^\*?P\d{4,6}[A-Z]?\d*\*?$|Total for Question|TOTAL FOR PAPER"
    r"|Answer ALL questions|^\.+$|Pearson|International GCSE"
    r"|Strand, London|WC2R|Registered company|© |^\s*\(Total"
    r"|Paper reference|Centre Number|Candidate Number|Total Marks"
    r"|Instructions|Information|Advice$",
    re.I,
)
_DOTS = re.compile(r"[.…]{4,}")


@dataclass
class Stem:
    paper_id: str
    q: int
    part: str
    text: str
    tariff: int | None

    @property
    def ref(self) -> str:
        return f"{self.q}{self.part}"


def _lines(page: fitz.Page) -> list[tuple[float, float, str]]:
    """Horizontal text lines only, as (left edge, right edge, text)."""
    out = []
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            if tuple(round(v) for v in line["dir"]) != (1, 0):
                continue  # the rotated "DO NOT WRITE IN THIS AREA" rails
            text = "".join(span["text"] for span in line["spans"])
            text = demojibake(_DOTS.sub(" ", text)).replace("\xa0", " ").strip()
            if not text or _NOISE.search(text):
                continue
            out.append((line["bbox"][0], line["bbox"][2], text))
    return out


def _question_margin(pages: list[list[tuple[float, float, str]]]) -> float:
    """Find the indent the "(a)" parts are set at, so question numbers can be told
    apart from every other number on the page.

    The ladder moved between sessions -- the 2018 and 2019 papers set the question
    number at x=71 where the 2023 papers use x=52 -- so it is measured per paper
    rather than assumed.
    """
    xs = sorted(x0 for page in pages for x0, _, text in page if ALPHA_RE.match(text))
    alpha_x = xs[len(xs) // 2] if xs else DEFAULT_ALPHA_X
    return alpha_x - 5.0


def parse_qp(path: Path, paper_id: str) -> list[Stem]:
    """Read one question paper into the stem of every lettered part."""
    stems: list[Stem] = []
    current: Stem | None = None
    q_now, letter_now = 0, ""

    def open_part(part: str, seed: str) -> Stem:
        stem = Stem(paper_id, q_now, part, seed.strip(), None)
        stems.append(stem)
        return stem

    with fitz.open(path) as doc:
        pages = [_lines(page) for page in doc]
        qnum_x = _question_margin(pages)

        for page_lines in pages:
            for x0, x1, text in page_lines:
                tariff = TARIFF_RE.search(text)
                if tariff and x1 >= TARIFF_X:
                    if current is not None and current.tariff is None:
                        current.tariff = int(tariff.group(1))
                    text = TARIFF_RE.sub("", text).strip()
                    if not text:
                        continue

                qnum = QNUM_RE.match(text) if x0 < qnum_x else None
                if qnum:
                    q_now, letter_now = int(qnum.group(1)), ""
                    text = text[qnum.end():]
                    current = open_part("", text)
                    continue

                alpha = ALPHA_RE.match(text)
                if alpha:
                    letter_now = f"({alpha.group(1)})"
                    text = text[alpha.end():]
                    roman = ROMAN_RE.match(text)
                    part = letter_now + (f"({roman.group(1)})" if roman else "")
                    current = open_part(part, text[roman.end():] if roman else text)
                    continue

                roman = ROMAN_RE.match(text)
                if roman:
                    current = open_part(f"{letter_now}({roman.group(1)})", text[roman.end():])
                    continue

                if current is not None:
                    current.text = f"{current.text} {text}".strip()

    return [s for s in stems if s.text]


def index_stems(stems: list[Stem]) -> dict[str, Stem]:
    """Index by question reference, keeping the first occurrence of each."""
    out: dict[str, Stem] = {}
    for stem in stems:
        out.setdefault(stem.ref, stem)
    return out
