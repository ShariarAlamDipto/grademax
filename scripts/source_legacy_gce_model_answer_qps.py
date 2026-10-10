#!/usr/bin/env python3
"""Source clean question papers for the two remaining Model-Answer slots.

The 2026-09-21 audit found two `*_QP.pdf` files in
`data/Ultimate Final IAL/Mathematics` that are still PMT Model Answers and, unlike
the other 164, have no clean replacement anywhere in the archive:

  * Mathematics_D1_2015_May-Jun_QP.pdf  -- pencil handwritten solutions
  * Mathematics_P2_2017_May-Jun_QP.pdf  -- red-ink solutions over a genuine paper

Both slots are LEGACY UK GCE papers, not IAL -- their own mark schemes say
"Decision Mathematics 1 (6689/01)" and "Core Mathematics 2 (6664/01)".  So the
replacements come from PMT's legacy `Papers-Edexcel` tree, NOT the Edexcel-IAL tree.
(Deriving the unit from the slot's own mark scheme is the rule; the archive's
P1..P4 labels mean different units in different eras.)

The download is cleaned of PMT watermarks and stamped GradeMax exactly like every
other paper in the archive, then verified with the audit's detector.  Files are
written to a STAGING folder for review -- this script never touches the archive
or R2.

Usage:
    python -X utf8 scripts/source_legacy_gce_model_answer_qps.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import fitz  # PyMuPDF
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from source_m1_question_papers import PMT_RE, clean_and_stamp  # noqa: E402

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}

STAGING = REPO_ROOT / "data" / "staging" / "legacy_gce_qp_replacements"
PMT_LEGACY = "https://pmt.physicsandmathstutor.com/download/Maths/A-level/{unit}/Papers-Edexcel/QP/{month} {year} QP.pdf"

TARGETS = [
    {
        "name": "Mathematics_D1_2015_May-Jun_QP.pdf",
        "unit": "D1", "month": "June", "year": "2015",
        "expect_code": "6689",
        "archive_slot": "data/Ultimate Final IAL/Mathematics/2015/May-Jun",
        "r2_key": "ial/decision-mathematics-1/2015/may-jun/Mathematics_D1_2015_May-Jun_QP.pdf",
    },
    {
        "name": "Mathematics_P2_2017_May-Jun_QP.pdf",
        "unit": "C2", "month": "June", "year": "2017",
        "expect_code": "6664",
        "archive_slot": "data/Ultimate Final IAL/Mathematics/2017/May-Jun",
        "r2_key": "ial/pure-mathematics-2/2017/may-jun/Mathematics_P2_2017_May-Jun_QP.pdf",
    },
]


def is_clean_question_paper(data: bytes) -> tuple[bool, str]:
    """The validated 2026-09-21 rule: a Model Answer is a full-page raster scan of
    handwriting or coloured pen ink; a genuine paper is neither."""
    doc = fitz.open(stream=data, filetype="pdf")
    n = doc.page_count
    idx = list(range(n))[2:10] or list(range(n))[:8]
    big = col_ops = tot_ops = 0
    for i in idx:
        pg = doc[i]
        area = max(pg.rect.width * pg.rect.height, 1)
        for im in pg.get_images(full=True):
            try:
                r = pg.get_image_rects(im[0])
            except Exception:
                continue
            if r and (r[0].width * r[0].height) / area > 0.55:
                big += 1
                break
        try:
            for d in pg.get_drawings():
                c = d.get("color") or d.get("fill")
                if not c:
                    continue
                tot_ops += 1
                if max(c) - min(c) > 0.15:
                    col_ops += 1
        except Exception:
            pass
    doc.close()
    raster = big / max(len(idx), 1)
    colf = col_ops / max(tot_ops, 1)
    if raster >= 0.8:
        return False, f"full-page raster scan ({raster:.2f}) - still a Model Answer"
    if colf >= 0.20:
        return False, f"coloured pen ink ({colf:.2f}) - still a Model Answer"
    return True, f"clean (raster={raster:.2f} colour_ink={colf:.2f})"


def main() -> int:
    STAGING.mkdir(parents=True, exist_ok=True)
    failures = 0

    for t in TARGETS:
        url = PMT_LEGACY.format(unit=t["unit"], month=t["month"], year=t["year"])
        print(f"\n=== {t['name']}  (legacy {t['unit']}, code {t['expect_code']}) ===")
        print(f"  GET {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60)
        except Exception as exc:
            print(f"  [FAIL] download error: {exc}")
            failures += 1
            continue
        if resp.status_code != 200 or not resp.content.startswith(b"%PDF"):
            print(f"  [FAIL] HTTP {resp.status_code}, {len(resp.content)} bytes - not a PDF")
            failures += 1
            continue

        raw = resp.content
        doc = fitz.open(stream=raw, filetype="pdf")
        head = " ".join(doc[i].get_text() for i in range(min(3, doc.page_count)))
        doc.close()
        if t["expect_code"] not in head:
            print(f"  [WARN] paper code {t['expect_code']} not found on the first pages "
                  f"- verify this is the right unit before using it")

        cleaned, redactions = clean_and_stamp(raw)
        ok, why = is_clean_question_paper(cleaned)
        gone = PMT_RE.search(" ".join(
            p.get_text() for p in fitz.open(stream=cleaned, filetype="pdf"))) is None

        out = STAGING / t["name"]
        out.write_bytes(cleaned)
        flag = "OK" if (ok and gone) else "CHECK"
        print(f"  [{flag}] -> {out.relative_to(REPO_ROOT)}")
        print(f"         {why}; pmt_watermark_gone={gone}, redactions={redactions}")
        print(f"         archive slot : {t['archive_slot']}")
        print(f"         live R2 key  : {t['r2_key']}")
        if not (ok and gone):
            failures += 1

    print(f"\nStaged in {STAGING.relative_to(REPO_ROOT)}. "
          f"Nothing was written to the archive or R2.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
