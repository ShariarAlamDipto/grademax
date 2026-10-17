#!/usr/bin/env python3
"""
Find live question / mark-scheme cuts that show content the original paper
keeps hidden (a red graph-paper grid, a large diagonal "...Paper" watermark):
show_pdf_page copies a page region without the source's optional-content
visibility, so hidden layers appear in the cut.

    python -X utf8 scripts/audit_tool_cut_overlays.py

Signal: share of strongly saturated red pixels in the cut (exam papers are
black on white; the hidden grid is pure red). Each flagged cut is compared
with the same paper page rendered normally, so a genuinely red figure in the
paper is not reported. Writes data/analysis/tool_cut_overlays.json.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import fitz
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.live_paper_sources import ROOT  # noqa: E402

CODES = ["4PH1", "4MB1", "4PM1", "4CH1", "4BI1", "4HB1",
         "WME01", "WMA11", "WMA12", "WMA13", "WMA14", "WST01"]
PUBLISHABLE = {"PROVEN", "SEQUENCE_PROVEN", "LABEL_PROVEN", "MANUAL_PROVEN", "REVIEWED_PROVEN"}
RED_MIN = 0.004  # share of pixels; the grid covers ~5-20% of a cut
OUT = ROOT / "data" / "analysis" / "tool_cut_overlays.json"


def red_share(pdf: Path) -> float:
    worst = 0.0
    with fitz.open(pdf) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=30, colorspace=fitz.csRGB, alpha=False)
            a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3).astype(int)
            red = (a[..., 0] > 180) & (a[..., 1] < 140) & (a[..., 2] < 140)
            worst = max(worst, float(red.mean()))
    return worst


def main() -> int:
    flagged, counts = [], Counter()
    for code in CODES:
        rows = json.loads((ROOT / "data/analysis/live_rebuild" / code / "verdicts.json").read_text(encoding="utf-8"))["rows"]
        for r in rows:
            if r["verdict"] not in PUBLISHABLE:
                continue
            for kind in ("qp", "ms"):
                f = r.get(kind)
                if not f or not (ROOT / f).is_file():
                    continue
                share = red_share(ROOT / f)
                if share >= RED_MIN:
                    src = ROOT / "data/analysis/live_rebuild" / code / "sources" / f"{r['live_key']}_{kind}.pdf"
                    src_share = red_share(src) if src.is_file() else None
                    flagged.append({"code": code, "paper": r["live_key"], "question": r["question"],
                                    "kind": kind, "cut_red": round(share, 4),
                                    "source_red": None if src_share is None else round(src_share, 4)})
                    counts[(code, kind)] += 1
        print(f"{code}: flagged {sum(v for (c, _), v in counts.items() if c == code)}")
    OUT.write_text(json.dumps(flagged, indent=1), encoding="utf-8")
    print(f"total flagged cuts: {len(flagged)} -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
