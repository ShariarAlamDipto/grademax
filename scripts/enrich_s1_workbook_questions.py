#!/usr/bin/env python3
"""
Phase 2 for the IAL Statistics 1 (WST01) chapterwise workbook: turn the Phase 1
segments into classifier-ready question records.

    python scripts/enrich_s1_workbook_questions.py            # dry run
    python scripts/enrich_s1_workbook_questions.py --execute

Reads `data/workbook/s1/*/manifest.json`, writes
`data/workbook/s1_questions.json`. Nothing else is touched, and re-running is
safe: the file is rewritten from the manifests every time.

DIFFICULTY COMES FROM THE MARK TARIFF, NOT FROM A MODEL
-------------------------------------------------------
The 4PM1 build measured this directly: an LLM asked to rate difficulty returned
2 easy / 317 medium / 116 hard at a mean self-reported confidence of 0.93, which
is a model agreeing with itself rather than a signal. The mark tariff is printed
on the paper, costs nothing and correlates cleanly with how much work a question
is.

**The bands are S1's own and must not be copied from another subject.** Measured
over these 179 questions: mean 11.3, median 12, range 3-17. The 4PM1 bands
(easy <= 6) would call 12 of 179 questions easy; the 4MB1 bands (easy <= 3) would
call one. The cut points below are the most even three-way split of S1's actual
distribution.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.ial_qp_parse import (  # noqa: E402
    difficulty_for,
    extract_stem,
    extract_subparts,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SEGMENT_DIR = REPO_ROOT / "data" / "workbook" / "s1"
OUTPUT_PATH = REPO_ROOT / "data" / "workbook" / "s1_questions.json"

UNIT = "S1"
SUBJECT_CODE = "WST01"

#: Measured from this subject's own distribution (see the module docstring).
#: easy <= 10 | medium 11-12 | hard >= 13  ->  64 / 48 / 67  (35% / 26% / 37%)
EASY_MAX = 10
MEDIUM_MAX = 12

#: A stem shorter than this is not usable classifier input -- the question is
#: almost certainly carried by a figure or a table rather than by prose.
MIN_USABLE_STEM = 40

#: Residue from the +29 CMap repair and from Symbol-font glyphs. Their presence
#: means the text is readable but imperfect; the workbook prints the original
#: PDF pages, so this only ever affects classification.
_RESIDUE_RE = re.compile(r"[-]|\(\s*[a-z]\s*\)\s*=[a-z]")


def text_status(stem: str) -> str:
    """
    One of the three values the database CHECK constraint allows.

    Exactly three: 'ok', 'repaired', 'needs_vision'. The Maths B loader grew a
    fourth ('partially_garbled') and aborted 295 rows into a real load, minutes
    after a dry run reported success -- a dry run never attempts an insert, so
    it never meets a constraint.
    """
    if len(stem) < MIN_USABLE_STEM:
        return "needs_vision"
    if _RESIDUE_RE.search(stem):
        return "repaired"
    return "ok"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="write the JSON")
    args = parser.parse_args()

    manifests = sorted(SEGMENT_DIR.glob("*/manifest.json"))
    if not manifests:
        print(f"no manifests under {SEGMENT_DIR} -- run build_s1_workbook_segments.py --execute first")
        return 1

    mode = "EXECUTE" if args.execute else "DRY RUN"
    print(f"=== S1 ({SUBJECT_CODE}) enrichment  [{mode}] ===\n")

    records: list[dict] = []
    statuses: dict[str, int] = {}
    difficulties: dict[str, int] = {}
    subpart_verified = subpart_total = 0

    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        qp_path = REPO_ROOT / manifest["source_qp"]
        if not qp_path.exists():
            print(f"  !! missing source QP for {manifest['key']}: {qp_path}")
            continue

        print(f"  {manifest['key']:16s} {len(manifest['questions'])} questions", flush=True)
        with fitz.open(qp_path) as doc:
            for entry in manifest["questions"]:
                number = entry["question_number"]
                marks = entry["marks"]
                pages = (entry["qp_pages"][0], entry["qp_pages"][1])

                stem = extract_stem(doc, pages, number)
                parts = extract_subparts(doc, pages)
                status = text_status(stem)
                band = difficulty_for(marks, EASY_MAX, MEDIUM_MAX)

                # Sub-part marks are kept only when they reconcile with the
                # question total. Same verify-or-drop discipline as the marks
                # themselves: a wrong breakdown is worse than none.
                part_marks = [p.marks for p in parts]
                reconciled = bool(parts) and all(m is not None for m in part_marks) and sum(part_marks) == marks
                if parts:
                    subpart_total += 1
                    if reconciled:
                        subpart_verified += 1

                statuses[status] = statuses.get(status, 0) + 1
                difficulties[band] = difficulties.get(band, 0) + 1

                records.append(
                    {
                        "slug": f"{UNIT}.{manifest['key']}.Q{number:03d}",
                        "subject_code": SUBJECT_CODE,
                        "source_paper_key": manifest["key"],
                        "source_question_number": number,
                        "year": manifest["year"],
                        "season": manifest["season"],
                        "marks": marks,
                        "mark_source": entry["mark_source"],
                        "difficulty": band,
                        "qp_pages": list(pages),
                        "qp_pdf": f"s1/{manifest['key']}/questions/q{number}.pdf",
                        "stem": stem,
                        "stem_chars": len(stem),
                        "text_status": status,
                        "sub_parts": (
                            [{"label": p.label, "marks": p.marks} for p in parts]
                            if reconciled
                            else []
                        ),
                        "sub_parts_verified": reconciled,
                        "has_markscheme": entry["has_markscheme"],
                    }
                )

    total = len(records)
    print(f"questions         : {total}")
    print(f"difficulty        : {difficulties}")
    print(f"text status       : {statuses}")
    print(
        f"sub-parts         : {subpart_verified}/{subpart_total} reconciled "
        f"({subpart_verified * 100 // max(subpart_total, 1)}% of questions that print parts)"
    )
    usable = sum(v for k, v in statuses.items() if k != "needs_vision")
    print(f"usable for Phase 3: {usable}/{total} ({usable * 100 // max(total, 1)}%)")

    if args.execute:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = OUTPUT_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(OUTPUT_PATH)  # atomic: a half-written cache destroys the run
        print(f"\nwrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    else:
        print("\nDry run only. Re-run with --execute to write.")
        if records:
            sample = records[0]
            print(f"\nsample: {sample['slug']} marks={sample['marks']} "
                  f"{sample['difficulty']} parts={sample['sub_parts']}")
            print(f"  stem: {sample['stem'][:200]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
