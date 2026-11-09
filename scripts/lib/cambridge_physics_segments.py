"""
Cut Cambridge IGCSE Physics (0625) structured papers into whole questions and
pair each with its own mark-scheme block. Used only by
scripts/onboard_cambridge_physics.py (Paper 4 Theory and Paper 6 Alternative
to Practical, variant 2).

HOW A QUESTION IS CUT
---------------------
Cambridge closes every question with "[Total: X]". Question N runs from its
own margin number (x < 62, the line it opens) to the bottom of the N-th total
line. Pages in between are copied whole; "BLANK PAGE" sheets and furniture
strips are dropped by the shared cleaner. The totals must add up to the
component's paper total (Paper 4 = 80, Paper 6 = 40) or the paper is held.

HOW A SCHEME IS CUT
-------------------
Two layouts exist. 2017+ schemes are "Question | Answer | Marks" tables:
only pages that carry that header are scheme pages (the generic-marking
pages before them also number their points 1, 2, 3 ... at the same x), and a
label is the first word of a line left of the "Answer" header. 2015-2016
schemes print "Page n | Mark Scheme | Syllabus | Paper" and the question
number alone at x ~50. Labels are taken strictly in order 1..N; block N runs
from N's first label to N+1's first label.

PROOF (verdict names match lib.igcse_science_rebuild.PUBLISHABLE)
-----
Paper level: both covers print 0625/<component> and the same series and
year, the question count equals the scheme's, and the QP totals add up to
the paper total. Question level:
  PROVEN        scheme block names only question N, every part letter the
                question prints is in the block (and no others), and the
                block's Marks column adds up to the question's [Total].
  LABEL_PROVEN  as PROVEN but the Marks column could not be summed exactly
                (alternatives, "max" rows); the paper-level proof holds.
Anything else is held with its reason. Never loosen these checks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import fitz

from lib.igcse_science_rebuild import (
    PUBLISHABLE, _clean_regions, _is_blank_sheet, _lines, _md5, upright, write_cut,
)
from lib.live_rebuild_common import is_scrambled, ocr_copy

TOTAL_RE = re.compile(r"\[\s*Total\s*[:;.]?\s*(\d{1,2})\s*\]", re.I)
MARK_RE = re.compile(r"\[\s*(\d{1,2})\s*\]")
PAPER_MARKS = {"4": 80, "6": 40}
NUMBER_MAX_X = 62.0
PAD = 4.0
LABEL_RE = re.compile(r"^(\d{1,2})((?:\s*\(\s*[a-z]{1,4}\s*\))*)(?:[,&].*)?$")  # "5(c)(i),(ii)"
PART_RE = re.compile(r"^\(([a-h])\)(?:\(|$)")  # "(a)" or "(a)(i)(ii)"
MARK_CODE_RE = re.compile(r"^(?:[BCAM])(\d)$")
SEASON_TEXT = {
    "feb-mar": r"(?:February\s*/\s*)?March",
    "may-jun": r"May\s*/\s*June",
    "oct-nov": r"October\s*/\s*November",
}


@dataclass(frozen=True)
class Label:
    page: int
    top: float
    number: int
    part: str | None  # top-level part letter, when the label names one


@dataclass(frozen=True)
class SchemeLayout:
    labels: tuple[Label, ...]
    content_pages: tuple[int, ...]
    marks_x: dict[int, float]  # page -> x of the "Marks" header (table layout)
    table: bool


# ── question paper ──────────────────────────────────────────────────────────

def _marks_lines(doc: fitz.Document):
    """(kind, marks, page, bottom) for every "[Total: X]" and "[k]" in order."""
    found = []
    for index, page in enumerate(doc):
        for text, rect in _lines(page):
            for match in TOTAL_RE.finditer(text):
                found.append(("total", int(match.group(1)), index, rect.y1))
            for match in MARK_RE.finditer(text):
                found.append(("part", int(match.group(1)), index, rect.y1))
    return sorted(found, key=lambda f: (f[2], f[3]))


def margin_numbers(doc: fitz.Document) -> list[tuple[int, int, float]]:
    """Question numbers 1, 2, 3 ... standing in the margin, taken strictly in order."""
    spots, want, position = [], 1, (-1, -1.0)
    candidates = []
    for index, page in enumerate(doc):
        if index == 0:
            continue  # the cover
        words = page.get_text("words")
        for w in words:
            if not (w[4].isdigit() and w[0] < NUMBER_MAX_X and 40 < w[1] < page.rect.height - 50):
                continue
            if any(abs(v[1] - w[1]) < 5 and v[0] > w[2] for v in words):
                candidates.append((index, w[1], int(w[4])))
    for index, top, number in sorted(candidates):
        if number == want and (index, top) > position:
            spots.append((number, index, top))
            position, want = (index, top), want + 1
    return spots


@dataclass(frozen=True)
class QuestionCut:
    number: int
    marks: int
    regions: tuple[tuple[int, float | None, float | None], ...]
    has_total: bool


def question_cuts(doc: fitz.Document, component: str) -> tuple[list[QuestionCut], str]:
    """
    Question N runs from its margin number to its "[Total: X]" (or, for a
    one-part question printing no total, to its last "[k]" before N+1). Its
    marks are the total; where a total is printed its "[k]" marks must add up
    to it, and the questions must add up to the paper total.
    """
    numbers = margin_numbers(doc)
    if not numbers:
        return [], "no margin numbers"
    marks_lines = _marks_lines(doc)
    cuts = []
    for i, (number, page_no, top) in enumerate(numbers):
        start = (page_no, top)
        limit = (numbers[i + 1][1], numbers[i + 1][2]) if i + 1 < len(numbers) else (doc.page_count, 0.0)
        inside = [m for m in marks_lines if start <= (m[2], m[3]) < limit]
        totals = [m for m in inside if m[0] == "total"]
        parts = [m for m in inside if m[0] == "part"]
        if len(totals) > 1:
            return [], f"q{number}: {len(totals)} total lines"
        if totals:
            end, marks = totals[0], totals[0][1]
            part_sum = sum(m[1] for m in parts if (m[2], m[3]) <= (end[2], end[3]))
            if part_sum != marks:
                return [], f"q{number}: part marks add to {part_sum}, [Total: {marks}]"
        elif parts:
            end, marks = parts[-1], sum(m[1] for m in parts)
        else:
            return [], f"q{number}: no marks printed"
        regions = []
        for index in range(page_no, end[2] + 1):
            region_top = max(0.0, top - 2 * PAD) if index == page_no else None
            region_end = end[3] + PAD if index == end[2] else None
            regions.append((index, region_top, region_end))
        kept = _clean_regions(doc, regions)
        if not kept:
            return [], f"q{number}: nothing left after cleaning"
        cuts.append(QuestionCut(number, marks, kept, bool(totals)))
    total = sum(c.marks for c in cuts)
    if total != PAPER_MARKS[component]:
        return [], (f"question marks {[c.marks for c in cuts]} add to {total}, "
                    f"paper total is {PAPER_MARKS[component]}")
    return cuts, ""


def qp_parts(doc: fitz.Document, regions) -> tuple[str, ...]:
    """Top-level part letters "(a)" standing in the part column of the cut."""
    seen: list[str] = []
    for page_no, top, bottom in regions:
        page = doc[page_no]
        t = 0.0 if top is None else top
        b = page.rect.height if bottom is None else bottom
        for w in page.get_text("words"):
            match = PART_RE.match(w[4])
            if match and w[0] < 100 and t <= w[1] <= b and match.group(1) not in seen:
                seen.append(match.group(1))
    return tuple(seen)


# ── mark scheme ─────────────────────────────────────────────────────────────

MARKS_HEADER_RE = re.compile(r"^(?:Ma|Mar|Mark|Marks|arks|rks|ks)$")


def _header_row(page: fitz.Page) -> tuple[float, float, float] | None:
    """
    (right edge of the Question header, x of the Marks header, header y) when
    the page carries the "Question | Answer | Marks" row. Older tables print
    "Mark", and some pages split the words into glyph runs ("Que" + "estion",
    "Ma" + "arks"), so the row is recognised by "Answer" with a Q-word at the
    left and a Mark-word at the right.
    """
    words = page.get_text("words")
    for answer in (w for w in words if w[4] == "Answer"):
        row = [w for w in words if abs(w[1] - answer[1]) < 5]
        left = [w for w in row if w[0] < 130 and re.match(r"^(?:Q|Que|uestion|estion)", w[4])]
        right = [w for w in row if w[0] > answer[2] + 100 and MARKS_HEADER_RE.match(w[4])]
        if left and right:
            return max(w[2] for w in left), min(w[0] for w in right), answer[1]
    return None


def _label_of(text: str) -> tuple[int, str | None] | None:
    first = text.split()[0] if text.split() else ""
    match = LABEL_RE.match(first)
    if not match:
        return None
    part = re.match(r"\s*\(\s*([a-h])", match.group(2) or "")
    return int(match.group(1)), part.group(1) if part else None


def _column_lines(page: fitz.Page, max_x: float, min_y: float) -> list[tuple[str, float]]:
    """
    Text starting left of `max_x`, one entry per printed row, with touching
    glyph runs glued ("1" + "0(a)" is "10(a)" on 2017 May-Jun P42's scheme).
    """
    words = sorted((w for w in page.get_text("words")
                    if min_y < w[1] < page.rect.height - 40), key=lambda w: (w[1], w[0]))
    rows: list[list] = []
    for w in words:
        if rows and abs(rows[-1][0][1] - w[1]) < 3:
            rows[-1].append(w)
        else:
            rows.append([w])
    out = []
    for row in rows:
        row.sort(key=lambda w: w[0])
        if row[0][0] >= max_x:
            continue
        text = row[0][4]
        for prev, w in zip(row, row[1:]):
            if w[0] < prev[2] - 1 and w[4][:1] == prev[4][-1:]:
                text += w[4][1:]  # overlapping runs repeat a glyph: "10" + "0(c)(i)"
            else:
                text += ("" if w[0] - prev[2] < 1.5 else " ") + w[4]
        out.append((text, min(w[1] for w in row)))
    return out


def scheme_layout(doc: fitz.Document) -> SchemeLayout:
    headers = {i: _header_row(p) for i, p in enumerate(doc)}
    table_pages = [i for i, h in headers.items() if h]
    labels: list[Label] = []
    if table_pages:
        for index in table_pages:
            label_x, _, header_y = headers[index]
            for text, top in _column_lines(doc[index], label_x + 4, header_y + 2):
                found = _label_of(text)
                if found:
                    labels.append(Label(index, top, *found))
        return SchemeLayout(tuple(labels), tuple(table_pages),
                            {i: headers[i][1] for i in table_pages}, True)
    pages = []
    for index, page in enumerate(doc):
        if index == 0 or not re.search(r"Mark\s+Scheme", page.get_text()):
            continue
        pages.append(index)
        for text, top in _column_lines(page, NUMBER_MAX_X, 55):
            found = _label_of(text)
            if found:
                labels.append(Label(index, top, *found))
    return SchemeLayout(tuple(labels), tuple(pages), {}, False)


OLD_PAGE_HEADER_BOTTOM = 62.0
HEADER_REACH = 45.0


def _block_end(doc: fitz.Document, following: Label) -> tuple[int, float]:
    """Just above the next question's label, or above the table header row
    the board repeats right before it, so a block never ends on that row."""
    end = following.top
    for w in doc[following.page].get_text("words"):
        if w[4] == "Answer" and following.top - HEADER_REACH <= w[1] < following.top:
            end = min(end, w[1])
    return following.page, end - PAD


def scheme_blocks(doc: fitz.Document, layout: SchemeLayout, count: int):
    """Question -> regions, taking each question's first label strictly in order."""
    starts: list[Label] = []
    position = (-1, -1.0)
    for number in range(1, count + 1):
        label = next((b for b in layout.labels
                      if b.number == number and (b.page, b.top) > position), None)
        if label is None:
            return {}, f"no scheme label for question {number}"
        starts.append(label)
        position = (label.page, label.top)
    extra = [b for b in layout.labels if b.number > count and (b.page, b.top) > position]
    if extra:
        return {}, f"scheme labels beyond question {count}: {sorted({b.number for b in extra})}"
    last_page = layout.content_pages[-1]
    blocks = {}
    for i, label in enumerate(starts):
        end = (_block_end(doc, starts[i + 1]) if i + 1 < len(starts) else (last_page, None))
        regions = []
        for index in range(label.page, end[0] + 1):
            if index not in layout.content_pages:
                continue
            # 2015-2016 pages open with a "Page n | Mark Scheme | Syllabus |
            # Paper" box: a continuation starts below it.
            continuation = None if layout.table else OLD_PAGE_HEADER_BOTTOM
            top = max(0.0, label.top - PAD) if index == label.page else continuation
            bottom = end[1] if index == end[0] else None
            regions.append((index, top, bottom))
        blocks[label.number] = tuple(regions)
    return blocks, ""


def _in(regions, page_no: int, y: float) -> bool:
    for index, top, bottom in regions:
        if index == page_no and (top is None or y >= top - 1) and (bottom is None or y < bottom):
            return True
    return False


def _column_marks(doc: fitz.Document, layout: SchemeLayout, regions, labels) -> int | None:
    """
    The block's Marks column, summed part by part. A part whose final answer
    carries "A2"/"A3" lists its C marks as partial credit for the same marks,
    so there only B, M and A marks count. Bracketed marks are an alternative
    method. A "max" row makes the sum inexact (None).
    """
    starts = sorted((b.page, b.top) for b in labels)
    parts: dict[int, list[tuple[str, int]]] = {}
    for index, top, bottom in regions:
        x = layout.marks_x.get(index)
        if x is None:
            continue
        page = doc[index]
        words = page.get_text("words")
        # 2016-2017 tables close each question with a "Total" row whose
        # number stands in the Marks column; it is not a mark of its own.
        total_rows = [w[1] for w in words if re.match(r"^Total", w[4])]
        for w in words:
            if w[0] < x - 15 or not _in(regions, index, w[1]) or w[1] > page.rect.height - 40:
                continue
            if any(abs(w[1] - y) < 4 for y in total_rows):
                continue
            token = w[4]
            if re.match(r"^max", token, re.I):
                return None
            if token.startswith("("):
                continue
            code = MARK_CODE_RE.match(token)
            kind, value = (token[0], int(code.group(1))) if code else                 ("B", int(token)) if token.isdigit() and len(token) == 1 else (None, 0)
            if kind:
                part = sum(1 for s in starts if s <= (index, w[1] + 1))
                parts.setdefault(part, []).append((kind, value))
    total = 0
    for marks in parts.values():
        final_answer = any(k == "A" and v >= 2 for k, v in marks)
        total += sum(v for k, v in marks if not (final_answer and k == "C"))
    return total


def block_evidence(doc: fitz.Document, layout: SchemeLayout, regions) -> dict:
    labels = [b for b in layout.labels if _in(regions, b.page, b.top)]
    parts: list[str] = []
    for b in labels:
        if b.part and b.part not in parts:
            parts.append(b.part)
    if not layout.table:  # old layout: "(a)" stands in its own column
        for index, top, bottom in regions:
            for w in doc[index].get_text("words"):
                m = PART_RE.match(w[4])
                if m and w[0] < 120 and _in(regions, index, w[1]) and m.group(1) not in parts:
                    parts.append(m.group(1))
    if layout.table:
        marks = _column_marks(doc, layout, regions, labels)
    else:  # 2015-2016 schemes print "[Total: X]" under each question
        printed = [int(m.group(1)) for index, top, bottom in regions
                   for text, rect in _lines(doc[index]) if _in(regions, index, rect.y0)
                   for m in TOTAL_RE.finditer(text)]
        marks = printed[0] if len(printed) == 1 else None
    return {"numbers": sorted({b.number for b in labels}), "parts": tuple(sorted(parts)),
            "marks": marks}


# ── paper identity ──────────────────────────────────────────────────────────

def cover_identity(doc: fitz.Document, component_code: str, season: str, year: int) -> bool:
    text = " ".join(doc[i].get_text() for i in range(min(2, doc.page_count)))
    code_ok = re.search(rf"0625\s*/\s*{component_code}\b", text) is not None
    series_ok = re.search(rf"{SEASON_TEXT[season]}\s*{year}", text, re.I) is not None
    return code_ok and series_ok


# ── one paper ───────────────────────────────────────────────────────────────

def _read_with(source: Path, check) -> tuple[Path, str]:
    """
    The document to read: the source's own text layer when `check` passes on
    it, else an OCR copy when the layer is scrambled (2025 May-Jun P62 uses
    shifted glyphs throughout). 2020+ covers alone are encoded, which trips
    is_scrambled although every question page reads cleanly, so the original
    is always tried first. Cuts are always written from the source.
    """
    with fitz.open(source) as doc:
        why = check(doc)
    if not why or not is_scrambled(source):
        return source, why
    copy = ocr_copy(source)
    with fitz.open(copy) as doc:
        return copy, check(doc)


def stage_and_prove(paper, out_dir: Path, root: Path,
                    decisions: dict | None = None) -> tuple[list[dict], str]:
    decisions = decisions or {}
    component = paper.paper_number[0]
    qp_source, ms_source = upright(paper.qp_path), upright(paper.ms_path)
    identity = (paper.paper_number, paper.season, paper.year)
    for kind, source in (("QP", qp_source), ("MS", ms_source)):
        _, why = _read_with(source, lambda d: "" if cover_identity(d, *identity)
                            else f"{kind} cover does not print this component/series")
        if why:
            return [], why
    qp_read, why = _read_with(qp_source, lambda d: question_cuts(d, component)[1])
    if why:
        return [], why
    ms_read, why = _read_with(ms_source, lambda d: "" if scheme_layout(d).labels else "no scheme labels")
    if why:
        return [], why
    with fitz.open(qp_read) as qd, fitz.open(ms_read) as md:
        cuts, why = question_cuts(qd, component)
        if not cuts:
            return [], why
        layout = scheme_layout(md)
        blocks, why = scheme_blocks(md, layout, len(cuts))
        if not blocks:
            return [], why
        rows = []
        with fitz.open(qp_source) as qsrc, fitz.open(ms_source) as msrc:
            for cut in cuts:
                regions = tuple(r for r in cut.regions if not _is_blank_sheet(qsrc[r[0]])) or cut.regions
                ms_regions = _clean_regions(md, list(blocks[cut.number])) or blocks[cut.number][:1]
                qp_file = out_dir / paper.key / "questions" / f"q{cut.number}.pdf"
                ms_file = out_dir / paper.key / "markschemes" / f"q{cut.number}.pdf"
                write_cut(qsrc, regions, qp_file)
                write_cut(msrc, ms_regions, ms_file)
                evidence = block_evidence(md, layout, blocks[cut.number])
                parts = qp_parts(qd, cut.regions)
                verdict, detail = judge(cut.number, cut.marks, parts, evidence)
                verdict, detail = reviewed(decisions.get(f"{paper.key}|{cut.number}"),
                                           verdict, detail, qp_file, ms_file)
                rows.append({
                    "paper": paper.key, "question": cut.number, "marks": cut.marks,
                    "verdict": verdict, "detail": detail,
                    "page_number": regions[0][0] + 1, "page_count": len(regions),
                    "qp": str(qp_file.relative_to(root)), "ms": str(ms_file.relative_to(root)),
                    "live_key": paper.key, "paper_id": paper.paper_id,
                    "qp_parts": list(parts), "ms_parts": list(evidence["parts"]),
                    "ms_marks": evidence["marks"],
                    "qp_md5": _md5(qp_file), "ms_md5": _md5(ms_file),
                })
    return rows, ""


def reviewed(decision: dict | None, verdict: str, detail: str,
             qp_file: Path, ms_file: Path) -> tuple[str, str]:
    """
    A pair read together and recorded in manual_review.json. It counts only
    for the exact cuts that were read (md5 of what each cut shows), and only
    where the automatic proof did not already pass.
    """
    if not decision or verdict in PUBLISHABLE:
        return verdict, detail
    if decision.get("qp_md5") != _md5(qp_file) or decision.get("ms_md5") != _md5(ms_file):
        return verdict, f"{detail} [review on file is for an older cut]"
    if decision["decision"] == "CONFIRMED":
        return "REVIEWED_PROVEN", f"read together: {decision['reason']}"
    if decision["decision"] == "REJECTED":
        return "REJECTED", f"read together: {decision['reason']}"
    return verdict, detail


def judge(number: int, marks: int, qp_parts_: tuple[str, ...], evidence: dict) -> tuple[str, str]:
    if evidence["numbers"] != [number]:
        return "MS_WRONG", f"scheme block names questions {evidence['numbers']}"
    if qp_parts_ and evidence["parts"] and set(qp_parts_) != set(evidence["parts"]):
        return "MS_PARTIAL", f"parts: question {list(qp_parts_)}, scheme {list(evidence['parts'])}"
    if qp_parts_ and not evidence["parts"]:
        return "MS_PARTIAL", f"question prints parts {list(qp_parts_)}, scheme shows none"
    if evidence["marks"] == marks:
        return "PROVEN", "scheme names only this question; parts and marks agree"
    return "LABEL_PROVEN", (f"scheme names only q{number}; parts agree; marks column "
                            f"{evidence['marks']} vs [Total: {marks}]; paper identity proven")
