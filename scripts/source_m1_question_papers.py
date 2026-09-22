"""Source clean Mechanics M1 question papers missing from the local archive.

Background
----------
The `data/processed/Mechanics_1/pages/` PDFs were built from PMT *Model Answer*
documents mislabelled as question papers. 10 of the 15 affected papers already
have clean QPs in `data/Ultimate Final IGCSE/Mechanics_1/`; the remaining 5 were
downloaded from Physics & Maths Tutor into a staging folder.

This script cleans those 5 staged downloads (redact every PMT watermark, stamp
GradeMax top-right — identical treatment to the existing clean QPs) and files
them into the IGCSE archive tree under the standard
`Mechanics_1_<year>_<season>_Paper_1_QP.pdf` naming.

Idempotent: re-running overwrites the output files with a freshly cleaned copy.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

REPO_ROOT = Path(__file__).resolve().parent.parent
STAGING = REPO_ROOT / "tmp_dl"
ARCHIVE = REPO_ROOT / "data" / "Ultimate Final IGCSE" / "Mechanics_1"

# staged filename -> (year, season_folder) in the archive tree
TARGETS: dict[str, tuple[str, str]] = {
    "2012_Jan.pdf": ("2012", "Jan"),
    "2012_Jun.pdf": ("2012", "May-Jun"),
    "2014_Jun.pdf": ("2014", "May-Jun"),
    "2016_Jun.pdf": ("2016", "May-Jun"),
    "2018_Specimen.pdf": ("2018", "Specimen"),
}

# Third-party marks to strip. Official Pearson/Edexcel text must survive.
PMT_RE = re.compile(r"physicsandmathstutor|pmt\.education|\bpmt\b", re.IGNORECASE)
URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
OFFICIAL_RE = re.compile(r"pearson|edexcel", re.IGNORECASE)
TOP_STRIP_PT = 42.0
BOTTOM_STRIP_PT = 30.0

# GradeMax stamp — same spec as scripts/ingest_cambridge_papers.py
GM_TEXT = "GradeMax"
GM_FONT = "tiro"        # Times-Roman builtin
GM_FONT_SIZE = 11.0
GM_RIGHT_MARGIN = 8.0
GM_BASELINE_Y = 14.0


def clean_and_stamp(pdf_bytes: bytes) -> tuple[bytes, int]:
    """Redact PMT watermarks + stamp GradeMax top-right on every page.

    Returns (out_bytes, redaction_count).
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    redactions = 0
    gm_width = fitz.get_text_length(GM_TEXT, fontname=GM_FONT, fontsize=GM_FONT_SIZE)

    for page in doc:
        text = page.get_text()
        page_redacted = False
        bottom_edge = page.rect.height - BOTTOM_STRIP_PT

        if PMT_RE.search(text) or URL_RE.search(text):
            for block in page.get_text("dict")["blocks"]:
                if block.get("type") != 0:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        span_text = span.get("text", "")
                        if not span_text.strip():
                            continue
                        bbox = fitz.Rect(span["bbox"])
                        in_strip = bbox.y1 <= TOP_STRIP_PT or bbox.y0 >= bottom_edge
                        is_pmt = bool(PMT_RE.search(span_text))
                        is_strip_url = (
                            in_strip
                            and URL_RE.search(span_text)
                            and not OFFICIAL_RE.search(span_text)
                            and "grademax" not in span_text.lower()
                        )
                        if is_pmt or is_strip_url:
                            page.add_redact_annot(bbox, fill=(1, 1, 1))
                            redactions += 1
                            page_redacted = True

        if page_redacted:
            # graphics=NONE: a text redaction must never pull out nearby line art
            page.apply_redactions(graphics=fitz.PDF_REDACT_LINE_ART_NONE)

        if "grademax" not in text.lower():
            x = page.rect.width - gm_width - GM_RIGHT_MARGIN
            page.insert_text(
                (x, GM_BASELINE_Y), GM_TEXT,
                fontname=GM_FONT, fontsize=GM_FONT_SIZE, color=(0, 0, 0),
                overlay=True,
            )

    out = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    return out, redactions


def verify(pdf_bytes: bytes) -> tuple[bool, bool]:
    """Return (pmt_gone, grademax_present) from the cleaned bytes."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full = " ".join(p.get_text() for p in doc)
    doc.close()
    return (PMT_RE.search(full) is None, "grademax" in full.lower())


def main() -> int:
    if not STAGING.exists():
        print(f"ERROR: staging folder missing: {STAGING}", file=sys.stderr)
        return 1

    failures = 0
    for staged_name, (year, season) in TARGETS.items():
        src = STAGING / staged_name
        if not src.exists():
            print(f"MISSING staged download: {src}")
            failures += 1
            continue

        cleaned, n_redactions = clean_and_stamp(src.read_bytes())
        pmt_gone, gm_present = verify(cleaned)

        out_dir = ARCHIVE / year / season
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"Mechanics_1_{year}_{season}_Paper_1_QP.pdf"
        out_path.write_bytes(cleaned)

        flag = "OK" if (pmt_gone and gm_present) else "CHECK"
        if not (pmt_gone and gm_present):
            failures += 1
        rel = out_path.relative_to(REPO_ROOT)
        print(
            f"[{flag}] {staged_name:18} -> {rel}  "
            f"(redactions={n_redactions}, pmt_gone={pmt_gone}, grademax={gm_present})"
        )

    print(f"\nDone. {len(TARGETS) - failures}/{len(TARGETS)} clean and stamped.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
