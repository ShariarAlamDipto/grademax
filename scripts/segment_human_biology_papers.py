#!/usr/bin/env python3
"""
GradeMax — Human Biology Paper Segmenter
=========================================
Segments raw IGCSE Human Biology question papers into individual question PDFs.

Input:  data/IGCSE FINAL/Human_Biology/{Year}/{Season}/Human_Biology_{Year}_{Season}_Paper_{N}_QP.pdf
Output: data/processed/Human_Biology/{Year}_{season}_{paper_num}/
          manifest.json
          pages/q1.pdf, q2.pdf, ...
          markschemes/q1.pdf, q2.pdf, ...

Usage:
  python scripts/segment_human_biology_papers.py
  python scripts/segment_human_biology_papers.py --year-from 2019 --year-to 2025
  python scripts/segment_human_biology_papers.py --dry-run
  python scripts/segment_human_biology_papers.py --overwrite
"""

import fitz  # PyMuPDF
import json
import re
import argparse
import sys
from pathlib import Path
from typing import Optional

RAW_BASE       = Path(__file__).parent.parent / "data" / "IGCSE FINAL" / "Human_Biology"
PROCESSED_BASE = Path(__file__).parent.parent / "data" / "processed" / "Human_Biology"

SUBJECT_CODE = "4HB1"

SEASON_MAP = {
    "May-Jun":  "may-jun",
    "Jan":      "jan",
    "Oct-Nov":  "oct-nov",
    "Specimen": "specimen",
}


# ---------------------------------------------------------------------------
# Filename parsing
# ---------------------------------------------------------------------------

def parse_filename(filename: str) -> Optional[dict]:
    """
    Parse e.g. Human_Biology_2023_May-Jun_Paper_1R_QP.pdf
    Returns dict or None if unrecognised.
    """
    stem = filename[:-4] if filename.endswith(".pdf") else filename

    m = re.match(
        r'^Human_Biology_(\d{4})_([A-Za-z][A-Za-z0-9\-]*)_Paper_([A-Za-z0-9]+)_(QP|MS)$',
        stem,
        re.IGNORECASE,
    )
    if not m:
        return None

    year       = int(m.group(1))
    season_raw = m.group(2)
    paper_num  = m.group(3)
    paper_type = m.group(4).upper()

    season_db = SEASON_MAP.get(season_raw)
    if season_db is None:
        return None

    return {
        "year":         year,
        "season_raw":   season_raw,
        "season_db":    season_db,
        "paper_number": paper_num,
        "paper_type":   paper_type,
    }


# ---------------------------------------------------------------------------
# Question boundary detection
# ---------------------------------------------------------------------------

def detect_fences(doc: fitz.Document) -> dict:
    fences = {}
    for page_idx in range(len(doc)):
        text = doc[page_idx].get_text("text")
        for m in re.finditer(r'Total\s+for\s+[Qq]uestion\s+(\d+)', text):
            fences[int(m.group(1))] = page_idx
    return fences


def detect_question_starts(doc: fitz.Document) -> dict:
    starts = {}
    for page_idx in range(len(doc)):
        for line in doc[page_idx].get_text("text").splitlines():
            m = re.match(r'^\s*(\d{1,2})\s+[A-Z(a-z]', line)
            if m:
                q_num = int(m.group(1))
                if q_num not in starts:
                    starts[q_num] = page_idx
    return starts


def detect_ms_question_starts(doc: fitz.Document) -> dict:
    starts = {}
    for page_idx in range(len(doc)):
        text = doc[page_idx].get_text("text")
        for m in re.finditer(r'(?:^|\n)\s*(?:Question|Q\.?)\s+(\d+)', text):
            q_num = int(m.group(1))
            if q_num not in starts:
                starts[q_num] = page_idx
    return starts


def ranges_from_fences(fences: dict, total_pages: int) -> dict:
    if not fences:
        return {}
    sorted_f = sorted(fences.items())
    questions = {}
    for i, (q_num, end_page) in enumerate(sorted_f):
        start = 0 if i == 0 else sorted_f[i - 1][1] + 1
        questions[q_num] = list(range(start, end_page + 1))
    return questions


def ranges_from_starts(starts: dict, total_pages: int) -> dict:
    if not starts:
        return {}
    sorted_s = sorted(starts.items())
    questions = {}
    for i, (q_num, start_page) in enumerate(sorted_s):
        end_page = sorted_s[i + 1][1] - 1 if i + 1 < len(sorted_s) else total_pages - 1
        questions[q_num] = list(range(start_page, end_page + 1))
    return questions


def even_distribution(num_questions: int, total_pages: int) -> dict:
    if num_questions == 0:
        return {}
    ppq = max(1, total_pages // num_questions)
    questions = {}
    for i in range(num_questions):
        start = i * ppq
        end   = start + ppq - 1 if i < num_questions - 1 else total_pages - 1
        questions[i + 1] = list(range(start, min(end + 1, total_pages)))
    return questions


# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------

def extract_pages_to_pdf(source_doc: fitz.Document, page_indices: list, output_path: Path) -> bool:
    try:
        out = fitz.open()
        for idx in page_indices:
            if 0 <= idx < len(source_doc):
                out.insert_pdf(source_doc, from_page=idx, to_page=idx)
        if len(out) == 0:
            out.close()
            return False
        out.save(str(output_path))
        out.close()
        return True
    except Exception as e:
        print(f"      [ERR] extract_pages_to_pdf {output_path.name}: {e}")
        return False


def extract_text_from_pages(doc: fitz.Document, page_indices: list) -> str:
    return "\n".join(
        doc[idx].get_text("text") for idx in page_indices if 0 <= idx < len(doc)
    )


# ---------------------------------------------------------------------------
# Core segmentation
# ---------------------------------------------------------------------------

def segment_qp(qp_path: Path, output_dir: Path, dry_run: bool) -> Optional[list]:
    try:
        doc = fitz.open(str(qp_path))
    except Exception as e:
        print(f"    [ERR] Cannot open QP: {e}")
        return None

    total_pages = len(doc)
    fences = detect_fences(doc)
    if len(fences) >= 2:
        questions = ranges_from_fences(fences, total_pages)
        method = "fence"
    else:
        starts = {q: p for q, p in detect_question_starts(doc).items() if q <= 30}
        if len(starts) >= 2:
            questions = ranges_from_starts(starts, total_pages)
            method = "regex"
        else:
            questions = even_distribution(max(2, total_pages // 2), total_pages)
            method = "even-dist"

    print(f"    QP: {len(questions)} questions ({method}), {total_pages} pages")

    if dry_run:
        doc.close()
        return [
            {"question_number": str(q), "qp_pages": pages, "text_excerpt": "", "has_markscheme": False}
            for q, pages in sorted(questions.items())
        ]

    pages_dir = output_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    q_data = []
    for q_num, page_list in sorted(questions.items()):
        q_pdf = pages_dir / f"q{q_num}.pdf"
        extract_pages_to_pdf(doc, page_list, q_pdf)
        text = extract_text_from_pages(doc, page_list)
        q_data.append({
            "question_number": str(q_num),
            "qp_pages":        page_list,
            "text_excerpt":    text[:500],
            "has_markscheme":  False,
        })

    doc.close()
    return q_data


def segment_ms(ms_path: Path, output_dir: Path, q_data: list, dry_run: bool) -> None:
    try:
        doc = fitz.open(str(ms_path))
    except Exception as e:
        print(f"    [WARN] Cannot open MS: {e}")
        return

    total_pages   = len(doc)
    num_questions = len(q_data)

    fences = detect_fences(doc)
    if len(fences) >= 2:
        ms_qs  = ranges_from_fences(fences, total_pages)
        method = "fence"
    else:
        starts = detect_ms_question_starts(doc)
        if len(starts) >= 2:
            ms_qs  = ranges_from_starts(starts, total_pages)
            method = "Question header"
        else:
            ms_qs  = even_distribution(num_questions, total_pages)
            method = "even-dist"

    print(f"    MS: {len(ms_qs)} sections ({method}), {total_pages} pages")

    if dry_run:
        for qd in q_data:
            qd["has_markscheme"] = True
        doc.close()
        return

    ms_dir = output_dir / "markschemes"
    ms_dir.mkdir(parents=True, exist_ok=True)

    for qd in q_data:
        q_num = int(qd["question_number"])
        if q_num in ms_qs:
            ms_pdf = ms_dir / f"q{q_num}.pdf"
            if extract_pages_to_pdf(doc, ms_qs[q_num], ms_pdf):
                qd["has_markscheme"] = True

    doc.close()


# ---------------------------------------------------------------------------
# Per-paper orchestration
# ---------------------------------------------------------------------------

def process_paper(
    qp_path: Path,
    ms_path: Optional[Path],
    meta: dict,
    dry_run: bool,
    overwrite: bool,
) -> bool:
    folder_name = f"{meta['year']}_{meta['season_db']}_{meta['paper_number']}"
    output_dir  = PROCESSED_BASE / folder_name
    manifest    = output_dir / "manifest.json"

    if manifest.exists() and not overwrite:
        return False

    print(f"\n  [{folder_name}]")
    print(f"    QP: {qp_path.name}")
    print(f"    MS: {ms_path.name if ms_path else 'not found'}")

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    q_data = segment_qp(qp_path, output_dir, dry_run)
    if q_data is None:
        return False

    if ms_path and ms_path.exists():
        segment_ms(ms_path, output_dir, q_data, dry_run)

    manifest_data = {
        "subject_code":    SUBJECT_CODE,
        "year":            meta["year"],
        "season":          meta["season_db"],
        "paper_number":    meta["paper_number"],
        "total_questions": len(q_data),
        "questions":       q_data,
    }

    if not dry_run:
        manifest.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
        print(f"    Wrote manifest — {len(q_data)} questions")
    else:
        print(f"    [DRY RUN] would write manifest — {len(q_data)} questions")

    return True


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Segment Human Biology (4HB1) papers into individual question PDFs"
    )
    parser.add_argument("--year-from", type=int, default=2011)
    parser.add_argument("--year-to",   type=int, default=2025)
    parser.add_argument("--dry-run",   action="store_true",
                        help="Show plan without writing files")
    parser.add_argument("--overwrite", action="store_true",
                        help="Re-segment already processed papers")
    args = parser.parse_args()

    if not RAW_BASE.exists():
        print(f"[ERR] Raw directory not found: {RAW_BASE}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  HUMAN BIOLOGY ({SUBJECT_CODE})")
    print(f"  Source : {RAW_BASE}")
    print(f"  Output : {PROCESSED_BASE}")
    print(f"{'='*60}")

    processed = skipped = errors = 0

    for year_dir in sorted(RAW_BASE.iterdir()):
        if not year_dir.is_dir():
            continue
        try:
            year = int(year_dir.name)
        except ValueError:
            continue
        if not (args.year_from <= year <= args.year_to):
            continue

        for season_dir in sorted(year_dir.iterdir()):
            if not season_dir.is_dir():
                continue

            for qp_path in sorted(season_dir.glob("*_QP.pdf")):
                meta = parse_filename(qp_path.name)
                if meta is None:
                    print(f"  [SKIP] Cannot parse: {qp_path.name}")
                    errors += 1
                    continue

                ms_name = qp_path.name.replace("_QP.pdf", "_MS.pdf")
                ms_path = season_dir / ms_name
                if not ms_path.exists():
                    ms_path = None

                result = process_paper(qp_path, ms_path, meta, args.dry_run, args.overwrite)
                if result:
                    processed += 1
                else:
                    skipped += 1

    print(f"\n  Done — processed={processed}, skipped={skipped}, errors={errors}")
    print("\n[DONE]  Segmentation complete.")


if __name__ == "__main__":
    main()
