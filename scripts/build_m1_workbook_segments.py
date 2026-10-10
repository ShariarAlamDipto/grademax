#!/usr/bin/env python3
"""
Phase 1 for the IAL Mechanics 1 (WME01) chapterwise workbook: cut every question
paper into one PDF per question, and attach each question's mark scheme.

    python scripts/build_m1_workbook_segments.py            # dry run
    python scripts/build_m1_workbook_segments.py --execute  # write the tree
    python scripts/build_m1_workbook_segments.py --audit    # re-verify output

A copy of the S1 segmenter, per the one-script-per-subject rule. M1 is an IAL
unit set on the same page format (every page names its owner: "1." to start a
question, "Question 1 continued" after), so the shared `lib/ial_qp_parse`
reads it unchanged.

Sources: data/workbook/ial_sources/m1/ -- January 2019 to June 2026, each paper
checked against its own cover (collect_m1_chapterwise_sources.py). The M1
yearwise book's source audit already proved the archive's June 2023 slot held
January 2023's paper and that October 2019 was missing; the collector uses that
audit's verified files.
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

from lib.ial_chapterwise_build import (  # noqa: E402
    attach_markschemes,
    source_papers,
    write_slice,
)
from lib.ial_qp_parse import (  # noqa: E402
    RECOVERY_PREFIX,
    QUESTION_CONT_RE,
    QUESTION_START_RE,
    build_questions,
    content_fingerprint,
    page_lines,
    read_paper,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT / "data" / "Ultimate Final IAL" / "Mathematics"
OUTPUT_DIR = REPO_ROOT / "data" / "workbook" / "m1"
REPORT_PATH = REPO_ROOT / "data" / "workbook" / "m1_segmentation_report.json"

UNIT = "M1"
PAPER_TOTAL_MARKS = 75

#: Papers held out, with the reason. Nothing is dropped silently.
EXCLUDED_PAPERS: dict[str, str] = {}

#: Page ranges read off a rendered contact sheet, for papers whose text layer
#: cannot be parsed at all. `{paper_key: {question: (start, end, marks)}}`.
#: Empty today -- the hook exists so the specimen can be added without touching
#: any logic.
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
    key: str  # '2019_jan'
    year: int
    season: str
    qp_path: Path
    ms_path: Path | None


@dataclass
class PaperResult:
    source: PaperSource
    questions: list = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    skipped_reason: str | None = None

    @property
    def defects(self) -> list[str]:
        """Problems that are genuinely wrong, excluding successful recoveries."""
        return [p for p in self.problems if not p.startswith(RECOVERY_PREFIX)]

    @property
    def recoveries(self) -> list[str]:
        return [p for p in self.problems if p.startswith(RECOVERY_PREFIX)]

    @property
    def ok(self) -> bool:
        return not self.defects and self.skipped_reason is None


# ─────────────────────────────────────────────────────────────────────────────
# Discovery
# ─────────────────────────────────────────────────────────────────────────────


def discover_papers() -> tuple[list[PaperSource], list[str]]:
    """
    The unit's VERIFIED sittings, from data/workbook/ial_sources/<unit>/.

    Since 2026-10-06 papers come from the folder lib/ial_chapterwise_sources.py
    assembles -- every question paper and mark scheme checked against its own
    printed identity, the archive's wrong files replaced, duplicates refused.
    The content-fingerprint duplicate check is kept as a second guard.
    """
    notes: list[str] = []
    unique: list[PaperSource] = []
    seen: dict[str, str] = {}
    for row in source_papers(UNIT):
        if row["key"] in EXCLUDED_PAPERS:
            notes.append(f"excluded {row['key']}: {EXCLUDED_PAPERS[row['key']]}")
            continue
        fingerprint = content_fingerprint(row["qp"])
        if fingerprint in seen:
            notes.append(f"duplicate: {row['key']} is the same paper as {seen[fingerprint]}")
            continue
        seen[fingerprint] = row["key"]
        unique.append(PaperSource(key=row["key"], year=row["year"], season=row["season"],
                                  qp_path=row["qp"], ms_path=row["ms"]))
    return unique, notes


# ─────────────────────────────────────────────────────────────────────────────
# Processing
# ─────────────────────────────────────────────────────────────────────────────


def process_paper(source: PaperSource) -> PaperResult:
    facts = read_paper(source.qp_path)
    questions, problems = build_questions(facts, PAPER_TOTAL_MARKS)
    return PaperResult(source=source, questions=questions, problems=problems)


def extract_range(source_pdf: Path, page_range: tuple[int, int], target: Path) -> None:
    """Write pages [start, end] of `source_pdf` to `target` as a new PDF."""
    start, end = page_range
    target.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(source_pdf) as src:
        out = fitz.open()
        try:
            out.insert_pdf(src, from_page=start, to_page=end)
            out.save(target)
        finally:
            out.close()


def write_paper(result: PaperResult) -> tuple[int, dict[str, int]]:
    paper_dir = OUTPUT_DIR / result.source.key
    written = 0
    for question in result.questions:
        extract_range(
            result.source.qp_path,
            question.pages,
            paper_dir / "questions" / f"q{question.number}.pdf",
        )
        written += 1

    # Mark schemes are attached ONLY where their marks reconcile with the
    # question paper's. A question with no entry here gets no mark scheme file
    # and `has_markscheme: false` -- a blank slot a student can act on, rather
    # than another question's scheme presented as this one's.
    blocks: dict = {}
    ms_stats: dict[str, int] = {}
    if result.source.ms_path is not None:
        expected = {q.number: q.marks for q in result.questions}
        blocks = attach_markschemes(result.source.ms_path, expected)
        for number, part in blocks.items():
            write_slice(result.source.ms_path, part,
                        paper_dir / "markschemes" / f"q{number}.pdf")
            ms_stats[part.route] = ms_stats.get(part.route, 0) + 1
            written += 1

    manifest = {
        "key": result.source.key,
        "markscheme_stats": ms_stats,
        "unit": UNIT,
        "subject_code": "WME01",
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
                "ms_pages": (
                    list(blocks[q.number].pages) if q.number in blocks else None
                ),
                "ms_band": (
                    [blocks[q.number].top, blocks[q.number].bottom]
                    if q.number in blocks else None
                ),
                "ms_extractor": (
                    blocks[q.number].route if q.number in blocks else None
                ),
                "has_markscheme": q.number in blocks,
            }
            for q in result.questions
        ],
    }
    paper_dir.mkdir(parents=True, exist_ok=True)
    (paper_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return written, ms_stats


# ─────────────────────────────────────────────────────────────────────────────
# Audit -- the Phase 1 gate
# ─────────────────────────────────────────────────────────────────────────────


def audit_output() -> int:
    """
    Re-open every written segment and confirm it holds the question its
    filename claims, and only that question.

    This exists because both prior subjects shipped a pipeline that reported
    success while the output was wrong -- Maths B's crop offset produced 137
    silently mislabelled segments that every in-process check passed. Verify
    against the artifact, not against the script's own summary.
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
    print(f"=== M1 (WME01) workbook segmentation  [{mode}] ===\n")
    for note in notes:
        print(f"  note: {note}")
    print(f"\n{len(sources)} unique papers to process\n")

    results = [process_paper(source) for source in sources]

    written = 0
    ms_totals: dict[str, int] = {}
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
            count, stats = write_paper(result)
            written += count
            for key, value in stats.items():
                ms_totals[key] = ms_totals.get(key, 0) + value

    good = [r for r in results if r.ok]
    total_questions = sum(len(r.questions) for r in good)
    sources_used: dict[str, int] = {}
    for result in good:
        for question in result.questions:
            sources_used[question.mark_source] = sources_used.get(question.mark_source, 0) + 1

    print()
    recovered = sum(len(r.recoveries) for r in results)
    print(f"papers clean      : {len(good)}/{len(results)}")
    if recovered:
        print(f"recovered bounds  : {recovered} (printed evidence, not inferred)")
    print(f"questions         : {total_questions}")
    print(f"mark provenance   : {sources_used}")
    if args.execute:
        print(f"segment PDFs      : {written} written to {OUTPUT_DIR}")
        attached = sum(v for k, v in ms_totals.items() if k != "rejected")
        print(
            f"mark schemes      : {attached}/{total_questions} attached "
            f"({attached * 100 // max(total_questions, 1)}%), "
            f"{ms_totals.get('rejected', 0)} dropped as unreconciled  {ms_totals}"
        )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(
            {
                "unit": UNIT,
                "subject_code": "WME01",
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
