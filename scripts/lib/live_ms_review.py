"""
Human (Claude) review of question <-> mark-scheme pairs that text alone cannot
prove: render both side by side, read them, record the decision.

    data/analysis/live_rebuild/<CODE>/manual_review.json

    {
      "2019_may-jun_P2|4": {
        "decision": "CONFIRMED" | "REJECTED",
        "reason": "scheme opens 4(a)(i) 'kinetic energy store' = QP 4(a)(i)",
        "ms_pages": [7, 8]          # optional: whole source-MS pages to use instead
      }
    }

A CONFIRMED entry is the worked-solutions method applied to linkage: the pair
was read together and the scheme answers this question's parts. Nothing is
CONFIRMED by default; every entry carries its reason.
"""

from __future__ import annotations

import json
from pathlib import Path

import fitz

GAP = 12


def load_decisions(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def render_pair(qp_pdf: Path, ms_pdf: Path | None, out_png: Path, *, dpi: int = 55,
                max_pages: int = 3) -> Path:
    """Question pages stacked on the left, scheme pages on the right."""
    def column(pdf: Path | None) -> list[fitz.Pixmap]:
        if pdf is None or not pdf.is_file():
            return []
        with fitz.open(pdf) as doc:
            return [doc[i].get_pixmap(dpi=dpi) for i in range(min(doc.page_count, max_pages))]

    left, right = column(qp_pdf), column(ms_pdf)
    width_l = max((p.width for p in left), default=0)
    width_r = max((p.width for p in right), default=0)
    height = max(sum(p.height + GAP for p in left), sum(p.height + GAP for p in right), 10)
    canvas = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, width_l + GAP + width_r, height), False)
    canvas.clear_with(255)
    for pixes, x in ((left, 0), (right, width_l + GAP)):
        y = 0
        for pix in pixes:
            if pix.alpha:
                pix = fitz.Pixmap(pix, 0)
            if pix.colorspace != fitz.csRGB:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            pix.set_origin(x, y)
            canvas.copy(pix, pix.irect)
            y += pix.height + GAP
    out_png.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_png)
    return out_png
