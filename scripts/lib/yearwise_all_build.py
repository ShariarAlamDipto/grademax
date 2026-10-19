"""
Build the 2018-2026 yearwise books for one subject from the LINKED sittings of
the linkage audit (data/yearwise_all/linkage/<book>.json).

Volumes: a sitting's papers (Paper 1 + Paper 2, or all IAL units of a series)
stay together, volumes split at sitting boundaries in date order (user
decision 2026-10-04: year ranges), and the question book and its companion
mark-scheme book share the same split. The split uses the FEWEST volumes that
keep BOTH books of every pair at or under the binding limit, then balances
them (minimises the largest volume) so the last book is not a thin stub.

Cross-references, both directions -- the linkage is the point of the book:
    question sheet  "Mark scheme: Q3 p. 212 | Q4 p. 213"   (per question)
    scheme sheet    "Question paper: p. 45"                 (per paper)
Page numbers do not depend on what the headers say, so both books are laid
out first (every page number known), then rendered.

Space: covers, BLANK PAGE sheets and blank answer sides over the allowance are
dropped; formulae / equation / data sheets are printed ONCE per volume, from
the latest paper in it; Pearson's General Marking Guidance once per scheme book.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import fitz

from .yearwise_all_catalogue import ROOT, SEASONS, WORK, units_of
from .yearwise_all_layout import (
    SEP, Volume, clean_source, contents_pages, make_cover, place_exam, place_scheme,
    stamp_page_numbers,
    title_page)
from .yearwise_all_pages import LabelledPaper, label_paper, pages_to_keep
from .yearwise_layout import SEASON_LABEL
from .yearwise_ms_index import first_scheme_page, question_start_pages

PAGE_LIMIT = 450
# What a scheme page can carry and still be empty: our stamps, and Pearson's
# closing "Pearson Education Limited. Registered company number 872828 with its
# registered office at 80 Strand, London ..." -- alone on a scheme's last page.
BOILERPLATE = re.compile(
    r"GradeMax|[^\n]*[·|][^\n]*"
    r"|Pearson\s+Education\s+Limited\.?.*?(?:United\s+Kingdom|CM20\s*2JE)|\s", re.S)
FRONT_ESTIMATE = 12           # title + contents + reference / guidance sheets
GUIDANCE = re.compile(r"General\s+Marking\s+Guidance|General\s+Principles", re.I)
BOOKLET_COVER = re.compile(r"Do\s+not\s+return\s+this\s+Booklet|Candidate\s+surname", re.I)


@dataclass
class Paper:
    unit_key: str
    unit_label: str           # "Paper 1" / "Unit 4" / "P2"
    year: int
    season: str
    qp: Path
    ms: Path
    item: str | None
    totals: list[tuple[int, int]]
    lp: LabelledPaper | None = None
    kept: list = field(default_factory=list)
    ms_first: int = 0
    ms_count: int = 0
    ms_keep: list = field(default_factory=list)   # scheme page indices printed
    ms_starts: dict[int, int] = field(default_factory=dict)   # q -> page offset in scheme
    qp_page: int = 0          # absolute page numbers, filled at layout
    ms_page: int = 0
    q_pages: dict[int, int] = field(default_factory=dict)

    @property
    def session(self) -> str:
        return f"{SEASON_LABEL[self.season]} {self.year}"

    @property
    def reference(self) -> str:
        return f"{self.unit_label}{SEP}{self.item}" if self.item else self.unit_label


def load(book: str, unit_label) -> list[list[Paper]]:
    """LINKED papers grouped by sitting, in date order."""
    units = {u.key: u for u in units_of(book)}
    data = json.loads((WORK / "linkage" / f"{book}.json").read_text(encoding="utf-8"))
    by_sitting: dict[tuple[int, str], list[Paper]] = {}
    for u in data:
        for s in u["sittings"]:
            if s["verdict"] != "LINKED":
                continue
            year, season = s["sitting"].split(" ", 1)
            by_sitting.setdefault((int(year), season), []).append(Paper(
                unit_key=u["unit"], unit_label=unit_label(units[u["unit"]]),
                year=int(year), season=season, qp=ROOT / s["qp"]["path"], ms=ROOT / s["ms"]["path"],
                item=s["qp"]["item_code"], totals=[tuple(t) for t in s["qp"]["qp_totals"]]))
    order = list(units)
    return [sorted(by_sitting[k], key=lambda p: order.index(p.unit_key))
            for k in sorted(by_sitting, key=lambda k: (k[0], SEASONS.index(k[1])))]


def prepare(p: Paper, allowance: int) -> None:
    p.lp = label_paper(p.qp, p.item)
    p.kept = pages_to_keep(p.lp, allowance)
    with fitz.open(p.ms) as doc:
        p.ms_first = first_scheme_page(doc)
        # Pearson schemes carry the odd truly blank page (no text beyond our
        # stamp, no image, no table) -- printing it wastes a sheet.
        p.ms_keep = [i for i in range(p.ms_first, doc.page_count)
                     if len(BOILERPLATE.sub("", doc[i].get_text())) > 5
                     or doc[i].get_images() or len(doc[i].get_drawings()) > 3]
        p.ms_count = len(p.ms_keep)
    position = {page: k for k, page in enumerate(p.ms_keep)}
    p.ms_starts = {}
    for q, i in question_start_pages(p.ms, p.totals).items():
        following = [page for page in p.ms_keep if page >= i]
        if following:
            p.ms_starts[q] = position[following[0]]


def split(groups: list[list[Paper]]) -> list[list[list[Paper]]]:
    """Fewest contiguous volumes within the limit for BOTH books, then balanced."""
    cap = PAGE_LIMIT - FRONT_ESTIMATE
    qs = [sum(len(p.kept) for p in g) for g in groups]
    ms = [sum(p.ms_count for p in g) for g in groups]
    n = len(groups)
    if max(max(qs), max(ms)) > cap:
        raise SystemExit("one sitting alone exceeds the page limit")

    def fits(i: int, j: int) -> bool:
        return sum(qs[i:j]) <= cap and sum(ms[i:j]) <= cap

    # best[k][j]: smallest achievable largest-volume over groups[:j] in k volumes
    inf = math.inf
    best = [[inf] * (n + 1) for _ in range(n + 1)]
    cut = [[0] * (n + 1) for _ in range(n + 1)]
    best[0][0] = 0
    for k in range(1, n + 1):
        for j in range(1, n + 1):
            for i in range(k - 1, j):
                if best[k - 1][i] < inf and fits(i, j):
                    worst = max(best[k - 1][i], sum(qs[i:j]), sum(ms[i:j]))
                    if worst < best[k][j]:
                        best[k][j], cut[k][j] = worst, i
        if best[k][n] < inf:
            parts, j = [], n
            for kk in range(k, 0, -1):
                i = cut[kk][j]
                parts.append(groups[i:j])
                j = i
            return parts[::-1]
    raise SystemExit("no split fits")


def _contents_len(entries: list[dict], v: Volume) -> int:
    scratch = fitz.open()
    contents_pages(scratch, entries, v)
    n = scratch.page_count
    scratch.close()
    return n


def _entries(papers: list[Paper], attr: str) -> list[dict]:
    return [{"year": p.year, "season": p.season, "page": getattr(p, attr),
             "reference": p.reference, "note": None} for p in papers]


def _reference_sheets(papers: list[Paper]) -> list[tuple[Paper, int]]:
    """One copy of each unit's formulae / equation sheets, from its latest paper."""
    latest: dict[str, Paper] = {}
    for p in papers:
        if any(s.role == "reference" for s in p.lp.sheets):
            latest[p.unit_key] = p
    out, seen = [], []
    for p in latest.values():
        with fitz.open(p.qp) as doc:
            for s in p.lp.sheets:
                text = doc[s.index].get_text()
                # Paper 1 and Paper 2 append the SAME Equation Booklet: print it
                # once. The copies differ in item code, stamp line and text
                # extraction ORDER (same 615 characters, 0.84 sequence ratio),
                # so they are compared as sets of words.
                if s.role != "reference" or BOOKLET_COVER.search(text):
                    continue
                key = set(re.findall(r"[a-z]{3,}", re.sub(r"[^\n]*·[^\n]*", "", text.lower())))
                if any(len(key & k) / max(1, len(key | k)) > 0.9 for k in seen):
                    continue
                seen.append(key)
                out.append((p, s.index))
    return out


def _guidance(first: Paper) -> list[int]:
    with fitz.open(first.ms) as doc:
        return [i for i in range(1, first.ms_first) if GUIDANCE.search(doc[i].get_text())]


def layout(papers: list[Paper], vq: Volume, vm: Volume) -> dict:
    """Assign every absolute page number in both books; nothing is drawn yet."""
    refs = _reference_sheets(papers)
    guidance = _guidance(papers[0])
    q_front = 1 + _contents_len(_entries(papers, "qp_page"), vq) + len(refs)
    m_front = 1 + _contents_len(_entries(papers, "ms_page"), vm) + len(guidance)
    qn, mn = q_front, m_front
    for p in papers:
        p.qp_page, p.ms_page = qn + 1, mn + 1
        for offset, sheet in enumerate(p.kept):
            for q in sheet.starts:
                p.q_pages[q] = qn + 1 + offset
        qn += len(p.kept)
        mn += p.ms_count
    return {"refs": refs, "guidance": guidance, "q_front": q_front, "m_front": m_front,
            "q_pages": qn, "m_pages": mn}


def _located_before(p: Paper, q: int) -> int:
    """For a question whose scheme page could not be read: the page of the
    nearest EARLIER located question -- its answers lie at or after it."""
    earlier = [o for o in p.ms_starts if o < q]
    return p.ms_page + (p.ms_starts[max(earlier)] if earlier else 0)


def render_questions(papers: list[Paper], vq: Volume, plan: dict, partner: str) -> fitz.Document:
    doc = fitz.open()
    title_page(doc, vq, len(papers), partner)
    contents_pages(doc, _entries(papers, "qp_page"), vq)
    for p, index in plan["refs"]:
        with clean_source(p.qp) as src:
            place_exam(doc, src, index, p.lp.trim, "Formulae and data",
                       f"printed once for every paper in this volume{SEP}from {p.unit_label} {p.session}")
    for p in papers:
        with clean_source(p.qp) as src:
            for sheet in p.kept:
                if sheet.starts:
                    refs = [f"Q{q} p. {p.ms_page + p.ms_starts[q]}" if q in p.ms_starts
                            else f"Q{q} from p. {_located_before(p, q)}" for q in sheet.starts]
                    right = "Mark scheme: " + SEP.join(refs)
                else:
                    right = f"{p.reference}{SEP}mark scheme from p. {p.ms_page}"
                place_exam(doc, src, sheet.index, p.lp.trim, f"{p.unit_label}{SEP}{p.session}", right)
    stamp_page_numbers(doc, vq)
    return doc


def render_schemes(papers: list[Paper], vm: Volume, plan: dict, partner: str) -> fitz.Document:
    doc = fitz.open()
    title_page(doc, vm, len(papers), partner)
    contents_pages(doc, _entries(papers, "ms_page"), vm)
    with clean_source(papers[0].ms) as src:
        for i in plan["guidance"]:
            place_scheme(doc, src, i, "General Marking Guidance",
                         "printed once for every scheme in this volume")
    for p in papers:
        with clean_source(p.ms) as src:
            for i in p.ms_keep:
                place_scheme(doc, src, i, f"{p.unit_label}{SEP}{p.session}{SEP}Mark scheme",
                             f"Question paper: p. {p.qp_page}")
    stamp_page_numbers(doc, vm)
    return doc


def build(book: str, subject: str, code: str, level: str, unit_label, allowance: int,
          out_dir: Path, lockup: Path | None, execute: bool) -> int:
    groups = load(book, unit_label)
    for g in groups:
        for p in g:
            prepare(p, allowance)
    parts = split(groups)
    report = {"book": book, "allowance": allowance, "limit": PAGE_LIMIT, "volumes": []}
    out_dir.mkdir(parents=True, exist_ok=True)
    over = 0
    for n, part in enumerate(parts, 1):
        papers = [p for g in part for p in g]
        span = f"{papers[0].session} - {papers[-1].session}"
        vq = Volume(subject, code, level, "questions", n, len(parts), span)
        vm = Volume(subject, code, level, "markschemes", n, len(parts), span)
        plan = layout(papers, vq, vm)
        q = render_questions(papers, vq, plan, f"Answers: {subject} Mark Schemes, Volume {n}.\n"
                             "Every question's first page names the page its mark scheme starts on.")
        m = render_schemes(papers, vm, plan, f"Questions: {subject} Question Papers, Volume {n}.\n"
                           "Every scheme names the page its question paper starts on.")
        assert q.page_count == plan["q_pages"] and m.page_count == plan["m_pages"], "layout drift"
        for v, doc in ((vq, q), (vm, m)):
            flag = "  OVER LIMIT" if doc.page_count > PAGE_LIMIT else ""
            over += bool(flag)
            print(f"  Volume {n} {v.title:15} {span:45} {doc.page_count:4} pages{flag}")
            stem = f"{code}_Yearwise_Vol{n}_{'Questions' if v.is_questions else 'MarkSchemes'}"
            if execute:
                doc.save(out_dir / f"{stem}_interior.pdf", garbage=3, deflate=True)
                make_cover(out_dir / f"{stem}_cover.pdf", v, lockup)
            doc.close()
        report["volumes"].append({"volume": n, "span": span, "questions_pages": plan["q_pages"],
                                  "markschemes_pages": plan["m_pages"], "papers": [
            {"unit": p.unit_key, "sitting": f"{p.year} {p.season}", "item": p.item,
             "qp_page": p.qp_page, "ms_page": p.ms_page, "source_pages": len(p.lp.sheets),
             "kept_pages": len(p.kept), "question_pages": p.q_pages,
             "ms_question_pages": {q: p.ms_page + o for q, o in p.ms_starts.items()},
             "problems": p.lp.problems} for p in papers]})
    if execute:
        (out_dir / "print_index.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"\n{len(parts)} volume pair(s){'  -- ' + str(over) + ' OVER THE LIMIT' if over else ''}"
          f"{'' if execute else '   (dry run: nothing written)'}")
    return 1 if over else 0
