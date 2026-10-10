"""
Rebuild one IAL unit's LIVE question + mark-scheme segments (P1-P4, S1, M1)
from whole-paper PDFs and prove every pair before it can be published.

The IGCSE rebuilds (lib/live_rebuild_common.run) drive a workbook segmenter
module; the IAL units share one parser instead, so this is that loop for IAL:

  DOCUMENTS  the unit's VERIFIED sitting (data/workbook/ial_sources/<unit>/,
             each QP and MS checked against its own printed identity) when
             there is one; otherwise the live paper's own QP + MS, which count
             as identified only if the content-pairing audit passed those
             exact URLs.
  CUTTING    questions: lib.ial_qp_parse (page headers "3." / "Question 3
             continued", fences, part tallies; the paper must reconcile to its
             75 marks or it is held). Schemes: lib.ial_chapterwise_build
             (numbered block whose printed "(N marks)" equals the question's
             marks, else a codes-sum block trimmed at the next number).
  THE GATE   lib.live_rebuild_common.verify_paper with the IAL evidence reader
             (lib.live_ms_linkage_ial): number AND marks on both sides. On top,
             a scheme document not identified above must prove itself: at
             least half its questions (min 3) number+marks PROVEN, or nothing
             from it is published (DOC_UNVERIFIED) -- another sitting's scheme
             can match a question or two by chance, never half a paper.

Only papers that already serve questions are rebuilt: this repairs the live
tools, it does not add sittings to them. Staging only:
data/analysis/live_rebuild/<CODE>/{sources,segments,verdicts.json}.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import fitz

from lib import live_ms_linkage_ial
from lib import live_rebuild_common as common
from lib.ial_chapterwise_build import SOURCES, attach_markschemes, write_slice
from lib.ial_qp_parse import RECOVERY_PREFIX, build_questions, read_paper
from lib.live_ms_review import load_decisions, render_pair
from lib.igcse_science_rebuild import upright
from lib.live_paper_sources import (REBUILD_DIR, ROOT, LivePaper, fetch_rows, load_live_papers,
                                    subject_id, supabase_client)

PAPER_TOTAL_MARKS = 75
PUBLISHABLE = common.PUBLISHABLE


@dataclass(frozen=True)
class Docs:
    qp: Path
    ms: Path | None
    origin: str          # "verified source" | "live (pairing OK)" | "live (unidentified)"
    identified: bool


def choose_docs(unit: str, paper: LivePaper, pairing_ok: set[str]) -> Docs | None:
    verified = SOURCES / unit.lower() / f"{paper.year}_{paper.season}"
    if (verified / "QP.pdf").is_file():
        ms = verified / "MS.pdf"
        return Docs(verified / "QP.pdf", ms if ms.is_file() else None, "verified source", True)
    if paper.qp_path is None:
        return None
    identified = paper.paper_id in pairing_ok
    return Docs(paper.qp_path, paper.ms_path,
                "live (pairing OK)" if identified else "live (unidentified)", identified)


def extract_pages(source: Path, pages: tuple[int, int], target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(source) as src, fitz.open() as out:
        out.insert_pdf(src, from_page=pages[0], to_page=pages[1])
        out.save(target)


BLOCK_TOTAL_RE = re.compile(r"^\(\s*(\d{1,2})\s*marks?\s*\)$", re.I)
HEADER_RE = re.compile(r"^Question(\s+Number)?$", re.I)


def _scheme_lines(page: fitz.Page) -> list[tuple[str, fitz.Rect]]:
    lines: dict[tuple[int, int], list] = {}
    for w in page.get_text("words"):
        lines.setdefault((w[5], w[6]), []).append(w)
    out = []
    for words in lines.values():
        rect = fitz.Rect(words[0][:4])
        for w in words[1:]:
            rect |= fitz.Rect(w[:4])
        out.append((" ".join(w[4] for w in words).strip(), rect))
    return sorted(out, key=lambda item: (item[1].y0, item[1].x0))


def tally_bands(ms_path: Path, marks: list[int]) -> list[list[tuple]] | None:
    """
    Scheme regions per question when the scheme's own block totals -- the
    "(5 marks)" line closing each IAL question -- read, in document order,
    exactly the paper's question marks. Question N then runs from just past
    N-1's total to its own; question 1 from the first "Question / Scheme /
    Marks" header before its total. Any other count or order: None (the
    sequence is the proof, so nothing is guessed).
    2023 Oct-Nov P1: the attacher placed 5 of 11, the totals read 5,4,6,7,7,
    6,10,7,7,6,10 = the question marks.
    """
    with fitz.open(ms_path) as doc:
        if any(page.rotation for page in doc):
            return None
        totals, opens = [], []
        for index, page in enumerate(doc):
            lines = _scheme_lines(page)
            width = page.rect.width
            for i, (text, rect) in enumerate(lines):
                match = BLOCK_TOTAL_RE.match(text)
                if match:
                    totals.append((int(match.group(1)), index, rect))
                    continue
                if not HEADER_RE.match(text):
                    continue
                # A header opens question N when the first left-column row below
                # it starts with N ("3(a)", "3.", "3 (i)"); continuation headers
                # over a question's notes do not.
                below = [t for t, r in lines[i + 1:]
                         if r.y0 > rect.y1 and r.y0 < rect.y1 + 70 and r.x0 < width * 0.22
                         and not re.match(r"^(Number|Scheme|Marks)$", t, re.I)]
                head = re.match(r"^(\d{1,2})(?!\d)", below[0]) if below else None
                if head:
                    opens.append((int(head.group(1)), index, rect.y0))
        if [m for m, _, _ in totals] != marks:
            return None
        count = len(marks)
        start_of: dict[int, tuple[int, float]] = {}
        for number, page_no, y in opens:
            if 1 <= number <= count:
                start_of.setdefault(number, (page_no, max(0.0, y - 4)))
        if sorted(start_of) != list(range(1, count + 1)):
            return None
        starts = [start_of[n] for n in range(1, count + 1)]
        if any(b <= a for a, b in zip(starts, starts[1:])):
            return None
        # Each question runs from its own header to the next one's (its notes
        # follow its "(N marks)" line); its total must lie inside.
        last_page = doc.page_count - 1
        ends = starts[1:] + [(last_page, None)]
        bands = []
        for (begin, end), (_, t_page, t_rect) in zip(zip(starts, ends), totals):
            if not (begin <= (t_page, t_rect.y0) and (end[1] is None or (t_page, t_rect.y0) < end)):
                return None
            regions = [(p, begin[1] if p == begin[0] else None,
                        end[1] if (p == end[0] and end[1] is not None) else None)
                       for p in range(begin[0], end[0] + 1)]
            if end[1] is not None and end[1] <= 30 and len(regions) > 1:
                regions = regions[:-1]  # next question opens at the top of its page
            bands.append(regions)
        return bands


LABEL_RE = re.compile(r"^(\d{1,2})(?:\s*[.(]|\s*$|\s+\(?[a-h]\)?(?:\s|$))")


def label_bands(ms_path: Path, count: int) -> list[list[tuple]] | None:
    """
    Scheme regions per question from the question numbers in the margin
    column ("1.", "2(a)", "3 (a)"), taken strictly in order: question N runs
    from its own number to N+1's. For old schemes that print only part totals
    ("(2)") and no question total, so the totals cannot be sequenced (M1
    2015 May-Jun: attacher placed 0/8). Proof is left to the judge.
    """
    with fitz.open(ms_path) as doc:
        found, table = [], None
        for index, page in enumerate(doc):
            width = page.rect.width
            for text, rect in _scheme_lines(page):
                # The numbered marking-guidance list ("1. The total number of
                # marks...") precedes the table: labels count only after its
                # first "Question" header.
                if table is None:
                    if HEADER_RE.match(text):
                        table = (index, rect.y0, rect.x0)
                    continue
                # ...and only in the header's own column: a lone "2" in
                # question 1's working (x 168 against the column's 116) is not
                # question 2.
                if not (table[2] - 15 <= rect.x0 <= table[2] + 30) or rect.x0 > width * 0.25:
                    continue
                match = LABEL_RE.match(text)
                if match:
                    top = rect.y0
                    # start at the "Question Number | Scheme | Marks" row just above
                    for other, box in _scheme_lines(page):
                        if HEADER_RE.match(other) and rect.y0 - 45 <= box.y0 < rect.y0:
                            top = min(top, box.y0)
                    found.append((int(match.group(1)), index, top))
        starts, position = [], (-1, -1.0)
        for number in range(1, count + 1):
            hit = next(((p, y) for n, p, y in found if n == number and (p, y) > position), None)
            if hit is None:
                return None
            starts.append((hit[0], max(0.0, hit[1] - 4)))
            position = hit
        last = doc.page_count - 1
        while last > starts[-1][0] and len(doc[last].get_text("words")) < 60:
            last -= 1  # Pearson back page
        ends = starts[1:] + [(last, None)]
        bands = []
        for begin, end in zip(starts, ends):
            regions = [(p, begin[1] if p == begin[0] else None,
                        end[1] if (p == end[0] and end[1] is not None) else None)
                       for p in range(begin[0], end[0] + 1)]
            if end[1] is not None and end[1] <= 60 and len(regions) > 1:
                regions = regions[:-1]
            bands.append(regions)
        return bands


def write_regions(source: Path, regions: list[tuple], target: Path) -> None:
    """Copy whole pages; clip pages a band shares. Thin leftovers are dropped."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(source) as src, fitz.open() as out:
        for page_no, top, bottom in regions:
            page = src[page_no]
            if top is None and bottom is None:
                out.insert_pdf(src, from_page=page_no, to_page=page_no)
                continue
            clip = fitz.Rect(0, top or 0.0, page.rect.width, bottom or page.rect.height)
            if clip.height < 24:
                continue
            sheet = out.new_page(width=clip.width, height=clip.height)
            sheet.show_pdf_page(sheet.rect, src, page_no, clip=clip)
        if out.page_count == 0:
            out.insert_pdf(src, from_page=regions[0][0], to_page=regions[0][0])
        out.save(target, garbage=3, deflate=True)
    common.drop_furniture_pages(target)


def cut_paper(docs: Docs, paper_dir: Path) -> tuple[list, list[str], list[str]]:
    """Write questions/ and markschemes/ for one paper; (segments, defects, notes)."""
    questions, problems = build_questions(read_paper(docs.qp), PAPER_TOTAL_MARKS)
    defects = [p for p in problems if not p.startswith(RECOVERY_PREFIX)]
    notes = [p for p in problems if p.startswith(RECOVERY_PREFIX)]
    if defects or not questions:
        return [], defects or ["no questions read"], notes
    if paper_dir.exists():
        shutil.rmtree(paper_dir)  # a stale scheme file must never survive a re-cut
    for q in questions:
        target = paper_dir / "questions" / f"q{q.number}.pdf"
        extract_pages(docs.qp, q.pages, target)
        common.drop_blank_sheets(target)
    if docs.ms is not None:
        blocks = attach_markschemes(docs.ms, {q.number: q.marks for q in questions})
        bands = None
        if len(blocks) < len(questions):
            # Old landscape schemes are stored as /Rotate 90 pages: band and cut
            # them from an upright copy (still vector) in displayed coordinates.
            ms_up = upright(docs.ms)
            bands = (tally_bands(ms_up, [q.marks for q in questions])
                     or label_bands(ms_up, len(questions)))
        for number, part in blocks.items():
            target = paper_dir / "markschemes" / f"q{number}.pdf"
            write_slice(docs.ms, part, target)
            common.drop_furniture_pages(target)
        filled = 0
        if bands:
            # Only the questions the attacher could not place are cut from the
            # bands; its own blocks stand.
            for q, regions in zip(questions, bands):
                if q.number not in blocks:
                    write_regions(ms_up, regions, paper_dir / "markschemes" / f"q{q.number}.pdf")
                    filled += 1
        notes.append(f"schemes attached {len(blocks)}/{len(questions)}"
                     + (f"; {filled} more cut from the scheme's own number/total sequence"
                        if filled else ""))
    segments = [SimpleNamespace(number=q.number, marks=q.marks, qp_pages=q.pages)
                for q in questions]
    return segments, [], notes


def apply_hand_cuts(docs: Docs, paper_dir: Path, key: str, segments, decisions: dict) -> None:
    """
    A reading in manual_review.json may carry "ms_regions": [[page, top, bottom],
    ...] -- 0-based pages of the UPRIGHT scheme, points, null = page edge --
    when no automatic cut is right. The cut is written from those regions;
    the decision still has to say CONFIRMED for it to publish.
    """
    if docs.ms is None:
        return
    for segment in segments:
        regions = decisions.get(f"{key}|{segment.number}", {}).get("ms_regions")
        if regions:
            write_regions(upright(docs.ms), [tuple(r) for r in regions],
                          paper_dir / "markschemes" / f"q{segment.number}.pdf")


def require_identity(rows: list[dict], identified: bool) -> None:
    """Publish nothing from an unidentified scheme that cannot prove half a paper."""
    if identified:
        return
    proven = sum(r["verdict"] == "PROVEN" for r in rows)
    if proven >= max(3, len(rows) / 2):
        return
    for r in rows:
        if r["verdict"] in PUBLISHABLE:
            r["verdict"], r["detail"] = "DOC_UNVERIFIED", (
                f"scheme document unidentified and only {proven}/{len(rows)} pairs proven")


def live_paper_ids(code: str) -> set[str]:
    sb = supabase_client()
    sid = subject_id(sb, code)
    ids = [p["id"] for p in fetch_rows(lambda o: sb.table("papers").select("id")
                                       .eq("subject_id", sid).range(o, o + 999))]
    served: set[str] = set()
    for i in range(0, len(ids), 50):
        part = ids[i:i + 50]
        served |= {r["paper_id"] for r in fetch_rows(
            lambda o, part=part: sb.table("pages").select("paper_id").in_("paper_id", part)
            .not_.is_("qp_page_url", "null").range(o, o + 999))}
    return served


def run(code: str, unit: str, argv: list[str] | None = None) -> int:
    live_ms_linkage_ial.install()
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", help="one live key, e.g. 2019_jan_P1")
    parser.add_argument("--render", action="store_true",
                        help="draw every unproven pair to review/ for reading")
    args = parser.parse_args(argv)

    stage = REBUILD_DIR / code
    segments_dir = stage / "segments"
    verdicts_path = stage / "verdicts.json"
    decisions = load_decisions(stage / "manual_review.json")

    papers = load_live_papers(code)
    pairing_ok = common.pairing_verified(papers)
    served = live_paper_ids(code)
    papers = [p for p in papers if p.paper_id in served]
    if args.paper:
        papers = [p for p in papers if p.key == args.paper]

    report: dict = {"papers": {}, "rows": []}
    for paper in papers:
        docs = choose_docs(unit, paper, pairing_ok)
        if docs is None:
            report["papers"][paper.key] = {"status": "NO_QP_SOURCE"}
            print(f"{paper.key:22} NO QP SOURCE")
            continue
        paper_dir = segments_dir / paper.key
        segments, defects, notes = cut_paper(docs, paper_dir)
        entry = {"status": "OK" if segments else "HELD", "key": paper.key,
                 "origin": docs.origin, "issues": defects, "warnings": notes}
        report["papers"][paper.key] = entry
        if not segments:
            print(f"{paper.key:22} HELD ({docs.origin}): {defects[:2]}")
            continue
        apply_hand_cuts(docs, paper_dir, paper.key, segments, decisions)
        rows = common.verify_paper(ROOT, paper_dir, paper.key, segments, decisions,
                                   document_verified=docs.identified)
        require_identity(rows, docs.identified)
        for row in rows:
            row["live_key"] = paper.key
            row["paper_id"] = paper.paper_id
        report["rows"].extend(rows)
        counts = Counter(r["verdict"] for r in rows)
        good = sum(counts[v] for v in PUBLISHABLE)
        print(f"{paper.key:22} {good:2}/{len(rows):2} publishable  [{docs.origin}]  "
              f"{dict(counts) if good < len(rows) else ''}")

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
                render_pair(ROOT / row["qp"], ROOT / row["ms"] if row["ms"] else None,
                            stage / "review" / f"{row['paper']}_q{row['question']}.png")

    counts = Counter(r["verdict"] for r in report["rows"])
    held = [k for k, v in report["papers"].items() if v["status"] != "OK"]
    print(f"\nquestions: {sum(counts.values())}  {dict(counts)}")
    print(f"publishable: {sum(counts[v] for v in PUBLISHABLE)}")
    print(f"papers held ({len(held)}): {held}")
    return 0
