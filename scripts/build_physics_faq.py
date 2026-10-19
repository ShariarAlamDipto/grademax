"""Build the chapterwise 'most-asked questions' FAQ PDF for Edexcel IGCSE Physics (4PH1).

Content lives in data/faq/physics/*.json. Question frequencies are NOT hand-written:
each FAQ entry carries a regex that is matched against the real past-paper text so the
"asked in N of M papers" badge is computed from the archive at build time.

Usage:  python scripts/build_physics_faq.py [--corpus PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.physics_faq_corpus import build_corpus  # noqa: E402
from lib.physics_faq_render import render_pdf  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "data" / "faq" / "physics"
DEFAULT_OUT = ROOT / "data" / "faq" / "Edexcel_IGCSE_Physics_4PH1_Chapterwise_FAQ.pdf"


def load_content() -> tuple[dict, list[dict], dict | None]:
    meta = json.loads((CONTENT_DIR / "meta.json").read_text(encoding="utf-8"))
    chapters = []
    for path in sorted(CONTENT_DIR.glob("ch*.json"), key=lambda p: int(re.sub(r"\D", "", p.name))):
        chapters.append(json.loads(path.read_text(encoding="utf-8")))
    if not chapters:
        raise SystemExit(f"no chapter files found in {CONTENT_DIR}")
    skills_path = CONTENT_DIR / "skills.json"
    skills = json.loads(skills_path.read_text(encoding="utf-8")) if skills_path.exists() else None
    return meta, chapters, skills


def score_items(sections: list[dict], corpus: list[dict]) -> list[str]:
    """Attach a computed frequency to every FAQ entry. Returns a list of warnings."""
    warnings: list[str] = []
    all_papers = {q["paper_id"] for q in corpus}
    for ch in sections:
        for item in ch["items"]:
            rx = item.get("rx")
            if not rx:
                item["freq"] = None
                continue
            pat = re.compile(rx, re.I)
            hits = [q for q in corpus if pat.search(q["qp_text"])]
            papers = sorted({q["paper_id"] for q in hits})
            years = sorted({q["year"] for q in hits})
            item["freq"] = {
                "papers": len(papers),
                "total_papers": len(all_papers),
                "questions": len(hits),
                "years": years,
                "paper_ids": papers,
            }
            if not papers:
                label = ch.get("n", ch.get("title", "?"))
                warnings.append(f"[{label}] no corpus match for /{rx}/ -- {item['q'][:60]}")
    return warnings


def order_items(sections: list[dict]) -> None:
    """Rank each section's entries by how many papers actually asked them."""
    for ch in sections:
        ch["items"].sort(key=lambda it: -((it.get("freq") or {}).get("papers") or 0))


def chapter_stats(chapters: list[dict], corpus: list[dict]) -> None:
    """Attach measured question counts and mark shares to each chapter."""
    counts = Counter(q["topic"] for q in corpus)
    marks = Counter()
    for q in corpus:
        marks[q["topic"]] += q.get("marks_real") or 0
    total_q = sum(counts.values())
    total_m = sum(marks.values())
    for ch in chapters:
        key = str(ch["n"])
        ch["n_questions"] = counts.get(key, 0)
        ch["q_share"] = counts.get(key, 0) / total_q if total_q else 0
        ch["m_share"] = marks.get(key, 0) / total_m if total_m else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", default=str(ROOT / "data" / "processed" / "Physics Processed"))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--from-year", type=int, default=2018)
    ap.add_argument("--to-year", type=int, default=2025)
    args = ap.parse_args()

    print(f"[1/4] reading past-paper archive: {args.archive}")
    corpus, corpus_report = build_corpus(Path(args.archive), args.from_year, args.to_year)
    for line in corpus_report:
        print(f"      {line}")

    print("[2/4] loading FAQ content")
    meta, chapters, skills = load_content()
    sections = chapters + ([skills] if skills else [])
    print(f"      {len(chapters)} chapters, {sum(len(c['items']) for c in sections)} entries")

    print("[3/4] computing question frequencies from the archive")
    warnings = score_items(sections, corpus)
    order_items(sections)
    chapter_stats(chapters, corpus)
    for w in warnings:
        print(f"      WARNING {w}")

    meta["n_papers"] = len({q["paper_id"] for q in corpus})
    meta["n_questions"] = len(corpus)

    print(f"[4/4] rendering PDF -> {args.out}")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    render_pdf(meta, chapters, out, skills=skills)
    doc = fitz.open(out)
    print(f"      done: {doc.page_count} pages, {out.stat().st_size / 1024:.0f} KB")
    doc.close()
    return 1 if warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
