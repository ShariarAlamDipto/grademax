"""Deterministic text + structure extraction from per-question PDFs (PyMuPDF)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field

import fitz  # PyMuPDF

# Lines / fragments that are page furniture, not question content.
_NOISE_PATTERNS = [
    re.compile(r"^\*?P\d{5}[A-Z0-9]*\*?$"),          # barcode e.g. *P73430A0824*
    re.compile(r"DO NOT WRITE IN THIS AREA", re.I),
    re.compile(r"·"),                                  # scraper/PMT watermark line
    re.compile(r"^\s*Turn over\s*$", re.I),
    re.compile(r"^\s*Total Marks\s*$", re.I),
    re.compile(r"^\s*BLANK PAGE\s*$", re.I),
    re.compile(r"©\s*\d{4}\s*Pearson", re.I),
    re.compile(r"^\s*\d+\s*$"),                         # lone page numbers
]

_TOTAL_RE = re.compile(r"Total for Question\s*\d+\s*(?:=|is)\s*(\d+)\s*mark", re.I)
_SUBPART_RE = re.compile(r"\(([a-h])\)")
_ROMAN_RE = re.compile(r"\(([ivx]{1,4})\)")


@dataclass
class QuestionText:
    text: str                       # cleaned question text
    raw_chars: int
    total_marks: int | None
    subpart_labels: list[str]
    n_subparts: int
    has_diagram: bool
    has_graph: bool
    has_data_table: bool
    n_images: int
    pages: int
    extras: dict = field(default_factory=dict)


def _read(path: str) -> tuple[str, int, int]:
    doc = fitz.open(path)
    text = "".join(p.get_text() for p in doc)
    n_images = 0
    for p in doc:
        for img in p.get_images(full=True):
            # Skip tiny images (icons); count plausible figures.
            n_images += 1
    pages = doc.page_count
    doc.close()
    return text, n_images, pages


def clean_text(raw: str) -> str:
    out = []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        if any(p.search(s) for p in _NOISE_PATTERNS):
            continue
        out.append(s)
    text = "\n".join(out)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _ordered_unique(seq: list[str]) -> list[str]:
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def extract_question(qp_path: str) -> QuestionText:
    raw, n_images, pages = _read(qp_path)
    text = clean_text(raw)
    low = text.lower()

    tm = _TOTAL_RE.search(raw)
    total = int(tm.group(1)) if tm else None

    letters = _ordered_unique(_SUBPART_RE.findall(text))
    # Keep only a contiguous run from 'a' (avoids stray "(a)" inside prose).
    contiguous: list[str] = []
    expected = ord("a")
    for ch in letters:
        if ord(ch) == expected:
            contiguous.append(ch)
            expected += 1
    romans = _ordered_unique(_ROMAN_RE.findall(text))

    has_graph = any(k in low for k in ("grid", "axes", "graph", "plot ", "sketch the graph", "sketch a graph"))
    has_table = ("\t" in raw) or bool(re.search(r"\btable\b", low)) or low.count("|") > 4
    has_diagram = (n_images > 0) or any(
        k in low for k in ("figure", "diagram", "shows", "apparatus", "not to scale", "the circuit")
    )

    return QuestionText(
        text=text,
        raw_chars=len(raw),
        total_marks=total,
        subpart_labels=contiguous,
        n_subparts=len(contiguous),
        has_diagram=has_diagram,
        has_graph=has_graph,
        has_data_table=has_table,
        n_images=n_images,
        pages=pages,
        extras={"romans": romans},
    )


def read_markscheme_text(ms_path: str, limit: int = 3000) -> str:
    try:
        return clean_text(_read(ms_path)[0])[:limit]
    except Exception:
        return ""
