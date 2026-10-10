"""
Turn a hand-picked question start and the next question's start in a mark
scheme into "ms_display_regions" for manual_review.json.

Anchors are (page, y) in DISPLAYED points, as lib/ms_anchor_list.anchors
prints them. Each edge snaps up to the nearest table rule just above the
anchor's text (rules sit 1-4pt above a row's first line), so a cut never keeps
a sliver of the neighbouring row. Pages between start and end are taken whole
down to the running footer. The result is only a proposal: it is rendered and
read before it is recorded.
"""

from __future__ import annotations

from pathlib import Path

import fitz

SNAP_REACH = 8.0     # a rule this far above the anchor text is the row's top edge
TEXT_LEAD = 2.5      # no rule found: start this far above the text
BODY_MARGIN = 30.0   # running header/footer band kept off whole pages


def _rules(page: fitz.Page) -> list[float]:
    matrix = page.rotation_matrix
    ys = set()
    for drawing in page.get_drawings():
        rect = fitz.Rect(drawing["rect"]) * matrix
        rect.normalize()
        if rect.height <= 2.0:
            ys.add(round(rect.y0, 1))
        else:  # filled cells / boxes: both horizontal edges are rules
            ys.update((round(rect.y0, 1), round(rect.y1, 1)))
    return sorted(ys)


def edge(page: fitz.Page, text_y: float, reach: float = SNAP_REACH) -> float:
    above = [y for y in _rules(page) if text_y - reach <= y <= text_y + 0.5]
    return max(above) - 0.5 if above else text_y - TEXT_LEAD


def label_cuts(ms_path: Path, labels: list[tuple[int, int, float]],
               row_reach: float = 45.0) -> dict[int, list[list[float]]]:
    """
    Whole-paper cut for tables that CENTRE the question number in a tall row
    (2019 Jan P1): the row's first working line stands above its label, so a
    cut at the label slices it off. Each question starts at the last rule at
    or above its label (within row_reach, and below the previous label) and
    runs to the next question's start. labels = [(question, page, y)] in order.
    """
    with fitz.open(ms_path) as doc:
        starts = []
        previous: tuple[int, float] | None = None
        for question, page_index, y in labels:
            reach = row_reach
            if previous and previous[0] == page_index:
                reach = min(reach, y - previous[1] - 1.0)
            page = doc[page_index]
            top = edge(page, y, reach)
            # A table header row standing right above belongs to this question.
            header = [r.y0 for r, w in _shown_words(page)
                      if w in ("Question", "Qu") and top - 30.0 <= r.y0 <= top + 1.0]
            if header:
                top = edge(page, min(header))
            starts.append((question, page_index, top))
            previous = (page_index, y)
        cuts: dict[int, list[list[float]]] = {}
        for i, (question, s_page, s_top) in enumerate(starts):
            if i + 1 < len(starts):
                _, e_page, e_top = starts[i + 1]
            else:
                e_page, e_top = s_page, body_bottom(doc[s_page])
            out = []
            for index in range(s_page, e_page + 1):
                page = doc[index]
                top = s_top if index == s_page else BODY_MARGIN
                bottom = e_top if index == e_page else body_bottom(page)
                if index == e_page and index != s_page and holds_only_header(page, top, bottom):
                    continue
                if bottom - top > 4.0:
                    out.append([index, round(top, 1), round(bottom, 1)])
            cuts[question] = out
    return cuts


def _shown_words(page: fitz.Page) -> list[tuple[fitz.Rect, str]]:
    matrix = page.rotation_matrix
    return [(fitz.Rect(w[:4]) * matrix, w[4]) for w in page.get_text("words")]


def body_bottom(page: fitz.Page) -> float:
    return page.rect.height - BODY_MARGIN


HEADER_WORDS = {"Question", "Qu", "Q", "Number", "Working", "Answer", "Mark", "Marks",
                "Notes", "Scheme", "Total", "Sub-", "Sub-Total", "AO", "Additional",
                "Guidance", "Part"}


def holds_only_header(page: fitz.Page, top: float, bottom: float) -> bool:
    """True when the strip is a continuation page's bare table header (plus the stamp)."""
    matrix = page.rotation_matrix
    for w in page.get_text("words"):
        rect = fitz.Rect(w[:4]) * matrix
        middle = (rect.y0 + rect.y1) / 2
        if top <= middle <= bottom and w[4] not in HEADER_WORDS and rect.y0 > BODY_MARGIN:
            return False
    return True


def regions(ms_path: Path, start: tuple[int, float], end: tuple[int, float] | None,
            top_margin: float = BODY_MARGIN) -> list[list[float]]:
    """
    start/end = (page, y of the label text). end None = to the bottom of the
    start page. An end at the very top of its page closes on the page before.
    """
    out: list[list[float]] = []
    with fitz.open(ms_path) as doc:
        s_page, s_y = start
        e_page, e_y = end if end is not None else (s_page, None)
        for index in range(s_page, e_page + 1):
            page = doc[index]
            top = edge(page, s_y) if index == s_page else top_margin
            if index == e_page and e_y is not None:
                bottom = edge(page, e_y)
            else:
                bottom = body_bottom(page)
            if index == e_page and index != s_page and holds_only_header(page, top, bottom):
                continue
            if bottom - top > 4.0:
                out.append([index, round(top, 1), round(bottom, 1)])
    return out
