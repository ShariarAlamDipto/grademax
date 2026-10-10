#!/usr/bin/env python3
"""
Rebuild every live IGCSE Physics (4PH1/4PH0) question + mark-scheme segment the
test builder and worksheet generator serve, from the whole-paper PDFs, and
PROVE each pair before it can be published.

    python scripts/rebuild_physics_live_segments.py            # build + verify (staging only)
    python scripts/rebuild_physics_live_segments.py --paper 2015_jan_P1 --verbose

Writes only to data/analysis/live_rebuild/4PH1/ -- nothing live. Publishing is
publish_physics_live_segments.py, which reads the verdicts written here.

WHY A REBUILD AND NOT A PATCH
-----------------------------
The 2026-10-07 content audit (audit_physics_live_ms_linkage.py) found the
WHOLE-PAPER documents are right -- every 2018+ paper's QP fences and MS tallies
agree question by question -- while the live per-question cuts are not: runs of
questions dumped into one file, cuts taken from another sitting's document,
schemes holding two questions. So the cuts are redone from the documents.

CUTTING reuses build_physics_workbook_segments.py (fences, blank pages,
Equation Booklet excluded, hidden-layer safe extraction, banded schemes).

ONE ADDITION: SCHEMES THAT NAME NO QUESTION
-------------------------------------------
Every 2011-2017 scheme (4PH0 era) closes a block with a bare "Total 3 marks";
the workbook segmenter only reads "Total for question N = M marks" and so
attached nothing for those years. Here the bare tallies are attached ONLY when
their marks sequence equals the question paper's fence marks for EVERY question
in order (after dropping a trailing whole-paper total). A 7-16 long sequence of
tariffs does not line up by accident, and anything short of a full match
attaches nothing: a missing scheme is honest, a neighbour's is not.

THE GATE
--------
Every written pair is re-read by lib.live_ms_linkage.judge -- the same rules the
live audit uses, independent of the cutting code. A pair is publishable when it
is PROVEN, or when the paper's full tally sequence matched (SEQUENCE_PROVEN) and
the pair itself shows no contradiction. Everything else is listed for review.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_physics_workbook_segments as seg  # noqa: E402
from lib import ms_bands  # noqa: E402
from lib.live_ms_linkage import judge, read_evidence  # noqa: E402
from lib.live_ms_review import load_decisions, render_pair  # noqa: E402
import lib.live_rebuild_common  # noqa: E402,F401 -- installs the guarded header snap
from lib.live_paper_sources import REBUILD_DIR, LivePaper, load_live_papers  # noqa: E402

CODE = "4PH1"

# ── scrambled text layers ───────────────────────────────────────────────────
# 2013 May-Jun P1/P1R/P2R and 2015 May-Jun P1 embed fonts whose glyph codes have
# no Unicode map: the page LOOKS right, the text layer is noise, so no fence can
# be read. For those documents only, every get_text call is answered from a
# Tesseract OCR text page instead. The PDFs themselves are not changed.
TESSDATA = Path("C:/Program Files/Tesseract-OCR/tessdata")
OCR_DOCS: set[str] = set()
_original_get_text = seg.fitz.Page.get_text


def _ocr_get_text(self, *args, **kwargs):
    name = getattr(self.parent, "name", "") or ""
    if "textpage" not in kwargs and name and str(Path(name).resolve()) in OCR_DOCS:
        kwargs["textpage"] = self.get_textpage_ocr(dpi=200, full=True, language="eng",
                                                   tessdata=str(TESSDATA))
    return _original_get_text(self, *args, **kwargs)


seg.fitz.Page.get_text = _ocr_get_text


def is_scrambled(qp_path: Path) -> bool:
    """Plenty of text, yet not one readable 'Question' anywhere."""
    with seg.fitz.open(qp_path) as doc:
        text = " ".join(page.get_text() for page in doc)
    return len(text) > 5000 and "Question" not in text
STAGE_DIR = REBUILD_DIR / CODE
SEGMENTS_DIR = STAGE_DIR / "segments"
VERDICTS_PATH = STAGE_DIR / "verdicts.json"
REVIEW_PATH = STAGE_DIR / "manual_review.json"
RENDER_DIR = STAGE_DIR / "review"
DECISIONS = load_decisions(REVIEW_PATH)

_current_key: list[str] = [""]
_current_total: list[int] = [0]

_original_locate = seg.locate_ms_blocks


def sequence_assignment(
    tallies: list[ms_bands.Tally], fences: dict[int, tuple[int, int, float]], paper_total: int
) -> dict[int, int] | None:
    """question -> tally index, only when the marks sequences match exactly."""
    marks = [t.marks for t in tallies]
    if len(marks) == len(fences) + 1 and marks[-1] == paper_total:
        marks = marks[:-1]
    expected = [fences[q][1] for q in sorted(fences)]
    if marks != expected:
        return None
    return {q: i for i, q in enumerate(sorted(fences))}


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
    with seg.fitz.open(ms_path) as doc:
        for index, page in enumerate(doc):
            axis = ms_bands.page_axis(page)
            if axis is None:
                continue
            matrix = page.rotation_matrix
            shown = [(seg.fitz.Rect(w[:4]) * matrix, w) for w in page.get_text("words")]
            header_bottom = -1.0
            for rect, w in shown:
                if w[4] == "Question":
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
        ((seg.fitz.Rect(w[:4]) * matrix, w[4]) for w in page.get_text("words")),
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
    with seg.fitz.open(ms_path) as doc:
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
    with seg.fitz.open(ms_path) as doc:
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
        result[question] = tuple(seg.Region(page=p) for p in pages)
    warnings.append(f"mark scheme read as one question per page run: {len(result)}/{len(fences)}")
    return result


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
    with seg.fitz.open(ms_path) as doc:
        last_page = doc.page_count - 1
    bands = ms_bands.bands_from_headers(labels, assignment, last_page=last_page,
                                        runs_to_end=max(fences))
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
        result[question] = ms_bands.band_to_regions(band, seg.Region, extents)
    warnings.append(f"mark scheme read by margin labels: {len(result)}/{len(fences)}")
    return result


def locate_ms_blocks_live(ms_path: Path, fences):
    kept, warnings = _original_locate(ms_path, fences)
    if len(kept) == len(fences) or seg.find_physics_tallies(ms_path):
        return kept, warnings

    tallies = ms_bands.find_tallies(ms_path)
    assignment = sequence_assignment(tallies, fences, _current_total[0])
    if assignment is None:
        warnings.append(
            f"bare tallies {[t.marks for t in tallies]} do not match fence marks "
            f"{[fences[q][1] for q in sorted(fences)]}"
        )
        by_label = label_blocks(ms_path, fences, warnings)
        return (by_label if len(by_label) > len(kept) else kept), warnings

    headers = ms_bands.find_block_headers(ms_path)
    bands = ms_bands.bands_from_tallies(tallies, assignment, headers)
    first = min(assignment, key=assignment.get)
    if first in bands:
        bands[first] = seg.extend_first_band(bands[first], first, headers)
    with seg.fitz.open(ms_path) as doc:
        last_page = doc.page_count - 1
    result: dict[int, tuple] = {}
    for question, band in sorted(bands.items()):
        band = seg.skip_empty_opening(ms_path, band)
        if band.start_page > last_page:
            continue
        inside = [t for t in tallies if ms_bands.verify_band([t], band)]
        if len(inside) != 1:
            warnings.append(f"q{question}: sequence band holds {len(inside)} tallies -- dropped")
            continue
        extents = ms_bands.page_extents_of(ms_path, band.axis)
        result[question] = ms_bands.band_to_regions(band, seg.Region, extents)
    warnings.append(f"mark scheme read as a bare-tally sequence: {len(result)}/{len(fences)}")
    return result, warnings


seg.locate_ms_blocks = locate_ms_blocks_live


_original_extract = seg.extract_regions


def extract_regions_live(source_pdf: Path, regions, target: Path) -> None:
    """
    seg.extract_regions, made safe for pages that carry /Rotate.

    Band coordinates come from get_text, i.e. the UNROTATED page, but
    extract_regions clamps them to page.rect (the ROTATED rectangle) and
    show_pdf_page clips rotated sources -- the 2011-2017 schemes are stored
    as /Rotate 90 pages, and their cuts lost the Question column and the left
    of every line. Each rotated page is copied alone, its rotation removed
    (appearance unchanged), and the band mapped through the matrix that
    remove_rotation returns before cutting.
    """
    with seg.fitz.open(source_pdf) as probe:
        rotated = any(probe[r.page].rotation for r in regions if r.cropped)
    if not rotated:
        _original_extract(source_pdf, regions, target)
        return
    with seg.open_source(source_pdf) as src:
        target.parent.mkdir(parents=True, exist_ok=True)
        out = seg.fitz.open()
        try:
            for region in regions:
                page = src[region.page]
                if not region.cropped:
                    out.insert_pdf(src, from_page=region.page, to_page=region.page)
                    continue
                full = seg.fitz.Rect(0, 0, page.cropbox.width, page.cropbox.height)
                clip = seg.fitz.Rect(
                    full.x0 if region.left is None else region.left,
                    full.y0 if region.top is None else region.top,
                    full.x1 if region.right is None else region.right,
                    full.y1 if region.bottom is None else region.bottom,
                ) & full
                # page.rotation_matrix maps unrotated -> displayed coordinates.
                # (remove_rotation's returned matrix carries the wrong offset on
                # these pages: 595 instead of 842, measured 2026-10-07.)
                matrix = page.rotation_matrix
                single = seg.fitz.open()
                single.insert_pdf(src, from_page=region.page, to_page=region.page)
                flat = single[0]
                if flat.rotation:
                    flat.remove_rotation()
                    clip = (clip * matrix) & flat.rect
                if clip.width < 20 or clip.height < 20:
                    out.insert_pdf(single)
                    continue
                band = out.new_page(width=clip.width, height=clip.height)
                band.show_pdf_page(seg.fitz.Rect(0, 0, clip.width, clip.height), single, 0,
                                   clip=clip)
            out.save(target)
        finally:
            out.close()


STRIP_MAX_HEIGHT = 120.0


def drop_empty_strips(target: Path) -> None:
    """
    Remove thin band pages that hold no text: the white space a band keeps
    between the last row of one question and the label of the next (a 91pt
    strip after 2013 May-Jun P1 q2's scheme). A full page is never removed.
    """
    with seg.fitz.open(target) as doc:
        empty = [
            i for i, page in enumerate(doc)
            if min(page.rect.width, page.rect.height) < STRIP_MAX_HEIGHT
            and not any(not seg.WATERMARK_RE.fullmatch(w[4]) for w in page.get_text("words"))
            and not page.get_images()
        ]
        if not empty or len(empty) == doc.page_count:
            return
        doc.delete_pages(empty)
        doc.save(target.with_suffix(".tmp"))
    target.with_suffix(".tmp").replace(target)


def extract_and_trim(source_pdf: Path, regions, target: Path) -> None:
    extract_regions_live(source_pdf, regions, target)
    drop_empty_strips(target)
    if target.parent.name == "questions":
        lib.live_rebuild_common.drop_blank_sheets(target)


seg.extract_regions = extract_and_trim


def paper_digit(paper_number: str) -> str:
    """'1', '1R', '1P', '1PR' -> '1'."""
    return re.match(r"\d", paper_number).group()


def to_source(paper: LivePaper) -> seg.PaperSource | None:
    if paper.qp_path is None:
        return None
    cover = seg.read_cover_code(paper.qp_path)
    if cover:
        spec = cover.split("/")[0]
    else:
        spec = "4PH1" if seg.session_rank(paper.year, paper.season) >= seg.session_rank(
            *seg.FIRST_4PH1) else "4PH0"
    total = seg.PAPER_TOTALS[(spec, paper_digit(paper.paper_number))]
    manual_key = f"{paper.year}_{paper.season}_{seg.PAPER_CODES.get(paper.paper_number, '')}"
    key = manual_key if manual_key in seg.MANUAL_QP_RANGES else paper.key
    return seg.PaperSource(key=key, year=paper.year, season=paper.season,
                           paper_number=paper.paper_number, spec=spec, total_marks=total,
                           qp_path=paper.qp_path, ms_path=paper.ms_path)


PUBLISHABLE = {"PROVEN", "SEQUENCE_PROVEN", "MANUAL_PROVEN", "REVIEWED_PROVEN"}


def _ms_marks(ms) -> int | None:
    if ms is None:
        return None
    if ms.totals:
        return ms.totals[-1][1]
    if ms.tallies:
        return ms.tallies[-1]
    return ms.column_marks


def verify_written(key: str, result: seg.PaperResult) -> list[dict]:
    """
    Re-read every written pair with the live audit's own rules.

    SEQUENCE_PROVEN is decided HERE, from the written files: when every
    question of the paper has a scheme and the schemes' marks equal the
    question files' marks for the whole paper in order, a scheme that prints
    no number is still pinned to its question by that sequence.
    """
    paper_dir = SEGMENTS_DIR / key
    read = []
    for s in result.segments:
        qp_file = paper_dir / "questions" / f"q{s.number}.pdf"
        ms_file = paper_dir / "markschemes" / f"q{s.number}.pdf"
        qp = read_evidence(qp_file, is_ms=False)
        ms = read_evidence(ms_file, is_ms=True) if ms_file.is_file() else None
        read.append((s, qp_file, ms_file, qp, ms))

    # Every scheme present, every readable one agreeing with its question's
    # marks in order, at most one unreadable; that one must still show its own
    # margin number (LABEL_ONLY) to be accepted.
    marks = [_ms_marks(ms) for _, _, _, _, ms in read]
    sequence_ok = (
        len(read) > 1
        and all(ms is not None for *_, ms in read)
        and all(m is None or m == s.marks for m, (s, *_) in zip(marks, read))
        and sum(m is None for m in marks) <= 1
    )
    rows = []
    for (s, qp_file, ms_file, qp, ms), m in zip(read, marks):
        verdict, detail = judge(s.number, qp, ms)
        pinned = m == s.marks or (m is None and verdict == "LABEL_ONLY")
        if verdict in ("MARKS_ONLY", "LABEL_ONLY") and sequence_ok and pinned:
            verdict, detail = "SEQUENCE_PROVEN", "whole paper's scheme marks match in order"
        if (verdict in ("UNREADABLE", "MARKS_ONLY") and key in seg.MANUAL_QP_RANGES and ms
                and ms.totals and ms.totals[0][0] == s.number):
            verdict, detail = "MANUAL_PROVEN", "hand-verified QP ranges; scheme names q"
        decision = DECISIONS.get(f"{key}|{s.number}")
        if decision and verdict not in PUBLISHABLE:
            if decision["decision"] == "CONFIRMED":
                verdict, detail = "REVIEWED_PROVEN", f"read together: {decision['reason']}"
            elif decision["decision"] == "REJECTED":
                verdict, detail = "REJECTED", f"read together: {decision['reason']}"
        rows.append({"paper": key, "question": s.number, "marks": s.marks, "verdict": verdict,
                     "page_number": s.qp_regions[0].page + 1,
                     "page_count": len({r.page for r in s.qp_regions}),
                     "detail": detail, "qp": str(qp_file.relative_to(seg.REPO_ROOT)),
                     "ms": str(ms_file.relative_to(seg.REPO_ROOT)) if ms else None})
    return rows


def apply_manual_pages(source: seg.PaperSource, result: seg.PaperResult) -> None:
    """Re-cut schemes whose pages were assigned by reading (`ms_pages`)."""
    for s in result.segments:
        decision = DECISIONS.get(f"{source.key}|{s.number}")
        # `ms_source` names a different scheme file when ours lacks the pages
        # (the 2017 specimen's copy starts at Q2; Q1 comes from Pearson's own
        # SAM booklet, kept under supplementary/).
        ms_file = (seg.REPO_ROOT / decision["ms_source"]
                   if decision and decision.get("ms_source") else source.ms_path)
        if decision and decision.get("ms_pages") and ms_file is not None:
            regions = tuple(seg.Region(page=p) for p in decision["ms_pages"])
            seg.extract_regions(ms_file, regions,
                                SEGMENTS_DIR / source.key / "markschemes" / f"q{s.number}.pdf")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", help="one live key, e.g. 2015_jan_P1")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--render", action="store_true",
                        help="draw every unproven pair to review/ for reading")
    args = parser.parse_args()

    seg.OUTPUT_DIR = SEGMENTS_DIR
    papers = load_live_papers(CODE)
    if args.paper:
        papers = [p for p in papers if p.key == args.paper]

    report: dict = {"papers": {}, "rows": []}
    for paper in papers:
        source = to_source(paper)
        if source is None:
            report["papers"][paper.key] = {"status": "NO_QP_SOURCE"}
            print(f"{paper.key:22} NO QP SOURCE")
            continue
        _current_key[0], _current_total[0] = source.key, source.total_marks
        scrambled = is_scrambled(source.qp_path)
        if scrambled:
            OCR_DOCS.add(str(source.qp_path.resolve()))
            for n in range(1, 30):
                OCR_DOCS.add(str((SEGMENTS_DIR / source.key / "questions" / f"q{n}.pdf").resolve()))
            print(f"{paper.key:22} scrambled text layer -- reading it by OCR")
        if source.ms_path is not None and is_scrambled(source.ms_path):
            OCR_DOCS.add(str(source.ms_path.resolve()))
            for n in range(1, 30):
                OCR_DOCS.add(str((SEGMENTS_DIR / source.key / "markschemes" / f"q{n}.pdf").resolve()))
            print(f"{paper.key:22} scrambled mark-scheme text -- reading it by OCR")
        result = seg.process_paper(source)
        status = "OK" if result.ok else "HELD"
        if result.ok:
            seg.write_paper(result)
            apply_manual_pages(source, result)
            rows = verify_written(source.key, result)
            for row in rows:
                row["live_key"] = paper.key
                row["paper_id"] = paper.paper_id
            report["rows"].extend(rows)
            counts = Counter(r["verdict"] for r in rows)
            good = sum(counts[v] for v in PUBLISHABLE)
            print(f"{paper.key:22} {source.spec} {good:2}/{len(rows):2} publishable  "
                  f"{dict(counts) if good < len(rows) else ''}")
        else:
            print(f"{paper.key:22} HELD: {result.issues[:2]}")
        report["papers"][paper.key] = {"status": status, "key": source.key,
                                       "issues": result.issues, "warnings": result.warnings}
        if args.verbose:
            for w in result.warnings:
                print("     ", w)

    if args.paper and VERDICTS_PATH.is_file():
        # Merge a single-paper run into the full report.
        full = json.loads(VERDICTS_PATH.read_text(encoding="utf-8"))
        done = set(report["papers"])
        full["rows"] = [r for r in full["rows"] if r["live_key"] not in done] + report["rows"]
        full["papers"].update(report["papers"])
        report = full
    VERDICTS_PATH.write_text(json.dumps(report, indent=1), encoding="utf-8")
    if args.render:
        for row in report["rows"]:
            if row["verdict"] in PUBLISHABLE:
                continue
            render_pair(seg.REPO_ROOT / row["qp"],
                        seg.REPO_ROOT / row["ms"] if row["ms"] else None,
                        RENDER_DIR / f"{row['paper']}_q{row['question']}.png")
    counts = Counter(r["verdict"] for r in report["rows"])
    held = [k for k, v in report["papers"].items() if v["status"] != "OK"]
    print(f"\nquestions: {sum(counts.values())}  {dict(counts)}")
    print(f"papers held ({len(held)}): {held}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
