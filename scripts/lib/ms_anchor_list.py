"""
Candidate question starts in a mark scheme, for cutting one by hand.

Prints every text line whose first word (in the left part of the page) looks
like a question label -- "7", "7.", "7(a)", "Q7" -- with its page and y in
DISPLAYED coordinates, plus the line's opening words. The reviewer picks the
true starts while looking at the rendered page; the cut itself is recorded as
"ms_regions" in manual_review.json and applied by live_rebuild_common.
"""

from __future__ import annotations

import re
from pathlib import Path

import fitz

LABEL = re.compile(r"^Q?\d{1,2}(?:\.|\(|$)")
LEFT = 0.30


def anchors(ms_path: Path) -> list[tuple[int, float, str]]:
    found = []
    with fitz.open(ms_path) as doc:
        for index, page in enumerate(doc):
            matrix = page.rotation_matrix
            width = (page.rect).width
            lines: dict[int, list] = {}
            for w in page.get_text("words"):
                rect = fitz.Rect(w[:4]) * matrix
                lines.setdefault(round(rect.y0 / 3), []).append((rect, w[4]))
            for _, words in sorted(lines.items()):
                words.sort(key=lambda t: t[0].x0)
                rect, first = words[0]
                if rect.x0 < width * LEFT and LABEL.match(first):
                    found.append((index, round(rect.y0, 1), " ".join(t for _, t in words[:8])))
    return found


def render_with_ruler(pdf: Path, page_index: int, out: Path, dpi: int = 60) -> Path:
    """The page as displayed, with a y ruler every 50pt down the left edge."""
    with fitz.open(pdf) as doc:
        page = doc[page_index]
        shape_doc = fitz.open()
        shape_doc.insert_pdf(doc, from_page=page_index, to_page=page_index)
        p = shape_doc[0]
        if p.rotation:
            p.remove_rotation()
        for y in range(0, int(p.rect.height), 50):
            p.draw_line((0, y), (18, y), color=(1, 0, 0), width=0.8)
            p.insert_text((20, y + 4), str(y), fontsize=7, color=(1, 0, 0))
        p.get_pixmap(dpi=dpi).save(out)
        shape_doc.close()
    return out


def per_table_regions(ms_path: Path, pad: float = 3.0) -> dict[int, list[list[float]]]:
    """
    For schemes that give every question its own small table (2014 Jan Maths B
    P1): each "Question" header opens a table; the question number ("7",
    "15(a)") is the first label standing under that header, left of the
    table's Answer/Working column. A table with no number continues the
    previous question (its notes run on). Returns {q: [[page, top, bottom]]}
    in page coordinates for "ms_regions" -- every one must still be READ.
    """
    tables = []  # (page, top, number or None)
    last_text: dict[int, float] = {}
    with fitz.open(ms_path) as doc:
        for index, page in enumerate(doc):
            words = page.get_text("words")
            last_text[index] = max((w[3] for w in words if w[4] != "GradeMax"), default=0)
            # A table that runs on from the previous page has no header here:
            # the text above the page's first header continues the question
            # before it (2013 May-Jun P2R q2(b) onwards).
            page_text = " ".join(w[4] for w in words)
            if "Registered company number" in page_text or "Further copies" in page_text:
                continue  # Pearson's back matter, never part of a question
            content = [w for w in words if w[4] != "GradeMax" and 60 < w[1] < page.rect.height - 45]
            first_head = min((w[1] for w in words if w[4] == "Question"), default=None)
            if content:
                top_text = min(w[1] for w in content)
                if first_head is None or top_text < first_head - 25:
                    tables.append((index, top_text - pad, None))
            for h in sorted((w for w in words if w[4] == "Question"), key=lambda w: w[1]):
                same_row = [w for w in words if w[4] in ("Answer", "Working", "Scheme")
                            and abs(w[1] - h[1]) < 4]
                right = min((w[0] for w in same_row), default=h[2] + 20) - 2
                labels = sorted((w for w in words
                                 if re.match(r"^\d{1,2}(\(|$)", w[4]) and h[3] < w[1] < h[3] + 40
                                 and h[0] - 25 <= w[0] and w[2] <= right),
                                key=lambda w: w[1])
                number = int(re.match(r"\d+", labels[0][4]).group()) if labels else None
                tables.append((index, h[1] - pad, number))
    out: dict[int, list[list[float]]] = {}
    current = None
    for i, (page, top, number) in enumerate(tables):
        nxt = tables[i + 1] if i + 1 < len(tables) else None
        bottom = nxt[1] if nxt and nxt[0] == page else last_text[page] + pad
        if number is not None:
            current = number
        if current is not None:
            out.setdefault(current, []).append([page, round(top, 1), round(bottom, 1)])
    return out


def ink_blocks(pdf: Path, page_index: int, dpi: int = 100, min_gap_pt: float = 6.0,
               top_pt: float = 55.0, bottom_margin_pt: float = 45.0) -> list[list[float]]:
    """
    Vertical extents (page points) of the inked blocks on a page, separated by
    fully blank horizontal bands at least `min_gap_pt` tall -- the gaps between
    one question's table and the next on IMAGE-ONLY schemes (no text layer, no
    vector rules). The stamp line at the top and the footer are excluded.
    """
    with fitz.open(pdf) as doc:
        page = doc[page_index]
        pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)
        scale = dpi / 72.0
        width, height, samples = pix.width, pix.height, pix.samples
        lo = int(top_pt * scale)
        hi = int((page.rect.height - bottom_margin_pt) * scale)
        inked = []
        for row in range(lo, min(hi, height)):
            line = samples[row * width:(row + 1) * width]
            inked.append(any(b < 160 for b in line[int(width * 0.04):int(width * 0.96)]))
        blocks, start, gap = [], None, 0
        min_gap = int(min_gap_pt * scale)
        for i, on in enumerate(inked):
            if on:
                if start is None:
                    start = i
                gap = 0
                end = i
            elif start is not None:
                gap += 1
                if gap >= min_gap:
                    blocks.append([(lo + start) / scale, (lo + end + 1) / scale])
                    start, gap = None, 0
        if start is not None:
            blocks.append([(lo + start) / scale, (lo + end + 1) / scale])
    return [[round(a, 1), round(b, 1)] for a, b in blocks]


NOTE_START = re.compile(r"^(Notes?|NB|N\.B\.?|\d\.|\(?[a-h]\)|Alternative|ALT|OR|Accept|Allow)", re.I)


def question_blocks(pdf: Path, pages: list[int], min_gap_pt: float = 6.0) -> list[list[list[float]]]:
    """
    Ink blocks across `pages`, grouped into questions in reading order: a block
    whose first word opens a note ("Notes", "NB", "1.", "(b)", "OR", ...) or that
    holds no text continues the current question; any other block starts the
    next one. Returns one region list ([page, top, bottom] ...) per question.
    The caller must check the count against the paper and READ every cut.
    """
    questions: list[list[list[float]]] = []
    with fitz.open(pdf) as doc:
        for page_index in pages:
            words = doc[page_index].get_text("words")
            for top, bottom in ink_blocks(pdf, page_index, min_gap_pt=min_gap_pt):
                inside = sorted((w for w in words if top - 1 <= w[1] <= bottom),
                                key=lambda w: (round(w[1] / 3), w[0]))
                first = inside[0][4] if inside else ""
                region = [page_index, round(top - 3, 1), round(bottom + 3, 1)]
                if questions and (not first or NOTE_START.match(first)):
                    questions[-1].append(region)
                else:
                    questions.append([region])
    return questions
