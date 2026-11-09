"""Segment and prove IAL Business (WBS11-WBS14) questions.

Each live QP PDF is the question paper followed by its Source Booklet. A paper has
three sections, one question each: SECTION A is question 1, B is 2, C is 3. The
question's prompts are in the question paper; the case material it uses is in the
Source Booklet under "Source(s) for use with Section X". A question cut is that
section's extracts followed by its question pages, ending on its
"(Total for Question N = M marks)" line. Pages that hold only ruled answer lines
are left out.

In the mark scheme every part starts on a new page with a "Question <prompt>"
header row; the next row carries the label ("1(a)", "2 Indicative content", or a
bare "3"). A question's scheme runs from the first page labelled N to the page
before the first page labelled N+1 (the last question to before the back cover).

A question is published only when (LABEL_PROVEN, in PUBLISHABLE):
  * the QP and MS print the same unit code (WBS11..WBS14) for the live row's
    unit, and the MS cover names the row's session and year;
  * the content-pairing audit judged the QP/MS pair OK for the URLs served;
  * the paper yields questions 1..3 with totals adding to 80;
  * the scheme cut is labelled with its own question only and covers every part
    letter the question prints.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import fitz

from lib.commerce_ms_fix import is_back_cover
from lib.ial_accounting_stage import FURNITURE_RE, _rows, write_stable
from lib.live_paper_sources import ROOT, LivePaper

UNIT_CODES = {f"Unit_{n}": f"WBS1{n}" for n in range(1, 5)}
SECTIONS = {"A": 1, "B": 2, "C": 3}
TOTAL_RE = re.compile(r"\(Total for Question (\d+)\s*=\s*(\d+) marks?\)", re.I)
SOURCE_RE = re.compile(r"^\s*Sources? for use with Section ([A-C])\b")
SECTION_RE = re.compile(r"^\s*SECTION ([A-C])\s*$")
MS_SESSION_RE = re.compile(r"\b(Summer|June|January|October|November)\s+(\d{4})\b")
SEASON_OF_WORD = {"January": "jan", "Summer": "may-jun", "June": "may-jun", "October": "oct-nov", "November": "oct-nov"}
QP_PART_RE = re.compile(r"(?:^|\s)\(([a-h])\)")
LINES_RE = re.compile(r"\.{6,}")


@dataclass(frozen=True)
class Question:
    number: int
    marks: int
    regions: tuple[tuple[int, float | None, float | None], ...]


PAGE_FURNITURE_RE = re.compile(r"·\s*(?:QP|MS)\s*$|DO NOT WRITE IN THIS AREA|^\s*(?:DO|NOT|WRITE|IN|THIS|AREA)\s*$"
                               r"|\bP\d{5}[A-Z]{0,2}\b|\*?P\d{5}[A-Z]{0,2}\d*\*?", re.I)


def _is_rule(text: str) -> bool:
    """A row of answer-line dots (possibly broken into groups) or barcode glyphs."""
    # The vertical "DO NOT WRITE IN THIS AREA" margin words share rows with the dots.
    text = re.sub(r"\b(?:DO|NOT|WRITE|IN|THIS|AREA)\b", "", text)
    return not re.sub(r"[.\s-…]", "", text)


def _text_rows(page: fitz.Page) -> list[tuple[str, float]]:
    return [(t, y) for t, y in _rows(page)
            if t.strip() and not _is_rule(t) and not FURNITURE_RE.search(t)
            and not PAGE_FURNITURE_RE.search(re.sub(r"\.{3,}", "", t).strip() or "x")]


def _has_prompt(page: fitz.Page) -> bool:
    """False for a page of only ruled answer lines and page furniture."""
    return any(len(LINES_RE.sub("", t).strip()) > 3 and not re.fullmatch(r"\s*\d{1,2}\s*", t)
               for t, _ in _text_rows(page))


def _has_prompt_above(page: fitz.Page, y: float) -> bool:
    """True when the page has real text (not lines or furniture) above y."""
    return any(ry < y and len(LINES_RE.sub("", t).strip()) > 3 and not TOTAL_RE.search(t)
               for t, ry in _text_rows(page))


def booklet_start(doc: fitz.Document) -> int:
    for i, page in enumerate(doc):
        if any(SOURCE_RE.match(t) for t, _ in _rows(page)):
            return i
    raise ValueError("no Source Booklet found")


def _sources(doc: fitz.Document, start: int) -> dict[int, list[tuple[int, float | None, float | None]]]:
    """Section question number -> Source Booklet regions for that section."""
    marks: list[tuple[int, float, int]] = []
    for p in range(start, len(doc)):
        for t, y in _rows(doc[p]):
            m = SOURCE_RE.match(t)
            if m:
                marks.append((p, y, SECTIONS[m[1]]))
    out: dict[int, list] = {}
    for k, (p0, y0, n) in enumerate(marks):
        p1, y1 = (marks[k + 1][0], marks[k + 1][1]) if k + 1 < len(marks) else (len(doc), None)
        regions = []
        for p in range(p0, p1 + 1 if y1 is not None else p1):
            page = doc[p]
            if p != p0 and not _has_prompt(page):
                continue  # blank page in the booklet
            if re.search(r"\bAcknowledgements\b", page.get_text()) and p != p0:
                break
            top = y0 - 6 if p == p0 else None
            bottom = y1 - 6 if (y1 is not None and p == p1) else None
            if p == p1 and y1 is not None and (bottom or 0) < 100:
                continue  # only the top margin above the next section's sources
            regions.append((p, top, bottom))
        out[n] = regions
    return out


def questions(doc: fitz.Document) -> list[Question]:
    """Questions 1..3: each section's extracts, then its question pages to its total line."""
    start = booklet_start(doc)
    sources = _sources(doc, start)
    section_at: dict[int, tuple[int, float]] = {}
    totals: dict[int, tuple[int, float, int]] = {}
    for p in range(start):
        page = doc[p]
        for t, y in _rows(page):
            m = SECTION_RE.match(t)
            if m:
                section_at.setdefault(SECTIONS[m[1]], (p, y))
        flat = " ".join(page.get_text().split())
        for n, marks in TOTAL_RE.findall(flat):
            hits = [w for w in page.get_text("words") if w[4].startswith("(Total")]
            y1 = max(w[3] for w in hits) if hits else page.rect.height
            totals.setdefault(int(n), (p, y1, int(marks)))
    out = []
    for n in sorted(section_at):
        if n not in totals:
            raise ValueError(f"question {n} has no total line")
        (p0, y0), (p1, y1, marks) = section_at[n], totals[n]
        own = []
        for p in range(p0, p1 + 1):
            if p not in (p0, p1) and not _has_prompt(doc[p]):
                continue  # a page of answer lines only
            top = y0 - 6 if p == p0 else None
            if p == p1 and p != p0 and not _has_prompt_above(doc[p], y1 - 20):
                top = y1 - 24  # keep only the total line of a lines-only last page
            own.append((p, top, y1 + 6 if p == p1 else None))
        out.append(Question(n, marks, tuple(sources.get(n, [])) + tuple(own)))
    return out


def _label(page: fitz.Page) -> int | None:
    """The question number on a scheme page: the row after its "Question" header."""
    rows = _rows(page)
    for k, (t, y) in enumerate(rows):
        if not re.match(r"^\s*Question\b", t):
            continue
        # "Question" / "Number" headers wrap, and the prompt can run over several
        # rows; the label is the first row below starting with a question number.
        for t2, y2 in rows[k + 1:]:
            if y2 - y > 150:
                break
            m = re.match(r"^\s*(?:Number\s+)?Q?([1-3])\s*(?:\(|$|\s)", t2)
            if m:
                return int(m[1])
        return None
    return None


def scheme_pages(ms: fitz.Document, numbers: list[int]) -> dict[int, list[int]]:
    labels = [(_label(p), i) for i, p in enumerate(ms)]
    start: dict[int, int] = {}
    for n, i in labels:
        if n is not None:
            start.setdefault(n, i)
    if sorted(start) != numbers:
        raise ValueError(f"scheme labels questions {sorted(start)}, paper has {numbers}")
    if [start[n] for n in numbers] != sorted(start[n] for n in numbers):
        raise ValueError(f"scheme questions out of order: {start}")
    end = len(ms)
    while end > 0 and is_back_cover(ms[end - 1]):
        end -= 1
    return {n: list(range(start[n], start[numbers[k + 1]] if k + 1 < len(numbers) else end))
            for k, n in enumerate(numbers)}


def scheme_check(n: int, ms_cut: fitz.Document, qp_cut: fitz.Document) -> str | None:
    labels = {_label(p) for p in ms_cut} - {None}
    if labels - {n}:
        return f"scheme cut labels question(s) {sorted(labels - {n})}"
    qp_parts = set(QP_PART_RE.findall(" ".join(p.get_text() for p in qp_cut)))
    ms_parts = set(re.findall(rf"\b{n}\s?\(([a-h])\)", " ".join(p.get_text() for p in ms_cut)))
    missing = sorted(qp_parts - ms_parts)
    return f"scheme cut lacks part(s) {missing} the question prints" if missing else None


def _identity(paper: LivePaper, qp: fitz.Document, ms: fitz.Document) -> str | None:
    code = UNIT_CODES.get(paper.paper_number)
    if code is None:
        return f"unknown unit {paper.paper_number}"
    cover = " ".join(qp[0].get_text().split())
    found = set(re.findall(r"WBS1[1-4]", " ".join(p.get_text() for p in qp)))
    if found != {code}:
        return f"QP prints {sorted(found)}, the live row is {code}"
    ms_cover = " ".join(" ".join(p.get_text().split()) for p in list(ms)[:2])
    ms_codes = set(re.findall(r"WBS1[1-4]", ms_cover))
    if ms_codes and ms_codes != {code}:
        return f"mark scheme prints {sorted(ms_codes)}, the live row is {code}"
    session = MS_SESSION_RE.search(ms_cover)
    if not session or int(session[2]) != paper.year or SEASON_OF_WORD[session[1]] != paper.season:
        return f"mark scheme session {session[0] if session else 'missing'} is not {paper.year} {paper.season}"
    if str(paper.year) not in cover and f"©{paper.year}" not in cover.replace(" ", ""):
        return f"QP cover does not carry {paper.year}"
    return None


def stage_paper(paper: LivePaper, segments: Path, paired: bool) -> tuple[str, list[dict]]:
    if not paper.qp_path or not paper.ms_path:
        return "HELD: missing QP or MS source", []
    if not paired:
        return "HELD: content-pairing audit has no OK verdict for these URLs", []
    out = segments / paper.key
    with fitz.open(paper.qp_path) as qp, fitz.open(paper.ms_path) as ms:
        why = _identity(paper, qp, ms)
        if why:
            return f"HELD: {why}", []
        qs = questions(qp)
        numbers = [q.number for q in qs]
        if numbers != [1, 2, 3] or sum(q.marks for q in qs) != 80:
            return f"HELD: questions {[(q.number, q.marks) for q in qs]} are not 1..3 totalling 80", []
        try:
            scheme = scheme_pages(ms, numbers)
        except ValueError as exc:
            return f"HELD: {exc}", []
        rows = []
        for q in qs:
            qp_path = out / "questions" / f"q{q.number}.pdf"
            ms_path = out / "markschemes" / f"q{q.number}.pdf"
            qp_path.parent.mkdir(parents=True, exist_ok=True)
            ms_path.parent.mkdir(parents=True, exist_ok=True)
            write_stable(qp, list(q.regions), qp_path)
            write_stable(ms, [(p, None, None) for p in scheme[q.number]], ms_path)
            with fitz.open(ms_path) as ms_cut, fitz.open(qp_path) as qp_cut:
                problem = scheme_check(q.number, ms_cut, qp_cut)
            rows.append({
                "paper": paper.key, "question": q.number, "marks": q.marks,
                "verdict": "HELD" if problem else "LABEL_PROVEN",
                "detail": problem or "section extracts + question pages; scheme pages labelled only with "
                                     "this question and covering every part; codes and session agree",
                "page_number": q.regions[0][0] + 1, "page_count": len(q.regions),
                "qp": str(qp_path.relative_to(ROOT)), "ms": str(ms_path.relative_to(ROOT)),
                "live_key": paper.key, "paper_id": paper.paper_id,
            })
    return f"{sum(r['verdict'] == 'LABEL_PROVEN' for r in rows)}/{len(rows)} proven", rows
