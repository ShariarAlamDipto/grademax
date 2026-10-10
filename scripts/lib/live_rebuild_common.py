"""
Shared machinery for rebuilding a subject's LIVE question + mark-scheme
segments from its whole-paper PDFs and proving every pair before publishing.

Extracted from rebuild_physics_live_segments.py (the first subject done,
2026-10-07); each subject keeps its own thin entry script that supplies its
workbook segmenter module (`seg`) and how to turn a live paper into that
segmenter's PaperSource.

What lives here, each learned on Physics:

* OCR for SCRAMBLED text layers -- fonts with no Unicode map look right and
  read as noise. Only flagged documents are OCR'd (Tesseract via PyMuPDF).
* ROTATION-SAFE cutting -- band coordinates come from the unrotated page, but
  the segmenters clamp to the rotated rect and show_pdf_page clips rotated
  sources; the old cuts lost the Question column. Each rotated page is copied
  alone, de-rotated, and the band mapped through page.rotation_matrix
  (remove_rotation's own returned matrix carries the wrong offset).
* EMPTY STRIPS -- thin band pages holding no text are dropped.
* THE GATE -- every written pair is re-read by lib.live_ms_linkage.judge;
  a paper whose scheme marks match its questions in order (at most one
  unreadable) pins its number-less schemes (SEQUENCE_PROVEN); a human reading
  recorded in manual_review.json can confirm or reject (lib.live_ms_review).
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Callable

import fitz

from lib import ms_bands
from lib.live_ms_linkage import judge, read_evidence
from lib.ms_label_blocks import table_labels
from lib.live_ms_review import load_decisions, render_pair
from lib.live_paper_sources import REBUILD_DIR, LivePaper, load_live_papers

PUBLISHABLE = {"PROVEN", "SEQUENCE_PROVEN", "MANUAL_PROVEN", "REVIEWED_PROVEN",
               "LABEL_PROVEN"}
TESSDATA = Path("C:/Program Files/Tesseract-OCR/tessdata")
STRIP_MAX_HEIGHT = 120.0
MIN_BAND = 4.0

# ── guarded header snap ─────────────────────────────────────────────────────
# ms_bands.bands_from_tallies moves a band's start FORWARD to the first header
# naming its question, to skip the previous question's trailing Guidance table.
# When the question's own opening header prints no number, that jump skips the
# question's first parts instead: 2014 May-Jun P1R q5's cut began at 5(f) and
# lost (a)-(e), while its total still matched. The snap is now taken only when
# the stretch it skips holds a header naming ANOTHER question -- the thing it
# exists to skip.
_original_own_header = ms_bands._own_header_within


def _guarded_own_header(headers, question, start_page, start_at, tally):
    """
    Where a band opened just past the previous question's tally, start it at
    the FIRST "Question" header that is unnumbered or names this question,
    skipping headers that name another question (the previous question's own
    trailing blocks). Anything before that header -- a "Part | Mark | Notes"
    guidance table, which is not a Question header -- is the previous
    question's and is left out.

    Measured cases (2026-10-07/08):
      2014 MJ Physics P1R q5   opening header unnumbered, "5" header later:
                               must start at the unnumbered one (keeps 5(a)-(e));
      2023 Jan FPM P1, 2024/2025 MJ FPM P2   guidance tables of q-1 between
                               its tally and q's header: must be skipped;
      2021 MJ FPM P2 q5        q4's Guidance block (headed "4") after q4's
                               tally: skipped because it names another question.
    """
    begin = (start_page, start_at if start_at is not None else -1.0)
    end = (tally.page, tally.lo)
    inside = sorted(
        (h for h in headers if h.axis == tally.axis and begin <= (h.page, h.lo) < end),
        key=lambda h: (h.page, h.lo),
    )
    for header in inside:
        if header.question is not None and header.question != question:
            continue
        return header
    return None


ms_bands._own_header_within = _guarded_own_header

# ms_bands hands a band thinner than MIN_BAND_EXTENT (24pt) back as the WHOLE
# PAGE -- a one-line scheme row is ~15-20pt, and the whole page is exactly the
# bundling this rebuild removes (2011 Maths B P1 q3 = Q1-Q9). Thin bands are
# cut as they are.
ms_bands.MIN_BAND_EXTENT = 4.0

# ── OCR for scrambled text layers ───────────────────────────────────────────
OCR_DOCS: set[str] = set()
_original_get_text = fitz.Page.get_text


def _ocr_get_text(self, *args, **kwargs):
    name = getattr(self.parent, "name", "") or ""
    if "textpage" not in kwargs and name and str(Path(name).resolve()) in OCR_DOCS:
        kwargs["textpage"] = self.get_textpage_ocr(dpi=200, full=True, language="eng",
                                                   tessdata=str(TESSDATA))
    return _original_get_text(self, *args, **kwargs)


fitz.Page.get_text = _ocr_get_text


IMAGE_ONLY_CHARS_PER_PAGE = 250  # our own stamp lines alone are ~100 a page

# Live keys whose question paper is readable EXCEPT for a page that is a
# picture: 2019 Jan P1 page 5 (Q8 and Q9, fences unreadable -> paper held).
# The automatic test above cannot see one image page among text pages without
# risking every paper, so these are listed.
OCR_QP_PAPERS = {"2019_jan_P1"}


def is_scrambled(pdf: Path) -> bool:
    """
    Plenty of text, yet not one readable 'Question' anywhere -- or a scan
    whose only text is our stamp (2019 May-Jun P2R: 36 image pages, ~100
    chars each). Either way the OCR copy is the readable document.
    """
    with fitz.open(pdf) as doc:
        text = " ".join(page.get_text() for page in doc)
        pages = max(doc.page_count, 1)
    if len(text) > 5000 and "Question" not in text:
        return True
    return pages > 2 and len(text) / pages < IMAGE_ONLY_CHARS_PER_PAGE


OCR_DPI = 200


def ocr_copy(pdf: Path) -> Path:
    """
    A once-only OCR'd copy of a scrambled document: each page rendered at
    OCR_DPI and given Tesseract's invisible text layer, at the page's own size,
    so every coordinate the segmenters read matches what they cut. Cached
    beside the source as <name>.ocr.pdf.

    Replaces per-call OCR (the get_text hook): the label readers read each
    page many times, and one scrambled Maths B paper ran 16+ CPU minutes
    without finishing that way. Cuts from the copy are images of the page,
    which is what a scrambled page effectively is anyway.
    """
    out = pdf.with_name(pdf.stem + ".ocr.pdf")
    if out.is_file():
        return out
    with fitz.open(pdf) as doc, fitz.open() as new:
        for page in doc:
            pix = page.get_pixmap(dpi=OCR_DPI)
            data = pix.pdfocr_tobytes(language="eng", tessdata=str(TESSDATA))
            with fitz.open("pdf", data) as one:
                new.insert_pdf(one)
        new.save(out, garbage=3, deflate=True)
    return out


# Scrambled documents whose glyph codes are a plain shift of the real text
# (2015 Jan P1R QP: "7RWDO IRU 4XHVWLRQ" = "Total for Question", +29). For
# these an exact decode beats OCR, which misplaced a question start (q3) and
# held the paper.
CAESAR_SHIFTED = {"2015_jan_P1R_qp.pdf": 29}


REAL_LINE_RE = re.compile(r"[a-z]{3}")


def _decoded_words(page: fitz.Page, shift: int) -> list[tuple[fitz.Rect, str]]:
    """
    Words rebuilt from the character layout: MuPDF's own word splitter treats
    the shifted digits (control codes 19-28) as whitespace and drops them.
    Shifted codes sit below 94 (a-z land on D-]) bar the odd symbol glyph (the
    degree sign is coded "q"), so a LINE with a run of three lower-case letters
    is real text -- our own stamp lines -- and is kept as is.
    """
    words: list[tuple[fitz.Rect, str]] = []
    raw = page.get_text("rawdict")
    for block in raw["blocks"]:
        for line in block.get("lines", []):
            chars = [c for span in line["spans"] for c in span["chars"]]
            real = REAL_LINE_RE.search("".join(c["c"] for c in chars)) is not None
            current, box = "", None
            for c in chars + [None]:
                if c is not None:
                    code = ord(c["c"])
                    text = c["c"] if real or code >= 94 or code + shift >= 127 \
                        else chr(code + shift)
                if c is None or text == " " or (c is not None and c["c"] == " "):
                    if current.strip():
                        words.append((box, current))
                    current, box = "", None
                    continue
                current += text
                rect = fitz.Rect(c["bbox"])
                box = rect if box is None else box | rect
    return words


def decoded_copy(pdf: Path, shift: int) -> Path:
    """
    The page as an image (what a reader sees) plus the decoded words as
    invisible text at their ORIGINAL positions, so the segmenters read the
    real text with exact coordinates. Cached as <name>.dec.pdf.
    """
    out = pdf.with_name(pdf.stem + ".dec.pdf")
    if out.is_file():
        return out
    with fitz.open(pdf) as doc, fitz.open() as new:
        for page in doc:
            target = new.new_page(width=page.rect.width, height=page.rect.height)
            target.insert_image(target.rect, pixmap=page.get_pixmap(dpi=OCR_DPI))
            for rect, text in _decoded_words(page, shift):
                x0, y0, x1, y1 = rect
                height = max(y1 - y0, 4.0)
                size = height * 0.72
                width = fitz.get_text_length(text, fontname="helv", fontsize=size) or 1.0
                # Squeeze/stretch the word to its original box so x-extents hold.
                matrix = fitz.Matrix((x1 - x0) / width, 1.0)
                target.insert_text((x0, y1 - height * 0.22), text, fontsize=size,
                                   fontname="helv", render_mode=3,
                                   morph=(fitz.Point(x0, y1), matrix))
        new.save(out, garbage=3, deflate=True)
    return out


def ocr_image_pages(pdf: Path) -> Path:
    """
    Like ocr_copy, but only pages whose text is (almost) nothing but our stamp
    are replaced by their OCR'd render; every other page keeps its original,
    exact text layer. Cached as <name>.ocrp.pdf.
    """
    out = pdf.with_name(pdf.stem + ".ocrp.pdf")
    if out.is_file():
        return out
    with fitz.open(pdf) as doc, fitz.open() as new:
        for index, page in enumerate(doc):
            if len(page.get_text().strip()) >= IMAGE_ONLY_CHARS_PER_PAGE:
                new.insert_pdf(doc, from_page=index, to_page=index)
                continue
            pix = page.get_pixmap(dpi=OCR_DPI)
            data = pix.pdfocr_tobytes(language="eng", tessdata=str(TESSDATA))
            with fitz.open("pdf", data) as one:
                new.insert_pdf(one)
        new.save(out, garbage=3, deflate=True)
    return out


def flag_ocr(source_pdf: Path, outputs: Path) -> None:
    OCR_DOCS.add(str(source_pdf.resolve()))
    for n in range(1, 40):
        OCR_DOCS.add(str((outputs / f"q{n}.pdf").resolve()))


# ── rotation-safe extraction ────────────────────────────────────────────────
def install_safe_extract(seg: ModuleType, opener: Callable[[Path], fitz.Document] | None = None):
    original = seg.extract_regions
    open_src = opener or fitz.open

    def extract(source_pdf: Path, regions, target: Path) -> None:
        # Every cropped region is cut here, rotated or not: the segmenters'
        # own extractors copy the WHOLE PAGE for any band under 20pt ("a bad
        # coordinate"), and a one-line mark scheme row is ~15pt -- 2011 Maths B
        # P1 q3 came out as all of Q1-Q9. Bands down to MIN_BAND are kept.
        if not any(r.cropped for r in regions):
            original(source_pdf, regions, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open_src(source_pdf) as src:
                out = fitz.open()
                try:
                    for region in regions:
                        page = src[region.page]
                        if not region.cropped:
                            out.insert_pdf(src, from_page=region.page, to_page=region.page)
                            continue
                        full = fitz.Rect(0, 0, page.cropbox.width, page.cropbox.height)
                        clip = fitz.Rect(
                            full.x0 if region.left is None else region.left,
                            full.y0 if region.top is None else region.top,
                            full.x1 if region.right is None else region.right,
                            full.y1 if region.bottom is None else region.bottom,
                        ) & full
                        matrix = page.rotation_matrix
                        single = fitz.open()
                        single.insert_pdf(src, from_page=region.page, to_page=region.page)
                        flat = single[0]
                        if flat.rotation:
                            flat.remove_rotation()
                            clip = (clip * matrix) & flat.rect
                        if clip.width < MIN_BAND or clip.height < MIN_BAND:
                            continue  # nothing there to show; never the whole page
                        band = out.new_page(width=clip.width, height=clip.height)
                        band.show_pdf_page(fitz.Rect(0, 0, clip.width, clip.height), single, 0,
                                           clip=clip)
                    out.save(target)
                finally:
                    out.close()
        drop_empty_strips(target)
        if target.parent.name == "questions":
            drop_blank_sheets(target)
        else:
            drop_furniture_pages(target)

    seg.extract_regions = extract
    return extract


BLANK_SHEET_RE = re.compile(r"BLANK\s+PAGE", re.I)
FURNITURE_RE = re.compile(
    r"TURN\s+OVER(\s+FOR\s+QUESTION\s+\d+)?|DO\s+NOT\s+WRITE\s+IN\s+THIS\s+AREA|"
    r"Pearson\s+Edexcel[^\n]*|Sample\s+Assessment\s+Materials[^\n]*|Issue\s+\d[^\n]*|"
    # Our stamp line is "Further Pure Maths · 2015 · May/Jun · Paper 2 · MS":
    # the subject name before the first "·" can be several words.
    r"©[^\n]*|GradeMax|[A-Za-z][A-Za-z ]*·[^\n]*|\S*\|\S*|\*?P\d{5}R*A\d*\*?|\d{1,4}",
    re.I,
)
BLANK_RESIDUE_MAX = 250


def drop_blank_sheets(target: Path) -> None:
    """
    Remove "BLANK PAGE" separator sheets from a question file. The segmenters'
    own detectors allow ~160 characters of residue; the 2017 specimen's SAM
    footer alone is longer, so Q3 opened on "BLANK PAGE -- TURN OVER FOR
    QUESTION 3". A sheet qualifies only if it says BLANK PAGE and little else
    remains once page furniture is removed.
    """
    with fitz.open(target) as doc:
        blank = []
        for i, page in enumerate(doc):
            text = page.get_text()
            if not BLANK_SHEET_RE.search(text):
                continue
            residue = re.sub(r"\s+", "", FURNITURE_RE.sub(" ", BLANK_SHEET_RE.sub(" ", text)))
            if len(residue) <= BLANK_RESIDUE_MAX:
                blank.append(i)
        if not blank or len(blank) == doc.page_count:
            return
        doc.delete_pages(blank)
        doc.save(target.with_suffix(".tmp"))
    target.with_suffix(".tmp").replace(target)


FURNITURE_RESIDUE_MAX = 0  # "Total 8 marks" alone must survive (2023 Oct-Nov P2 q4)


STAMP_BAND = 28.0      # our header stamp sits in the top ~25pt
FOOTER_BAND = 30.0
BODY_INK_MAX = 0.002   # share of dark pixels allowed in the body


def _has_body_ink(page) -> bool:
    """
    Whether anything is DRAWN below the stamp: a scheme sketch (a graph, a
    circuit) is vector paths with no text, and must never count as empty.
    """
    rect = page.rect
    if rect.height <= STAMP_BAND + FOOTER_BAND:
        body = fitz.Rect(rect.x0, rect.y0 + min(STAMP_BAND, rect.height / 2), rect.x1, rect.y1)
    else:
        body = fitz.Rect(rect.x0, rect.y0 + STAMP_BAND, rect.x1, rect.y1 - FOOTER_BAND)
    pix = page.get_pixmap(dpi=40, clip=body, colorspace=fitz.csGRAY)
    samples = pix.samples
    if not samples:
        return False
    dark = sum(1 for b in samples if b < 200)
    return dark / len(samples) > BODY_INK_MAX


def drop_furniture_pages(target: Path) -> None:
    """
    Remove scheme pages that carry nothing but page furniture -- an empty
    table frame, our stamp, a footer (2015 May-Jun FPM P2 q1 ended on one).
    Pages with images are kept: a scheme diagram has no text.
    """
    with fitz.open(target) as doc:
        empty = []
        for i, page in enumerate(doc):
            residue = re.sub(r"\s+", "", FURNITURE_RE.sub(" ", page.get_text()))
            if len(residue) <= FURNITURE_RESIDUE_MAX and not page.get_images() \
                    and not _has_body_ink(page):
                empty.append(i)
        if not empty or len(empty) == doc.page_count:
            return
        doc.delete_pages(empty)
        doc.save(target.with_suffix(".tmp"))
    target.with_suffix(".tmp").replace(target)


def drop_empty_strips(target: Path) -> None:
    with fitz.open(target) as doc:
        empty = [
            i for i, page in enumerate(doc)
            if min(page.rect.width, page.rect.height) < STRIP_MAX_HEIGHT
            and not any(w[4].strip() and w[4] != "GradeMax" for w in page.get_text("words"))
            and not page.get_images()
        ]
        if not empty or len(empty) == doc.page_count:
            return
        doc.delete_pages(empty)
        doc.save(target.with_suffix(".tmp"))
    target.with_suffix(".tmp").replace(target)


# ── the gate ────────────────────────────────────────────────────────────────
def _ms_marks(ms) -> int | None:
    if ms is None:
        return None
    if ms.totals:
        return ms.totals[-1][1]
    if ms.tallies:
        return ms.tallies[-1]
    return ms.column_marks


LEAD_MAX = 150  # characters allowed before a cut's first "Question" header


def _sideways(page) -> bool:
    dirs = [line["dir"] for block in page.get_text("dict")["blocks"]
            for line in block.get("lines", [])]
    return bool(dirs) and sum(abs(d[1]) > abs(d[0]) for d in dirs) > len(dirs) / 2


def leading_text_chars(ms_file: Path) -> int | None:
    """
    Characters of real text standing BEFORE the cut's first Question header,
    in displayed reading order -- the previous question's trailing guidance
    when a band starts too early. None when the cut is sideways (rotated
    tables have no meaningful "before") or prints no header at all.
    """
    with fitz.open(ms_file) as doc:
        before: list[str] = []
        for page in doc:
            if _sideways(page):
                return None
            matrix = page.rotation_matrix
            words = sorted(((fitz.Rect(w[:4]) * matrix, w[4]) for w in page.get_text("words")),
                           key=lambda t: (round(t[0].y0 / 3), t[0].x0))
            for _, token in words:
                if token in ("Question", "Q."):
                    return len(re.sub(r"\s+", "", FURNITURE_RE.sub(" ", " ".join(before))))
                before.append(token)
    return None


def _first_page(segment) -> int:
    # Physics/Maths B cut regions; Further Pure cuts whole page ranges.
    if hasattr(segment, "qp_regions"):
        return segment.qp_regions[0].page
    return segment.qp_pages[0]


def _page_count(segment) -> int:
    if hasattr(segment, "qp_regions"):
        return len({r.page for r in segment.qp_regions})
    return segment.qp_pages[1] - segment.qp_pages[0] + 1


def verify_paper(repo_root: Path, paper_dir: Path, key: str, segments, decisions: dict,
                 manual_proven: bool = False, document_verified: bool = False,
                 ms_from_ocr: bool = False) -> list[dict]:
    read = []
    for s in segments:
        qp_file = paper_dir / "questions" / f"q{s.number}.pdf"
        ms_file = paper_dir / "markschemes" / f"q{s.number}.pdf"
        qp = read_evidence(qp_file, is_ms=False)
        ms = read_evidence(ms_file, is_ms=True) if ms_file.is_file() else None
        if ms is not None and ms_from_ocr:
            # OCR misreads lone part letters ("b" -> "a", 2016 May-Jun P1 q11),
            # so an OCR'd scheme cannot fail part coverage; it still needs
            # number + marks, or a reading, to publish.
            ms = dataclasses.replace(ms, parts=())
        read.append((s, qp_file, ms_file, qp, ms))

    marks = [_ms_marks(ms) for *_, ms in read]
    sequence_ok = (
        len(read) > 1
        and all(ms is not None for *_, ms in read)
        and all(m is None or m == s.marks for m, (s, *_) in zip(marks, read))
        and sum(m is None for m in marks) <= 1
    )
    verdicts = [judge(s.number, qp, ms) for s, _, _, qp, ms in read]
    # The scheme DOCUMENT is this paper's when at least half its questions
    # (and never fewer than 3) already reconcile on number AND marks: a scheme
    # from another sitting cannot do that.
    proven_count = sum(v == "PROVEN" for v, _ in verdicts)
    # ... or the independent content-pairing audit identified both documents
    # (unit, paper, session from the scheme's own title page) as this paper's.
    document_ok = document_verified or proven_count >= max(3, len(read) / 2)
    rows = []
    for (s, qp_file, ms_file, qp, ms), m, (verdict, detail) in zip(read, marks, verdicts):
        pinned = m == s.marks or (m is None and verdict == "LABEL_ONLY")
        if verdict in ("MARKS_ONLY", "LABEL_ONLY") and sequence_ok and pinned:
            verdict, detail = "SEQUENCE_PROVEN", "whole paper's scheme marks match in order"
        # Number printed on the scheme agrees, every part the question prints
        # is in the cut (judge already rejects MS_PARTIAL), no other question's
        # number stands in the cut's Question column, and the document is this
        # paper's: the cut is this question's block, even where its marks
        # cannot be machine-reconciled (ALT methods, code variants).
        # Questions without lettered parts qualify too: a label cut runs from
        # this question's margin number to the next one's, and a cut holding
        # any other question's number was already dropped when it was cut.
        if verdict == "LABEL_ONLY" and document_ok:
            foreign = {h.question for h in table_labels(ms_file)} - {s.number, None}
            if not foreign:
                verdict, detail = "LABEL_PROVEN", (
                    f"scheme names q{s.number}, holds all parts {list(qp.parts) or 'n/a'}, no other "
                    f"question's number; paper has {proven_count} marks-proven pairs")
        if (verdict in ("UNREADABLE", "MARKS_ONLY") and manual_proven and ms
                and m == s.marks):
            verdict, detail = "MANUAL_PROVEN", "hand-verified QP ranges; scheme marks agree"
        if verdict in PUBLISHABLE and ms_file.is_file():
            lead = leading_text_chars(ms_file)
            if lead is not None and lead > LEAD_MAX:
                verdict, detail = "MS_EXTRA", (f"{lead} characters stand before the scheme's first "
                                               f"Question header (previous question's guidance?)")
        decision = decisions.get(f"{key}|{s.number}")
        if decision and verdict not in PUBLISHABLE:
            if decision["decision"] == "CONFIRMED":
                verdict, detail = "REVIEWED_PROVEN", f"read together: {decision['reason']}"
            elif decision["decision"] == "REJECTED":
                verdict, detail = "REJECTED", f"read together: {decision['reason']}"
        rows.append({
            "paper": key, "question": s.number, "marks": s.marks, "verdict": verdict,
            "detail": detail,
            "page_number": _first_page(s) + 1,
            "page_count": _page_count(s),
            "qp": str(qp_file.relative_to(repo_root)),
            "ms": str(ms_file.relative_to(repo_root)) if ms else None,
        })
    return rows


def display_regions(seg: ModuleType, ms_file: Path, bands) -> tuple:
    """
    [page, top, bottom] read off a ruler render, i.e. in DISPLAYED points.
    On a /Rotate 90 page a displayed horizontal band is a vertical strip of
    the stored page, so the band is mapped back through the rotation and
    becomes a full Region (left/right/top/bottom) in unrotated points --
    which is what install_safe_extract cuts on.
    """
    regions = []
    with fitz.open(ms_file) as doc:
        for p, t, b in bands:
            page = doc[p]
            shown = fitz.Rect(0, float(t), page.rect.width, float(b))
            stored = shown * page.derotation_matrix
            stored.normalize()
            regions.append(seg.Region(page=p, top=stored.y0, bottom=stored.y1,
                                      left=stored.x0, right=stored.x1))
    return tuple(regions)


SUPPLEMENT_BANNER = ("GradeMax supplement - NOT part of Pearson's published mark scheme. "
                     "Pearson's scheme prints no marking for the part(s) below; this is "
                     "GradeMax's own worked answer.")


def append_supplement(ms_file: Path, supplement: dict) -> None:
    """
    Append a clearly labelled GradeMax page to an official scheme cut, for a
    part the board's scheme never printed (2016 Jan P1 16(a)). The official
    cut is untouched; the banner says whose words follow.
    """
    with fitz.open(ms_file) as doc:
        width = doc[0].rect.width if doc.page_count else 595.0
        lines = supplement["lines"]
        height = 60.0 + 16.0 * (len(lines) + 3)
        page = doc.new_page(width=width, height=height)
        page.draw_rect(fitz.Rect(20, 12, width - 20, 44), color=(0.75, 0.2, 0.1),
                       fill=(1.0, 0.95, 0.9), width=0.8)
        page.insert_textbox(fitz.Rect(26, 15, width - 26, 44), SUPPLEMENT_BANNER,
                            fontsize=8.5, fontname="helv", color=(0.55, 0.1, 0.05))
        y = 64.0
        page.insert_text((26, y), supplement["title"], fontsize=10.5, fontname="hebo")
        for line in lines:
            y += 16.0
            page.insert_text((36, y), line, fontsize=10, fontname="helv")
        doc.save(ms_file.with_suffix(".tmp"))
    ms_file.with_suffix(".tmp").replace(ms_file)


def apply_manual_pages(seg: ModuleType, paper_dir: Path, source, segments, decisions: dict) -> None:
    pending_supplements: list[tuple[Path, dict]] = []
    _apply_manual(seg, paper_dir, source, segments, decisions, pending_supplements)
    for ms_file, supplement in pending_supplements:
        if ms_file.is_file():
            append_supplement(ms_file, supplement)


def _apply_manual(seg: ModuleType, paper_dir: Path, source, segments, decisions: dict,
                  pending_supplements: list) -> None:
    for s in segments:
        decision = decisions.get(f"{source.key}|{s.number}")
        if decision and decision.get("qp_display_regions"):
            # A question boundary through a tall first line (2019 Jan P1 q9:
            # its column vectors' top rows fell into q8's cut).
            seg.extract_regions(source.qp_path,
                                display_regions(seg, source.qp_path, decision["qp_display_regions"]),
                                paper_dir / "questions" / f"q{s.number}.pdf")
        if decision and decision.get("ms_supplement"):
            # Applied after any re-cut below, so register it to run last.
            pending_supplements.append((paper_dir / "markschemes" / f"q{s.number}.pdf",
                                        decision["ms_supplement"]))
        if not decision or not (decision.get("ms_pages") or decision.get("ms_regions")
                                or decision.get("ms_display_regions")):
            continue
        ms_file = (seg.REPO_ROOT / decision["ms_source"] if decision.get("ms_source")
                   else source.ms_path)
        if ms_file is None:
            continue
        if decision.get("ms_display_regions"):
            regions = display_regions(seg, ms_file, decision["ms_display_regions"])
        elif decision.get("ms_regions"):
            # [page, top, bottom] in the page's own (unrotated) points, read off
            # a ruler render (lib/ms_anchor_list.render_with_ruler).
            regions = tuple(seg.Region(page=p, top=float(t), bottom=float(b))
                            for p, t, b in decision["ms_regions"])
        else:
            regions = tuple(seg.Region(page=p) for p in decision["ms_pages"])
        seg.extract_regions(ms_file, regions, paper_dir / "markschemes" / f"q{s.number}.pdf")


# ── document identity from the content-pairing audit ───────────────────────
PAIRING_AUDIT = REBUILD_DIR.parent / "qp_ms_content_pairing.json"


def pairing_verified(papers: list[LivePaper]) -> set[str]:
    """
    Paper ids whose QP and MS the content-pairing audit
    (scripts/audit_qp_ms_content_pairing.py) judged OK FOR THE SAME URLS we
    serve today. Missing or stale audit -> empty set (fail safe).
    """
    if not PAIRING_AUDIT.is_file():
        return set()
    rows = json.loads(PAIRING_AUDIT.read_text(encoding="utf-8"))
    ok = {r["id"]: r for r in rows if r.get("verdict") == "OK"}
    return {
        p.paper_id for p in papers
        if p.paper_id in ok and ok[p.paper_id]["pdf_url"] == p.qp_url
        and ok[p.paper_id]["markscheme_pdf_url"] == p.ms_url
    }


# ── the run loop ────────────────────────────────────────────────────────────
def run(code: str, seg: ModuleType, to_source: Callable[[LivePaper], object | None],
        argv: list[str] | None = None, *, before_paper: Callable | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", help="one live key, e.g. 2015_jan_P1")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--render", action="store_true",
                        help="draw every unproven pair to review/ for reading")
    args = parser.parse_args(argv)

    stage = REBUILD_DIR / code
    segments_dir = stage / "segments"
    verdicts_path = stage / "verdicts.json"
    decisions = load_decisions(stage / "manual_review.json")
    seg.OUTPUT_DIR = segments_dir

    papers = load_live_papers(code)
    pairing_ok = pairing_verified(papers)
    if args.paper:
        papers = [p for p in papers if p.key == args.paper]

    report: dict = {"papers": {}, "rows": []}
    for paper in papers:
        source = to_source(paper)
        if source is None:
            report["papers"][paper.key] = {"status": "NO_QP_SOURCE"}
            print(f"{paper.key:22} NO QP SOURCE")
            continue
        paper_dir = segments_dir / source.key
        if paper.key in OCR_QP_PAPERS:
            source = dataclasses.replace(source, qp_path=ocr_image_pages(source.qp_path))
            print(f"{paper.key:22} picture page(s) in the question paper -- OCR'd those pages")
        elif source.qp_path.name in CAESAR_SHIFTED:
            source = dataclasses.replace(source, qp_path=decoded_copy(
                source.qp_path, CAESAR_SHIFTED[source.qp_path.name]))
            print(f"{paper.key:22} shifted-font question text -- using its decoded copy")
        elif is_scrambled(source.qp_path):
            source = dataclasses.replace(source, qp_path=ocr_copy(source.qp_path))
            print(f"{paper.key:22} scrambled question text -- using its OCR copy")
        if source.ms_path is not None and is_scrambled(source.ms_path):
            source = dataclasses.replace(source, ms_path=ocr_copy(source.ms_path))
            print(f"{paper.key:22} scrambled mark-scheme text -- using its OCR copy")
        if before_paper:
            before_paper(source)
        result = seg.process_paper(source)
        status = "OK" if result.ok else "HELD"
        if result.ok:
            seg.write_paper(result)
            apply_manual_pages(seg, paper_dir, source, result.segments, decisions)
            rows = verify_paper(seg.REPO_ROOT, paper_dir, source.key, result.segments, decisions,
                                manual_proven=source.key in getattr(seg, "MANUAL_QP_RANGES", {}),
                                document_verified=paper.paper_id in pairing_ok,
                                ms_from_ocr=source.ms_path is not None
                                and source.ms_path.name.endswith(".ocr.pdf"))
            for row in rows:
                row["live_key"] = paper.key
                row["paper_id"] = paper.paper_id
            report["rows"].extend(rows)
            counts = Counter(r["verdict"] for r in rows)
            good = sum(counts[v] for v in PUBLISHABLE)
            print(f"{paper.key:22} {good:2}/{len(rows):2} publishable  "
                  f"{dict(counts) if good < len(rows) else ''}")
        else:
            print(f"{paper.key:22} HELD: {result.issues[:2]}")
        report["papers"][paper.key] = {"status": status, "key": source.key,
                                       "issues": result.issues, "warnings": result.warnings}
        if args.verbose:
            for w in result.warnings:
                print("     ", w)

    if args.paper and verdicts_path.is_file():
        full = json.loads(verdicts_path.read_text(encoding="utf-8"))
        done = set(report["papers"])
        full["rows"] = [r for r in full["rows"] if r["live_key"] not in done] + report["rows"]
        full["papers"].update(report["papers"])
        report = full
    stage.mkdir(parents=True, exist_ok=True)
    verdicts_path.write_text(json.dumps(report, indent=1), encoding="utf-8")
    if args.render:
        for row in report["rows"]:
            if row["verdict"] not in PUBLISHABLE:
                render_pair(seg.REPO_ROOT / row["qp"],
                            seg.REPO_ROOT / row["ms"] if row["ms"] else None,
                            stage / "review" / f"{row['paper']}_q{row['question']}.png")

    counts = Counter(r["verdict"] for r in report["rows"])
    held = [k for k, v in report["papers"].items() if v["status"] != "OK"]
    print(f"\nquestions: {sum(counts.values())}  {dict(counts)}")
    print(f"publishable: {sum(counts[v] for v in PUBLISHABLE)}")
    print(f"papers held ({len(held)}): {held}")
    return 0
