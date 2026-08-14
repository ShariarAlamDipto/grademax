"""Re-segment every Mechanics M1 paper from the clean question papers.

The original `data/processed/Mechanics_1/` was segmented from PMT Model-Answer
PDFs (see project memory) and is broken on two axes: the "question papers" are
handwritten model answers, and nearly every paper assigned the whole document to
every question. This rebuilds the per-question QP + MS splits from the clean
sources using the patched M1Processor (table-based MS linking).

Sources per paper (first that exists wins):
  - 2012-2019: data/Ultimate Final IGCSE/Mechanics_1/<year>/<season>/Mechanics_1_..._Paper_1_{QP,MS}.pdf
  - 2020-2024: data/Ultimate Final IAL/Mathematics/<year>/<season>/Mathematics_M1_..._{QP,MS}.pdf

Output goes to a FRESH directory (data/processed/Mechanics_1_resegmented/) so the
live data is untouched until the new output is verified and promoted.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from m1_hardened_segmentation import M1Processor

REPO = Path(__file__).resolve().parent.parent
IGCSE = REPO / "data" / "Ultimate Final IGCSE" / "Mechanics_1"
IAL = REPO / "data" / "Ultimate Final IAL" / "Mathematics"
PROCESSED = REPO / "data" / "processed" / "Mechanics_1"
OUT = REPO / "data" / "processed" / "Mechanics_1_resegmented"

SEASON_FOLDER = {"Jan": "Jan", "Jun": "May-Jun", "Oct": "Oct-Nov", "Specimen": "Specimen"}

# Manual page ranges (0-indexed) for papers whose PDFs use a shifted subset font
# that extracts as garbage, defeating text-based detection. Ranges read off the
# rendered pages. When present, these override the segmenter entirely.
MANUAL_OVERRIDES: dict[tuple[str, str], dict] = {
    ("2014", "Jun"): {
        "qp": {1: [1], 2: [2], 3: [3, 4], 4: [5, 6], 5: [7, 8], 6: [9, 10], 7: [11, 12]},
        "ms": {1: [6], 2: [7], 3: [8], 4: [9], 5: [10, 11], 6: [12, 13], 7: [14, 15]},
    },
    ("2018", "Specimen"): {
        "qp": {1: [1, 2], 2: [3, 4], 3: [5, 6], 4: [7, 8, 9, 10],
               5: [11, 12, 13, 14], 6: [15, 16, 17, 18],
               7: [19, 20, 21, 22], 8: [23, 24, 25, 26, 27]},
        "ms": {1: [0], 2: [0], 3: [0], 4: [1], 5: [1], 6: [2], 7: [2], 8: [3]},
    },
}


def sources(year: str, season: str) -> tuple[Path | None, Path | None]:
    sf = SEASON_FOLDER[season]
    candidates = {
        "qp": [
            IGCSE / year / sf / f"Mechanics_1_{year}_{sf}_Paper_1_QP.pdf",
            IAL / year / sf / f"Mathematics_M1_{year}_{sf}_QP.pdf",
        ],
        "ms": [
            IGCSE / year / sf / f"Mechanics_1_{year}_{sf}_Paper_1_MS.pdf",
            IAL / year / sf / f"Mathematics_M1_{year}_{sf}_MS.pdf",
        ],
    }
    qp = next((p for p in candidates["qp"] if p.exists()), None)
    ms = next((p for p in candidates["ms"] if p.exists()), None)
    return qp, ms


def papers_to_process() -> list[tuple[str, str]]:
    out = []
    for f in sorted(glob.glob(str(PROCESSED / "*_segmented.json"))):
        m = re.match(r"(\d{4})_(\w+?)_P1", os.path.basename(f))
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    proc = M1Processor()
    summary = []

    for year, season in papers_to_process():
        qp, ms = sources(year, season)
        if not qp or not ms:
            summary.append((f"{year}_{season}", "SKIP", f"missing {'QP' if not qp else ''}{'MS' if not ms else ''}"))
            continue

        try:
            override = MANUAL_OVERRIDES.get((year, season))
            if override:
                qnums = sorted(override["qp"])
                result = {
                    "subject_code": "WME01",
                    "paper": {"year": int(year), "season": season, "paper_number": "P1"},
                    "questions": [
                        {"qnum": q, "qp_pages": override["qp"][q],
                         "ms_pages": override.get("ms", {}).get(q, []),
                         "marks_ms": None, "marks_meta": {"mode": "manual_override"}}
                        for q in qnums
                    ],
                    "metrics": {"question_count": len(qnums), "source": "manual_override"},
                }
            else:
                result = proc.process_paper(str(qp), str(ms), int(year), season, "P1")
            if "error" in result:
                summary.append((f"{year}_{season}", "ERROR", result["error"]))
                continue

            (OUT / f"{year}_{season}_P1_segmented.json").write_text(
                json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            proc.extract_question_pdfs(str(qp), str(ms), result["questions"], OUT, int(year), season, "P1")

            qs = result["questions"]
            ms_linked = sum(1 for q in qs if q.get("ms_pages"))
            summary.append((f"{year}_{season}", "OK", f"{len(qs)}q, MS {ms_linked}/{len(qs)}"))
        except Exception as e:  # noqa: BLE001 - report and continue the batch
            summary.append((f"{year}_{season}", "ERROR", str(e)[:120]))

    print("\n" + "=" * 60)
    print("RE-SEGMENTATION SUMMARY")
    print("=" * 60)
    ok = 0
    for name, status, detail in summary:
        print(f"[{status:5}] {name:14} {detail}")
        ok += status == "OK"
    print(f"\n{ok}/{len(summary)} papers re-segmented -> {OUT.relative_to(REPO)}")
    return 0 if ok == len(summary) else 1


if __name__ == "__main__":
    raise SystemExit(main())
