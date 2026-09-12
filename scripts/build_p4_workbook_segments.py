#!/usr/bin/env python3
"""
Phase 1 for the IAL Pure Mathematics 4 (WMA14) chapterwise workbook: cut every
question paper into one PDF per question.

    python scripts/build_p4_workbook_segments.py            # dry run
    python scripts/build_p4_workbook_segments.py --execute  # write the tree
    python scripts/build_p4_workbook_segments.py --audit    # re-verify output

Writes to `data/workbook/p4/` -- a NEW tree. Nothing under `data/processed/`
is touched, so this is reversible by deleting the output directory.

Dedicated to P4 per the standing rule that every subject gets its own script.
The IAL *page format* parsing it shares with S1 lives in
`scripts/lib/ial_qp_parse.py`; read that module's header first, it explains why
IAL cannot be segmented the way the IGCSE papers were.

THE WINDOW IS 2020 ONWARDS, AND THAT IS A CORRECTNESS CONSTRAINT
----------------------------------------------------------------
WMA14 was first assessed in June 2020. The source folder also contains ten
125-mark WMA02 "Core Mathematics C34" papers and four 75-mark legacy "C4"
papers, all filed under the same P4 directory. They are a DIFFERENT
SPECIFICATION: the trapezium rule appears in 10 of those 14 papers and in none
of the 14 genuine ones, and numerical iteration in 9 of 14 versus none -- both
are P2/P3 content under the 2018 specification.

Including them would put off-specification questions in front of a P4 student,
so `is_in_scope()` gates on the cover, not on the filename. Mining the legacy
papers behind a per-question specification filter is a deliberate later step.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.ial_qp_parse import (  # noqa: E402
    QUESTION_CONT_RE,
    QUESTION_START_RE,
    build_questions,
    content_fingerprint,
    page_lines,
    read_paper,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT / "data" / "Ultimate Final IAL" / "Mathematics"
OUTPUT_DIR = REPO_ROOT / "data" / "workbook" / "p4"
REPORT_PATH = REPO_ROOT / "data" / "workbook" / "p4_segmentation_report.json"

UNIT = "P4"
SUBJECT_CODE = "WMA14"
PAPER_TOTAL_MARKS = 75

#: Read off the cover of the first pages. A genuine WMA14 paper says so.
IN_SCOPE_CODE_RE = re.compile(r"WMA14", re.I)
OUT_OF_SCOPE_RE = re.compile(r"Core\s+Mathematics\s+C(?:34|4)\b|WMA02", re.I)

EXCLUDED_PAPERS: dict[str, str] = {}

#: Page ranges read off a rendered contact sheet, for papers whose text layer
#: cannot be parsed at all. Empty -- every in-scope P4 paper parses cleanly.
MANUAL_QP_RANGES: dict[str, dict[int, tuple[int, int, int]]] = {}

SEASON_FROM_FOLDER = {
    "jan": "jan",
    "may-jun": "may-jun",
    "oct-nov": "oct-nov",
    "specimen": "specimen",
}


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PaperSource:
    key: str
    year: int
    season: str
    qp_path: Path
    ms_path: Path | None


@dataclass
class PaperResult:
    source: PaperSource
    questions: list = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


# ─────────────────────────────────────────────────────────────────────────────
# Discovery
# ─────────────────────────────────────────────────────────────────────────────


def cover_text(pdf_path: Path, pages: int = 3) -> str:
    with fitz.open(pdf_path) as doc:
        return "\n".join(doc[i].get_text() for i in range(min(pages, doc.page_count)))


def is_in_scope(pdf_path: Path) -> tuple[bool, str]:
    """
    Decide from the paper's own cover whether it is genuine WMA14.

    The filename says 'P4' for all thirty files in this folder and is therefore
    worthless as evidence. The cover names the qualification and the paper code,
    and it is what decides.
    """
    text = cover_text(pdf_path)
    if OUT_OF_SCOPE_RE.search(text):
        legacy = OUT_OF_SCOPE_RE.search(text).group(0)
        return False, f"legacy qualification on cover ({legacy})"
    if IN_SCOPE_CODE_RE.search(text):
        return True, "WMA14 on cover"
    return False, "no WMA14 paper code found on the cover"


def discover_papers() -> tuple[list[PaperSource], list[str]]:
    notes: list[str] = []
    candidates: list[PaperSource] = []

    for qp_path in sorted(SOURCE_DIR.rglob(f"Mathematics_{UNIT}_*_QP.pdf")):
        match = re.search(rf"Mathematics_{UNIT}_(\d{{4}})_([A-Za-z-]+)_QP\.pdf$", qp_path.name)
        if not match:
            notes.append(f"unparseable filename, skipped: {qp_path.name}")
            continue
        year = int(match.group(1))
        season = SEASON_FROM_FOLDER.get(match.group(2).lower(), match.group(2).lower())
        key = f"{year}_{season}"

        if key in EXCLUDED_PAPERS:
            notes.append(f"excluded {key}: {EXCLUDED_PAPERS[key]}")
            continue

        in_scope, reason = is_in_scope(qp_path)
        if not in_scope:
            notes.append(f"out of scope {key}: {reason}")
            continue

        ms_path = qp_path.with_name(qp_path.name.replace("_QP.pdf", "_MS.pdf"))
        candidates.append(
            PaperSource(
                key=key,
                year=year,
                season=season,
                qp_path=qp_path,
                ms_path=ms_path if ms_path.exists() else None,
            )
        )

    unique: list[PaperSource] = []
    seen: dict[str, str] = {}
    for source in candidates:
        fingerprint = content_fingerprint(source.qp_path)
        if fingerprint in seen:
            notes.append(
                f"duplicate: {source.key} is the same paper as {seen[fingerprint]} "
                f"(identical text once the watermark session token is stripped)"
            )
            continue
        seen[fingerprint] = source.key
        unique.append(source)

    return unique, notes


# ─────────────────────────────────────────────────────────────────────────────
# Processing
# ─────────────────────────────────────────────────────────────────────────────


def process_paper(source: PaperSource) -> PaperResult:
    facts = read_paper(source.qp_path)
    questions, problems = build_questions(facts, PAPER_TOTAL_MARKS)
    return PaperResult(source=source, questions=questions, problems=problems)


def extract_range(source_pdf: Path, page_range: tuple[int, int], target: Path) -> None:
    start, end = page_range
    target.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(source_pdf) as src:
        out = fitz.open()
        try:
            out.insert_pdf(src, from_page=start, to_page=end)
            out.save(target)
        finally:
            out.close()


def write_paper(result: PaperResult) -> int:
    paper_dir = OUTPUT_DIR / result.source.key
    written = 0
    for question in result.questions:
        extract_range(
            result.source.qp_path,
            question.pages,
            paper_dir / "questions" / f"q{question.number}.pdf",
        )
        written += 1

    manifest = {
        "key": result.source.key,
        "unit": UNIT,
        "subject_code": SUBJECT_CODE,
        "year": result.source.year,
        "season": result.source.season,
        "source_qp": str(result.source.qp_path.relative_to(REPO_ROOT)),
        "source_ms": (
            str(result.source.ms_path.relative_to(REPO_ROOT))
            if result.source.ms_path
            else None
        ),
        "total_questions": len(result.questions),
        "total_marks": sum(q.marks for q in result.questions),
        "questions": [
            {
                "question_number": q.number,
                "marks": q.marks,
                "qp_pages": list(q.pages),
                "mark_source": q.mark_source,
                "ms_pages": None,
                "has_markscheme": False,
            }
            for q in result.questions
        ],
    }
    paper_dir.mkdir(parents=True, exist_ok=True)
    (paper_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return written


# ─────────────────────────────────────────────────────────────────────────────
# Audit -- the Phase 1 gate
# ─────────────────────────────────────────────────────────────────────────────


def audit_output() -> int:
    """
    Re-open every written segment and confirm it holds the question its
    filename claims, and only that question.

    Verify against the artifact, not against the script's own summary: both
    prior subjects shipped a pipeline that reported success while the output
    was wrong.
    """
    if not OUTPUT_DIR.exists():
        print(f"nothing to audit: {OUTPUT_DIR} does not exist")
        return 1

    manifests = sorted(OUTPUT_DIR.glob("*/manifest.json"))
    if not manifests:
        print(f"nothing to audit: no manifests under {OUTPUT_DIR}")
        return 1

    checked = mislabelled = bundled = unverifiable = 0

    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        paper_dir = manifest_path.parent

        for entry in manifest["questions"]:
            number = entry["question_number"]
            pdf_path = paper_dir / "questions" / f"q{number}.pdf"
            if not pdf_path.exists():
                print(f"  MISSING {manifest['key']} q{number}")
                unverifiable += 1
                continue

            checked += 1
            with fitz.open(pdf_path) as doc:
                owners: set[int] = set()
                opener: int | None = None
                for index, page in enumerate(doc):
                    for line in page_lines(page):
                        stripped = line.text.strip()
                        if line.x0 >= 80 or line.y0 >= 120:
                            continue
                        start = QUESTION_START_RE.match(stripped)
                        if start:
                            owners.add(int(start.group(1)))
                            if index == 0 and opener is None:
                                opener = int(start.group(1))
                        cont = QUESTION_CONT_RE.match(stripped)
                        if cont:
                            owners.add(int(cont.group(1)))

            if not owners:
                unverifiable += 1
                print(f"  UNVERIFIABLE {manifest['key']} q{number}: no page headers readable")
            elif opener is not None and opener != number:
                mislabelled += 1
                print(f"  MISLABELLED {manifest['key']} q{number}: opens with question {opener}")
            elif owners != {number}:
                bundled += 1
                print(
                    f"  BUNDLED {manifest['key']} q{number}: also carries "
                    f"{sorted(owners - {number})}"
                )

    print()
    print(f"audited {checked} segments across {len(manifests)} papers")
    print(f"  mislabelled : {mislabelled}")
    print(f"  bundled     : {bundled}")
    print(f"  unverifiable: {unverifiable}")
    gate_ok = not (mislabelled or bundled or unverifiable)
    print(f"\nGATE {'PASS' if gate_ok else 'FAIL'}")
    return 0 if gate_ok else 1


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="write the segment tree")
    parser.add_argument("--audit", action="store_true", help="re-verify written output")
    args = parser.parse_args()

    if args.audit:
        return audit_output()

    sources, notes = discover_papers()
    mode = "EXECUTE" if args.execute else "DRY RUN"
    print(f"=== P4 (WMA14) workbook segmentation  [{mode}] ===\n")
    for note in notes:
        print(f"  note: {note}")
    print(f"\n{len(sources)} unique in-scope papers to process\n")

    results = [process_paper(source) for source in sources]

    written = 0
    for result in sorted(results, key=lambda r: r.source.key):
        status = "OK  " if result.ok else "FAIL"
        marks = sum(q.marks for q in result.questions)
        print(
            f"  {status} {result.source.key:16s} "
            f"questions={len(result.questions):2d} marks={marks:3d}"
        )
        for problem in result.problems:
            print(f"         ! {problem}")
        if result.ok and args.execute:
            written += write_paper(result)

    good = [r for r in results if r.ok]
    total_questions = sum(len(r.questions) for r in good)
    sources_used: dict[str, int] = {}
    for result in good:
        for question in result.questions:
            sources_used[question.mark_source] = sources_used.get(question.mark_source, 0) + 1

    print()
    print(f"papers clean      : {len(good)}/{len(results)}")
    print(f"questions         : {total_questions}")
    print(f"mark provenance   : {sources_used}")
    if args.execute:
        print(f"segment PDFs      : {written} written to {OUTPUT_DIR}")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(
            {
                "unit": UNIT,
                "subject_code": SUBJECT_CODE,
                "mode": mode,
                "notes": notes,
                "papers_clean": len(good),
                "papers_total": len(results),
                "questions": total_questions,
                "mark_provenance": sources_used,
                "papers": [
                    {
                        "key": r.source.key,
                        "ok": r.ok,
                        "questions": len(r.questions),
                        "marks": sum(q.marks for q in r.questions),
                        "problems": r.problems,
                    }
                    for r in sorted(results, key=lambda r: r.source.key)
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"report            : {REPORT_PATH.relative_to(REPO_ROOT)}")

    if not args.execute:
        print("\nDry run only. Re-run with --execute to write, then --audit.")
    return 0 if len(good) == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
