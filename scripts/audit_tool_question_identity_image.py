#!/usr/bin/env python3
"""
Third identity proof, for the short questions the word test cannot decide
(audit_tool_question_identity_source.py: NOT_FROM_SOURCE / CUT_UNREADABLE --
mostly 2-mark questions with a handful of words).

    python -X utf8 scripts/audit_tool_question_identity_image.py

Every live question cut is a literal crop of one page of the question paper it
came from. So its image must be found, pixel for pixel, on a page of that
paper: the cut's first page is template-matched (OpenCV normalised
cross-correlation, grayscale, same resolution) against every page of the
source paper. MATCH_MIN = 0.90 means the crop is that paper's printed content.
The source paper's sitting is then the one already proven for it (cover or
its own mark scheme), recorded in tool_identity_source.json.

Writes data/analysis/tool_identity_image.json. Read-only otherwise.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import cv2
import fitz
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_tool_question_identity_source as src_audit  # noqa: E402
from lib.live_paper_sources import ROOT  # noqa: E402

IN = ROOT / "data" / "analysis" / "tool_identity_source.json"
OUT = ROOT / "data" / "analysis" / "tool_identity_image.json"
DPI = 60
MATCH_MIN = 0.90
UNDECIDED = {"NOT_FROM_SOURCE", "CUT_UNREADABLE"}


def gray(page: fitz.Page) -> np.ndarray:
    pix = page.get_pixmap(dpi=DPI, colorspace=fitz.csGRAY, alpha=False)
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)


def best_match(cut_pdf: Path, source_pdf: Path) -> tuple[float, int]:
    with fitz.open(cut_pdf) as cut:
        tpl = gray(cut[0])
    # trim our stamp band and blank margins so only printed content is matched
    rows = np.where(tpl.min(axis=1) < 200)[0]
    cols = np.where(tpl.min(axis=0) < 200)[0]
    if rows.size == 0 or cols.size == 0:
        return 0.0, -1
    tpl = tpl[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
    best, where = 0.0, -1
    with fitz.open(source_pdf) as doc:
        for i, page in enumerate(doc):
            img = gray(page)
            if img.shape[0] < tpl.shape[0] or img.shape[1] < tpl.shape[1]:
                continue
            score = float(cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED).max())
            if score > best:
                best, where = score, i
    return best, where


def main() -> int:
    rows = json.loads(IN.read_text(encoding="utf-8"))
    results, counts = [], Counter()
    for rec in rows:
        if rec["source_verdict"] not in UNDECIDED:
            continue
        code, live_key = rec["code"], rec["live_key"]
        verdicts = json.loads((src_audit.base.REBUILD / code / "verdicts.json").read_text(encoding="utf-8"))
        staged = next((r for r in verdicts["rows"] if r["live_key"] == live_key
                       and str(r["question"]) == str(rec["question"])), None)
        source = ROOT / rec["source"] if rec.get("source") else None
        out = {k: rec[k] for k in ("code", "year", "season", "paper", "question", "live_key")}
        if staged is None or source is None or not source.is_file():
            out["image_verdict"] = "NO_SOURCE"
        else:
            # match against the original paper too (cuts of scrambled papers come from the copy)
            cands = [source] + [p for p in source.parent.glob(f"{live_key}_qp*.pdf") if p != source]
            score, page, used = 0.0, -1, None
            for cand in cands:
                s, pg = best_match(ROOT / staged["qp"], cand)
                if s > score:
                    score, page, used = s, pg, cand
            out.update(score=round(score, 3), page=page + 1, matched=str(used.relative_to(ROOT)) if used else None)
            out["image_verdict"] = "IMAGE_PROVEN" if score >= MATCH_MIN else "IMAGE_UNMATCHED"
        counts[out["image_verdict"]] += 1
        results.append(out)
        print(f"{code} {live_key} q{rec['question']}: {out['image_verdict']} {out.get('score')}")
    OUT.write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(f"\n{dict(counts)}\nreport -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
