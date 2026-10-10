"""
Rebuild EVERY live IGCSE science question (Chemistry 4CH1, Biology 4BI1, Human
Biology 4HB1) and its mark scheme from the whole-paper PDFs, prove each pair,
and hand the result to lib.live_segments_publish.

WHY
---
The 2026-10-10 live linkage audit (lib.live_ms_linkage) found these subjects'
pairs mostly unprovable or wrong: Chemistry 20% proven / 24% wrong scheme,
Biology 18% / 28%, Human Biology 21% / 25%. The schemes were page slices (q3's
scheme opened on question 2's) and some question files were page slices too.
A live answer checker needs every question's own scheme, so the cuts are
rebuilt from the documents, as Physics / Maths B / FPM were.

HOW A QUESTION IS CUT
---------------------
308 of 314 papers print "(Total for Question N = X marks)" under every
question, in order. That line is an exact end. Question N runs from just
past question N-1's total line to the bottom of its own; question 1 starts at
the top of the page where its number stands in the margin. Whole pages are
copied as they are; a page shared with a neighbour is clipped. Strips holding
nothing but page furniture (the tail of a page after a total, "DO NOT WRITE IN
THIS AREA", barcodes, our stamp) and "BLANK PAGE" sheets are dropped.

Papers whose text layer is scrambled or image-only are read through an OCR
copy (lib.live_rebuild_common.ocr_copy) and cut from the original.

HOW A SCHEME IS CUT
-------------------
lib.ms_bands readings. Where the scheme closes every question with a tally
("Total 8 marks", Biology / Human Biology) and there are exactly as many
tallies as questions, block N runs from tally N-1 to tally N, moved forward to
N's own margin label when one stands inside. Otherwise (Chemistry prints no
tallies) block N runs from N's margin label to N+1's, labels taken strictly in
order.

PROOF
-----
lib.live_ms_linkage.judge on each written pair: the scheme must name this
question and agree on its marks (or its Marks column must sum to them), and
every part the question prints must be in it. Paper-level proofs as in
lib.live_rebuild_common.verify_paper. Anything else waits for a reading
recorded in manual_review.json (CONFIRMED / REJECTED), and an unproven scheme
is never published.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import fitz

from lib import ms_bands
from lib.live_ms_linkage import judge, read_evidence
from lib.live_ms_review import load_decisions
from lib.live_paper_sources import REBUILD_DIR, ROOT, LivePaper, load_live_papers
from lib.live_rebuild_common import is_scrambled, ocr_copy, ocr_image_pages, pairing_verified

PUBLISHABLE = {"PROVEN", "SEQUENCE_PROVEN", "LABEL_PROVEN", "REVIEWED_PROVEN"}

QP_TOTAL_RE = re.compile(r"Total\s+(?:for\s+)?Question\s+(\d{1,2})\s*[=:]?\s*(\d{1,2})\s*marks?", re.I)
LEFT_MARGIN_MAX_X = 85.0  # numbers sit at x 43-77
PAD = 4.0                  # points kept above a cut so a line is never sliced
MIN_STRIP = 24.0
MARGIN_PANEL = 40.0   # "DO NOT WRITE IN THIS AREA" side panels
FOOTER_BAND = 70.0    # barcode and page number
FURNITURE_RE = re.compile(
    r"DO\s*NOT\s*WRITE|Turn\s*over|Sample\s+Assessment\s+Materials|Pearson\s+Education\s+Limited|BLANK\s*PAGE|GradeMax|\*P\d{4,}|·|\||^\s*\d{1,3}\s*$|"
    r"^\s*\(?Total\s+for\s+Question|^\s*TOTAL\s+FOR\s+PAPER|^\s*Question\s*(number)?\b", re.I)
BLANK_RE = re.compile(r"BLANK\s+PAGE", re.I)


@dataclass(frozen=True)
class Spot:
    page: int
    top: float
    bottom: float


@dataclass(frozen=True)
class Segment:
    number: int
    marks: int | None
    regions: tuple[tuple[int, float | None, float | None], ...]  # (page, top, bottom)


# ── reading ─────────────────────────────────────────────────────────────────

def upright(pdf: Path) -> Path:
    """
    The document with every /Rotate page turned upright (still vector), so
    lines, labels and cuts all live in displayed coordinates. Old science
    schemes (2011-2013) are landscape tables stored as rotated portrait pages;
    reading them unrotated skipped every label. Cached as <name>.up.pdf.
    """
    with fitz.open(pdf) as doc:
        if not any(page.rotation for page in doc):
            return pdf
        out = pdf.with_name(pdf.stem + ".up.pdf")
        if not out.is_file():
            for page in doc:
                if page.rotation:
                    page.remove_rotation()
            doc.save(out, garbage=3, deflate=True)
        return out


STAMP_ONLY_CHARS = 120  # our two stamp lines are ~95 characters


def readable(pdf: Path) -> tuple[Path, str | bool]:
    if is_scrambled(pdf):
        return ocr_copy(pdf), "full"
    with fitz.open(pdf) as doc:
        # Picture pages among text pages (2019 May-Jun P1: cover-side pages
        # carry only our stamp): OCR just those, keep the exact text elsewhere.
        pictures = any(len(page.get_text().strip()) < STAMP_ONLY_CHARS and page.get_images()
                       for page in doc)
    if pictures:
        return ocr_image_pages(pdf), "pages"
    return pdf, False


def _lines(page: fitz.Page) -> list[tuple[str, fitz.Rect]]:
    """Text lines with their boxes, built from the word stream."""
    lines: dict[tuple[int, int], list] = {}
    for w in page.get_text("words"):
        lines.setdefault((w[5], w[6]), []).append(w)
    out = []
    for words in lines.values():
        rect = fitz.Rect(words[0][:4])
        for w in words[1:]:
            rect |= fitz.Rect(w[:4])
        out.append((" ".join(w[4] for w in words), rect))
    return sorted(out, key=lambda item: (item[1].y0, item[1].x0))


def qp_totals(doc: fitz.Document) -> list[tuple[int, int, Spot]]:
    """Every "(Total for Question N = X marks)" line, in document order."""
    found = []
    for index, page in enumerate(doc):
        lines = _lines(page)
        for i, (text, rect) in enumerate(lines):
            joined, box = text, rect
            if i + 1 < len(lines) and re.search(r"Total\s*(for)?\s*(Question)?\s*\d*\s*$", text, re.I):
                joined, box = text + " " + lines[i + 1][0], rect | lines[i + 1][1]
            match = QP_TOTAL_RE.search(joined)
            if match and (not found or found[-1][2] != Spot(index, box.y0, box.y1)):
                found.append((int(match.group(1)), int(match.group(2)), Spot(index, box.y0, box.y1)))
    deduped: list[tuple[int, int, Spot]] = []
    for item in found:
        if not deduped or deduped[-1][0] != item[0]:
            deduped.append(item)
    return deduped


def number_spot(doc: fitz.Document, number: int, first_page: int = 0,
                last_page: int | None = None) -> Spot | None:
    """Where a question's number first stands in the left margin, with text after it."""
    last = doc.page_count - 1 if last_page is None else last_page
    for index in range(first_page, last + 1):
        page = doc[index]
        height = page.rect.height
        words = page.get_text("words")
        for w in words:
            if w[4] == str(number) and w[0] < LEFT_MARGIN_MAX_X and 50 < w[1] < height - 60:
                if any(abs(v[1] - w[1]) < 4 and v[0] > w[2] for v in words):
                    return Spot(index, w[1], w[3])
    return None


def first_question_spot(doc: fitz.Document) -> Spot | None:
    """Question 1's margin number, else the top of the "Answer ALL questions" page."""
    spot = number_spot(doc, 1)
    if spot is not None:
        return spot
    for index, page in enumerate(doc):
        if re.search(r"Answer\s+ALL\s+questions", page.get_text(), re.I):
            return Spot(index, 40.0, 40.0)
    return None


def fill_missing_total(doc: fitz.Document, totals: list) -> list:
    """
    One unreadable "Total for Question k" (2019 May-Jun P1 q7): question k
    ends where question k+1's margin number stands. Its marks stay unknown.
    """
    numbers = [n for n, _, _ in totals]
    expected = list(range(1, numbers[-1] + 1)) if numbers else []
    gaps = sorted(set(expected) - set(numbers))
    if len(gaps) != 1 or gaps[0] == expected[-1] or sorted(numbers) != numbers:
        return totals
    k = gaps[0]
    before = next((t for t in totals if t[0] == k - 1), None)
    after = next(t for t in totals if t[0] == k + 1)
    start_page = before[2].page if before else 0
    spot = number_spot(doc, k + 1, start_page, after[2].page)
    if spot is None:
        return totals
    end = Spot(spot.page, spot.top - 2 * PAD - 8, spot.top - 2 * PAD)
    return sorted(totals + [(k, None, end)], key=lambda t: t[0])


# ── cutting ─────────────────────────────────────────────────────────────────

def _strip_is_furniture(page: fitz.Page, top: float, bottom: float) -> bool:
    clip = fitz.Rect(0, top, page.rect.width, bottom)
    residue = 0
    for text, rect in _lines(page):
        if not rect.intersects(clip):
            continue
        if FURNITURE_RE.search(text):
            continue
        residue += len(text.strip())
    if residue >= 15:
        return False
    # Diagrams carry no text: a drawing or picture lying in the strip's body
    # counts as content. Page furniture does not: the footer barcode, the
    # "DO NOT WRITE" margin panels and the question frame's edges.
    width, height = page.rect.width, page.rect.height
    body = fitz.Rect(MARGIN_PANEL, max(top, 0) - 1, width - MARGIN_PANEL,
                     min(bottom, height - FOOTER_BAND) + 1)

    def in_body(r: fitz.Rect) -> bool:
        return r.width > 30 and r.height > 30 and r in body

    if any(in_body(path["rect"]) for path in page.get_drawings()):
        return False
    return not any(in_body(fitz.Rect(img["bbox"])) for img in page.get_image_info())


def _is_blank_sheet(page: fitz.Page) -> bool:
    """A "BLANK PAGE" sheet: nothing but that line and page furniture."""
    if not BLANK_RE.search(page.get_text()):
        return False
    # Count real words only: on an OCR'd copy the margin panels read as noise
    # ("Ww", "oe<", "(o}Z"), which is not content.
    words = [w for t, _ in _lines(page) if not FURNITURE_RE.search(t)
             for w in re.findall(r"[A-Za-z]{4,}", t)]
    return len(words) < 10  # a question page never says "BLANK PAGE"


def _clean_regions(doc: fitz.Document, regions: list[tuple[int, float | None, float | None]]):
    kept = []
    for page_no, top, bottom in regions:
        page = doc[page_no]
        t = 0.0 if top is None else top
        b = page.rect.height if bottom is None else bottom
        if b - t < MIN_STRIP:
            continue
        if _is_blank_sheet(page):
            continue
        if _strip_is_furniture(page, t, b):
            continue
        kept.append((page_no, top, bottom))
    return tuple(kept)


PAPER_TOTAL_RE = re.compile(r"TOTAL\s+FOR\s+PAPER\s*[=:]?\s*(\d{2,3})\s*MARKS", re.I)


def printed_paper_total(doc: fitz.Document) -> int | None:
    for index in range(doc.page_count - 1, -1, -1):
        match = PAPER_TOTAL_RE.search(" ".join(w[4] for w in doc[index].get_text("words")))
        if match:
            return int(match.group(1))
    return None


def question_segments(read_doc: fitz.Document) -> tuple[list[Segment], str]:
    totals = fill_missing_total(read_doc, qp_totals(read_doc))
    numbers = [n for n, _, _ in totals]
    if not totals or numbers != list(range(1, len(numbers) + 1)):
        return [], f"question totals not 1..N: {numbers}"
    # Coverage guard: the questions found must add up to the paper's own total
    # (2015 May-Jun HB P2 printed "(Total Question 6 = 6 marks)" without "for"
    # and question 6 silently went missing).
    paper_total = printed_paper_total(read_doc)
    marks = [m for _, m, _ in totals]
    if paper_total and None not in marks and sum(marks) != paper_total:
        return [], f"question marks sum to {sum(marks)}, paper prints TOTAL {paper_total}"
    start = first_question_spot(read_doc)
    if start is None:
        return [], "question 1 not found"
    segments = []
    begin = (start.page, max(0.0, start.top - 20))
    for number, marks, spot in totals:
        regions = []
        for page_no in range(begin[0], spot.page + 1):
            top = begin[1] if page_no == begin[0] else None
            bottom = spot.bottom + PAD if page_no == spot.page else None
            if top is not None and top <= 1:
                top = None
            regions.append((page_no, top, bottom))
        kept = list(_clean_regions(read_doc, regions))
        # A leading strip (the foot of the previous page after its total) is
        # kept only when it holds this question's own number.
        if number > 1 and kept and kept[0][1] is not None and len(kept) > 1:
            page_no, top, bottom = kept[0]
            own = number_spot(read_doc, number, page_no, page_no)
            strip = fitz.Rect(0, top, read_doc[page_no].rect.width,
                              bottom if bottom is not None else read_doc[page_no].rect.height)
            words = [w for t, r in _lines(read_doc[page_no])
                     if r.intersects(strip) and not FURNITURE_RE.search(t)
                     for w in re.findall(r"[A-Za-z]{4,}", t)]
            # OCR can miss the number, so a strip with real text stays.
            if (own is None or own.top < top) and len(words) < 15:
                kept = kept[1:]
        segments.append(Segment(number, marks, tuple(kept)))
        begin = (spot.page, spot.bottom + PAD)
    return segments, ""


def write_cut(src: fitz.Document, regions, target: Path) -> None:
    with fitz.open() as new:
        for page_no, top, bottom in regions:
            page = src[page_no]
            if (top is None and bottom is None) or page.rotation:
                new.insert_pdf(src, from_page=page_no, to_page=page_no)
                continue
            t = 0.0 if top is None else max(0.0, top)
            b = page.rect.height if bottom is None else min(page.rect.height, bottom)
            clip = fitz.Rect(0, t, page.rect.width, b)
            sheet = new.new_page(width=clip.width, height=clip.height)
            sheet.show_pdf_page(sheet.rect, src, page_no, clip=clip)
        if new.page_count == 0:
            raise ValueError(f"empty cut for {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        new.save(target, garbage=3, deflate=True)


LABEL_COLUMN_FRACTION = 0.2
MAX_QUESTION_MARKS = 30
LABEL_RE = re.compile(r"^(\d{1,2})(?:\s*\(?[a-hivx]+\)?.*)?$")
HEADER_RE = re.compile(r"^\s*Question\b", re.I)
HEADER_REACH = 45.0


PART_TOKEN_RE = re.compile(r"^(\(?[a-h]\)?(\(?[ivx]{1,4}\)?)?|\(?[ivx]{1,4}\)?|[dD]?M\d.*|[•·▪-])$")


def looks_like_label(text: str) -> bool:
    """
    A question label stands alone or is followed by a part marker: "2",
    "2 (a)", "2 a i", "2(b)", "2 M1". Not "2 NaOH + (1) H2SO4 ..." -- a
    coefficient row inside question 1's scheme (2017 May-Jun P2), which was
    read as question 2's start: q1's cut lost (b) and (c) and q2's cut
    opened on them while its total still matched.
    """
    tokens = text.split()
    head = re.match(r"^(\d{1,2})(.*)$", tokens[0])
    if not head:
        return False
    rest = ([head.group(2)] if head.group(2) else []) + tokens[1:]
    return not rest or bool(PART_TOKEN_RE.match(rest[0]))


def _validated(doc: fitz.Document, labels: list) -> list:
    """Shared-reader labels kept only where their line looks like a label."""
    kept = []
    for b in labels:
        lines = [t for t, r in _lines(doc[b.page]) if abs(r.y0 - b.lo) < 4 and r.x0 < doc[b.page].rect.width * 0.3]
        if not lines or any(looks_like_label(t) for t in lines):
            kept.append(b)
    return kept


def science_labels(doc: fitz.Document) -> list[ms_bands.BlockHeader]:
    """
    Question numbers standing first on a line in the scheme's left column.

    ms_bands.find_question_labels wants the column at one x; science schemes
    indent it by page (2023 May-Jun P1: x 42-63), so their 6, 8 and 10 were
    missed and the paper was held. The block start is pulled up to the
    "Question number | Answer | ..." header row just above, when there is one.
    """
    found = []
    for index, page in enumerate(doc):
        if page.rotation:
            continue
        width, height = page.rect.width, page.rect.height
        lines = _lines(page)
        for text, rect in lines:
            if rect.x0 > width * LABEL_COLUMN_FRACTION or not (40 < rect.y0 < height - 40):
                continue
            match = LABEL_RE.match(text.split()[0])
            if not match or not looks_like_label(text):
                continue
            top = rect.y0
            for other, box in lines:
                if HEADER_RE.match(other) and rect.y0 - HEADER_REACH <= box.y0 < rect.y0:
                    top = min(top, box.y0)
            found.append(ms_bands.BlockHeader(page=index, lo=top, question=int(match.group(1)),
                                              axis=ms_bands.AXIS_Y))
    return found


def _last_content_page(ms_read: Path) -> int:
    """Last scheme page before Pearson's back matter."""
    with fitz.open(ms_read) as doc:
        last = doc.page_count - 1
        while last > 0 and not re.search(r"\(\w\)|\bM\d\b|accept|ignore|allow",
                                         doc[last].get_text(), re.I):
            last -= 1
        return last


def scheme_segments(ms_read: Path, count: int) -> tuple[dict[int, tuple], str, set[int]]:
    """
    Question number -> regions of its scheme block, why not (when empty), and
    the questions whose block OPENS on their own margin number.
    """
    # A paper's grand total ("Total for paper = 120 marks") is not a question's.
    tallies = [t for t in ms_bands.find_tallies(ms_read) if t.marks <= MAX_QUESTION_MARKS]
    with fitz.open(ms_read) as doc:
        page_count = doc.page_count
        own = science_labels(doc)
        shared = _validated(doc, ms_bands.find_question_labels(ms_read))
    labels = sorted(shared + own, key=lambda b: (b.page, b.lo))

    # Labels taken strictly in order: N's label is the first one after N-1's.
    chosen: dict[int, ms_bands.BlockHeader] = {}
    position = (-1, -1.0)
    for number in range(1, count + 1):
        for label in labels:
            if label.question == number and (label.page, label.lo) > position:
                chosen[number] = label
                position = (label.page, label.lo)
                break

    def tally_bands():
        """Block N = just past tally N-1 .. tally N, snapped to N's label inside it."""
        ends_ = [(t.page, t.hi + 1) for t in tallies]
        first = next((b for b in labels if b.question == 1 and (b.page, b.lo) < ends_[0]), None)
        start = (first.page, max(0.0, first.lo - 6)) if first else (tallies[0].page, 0.0)
        starts_, anchored_ = [], set()
        for number in range(1, count + 1):
            if number > 1:
                start = ends_[number - 2]
            own = next((b for b in labels if b.question == number
                        and start <= (b.page, b.lo) < ends_[number - 1]), None)
            if own:
                start = (own.page, max(0.0, own.lo - 6))
                anchored_.add(number)
            starts_.append(start)
        return starts_, ends_, anchored_

    anchored: set[int] = set()
    tally_ok = False
    with fitz.open(ms_read) as doc:
        numbered = qp_totals(doc)  # the scheme names its own totals (2014+ layouts)
    if [n for n, _, _ in numbered] == list(range(1, count + 1)):
        ends = [(spot.page, spot.bottom + 1) for _, _, spot in numbered]
        first = next((b for b in labels if b.question == 1 and (b.page, b.lo) < ends[0]), None)
        starts = [(first.page, max(0.0, first.lo - 6)) if first else (numbered[0][2].page, 0.0)]
        starts += ends[:-1]
        anchored = set(range(1, count + 1))  # each block closes on its own number
        tally_ok = all(a < b for a, b in zip(starts, ends))
    if not tally_ok and len(tallies) == count:
        starts, ends, anchored = tally_bands()
        tally_ok = all(s < e for s, e in zip(starts, ends))
    if not tally_ok:
        if not all(n in chosen for n in range(1, count + 1)):
            missing = [n for n in range(1, count + 1) if n not in chosen]
            why = "tally bands out of order" if len(tallies) == count else                 f"no scheme label for {missing} (tallies {len(tallies)} vs {count} questions)"
            return {}, why, set()
        anchored = set(range(1, count + 1))
        starts = [(chosen[n].page, max(0.0, chosen[n].lo - 3)) for n in range(1, count + 1)]
        last_page = tallies[-1].page if len(tallies) >= count else _last_content_page(ms_read)
        ends = starts[1:] + [(last_page, tallies[-1].hi + 1 if len(tallies) >= count
                              and tallies[-1].page == last_page else None)]
    # The last block stops above the paper's grand total when one is printed.
    grand = [t for t in ms_bands.find_tallies(ms_read) if t.marks > MAX_QUESTION_MARKS]
    if grand and (grand[-1].page, grand[-1].lo) > starts[-1]:
        g = grand[-1]
        last_end = ends[-1]
        if last_end[1] is None or (g.page, g.lo) < last_end:
            ends[-1] = (g.page, max(0.0, g.lo - 2))
    if not all(s < e for s, e in zip(starts, ends) if e[1] is not None):
        return {}, "scheme bands out of order", set()
    del page_count

    out = {}
    for number, (start, end) in enumerate(zip(starts, ends), start=1):
        regions = []
        for page_no in range(start[0], end[0] + 1):
            top = start[1] if page_no == start[0] else None
            bottom = end[1] if page_no == end[0] else None
            if top is not None and top <= 1:
                top = None
            regions.append((page_no, top, bottom))
        out[number] = regions
    return out, "", anchored


# ── the subject run ─────────────────────────────────────────────────────────

def _hand(decisions: dict, key: str, number: int, field: str):
    """Hand-set regions [[page, top, bottom], ...] (0-based page of the upright
    source, points; null top/bottom = page edge) from manual_review.json."""
    regions = decisions.get(f"{key}|{number}", {}).get(field)
    return tuple((int(p), t, b) for p, t, b in regions) if regions else None


def stage_paper(code: str, paper: LivePaper, out_root: Path,
                decisions: dict | None = None) -> list[dict] | str:
    decisions = decisions or {}
    if not paper.qp_path or not paper.ms_path:
        return "missing source"
    qp_source, ms_source = upright(paper.qp_path), upright(paper.ms_path)
    qp_read, qp_ocr = readable(qp_source)
    ms_read, ms_ocr = readable(ms_source)
    with fitz.open(qp_read) as read_doc:
        segments, why = question_segments(read_doc)
        if not segments:
            return why
        cleaned = []
        for s in segments:
            cleaned.append(Segment(s.number, s.marks, _clean_regions(read_doc, list(s.regions))
                                   if s.regions else s.regions))
    schemes, why, anchored = scheme_segments(ms_read, len(segments))
    if not schemes:
        if not all(_hand(decisions, paper.key, s.number, "ms_regions") for s in cleaned):
            return why
        schemes = {}
    paper_dir = out_root / paper.key
    rows = []
    with fitz.open(qp_source) as qp_src, fitz.open(ms_source) as ms_src, \
            fitz.open(ms_read) as ms_read_doc:
        for s in cleaned:
            qp_file = paper_dir / "questions" / f"q{s.number}.pdf"
            ms_file = paper_dir / "markschemes" / f"q{s.number}.pdf"
            if not s.regions:
                return f"q{s.number}: nothing left after cleaning"
            regions = (_hand(decisions, paper.key, s.number, "qp_regions")
                       or tuple(r for r in s.regions if not _is_blank_sheet(qp_src[r[0]]))
                       or s.regions)
            write_cut(qp_src, regions, qp_file)
            ms_regions = (_hand(decisions, paper.key, s.number, "ms_regions")
                          or _clean_regions(ms_read_doc, schemes[s.number])
                          or tuple(schemes[s.number][:1]))
            write_cut(ms_src, ms_regions, ms_file)
            rows.append({"number": s.number, "marks": s.marks, "qp": qp_file, "ms": ms_file,
                         "pages": [r[0] + 1 for r in s.regions], "ms_ocr": ms_ocr,
                         "qp_ocr": qp_ocr, "anchored": s.number in anchored})
    return rows


def _fresh(make):
    """The OCR helpers cache <name>.ocr.pdf / .ocrp.pdf beside the file and never
    refresh it; a cut that changed would be proved from its OLD text."""
    def run(path: Path) -> Path:
        for suffix in (".ocr.pdf", ".ocrp.pdf"):
            path.with_name(path.stem + suffix).unlink(missing_ok=True)
        return make(path)
    return run


def _md5(path: Path) -> str:
    """Fingerprint of what a cut SHOWS (page sizes + text). The file bytes
    change on every write (PDF /ID, dates), so they cannot pin a reading."""
    with fitz.open(path) as doc:
        shown = "|".join(f"{p.rect.width:.0f}x{p.rect.height:.0f}:{p.get_text()}" for p in doc)
    return hashlib.md5(shown.encode("utf-8")).hexdigest()


def _review_current(decision: dict, staged: dict) -> bool:
    """A reading counts only for the exact files that were read."""
    return (decision.get("qp_md5") in (None, _md5(staged["qp"]))
            and decision.get("ms_md5") in (None, _md5(staged["ms"])))


def prove_paper(code: str, paper: LivePaper, staged: list[dict], decisions: dict,
                pairing_ok: bool = False) -> list[dict]:
    key = paper.key
    read = []
    for s in staged:
        ocr = {"full": _fresh(ocr_copy), "pages": _fresh(ocr_image_pages)}
        qp_path = ocr[s["qp_ocr"]](s["qp"]) if s["qp_ocr"] else s["qp"]
        ms_path = ocr[s["ms_ocr"]](s["ms"]) if s["ms_ocr"] else s["ms"]
        qp = read_evidence(qp_path, is_ms=False)
        ms = read_evidence(ms_path, is_ms=True)
        if s["ms_ocr"] == "full":
            import dataclasses  # noqa: PLC0415
            ms = dataclasses.replace(ms, parts=())
        read.append((s, qp, ms))
    verdicts = [judge(s["number"], qp, ms) for s, qp, ms in read]
    tallies = [ms.tallies[-1] if ms.tallies else None for _, _, ms in read]
    sequence_ok = (len(read) > 1 and sum(t is None for t in tallies) <= 1
                   and all(t is None or t == s["marks"] for t, (s, _, _) in zip(tallies, read)))
    # Older science schemes print each block's total in the Marks column too,
    # so the column sums to exactly twice the question's marks.
    verdicts = [
        ("PROVEN", "margin number agrees; Marks column = marks + block total")
        if v == "LABEL_ONLY" and s["marks"] and ms.column_marks == 2 * s["marks"] else (v, d)
        for (s, _, ms), (v, d) in zip(read, verdicts)
    ]
    # The cut itself opens on this question's own margin number (labels taken
    # strictly in order), so where the judge's reader misses the number in an
    # old layout, the marks agreeing completes number + marks.
    verdicts = [
        ("PROVEN", "cut opens on its own margin number; marks agree")
        if s.get("anchored") and s["marks"] and (
            v == "MARKS_ONLY"
            or (v == "UNREADABLE" and ms.column_marks in (s["marks"], 2 * s["marks"])))
        else (v, d)
        for (s, _, ms), (v, d) in zip(read, verdicts)
    ]
    proven = sum(v == "PROVEN" for v, _ in verdicts)
    # The scheme document is this paper's: half the paper reconciles on number
    # AND marks, or the content-pairing audit identified both documents.
    document_ok = pairing_ok or proven >= max(3, len(read) / 2)
    rows = []
    for (s, qp, ms), (verdict, detail), tally in zip(read, verdicts, tallies):
        if verdict in ("MARKS_ONLY", "LABEL_ONLY") and sequence_ok and tally == s["marks"]:
            verdict, detail = "SEQUENCE_PROVEN", "whole paper's scheme tallies match in order"
        if verdict == "LABEL_ONLY" and document_ok:
            labels = [x for x in ms.labels]
            if labels and set(labels) <= {s["number"]}:
                verdict, detail = "LABEL_PROVEN", f"scheme names only q{s['number']}; {proven} proven in paper"
        # A question whose scheme lost parts may have lost them to THIS cut,
        # which then opens on them while its own total still matches.
        if rows and rows[-1]["verdict"] == "MS_PARTIAL" and verdict in PUBLISHABLE:
            verdict, detail = "NEIGHBOUR_SUSPECT", (f"q{s['number'] - 1}'s scheme is missing parts; "
                                                    f"this cut may hold them ({detail})")
        decision = decisions.get(f"{key}|{s['number']}")
        if decision and not _review_current(decision, s):
            decision = None
            if verdict not in PUBLISHABLE:
                detail = f"{detail} [review on file is for an older cut]"
        if decision and verdict not in PUBLISHABLE:
            if decision["decision"] == "CONFIRMED":
                verdict, detail = "REVIEWED_PROVEN", f"read together: {decision['reason']}"
            elif decision["decision"] == "REJECTED":
                verdict, detail = "REJECTED", f"read together: {decision['reason']}"
        rows.append({
            "paper": key, "question": s["number"], "marks": s["marks"], "verdict": verdict,
            "detail": detail, "page_number": s["pages"][0], "page_count": len(s["pages"]),
            "qp": str(s["qp"].relative_to(ROOT)), "ms": str(s["ms"].relative_to(ROOT)),
            "live_key": key, "paper_id": paper.paper_id,
        })
    return rows


def run(code: str, *, only: str | None = None) -> int:
    base = REBUILD_DIR / code
    out_root = base / "segments"
    decisions = load_decisions(base / "manual_review.json") if (base / "manual_review.json").is_file() else {}
    papers = load_live_papers(code)
    pairing = pairing_verified(papers)
    verdict_file = base / "verdicts.json"
    previous = json.loads(verdict_file.read_text(encoding="utf-8")) if verdict_file.is_file() and only else \
        {"papers": {}, "rows": []}
    paper_notes = dict(previous.get("papers", {}))
    rows = [r for r in previous.get("rows", []) if not only or only not in r["paper"]]
    for paper in papers:
        if only and only not in paper.key:
            continue
        try:
            staged = stage_paper(code, paper, out_root, decisions)
        except (ValueError, RuntimeError, IndexError) as exc:  # a cut that cannot be made
            staged = f"cut failed: {exc}"
        if isinstance(staged, str):
            paper_notes[paper.key] = f"HELD: {staged}"
            print(f"  {paper.key:24} HELD  {staged}")
            continue
        proved = prove_paper(code, paper, staged, decisions, paper.paper_id in pairing)
        rows += proved
        ok = sum(r["verdict"] in PUBLISHABLE for r in proved)
        paper_notes[paper.key] = f"{ok}/{len(proved)} proven"
        flag = "" if ok == len(proved) else "  <-- " + ", ".join(
            f"q{r['question']}:{r['verdict']}" for r in proved if r["verdict"] not in PUBLISHABLE)
        print(f"  {paper.key:24} {ok:2}/{len(proved):2}{flag}")
    verdict_file.write_text(json.dumps({"papers": paper_notes, "rows": rows}, indent=1),
                            encoding="utf-8")
    total = len(rows)
    ok = sum(r["verdict"] in PUBLISHABLE for r in rows)
    held = sum(1 for v in paper_notes.values() if v.startswith("HELD"))
    print(f"\n{code}: {ok}/{total} questions proven; {held} papers held")
    return 0
