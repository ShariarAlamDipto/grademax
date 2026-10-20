#!/usr/bin/env python3
"""Stage and publish question banks for IGCSE Accounting, Business and Economics.

Uses the existing total-line segmenter and question/mark-scheme proof gate.
Whole numbered questions retain their case study, figures and subparts. The
filters describe exam-paper scope, since these blocks span several chapters.
Only current-specification papers and proven pairs are published. Existing
question rows are preserved. Re-running adds only missing questions/topics.

    python -X utf8 scripts/onboard_igcse_commerce.py --subject 4AC1
    python -X utf8 scripts/onboard_igcse_commerce.py --subject 4AC1 --publish
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import re
import subprocess
import sys

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.igcse_science_rebuild import PUBLISHABLE, first_question_spot, prove_paper, stage_paper, upright, write_cut, _lines
from lib.live_paper_sources import REBUILD_DIR, ROOT, LivePaper, load_live_papers
from lib.live_rebuild_common import pairing_verified

SUBJECTS = {
    "4AC1": ("accounting", {
        "1": "Introduction to Bookkeeping and Accounting (Paper 1)",
        "2": "Financial Statements (Paper 2)",
    }),
    "4BS1": ("business", {
        "1": "Investigating Small Businesses (Paper 1)",
        "2": "Investigating Large Businesses (Paper 2)",
    }),
    "4EC1": ("economics", {
        "1": "Microeconomics and Business Economics (Paper 1)",
        "2": "Macroeconomics and the Global Economy (Paper 2)",
    }),
}


def paper_topic(paper_number: str) -> str:
    match = re.fullmatch(r"0?([12])R?", str(paper_number), re.I)
    if not match:
        raise ValueError(f"unsupported paper number: {paper_number}")
    return match[1]


def is_current_specification(code, paper) -> bool:
    if not paper.qp_path or not paper.ms_path:
        return False
    with fitz.open(paper.qp_path) as doc:
        return bool(re.search(rf"\b{code}\s*[/_]\s*0?[12]R?\b", doc[0].get_text(), re.I))


def add_business_formulae(paper, staged):
    """Keep supplied formulae and the shared case study with standalone questions."""
    source = upright(paper.qp_path)
    with fitz.open(source) as doc:
        formulae = [i for i in range(min(3, len(doc)))
                    if re.search(r"FORMULAE\s+FOR\s+INTERNATIONAL\s+GCSE\s+BUSINESS",
                                 doc[i].get_text(), re.I)]
        start = first_question_spot(doc)
        case_regions = []
        if start:
            end = next(((i, rect.y0) for i in range(start.page, len(doc))
                        for text, rect in _lines(doc[i])
                        if re.match(r"^\s*(?:1\s+)?\(a\)", text)), None)
            if end and (end[0] > start.page or end[1] - start.top > 40):
                case_regions = [(i, max(0, start.top - 4) if i == start.page else None,
                                 end[1] - 4 if i == end[0] else None)
                                for i in range(start.page, end[0] + 1)]
        case_path = staged[0]["qp"].parent.parent / "case_study.pdf"
        if case_regions:
            write_cut(doc, case_regions, case_path)
        for item in staged:
            target = item["qp"]
            with fitz.open(target) as question, fitz.open() as combined:
                for page in formulae:
                    combined.insert_pdf(doc, from_page=page, to_page=page)
                if case_regions and item["number"] != 1:
                    with fitz.open(case_path) as case:
                        for index, page in enumerate(case):
                            sheet = combined.new_page(width=page.rect.width, height=page.rect.height + 28)
                            sheet.insert_text((45, 18), "Shared case study", fontsize=10)
                            sheet.show_pdf_page(fitz.Rect(0, 28, page.rect.width, page.rect.height + 28),
                                                case, index)
                combined.insert_pdf(question)
                data = combined.tobytes(garbage=3, deflate=True)
            target.write_bytes(data)
            item["pages"] = ([i + 1 for i in formulae]
                             + ([i + 1 for i, _, _ in case_regions] if item["number"] != 1 else [])
                             + item["pages"])


def cached_papers(code: str):
    base = REBUILD_DIR / code
    rows = json.loads((base / "papers.json").read_text(encoding="utf-8"))
    result = []
    for row in rows:
        stem = f"{row['year']}_{row['season']}_P{row['paper_number']}"
        paths = [base / "sources" / f"{stem}_{kind}.pdf" for kind in ("qp", "ms")]
        result.append(LivePaper(row["id"], row["year"], row["season"], str(row["paper_number"]),
                                row["pdf_url"], row["markscheme_pdf_url"],
                                *[p if p.is_file() else None for p in paths]))
    return result


def stage(code: str, workers: int, *, cached: bool = False) -> dict:
    papers = cached_papers(code) if cached else load_live_papers(code)
    pairing = pairing_verified(papers)
    base = REBUILD_DIR / code
    notes, rows = {}, []

    def one(paper):
        if not is_current_specification(code, paper):
            return paper.key, "HELD: missing source or legacy specification", []
        paper_topic(paper.paper_number)
        staged = stage_paper(code, paper, base / "segments")
        if isinstance(staged, str):
            return paper.key, f"HELD: {staged}", []
        proved = prove_paper(code, paper, staged, {}, paper.paper_id in pairing)
        if code == "4BS1":
            add_business_formulae(paper, staged)
            for row, item in zip(proved, staged):
                row["page_count"] = len(item["pages"])
        for row in proved:
            row["topic"] = paper_topic(paper.paper_number)
        count = sum(row["verdict"] in PUBLISHABLE for row in proved)
        return paper.key, f"{count}/{len(proved)} proven", proved

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(one, paper): paper for paper in papers}
        for future in as_completed(futures):
            paper = futures[future]
            try:
                key, note, proved = future.result()
            except (ValueError, RuntimeError, IndexError) as exc:
                key, note, proved = paper.key, f"HELD: {exc}", []
            notes[key] = note
            rows.extend(proved)
            print(f"{code} {key:25} {note}", flush=True)
    result = {"scope": "current specification; complete questions; exam-paper filters",
              "papers": dict(sorted(notes.items())),
              "rows": sorted(rows, key=lambda r: (r["paper"], r["question"]))}
    (base / "verdicts.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(f"{code}: {dict(Counter(r['verdict'] for r in rows))}", flush=True)
    return result


def publish(code: str):
    subprocess.run(["node", "--env-file=.env.local", "scripts/publish-commerce-questions.mjs",
                    "--subject", code, "--execute"], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True, choices=SUBJECTS)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--publish", action="store_true", help="publish the staged proven pairs")
    parser.add_argument("--cached-sources", action="store_true", help="use cache-commerce-sources.mjs output")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")
    if args.publish:
        publish(args.subject)
    else:
        stage(args.subject, args.workers, cached=args.cached_sources)


if __name__ == "__main__":
    main()
