"""Segment and prove IAL Accounting (WAC11 Unit 1, WAC12 Unit 2) questions.

Each live QP PDF is two documents joined: the answer booklet (ruled answer
space, with each part's prompt repeated) and the Source Booklet, which holds
every question complete -- its data, tables and "Required" parts down to the
"(Total for Question N = M marks)" line. The question cut is the question's
Source Booklet section: complete and compact. Answer-booklet pages are left
out (they are mostly blank lines).

A question is published only when every check below passes (verdict
LABEL_PROVEN, in PUBLISHABLE); otherwise the paper is held with the reason:

  * the QP prints the unit's code (WAC11 / WAC12) and an exam date in the
    live row's session; the mark scheme prints the same code and session;
  * the content-pairing audit judged this QP/MS pair OK for the URLs served;
  * the Source Booklet yields questions 1..N in order, each ending on its own
    total line, and the scheme has exactly the same question numbers;
  * each scheme cut prints labels of its own question only and covers every
    part letter its question prints (lib/commerce_ms_fix._check).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import fitz

from lib.commerce_ms_fix import is_back_cover
from lib.igcse_science_rebuild import _lines, upright, write_cut
from lib.live_paper_sources import ROOT, LivePaper

UNIT_CODES = {"Unit_1": "WAC11", "Unit_2": "WAC12"}
ANSWER_BARCODE_RE = re.compile(r"\*P\d{5}[A-Z]{0,2}\d{4,}\*")
TOTAL_RE = re.compile(r"\(Total for Question (\d+)\s*=\s*(\d+) marks?\)", re.I)
FURNITURE_RE = re.compile(
    r"^\s*(?:\d+\s+)?P\d{5}[A-Z]{0,2}(?:\s+\d+)?\s*$|^\s*Turn over\s*$|GradeMax|^\s*\d+\s*$|"
    r"^\s*\*?P\d{5}[A-Z]{0,2}\*?\s*$|BLANK PAGE|©\s*\d{4} Pearson", re.I)
QP_DATE_RE = re.compile(r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)\s+\d{1,2}\s+"
                        r"(January|February|March|May|June|October|November)\s+(\d{4})")
MS_SESSION_RE = re.compile(r"\b(Summer|June|January|October|November)\s+(\d{4})\b")
COPYRIGHT_RE = re.compile(r"©\s*(\d{4})\s+Pearson")
# A scheme opens a question with "1(a)", "1 (a)", "Q1 (a)" or "Q1(a)(i)" (strong
# markers). "Question 1" is often an end-of-question reference, so it starts a
# question only when that question has no strong marker.
SCHEME_START_RE = re.compile(r"(?:(?<![\d(£$.,/-])\b|Q)([1-9])\s?\(a\)|(?:^|\s)Q([1-9])(?:\b|a\b)|"
                             r"^\s*([1-9])\s?\(i\)")
SCHEME_WEAK_RE = re.compile(r"\bQuestion\s+([1-9])\b")
QP_PART_RE = re.compile(r"(?:^|\s)\(([a-h])\)")
# Pearson published at least one scheme with a part left as a drafting note.
PLACEHOLDER_RE = re.compile(r"[^.]{0,40}\bto be (?:integrated|inserted|added)\b[^.]{0,40}|"
                            r"[^.]{0,30}\bfrom the Excel file\b", re.I)
SEASON_OF_MONTH = {"January": "jan", "February": "jan", "March": "jan", "May": "may-jun", "June": "may-jun",
                   "Summer": "may-jun", "October": "oct-nov", "November": "oct-nov"}
PAD = 6.0


@dataclass(frozen=True)
class Cut:
    number: int
    marks: int
    regions: tuple[tuple[int, float | None, float | None], ...]


def booklet_start(doc: fitz.Document) -> int:
    """First page after the cover that carries no answer-booklet barcode."""
    for i in range(1, len(doc)):
        if not ANSWER_BARCODE_RE.search(doc[i].get_text()):
            return i
    raise ValueError("no Source Booklet found (every page carries an answer-booklet barcode)")


def _content_box(page: fitz.Page) -> tuple[float, float] | None:
    """Top and bottom of the page's real content, ignoring headers, footers and watermarks."""
    ys = [(r.y0, r.y1) for text, r in _lines(page) if text.strip() and not FURNITURE_RE.search(text)]
    for d in page.get_drawings():
        r = d["rect"]
        if r.height < 0.9 * page.rect.height and r.width < 0.98 * page.rect.width:
            ys.append((r.y0, r.y1))
    if not ys:
        return None
    return min(y for y, _ in ys) - PAD, max(y for _, y in ys) + PAD


def _events(page: fitz.Page) -> list[tuple[float, str, int, int, float]]:
    """(y, kind, question, marks, y1) for question-number lines and total lines, top to bottom.

    A question number is a line at the left margin starting "N <text>", or a bare
    "N" there with the text beside it. Totals are found in the page text, since a
    total line is sometimes split over several text lines."""
    found = []
    for text, rect in _lines(page):
        m = re.match(r"^([1-9])\.?(?:\s+\S|$)", text)
        if m and rect.x0 < 80 and rect.y0 > 40 and rect.y1 < page.rect.height - 50 \
                and not FURNITURE_RE.search(text):
            found.append((rect.y0, "start", int(m[1]), 0, rect.y1))
    # Totals are located word by word: "Question" and its number are sometimes one
    # word joined by a thin space, which defeats a plain text search.
    words = page.get_text("words")
    flat_total = 0
    for i, w in enumerate(words):
        if not w[4].startswith("(Total"):
            continue
        span = words[i:i + 7]
        total = TOTAL_RE.search(" ".join(" ".join(x[4] for x in span).split()))
        if not total:
            continue
        rect = fitz.Rect(span[0][:4])
        for x in span:
            rect |= fitz.Rect(x[:4])
        found.append((rect.y0, "total", int(total[1]), int(total[2]), rect.y1))
        flat_total += 1
    if flat_total != len(TOTAL_RE.findall(" ".join(page.get_text().split()))):
        raise ValueError("a total line on this page could not be located")
    return sorted(found)


def source_cuts(doc: fitz.Document) -> list[Cut]:
    """Questions 1..N in the Source Booklet, each from its number line to its total line."""
    start_page = booklet_start(doc)
    cuts: list[Cut] = []
    expect, begun = 1, None  # begun = (page, top) of the question in progress
    for p in range(start_page, len(doc)):
        for y0, kind, n, marks, y1 in _events(doc[p]):
            if begun is None:
                if kind == "start" and n == expect:
                    begun = (p, y0 - PAD)
                continue
            if kind != "total":
                continue
            if n != expect:
                raise ValueError(f"Q{expect} ended on the total line of Q{n}")
            first_page, top = begun
            regions = []
            for q in range(first_page, p + 1):
                box = _content_box(doc[q])
                if box is None:
                    continue  # blank page inside the booklet
                lo = top if q == first_page else box[0]
                hi = y1 + PAD if q == p else box[1]
                if hi > lo:
                    regions.append((q, max(0.0, lo), min(doc[q].rect.height, hi)))
            cuts.append(Cut(expect, marks, tuple(regions)))
            expect, begun = expect + 1, None
    if begun is not None:
        raise ValueError(f"Q{expect} has no total line")
    if not cuts:
        raise ValueError("no questions found in the Source Booklet")
    return cuts


def _scheme_starts(page: fitz.Page) -> list[int]:
    return [int(next(g for g in m.groups() if g)) for text, _ in _rows(page)
            if not re.match(r"^\s*\(?\s*(?:Q\s?\d\.?\s+)?Total\b", text, re.I)
            for m in SCHEME_START_RE.finditer(text)]


def _rows(page: fitz.Page) -> list[tuple[str, float]]:
    """Visual rows: words whose vertical centres are within 3pt, left to right.
    Scheme tables put "2" and "(a)" in separate cells of one row."""
    rows: list[tuple[float, list]] = []
    for w in sorted(page.get_text("words"), key=lambda w: ((w[1] + w[3]) / 2, w[0])):
        mid = (w[1] + w[3]) / 2
        if rows and abs(rows[-1][0] - mid) <= 3:
            rows[-1][1].append(w)
        else:
            rows.append((mid, [w]))
    return [(" ".join(x[4] for x in sorted(ws, key=lambda x: x[0])), min(x[1] for x in ws)) for _, ws in rows]


def _markers(ms: fitz.Document, pattern: re.Pattern) -> list[tuple[int, float, int]]:
    """(page, y, question) for every marker row, in reading order."""
    out = []
    for p, page in enumerate(ms):
        rows = _rows(page)
        for k, (text, y) in enumerate(rows):
            if re.match(r"^\s*\(?\s*(?:Q\s?\d\.?\s+)?Total\b", text, re.I):
                continue  # "Q4 Total marks 30" and "(Total for Question 4 ...)" end a question
            bare = re.fullmatch(r"\s*([1-9])\s*", text)
            if pattern is SCHEME_START_RE and bare and k + 1 < len(rows) \
                    and re.match(r"^\s*\(a\)", rows[k + 1][0]) and rows[k + 1][1] - y < 30:
                out.append((p, y, int(bare[1])))  # a tall cell: "2" above "(a) ..."
                continue
            for m in pattern.finditer(text):
                out.append((p, y, int(next(g for g in m.groups() if g))))
    return sorted(out)


TABLE_HEADER_RE = re.compile(r"^\s*(?:Q\.?\s?No\.?|Question\s*(?:Number|No\.?)?|Section\s+[A-C])\b", re.I)


def _lift_to_header(ms: fitz.Document, page: int, y: float) -> float:
    """The top of a table header row ("Question Number | Answer | Mark") printed
    just above a question's first label, so the header travels with its question."""
    # The nearest header above the label; newer schemes put the part's question
    # text in the header row, so it can sit well above the label row.
    headers = [ry for text, ry in _rows(ms[page]) if TABLE_HEADER_RE.match(text)]
    above = [ry for ry in headers if 0 < y - ry <= 200]
    if not above:
        return y
    top = max(above)
    # A section heading ("Section B") directly over the header row goes with it.
    while (higher := [ry for ry in headers if 0 < top - ry <= 45]):
        top = max(higher)
    return top


def _has_content(page: fitz.Page, top: float | None, bottom: float | None) -> bool:
    """False when a slice holds only page furniture (running header, GradeMax mark)."""
    clip = fitz.Rect(0, top or 0, page.rect.width, bottom if bottom is not None else page.rect.height)
    lines = [ln for ln in page.get_text(clip=clip).splitlines() if ln.strip()]
    return any(not FURNITURE_RE.search(ln) and not re.search(r"·\s*(?:QP|MS)\s*$|^\s*\d{4}\s*$", ln)
               for ln in lines)


def scheme_regions(ms: fitz.Document, questions: list[int], *, lift_headers: bool = False,
                   start_re: re.Pattern | None = None,
                   ) -> dict[int, list[tuple[int, float | None, float | None]]]:
    """Question -> scheme regions, from its start marker to the next question's.

    Starts are taken in order, so a number inside an earlier answer cannot start
    a later question. A question may start part-way down a page that ends the
    previous one; the last question runs to before Pearson's back cover.

    With lift_headers, a question starts at the table header row printed just
    above its first label (IGCSE commerce schemes); without it the cut starts at
    the label itself (IAL Accounting, whose published cuts must keep their bytes).
    start_re replaces the strong start markers for schemes with their own label
    style (IGCSE ICT prints "1ai", "1biii", "1g")."""
    strong, weak = _markers(ms, start_re or SCHEME_START_RE), _markers(ms, SCHEME_WEAK_RE)
    starts: list[tuple[int, float]] = []
    after = (3, 0.0)  # schemes open with three pages of front matter
    for n in questions:
        hit = next(((p, y) for p, y, q in strong if q == n and (p, y) >= after), None) \
            or next(((p, y) for p, y, q in weak if q == n and (p, y) >= after), None)
        if hit is None:
            raise ValueError(f"scheme never names question {n}")
        after = (hit[0], hit[1] + 1)
        if lift_headers:
            hit = (hit[0], _lift_to_header(ms, hit[0], hit[1]))
        starts.append(hit)
    end = len(ms)
    while end > 0 and is_back_cover(ms[end - 1]):
        end -= 1
    regions = {}
    for k, n in enumerate(questions):
        (p0, y0) = starts[k]
        (p1, y1) = starts[k + 1] if k + 1 < len(questions) else (end, None)
        cut = []
        for p in range(p0, p1 + 1 if y1 is not None else p1):
            top = y0 - PAD if p == p0 else None
            bottom = y1 - PAD if (y1 is not None and p == p1) else None
            if p == p1 and y1 is not None and y1 - PAD <= (top or 0) + 20:
                continue  # the next question starts at the top of this page
            if p == p1 and bottom is not None and bottom < 60:
                continue
            if lift_headers and not _has_content(ms[p], top, bottom):
                continue  # a sliver of running header between this question and the next
            cut.append((p, top, bottom))
        regions[n] = cut
    return regions


def scheme_check(n: int, ms_cut: fitz.Document, qp_cut: fitz.Document) -> str | None:
    """The scheme cut names no other question and covers every part its question prints."""
    others = sorted({m for page in ms_cut for m in _scheme_starts(page) if m != n})
    if others:
        return f"scheme cut names question(s) {others}"
    placeholder = PLACEHOLDER_RE.search(" ".join(" ".join(p.get_text().split()) for p in ms_cut))
    if placeholder:
        return f"Pearson's scheme is incomplete here: \"{placeholder[0]}\""
    qp_parts = set(QP_PART_RE.findall(" ".join(p.get_text() for p in qp_cut)))
    # Schemes print parts as "(g)", "g)" or "2g)"; a lower-case letter must not
    # precede it, so words like "(see note)" do not count.
    ms_text = " ".join(p.get_text() for p in ms_cut)
    ms_parts = set(re.findall(r"(?<![a-z])([a-h])\s?\)", ms_text))
    # A scheme that opens "Q4 (i)" names part (a) by its question heading.
    if ms_cut.page_count and n in _scheme_starts(ms_cut[0]):
        ms_parts.add("a")
    missing = sorted(qp_parts - ms_parts)
    return f"scheme cut lacks part(s) {missing} the question prints" if missing else None


def _identity(paper: LivePaper, qp: fitz.Document, ms: fitz.Document) -> str | None:
    code = UNIT_CODES.get(paper.paper_number)
    if code is None:
        return f"unknown unit {paper.paper_number}"
    cover = qp[0].get_text()
    if code not in cover:
        return f"QP cover does not print {code}"
    date = QP_DATE_RE.search(cover)
    if date:
        if int(date[3]) != paper.year or SEASON_OF_MONTH[date[2]] != paper.season:
            return f"QP exam date {date[0]} is not {paper.year} {paper.season}"
    else:
        # Some covers carry no date in their text layer; their copyright year must match.
        year = COPYRIGHT_RE.search(" ".join(p.get_text() for p in qp))
        if not year or int(year[1]) != paper.year:
            return f"QP prints no exam date and copyright {year[1] if year else 'missing'} " \
                   f"is not {paper.year}"
    ms_cover = " ".join(ms[0].get_text().split())
    if code not in ms_cover or any(c in ms_cover for c in UNIT_CODES.values() if c != code):
        return f"mark scheme cover is not {code}"
    session = MS_SESSION_RE.search(ms_cover)
    if not session or int(session[2]) != paper.year or SEASON_OF_MONTH[session[1]] != paper.season:
        return f"mark scheme session {session[0] if session else 'missing'} is not {paper.year} {paper.season}"
    return None


def _fingerprint(path: Path) -> tuple:
    with fitz.open(path) as doc:
        return tuple((round(p.rect.width, 1), round(p.rect.height, 1), " ".join(p.get_text().split()),
                      len(p.get_images()), len(p.get_drawings())) for p in doc)


def write_stable(src: fitz.Document, regions, target: Path) -> None:
    """Write a cut, keeping the existing file when its content is unchanged.

    PDF bytes differ between saves of the same cut, and reads and review
    decisions pin each file's SHA-256, so an unchanged cut must keep its bytes."""
    fresh = target.with_suffix(".new.pdf")
    write_cut(src, regions, fresh)
    if target.is_file() and _fingerprint(target) == _fingerprint(fresh):
        fresh.unlink()
    else:
        fresh.replace(target)


def stage_paper(paper: LivePaper, segments: Path, paired: bool) -> tuple[str, list[dict]]:
    """Write the paper's cuts and return (note, rows). Rows are verdicted per question."""
    if not paper.qp_path or not paper.ms_path:
        return "HELD: missing QP or MS source", []
    if not paired:
        return "HELD: content-pairing audit has no OK verdict for these URLs", []
    out = segments / paper.key
    qp_src, ms_src = upright(paper.qp_path), upright(paper.ms_path)
    with fitz.open(qp_src) as qp, fitz.open(ms_src) as ms:
        why = _identity(paper, qp, ms)
        if why:
            return f"HELD: {why}", []
        cuts = source_cuts(qp)
        numbers = [c.number for c in cuts]
        if numbers != list(range(1, len(numbers) + 1)):
            return f"HELD: QP questions {numbers} are not 1..N", []
        try:
            scheme = scheme_regions(ms, numbers)
        except ValueError as exc:
            return f"HELD: {exc}", []
        rows = []
        for cut in cuts:
            qp_path = out / "questions" / f"q{cut.number}.pdf"
            ms_path = out / "markschemes" / f"q{cut.number}.pdf"
            qp_path.parent.mkdir(parents=True, exist_ok=True)
            ms_path.parent.mkdir(parents=True, exist_ok=True)
            write_stable(qp, list(cut.regions), qp_path)
            write_stable(ms, scheme[cut.number], ms_path)
            with fitz.open(ms_path) as ms_cut, fitz.open(qp_path) as qp_cut:
                problem = scheme_check(cut.number, ms_cut, qp_cut)
            rows.append({
                "paper": paper.key, "question": cut.number, "marks": cut.marks,
                "verdict": "HELD" if problem else "LABEL_PROVEN",
                "detail": problem or "source-booklet cut; scheme pages print only this question's "
                                     "labels and cover every part; codes and sessions agree",
                "page_number": cut.regions[0][0] + 1, "page_count": len(cut.regions),
                "qp": str(qp_path.relative_to(ROOT)), "ms": str(ms_path.relative_to(ROOT)),
                "live_key": paper.key, "paper_id": paper.paper_id,
            })
    proven = sum(r["verdict"] == "LABEL_PROVEN" for r in rows)
    return f"{proven}/{len(rows)} proven", rows
