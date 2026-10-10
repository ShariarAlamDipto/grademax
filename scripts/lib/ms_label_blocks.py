"""
Mark-scheme readers for schemes that print NO usable per-question tally:
cut by the question numbers in the table's own margin column, or -- where
every question opens on a fresh page -- by whole page runs.

Moved out of rebuild_physics_live_segments.py (2011-2017 Physics schemes)
for Maths B and Further Pure, whose older schemes ("Question Number |
Working | Notes | Mark", labels like "10.") have the same property.

`install(seg)` wraps seg.locate_ms_blocks: the subject's own reader runs
first; only questions it left without a scheme send the paper here, and the
result is used only if it attaches MORE questions. Every cut still goes
through the proof gate -- these readers only propose.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import ModuleType

import fitz

from lib import ms_bands

_REGION: list = [None]


def _labels_in(labels, band) -> set[int]:
    inside = set()
    for h in labels:
        if h.axis != band.axis or h.question is None:
            continue
        here = (h.page, h.lo)
        if here < (band.start_page, band.start_at or 0.0):
            continue
        if band.end_at is None:
            if h.page > band.end_page:
                continue
        elif here > (band.end_page, band.end_at):
            continue
        inside.add(h.question)
    return inside


TABLE_LABEL_RE = re.compile(r"^(\d{1,2})(?:$|\.|\()")
COLUMN_REACH = 30.0


def table_labels(ms_path: Path) -> list[ms_bands.BlockHeader]:
    """
    Question numbers standing in the table's "Question number" column, read in
    DISPLAYED coordinates so upright and /Rotate 90 pages are treated alike.

    ms_bands.find_question_labels loses its column when a scheme mixes upright
    and rotated pages (2013 May-Jun P1R ran 1..6 of 14, P2R 1..1). Here the
    column is simply the "Question" header's own x-range, page by page, and a
    label is a number -- or the "5(a)(i)" form the 2017 specimen prints --
    whose left edge sits inside it. Each anchor's `lo` is reported on the
    page's block axis in UNROTATED space, which is what the band code cuts on.
    """
    anchors: list[ms_bands.BlockHeader] = []
    column: tuple[float, float] | None = None
    with fitz.open(ms_path) as doc:
        for index, page in enumerate(doc):
            axis = ms_bands.page_axis(page)
            if axis is None:
                continue
            matrix = page.rotation_matrix
            shown = [(fitz.Rect(w[:4]) * matrix, w) for w in page.get_text("words")]
            header_bottom = -1.0
            for rect, w in shown:
                if w[4] in ("Question", "Q."):  # 2011 FPM schemes head the column "Q."
                    column = (rect.x0 - 20.0, rect.x0 + COLUMN_REACH)
                    header_bottom = max(header_bottom, rect.y1)
            if column is None:
                continue
            for rect, w in shown:
                match = TABLE_LABEL_RE.match(w[4])
                if not match or rect.y0 <= header_bottom:
                    continue
                if not column[0] <= rect.x0 <= column[1]:
                    continue
                lo, _ = ms_bands._extent(w[:4], axis)
                anchors.append(ms_bands.BlockHeader(page=index, lo=lo,
                                                    question=int(match.group(1)), axis=axis))
    anchors.sort(key=lambda h: (h.page, h.lo))
    return anchors


LEFT_FRACTION = 0.22


def _page_lead(page) -> tuple[int | None, bool]:
    """(first question number in the page's left column, page has a table header)."""
    matrix = page.rotation_matrix
    shown = sorted(
        ((fitz.Rect(w[:4]) * matrix, w[4]) for w in page.get_text("words")),
        key=lambda t: (round(t[0].y0 / 4), t[0].x0),
    )
    width = (page.rect * 1).width
    has_header = any(text == "Question" for _, text in shown)
    left = [(r, t) for r, t in shown if r.x0 < width * LEFT_FRACTION]
    for i, (rect, text) in enumerate(left):
        if not text.isdigit():
            continue
        # "1 0": a two-digit number set as two words on one row, or wrapped by
        # the narrow column into "1" over "0" at the same x (2013 May-Jun P1R).
        for other, digit in left[i + 1:]:
            if not digit.isdigit() or len(digit) != 1:
                continue
            same_row = abs(other.y0 - rect.y0) < 3 and 0 < other.x0 - rect.x1 < 4
            wrapped = abs(other.x0 - rect.x0) < 3 and 0 < other.y0 - rect.y0 < 22
            if same_row or wrapped:
                text += digit
                break
        if len(text) <= 2:
            return int(text), has_header
    return None, has_header


def page_blocks(ms_path: Path, fences, warnings: list[str]) -> dict[int, tuple]:
    """
    Whole-page blocks for the 2011-2017 schemes that start every question on a
    fresh page: question n opens on the first page whose left column begins
    with n; following pages that repeat n, or carry the table header and no
    number, continue it. A question 1 whose label is unreadable takes the table
    pages before question 2. Anything out of order attaches nothing.
    """
    with fitz.open(ms_path) as doc:
        leads = [_page_lead(page) for page in doc]
    first_table = next((i for i, (_, header) in enumerate(leads) if header), None)
    starts: dict[int, int] = {}
    expected, page_index = 1, 0
    while page_index < len(leads):
        number, _ = leads[page_index]
        if number == expected:
            starts[expected] = page_index
            expected += 1
        elif number == expected + 1 and expected == 1 and first_table is not None \
                and first_table < page_index:
            starts[1] = first_table
            starts[2] = page_index
            expected = 3
        page_index += 1
    if len(starts) != len(fences):
        warnings.append(f"page starts found for {sorted(starts)} of {len(fences)} -- none attached")
        return {}
    with fitz.open(ms_path) as doc:
        has_words = [bool(page.get_text("words")) for page in doc]
    result: dict[int, tuple] = {}
    last = max(starts)
    for question, start in starts.items():
        pages = [start]
        if question != last:
            # Starts are proven in order, so every page up to the next start is
            # this question's -- including a continuation page that prints no
            # header row (2013 May-Jun P1R q2). Blank pages are left out.
            pages += [i for i in range(start + 1, starts[question + 1]) if has_words[i]]
        else:
            for i in range(start + 1, len(leads)):
                number, header = leads[i]
                if number == question or (number is None and header):
                    pages.append(i)
                else:
                    break
        result[question] = tuple(_REGION[0](page=p) for p in pages)
    warnings.append(f"mark scheme read as one question per page run: {len(result)}/{len(fences)}")
    return result


LABEL_LEAD = 2.0   # start this far above the question's own label
LABEL_GAP = 1.0    # stop this far above the next question's label


def tighten(band):
    """
    bands_from_headers pads PAD_BEFORE (6pt) on both edges. On tight tables
    (2011 Maths B P1, ~15pt rows) the end padding sliced the last line of the
    row and the start padding took the previous row's descenders. The next
    question's number sits on its row's top rule, so the row ends 1pt above
    it; the row starts 2pt above its own label.
    """
    import dataclasses
    if band.axis != ms_bands.AXIS_Y:
        return band
    start = None if band.start_at is None else band.start_at + ms_bands.PAD_BEFORE - LABEL_LEAD
    end = None if band.end_at is None else band.end_at + ms_bands.PAD_BEFORE - LABEL_GAP
    return dataclasses.replace(band, start_at=start, end_at=end)


def label_blocks(ms_path: Path, fences, warnings: list[str]) -> dict[int, tuple]:
    # Whole pages first: when every question opens on a fresh page they are
    # exact, and they never cut through a rotated page.
    by_page = page_blocks(ms_path, fences, warnings)
    if len(by_page) == len(fences):
        return by_page
    found = _label_blocks(ms_path, fences, warnings, ms_bands.find_question_labels(ms_path))
    if len(found) == len(fences):
        return found
    by_table = _label_blocks(ms_path, fences, warnings, table_labels(ms_path))
    if len(by_table) > len(found):
        found = by_table
    if len(found) == len(fences):
        return found
    by_page = page_blocks(ms_path, fences, warnings)
    return by_page if len(by_page) > len(found) else found


def _label_blocks(ms_path: Path, fences, warnings: list[str], labels) -> dict[int, tuple]:
    """
    Cut a scheme that prints no usable tallies by the question numbers in its
    own margin column. Each number must appear in order 1..n, and each band must
    hold no OTHER question's margin number; a band that does is dropped.
    """
    assignment: dict[int, int] = {}
    expected = 1
    for index, h in enumerate(labels):
        if h.question == expected and expected in fences:
            assignment[expected] = index
            expected += 1
    if len(assignment) != len(fences):
        warnings.append(f"margin labels run 1..{expected - 1} of {len(fences)} -- none attached")
        return {}
    with fitz.open(ms_path) as doc:
        last_page = doc.page_count - 1
    bands = ms_bands.bands_from_headers(labels, assignment, last_page=last_page,
                                        runs_to_end=max(fences))
    bands = {q: tighten(b) for q, b in bands.items()}
    tallies = ms_bands.find_tallies(ms_path)
    result: dict[int, tuple] = {}
    for question, band in sorted(bands.items()):
        others = _labels_in(labels, band) - {question}
        if others:
            warnings.append(f"q{question}: label band also holds labels {sorted(others)} -- dropped")
            continue
        if len([t for t in tallies if ms_bands.verify_band([t], band)]) > 1:
            warnings.append(f"q{question}: label band holds two tallies -- dropped")
            continue
        extents = ms_bands.page_extents_of(ms_path, band.axis)
        result[question] = ms_bands.band_to_regions(band, _REGION[0], extents)
    warnings.append(f"mark scheme read by margin labels: {len(result)}/{len(fences)}")
    return result



def install(seg: ModuleType, name: str = "locate_ms_blocks") -> None:
    _REGION[0] = seg.Region
    original = getattr(seg, name)

    def locate(ms_path: Path, fences, *args, **kwargs):
        kept, warnings = original(ms_path, fences, *args, **kwargs)
        if len(kept) == len(fences):
            return kept, warnings
        extra: list[str] = []
        found = label_blocks(ms_path, fences, extra)
        if len(found) > len(kept):
            warnings.extend(extra)
            return found, warnings
        return kept, warnings

    setattr(seg, name, locate)
