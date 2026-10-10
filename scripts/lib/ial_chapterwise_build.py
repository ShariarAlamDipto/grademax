"""
What the IAL chapterwise segmenters (P1, P2, S1, M1) share since 2026-10-06:
where their papers come from, and how mark schemes are attached.

SOURCES: data/workbook/ial_sources/<unit>/<key>/{QP,MS}.pdf, assembled and
verified by lib/ial_chapterwise_sources.py. The segmenters no longer read the
raw archive, whose wrong files are documented there.

MARK SCHEMES, two verified routes, tried in order:
  1. lib/ial_ms_numbered -- the block the scheme NUMBERS as this question,
     accepted when its printed "(N marks)" total equals the QP's marks.
  2. lib/ial_ms_parse    -- the older reader, accepted when the block's M1/A1/B1
     codes or "(n)" tallies sum to the QP's marks.
Anything neither route verifies is left without a mark scheme. A block from
route 1 may carry a y-band where the next question starts low on its last page.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import fitz

from .ial_ms_numbered import PAD, extract_numbered_blocks, question_starts
from .ial_ms_parse import extract_blocks

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / "data" / "workbook" / "ial_sources"


@dataclass(frozen=True)
class MarkSchemeSlice:
    pages: tuple[int, int]
    top: float | None
    bottom: float | None
    route: str  # "printed total" | "summed part tallies" | "ruled codes" | "unruled codes"


def source_papers(unit: str) -> list[dict]:
    """[{key, year, season, qp, ms, origin}] for the unit's verified sittings."""
    folder = SOURCES / unit.lower()
    rows = json.loads((folder / "sources.json").read_text(encoding="utf-8"))
    return [{"key": r["key"], "year": r["year"], "season": r["season"],
             "qp": folder / r["key"] / "QP.pdf", "ms": folder / r["key"] / "MS.pdf",
             "origin": r["origin"]} for r in rows]


def attach_markschemes(ms_path: Path, expected: dict[int, int]) -> dict[int, MarkSchemeSlice]:
    numbered = extract_numbered_blocks(ms_path, expected)
    legacy, _ = extract_blocks(ms_path, expected)
    starts = question_starts(ms_path, expected)
    out: dict[int, MarkSchemeSlice] = {}
    for number in expected:
        if number in numbered:
            b = numbered[number]
            out[number] = MarkSchemeSlice((b.first_page, b.last_page), b.top, b.bottom,
                                          b.verified_by)
        elif number in legacy:
            out[number] = _trimmed(legacy[number], number, starts)
    return out


def _trimmed(block, number: int, starts: dict[int, tuple[int, float]]) -> MarkSchemeSlice:
    """
    A whole-page block from ial_ms_parse, cut where the scheme's own printed
    cells say the next question begins (and where this one begins, if low on
    its first page). P1 2019 Oct q1 showed q2's scheme on its shared page.
    """
    first, last = block.pages
    top = bottom = None
    own = starts.get(number)
    if own and own[0] == first and own[1] > 140:
        top = max(0.0, own[1] - 18.0)
    later = sorted(v for k, v in starts.items() if k > number and first <= v[0] <= last)
    if later:
        page, y = later[0]
        if y <= 140:
            last = max(first, page - 1)
        else:
            last, bottom = page, y - PAD
    return MarkSchemeSlice((first, last), top, bottom, f"{block.extractor} codes")


def write_slice(ms_path: Path, part: MarkSchemeSlice, target: Path) -> None:
    """Whole pages, except a banded first/last page drawn through a clip."""
    target.parent.mkdir(parents=True, exist_ok=True)
    first, last = part.pages
    with fitz.open(ms_path) as src:
        out = fitz.open()
        try:
            for index in range(first, last + 1):
                top = part.top if index == first else None
                bottom = part.bottom if index == last else None
                rect = src[index].rect
                if top is None and bottom is None:
                    out.insert_pdf(src, from_page=index, to_page=index)
                    continue
                clip = fitz.Rect(rect.x0, top if top is not None else rect.y0,
                                 rect.x1, bottom if bottom is not None else rect.y1)
                if clip.height < 30:
                    continue
                page = out.new_page(width=clip.width, height=clip.height)
                page.show_pdf_page(page.rect, src, index, clip=clip)
            out.save(target)
        finally:
            out.close()
