#!/usr/bin/env python3
"""Replace mislabelled IAL Maths/Further-Maths "QP" files that are actually PMT
Model Answers with the genuine question papers.

Background
----------
`data/Ultimate Final IAL/Mathematics` and `.../Further_Mathematics` were built by
scraping PMT's `/Edexcel-IAL/<Category>/<Unit>/MA/` (Model Answers) folder instead
of the sibling `/QP/` folder. 165 files named `*_QP.pdf` therefore contain
handwritten worked solutions rather than question papers. Years 2020+ are clean.

Audit that produced the file list:
    data/analysis/edexcel_ial_maths_QP_audit.csv   (verdict == MODEL_ANSWER)

What this script does, per contaminated file
--------------------------------------------
1. Download the matching genuine paper from PMT's `/QP/` folder.
2. Gate on page-1 verification: the download must look like a real question paper
   (Edexcel barcode paper-code text on several pages) and must NOT be handwritten.
   Anything that fails is skipped -- we never overwrite with an unverified file.
3. Redact PMT watermarks, stamp GradeMax (identical treatment to the clean papers
   already in the archive).
4. Move the old Model Answer into `data/quarantine/ial_maths_model_answers/`
   (it is still useful content, just wrongly named) and write the clean QP in place.

Dry-run by default; pass --commit to write.

Usage:
    python -X utf8 scripts/fix_ial_maths_model_answer_qps.py            # dry-run
    python -X utf8 scripts/fix_ial_maths_model_answer_qps.py --commit
    python -X utf8 scripts/fix_ial_maths_model_answer_qps.py --commit --limit 5
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
import time
from pathlib import Path

import fitz  # PyMuPDF
import requests

sys.path.insert(0, str(Path(__file__).parent))
from source_m1_question_papers import PMT_RE, clean_and_stamp, verify  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_CSV = REPO_ROOT / "data" / "analysis" / "edexcel_ial_maths_QP_audit.csv"
MAPPING_CSV = REPO_ROOT / "data" / "analysis" / "ial_maths_qp_fix_mapping.csv"
QUARANTINE = REPO_ROOT / "data" / "quarantine" / "ial_maths_model_answers"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}
REQUEST_DELAY_S = 1.0  # be polite to PMT

# Edexcel barcode paper-code, e.g. P54829A0124 -- present on genuine QPs only.
BARCODE_RE = re.compile(r"\b[PW]\d{4,6}[A-Z]\d{2,4}\b")
MIN_BARCODE_PAGES = 3
MAX_FULLPAGE_IMAGE_RATIO = 0.5  # above this the doc is a scan (handwriting)
MIN_AVG_TEXT = 800  # genuine typed QPs run 1300+ chars/page; MA scans run <150

SEASON_MONTHS = {
    "Jan": ("january", "february"),
    "May-Jun": ("may", "june"),
    "Oct-Nov": ("october", "november"),
    "Specimen": ("specimen", "sample"),
}


def looks_like_question_paper(
    pdf_bytes: bytes, expect_year: str, expect_season: str, trusted: bool = False
) -> tuple[bool, str]:
    """Gate a download before it is allowed to replace an archive file.

    Three independent checks:
      * not a scan   -- PMT Model Answers are full-page raster handwriting
      * real content -- barcode paper-code text, or a genuine typed text layer
      * right paper  -- the year/session on the page must match what we expect,
                        so a mis-mapped URL can never overwrite another session
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        return False, f"unreadable pdf ({type(exc).__name__})"

    try:
        n_pages = doc.page_count
        if n_pages < 3:
            return False, f"only {n_pages} pages"

        barcode_pages = 0
        fullpage_image_pages = 0
        total_chars = 0
        head_text = ""
        for i, page in enumerate(doc):
            text = page.get_text("text")
            total_chars += len(text.strip())
            if i < 2:
                head_text += " " + text
            if BARCODE_RE.search(text):
                barcode_pages += 1
            page_area = abs(page.rect.width * page.rect.height) or 1.0
            for img in page.get_images(full=True):
                if any(
                    abs(r.width * r.height) / page_area > 0.55
                    for r in page.get_image_rects(img[0])
                ):
                    fullpage_image_pages += 1
                    break
    finally:
        doc.close()

    scan_ratio = fullpage_image_pages / n_pages
    avg_text = total_chars / n_pages
    if scan_ratio > MAX_FULLPAGE_IMAGE_RATIO:
        return False, f"looks scanned/handwritten ({scan_ratio:.0%} full-page images)"
    if barcode_pages < MIN_BARCODE_PAGES and avg_text < MIN_AVG_TEXT:
        # `trusted` rows come from the official Pearson CDN with a `_que_` (question
        # paper) filename and have been visually confirmed. Some of those are drawn
        # as vector outlines with no text layer at all, so the text/barcode proxy
        # cannot see them. The scan/handwriting check above still applies.
        if not trusted:
            return False, f"no barcode ({barcode_pages}p) and thin text ({avg_text:.0f} ch/pg)"
        note_trust = " [trusted source]"
    else:
        note_trust = ""

    # Session gate. Reject only on POSITIVE evidence of a mismatch: some PMT PDFs
    # use fonts with no usable ToUnicode map, so their text extracts as garbage and
    # absence of the year proves nothing. The URL already comes from PMT's own
    # per-unit/per-session catalog, so it is the authority when text is unreadable.
    flat = " ".join(head_text.lower().split())
    note = ""
    if expect_season != "Specimen":
        years_seen = set(re.findall(r"20\d{2}", flat))
        if years_seen and expect_year not in years_seen:
            return False, f"session mismatch: expected {expect_year}, page says {sorted(years_seen)}"
        if not years_seen:
            note = ", session unverified (no text layer)"

    return True, f"barcode {barcode_pages}/{n_pages}, {avg_text:.0f} ch/pg{note}{note_trust}"


UNIT_CODE_RE = re.compile(r"\bW(?:MA|ME|ST|FM|DM)\d{2}\b")


def _unit_code(text: str) -> str | None:
    m = UNIT_CODE_RE.search(" ".join(text.split()))
    return m.group(0).upper() if m else None


def qp_matches_markscheme(pdf_bytes: bytes, ms_path: Path) -> tuple[bool, str]:
    """Require the downloaded QP to carry the same unit code as the slot's own
    mark scheme. The MS files are genuine, so this is the ground truth that the
    replacement paper belongs in this slot.

    Passes when either side has no readable code (some PDFs have no usable text
    layer) -- absence of evidence must not block an otherwise-verified paper.
    """
    if not ms_path.exists():
        return True, "no sibling MS"
    try:
        with fitz.open(ms_path) as ms:
            ms_code = _unit_code(ms[0].get_text())
        with fitz.open(stream=pdf_bytes, filetype="pdf") as qp:
            qp_code = _unit_code(qp[0].get_text())
    except Exception:  # noqa: BLE001
        return True, "unit check skipped"
    if ms_code and qp_code and ms_code != qp_code:
        return False, f"unit mismatch: QP={qp_code} but MS={ms_code}"
    return True, f"unit {qp_code or ms_code or '?'}"


def load_rows(mapping_csv: Path) -> list[dict[str, str]]:
    if not mapping_csv.exists():
        raise SystemExit(
            f"ERROR: mapping not found: {mapping_csv}\n"
            "Generate it first (see the audit + PMT discovery step)."
        )
    return list(csv.DictReader(mapping_csv.open(encoding="utf-8")))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true", help="actually write files")
    ap.add_argument("--limit", type=int, default=0, help="process at most N files")
    ap.add_argument(
        "--mapping", type=Path, default=MAPPING_CSV,
        help="mapping CSV to use (needs name,url,path,year,season columns)",
    )
    args = ap.parse_args()

    rows = load_rows(args.mapping)
    todo = [r for r in rows if r.get("url")]
    skipped_nourl = [r for r in rows if not r.get("url")]
    if args.limit:
        todo = todo[: args.limit]

    print(f"contaminated files with a source URL: {len(todo)}")
    print(f"no source URL (need manual sourcing):  {len(skipped_nourl)}")
    print(f"mode: {'COMMIT' if args.commit else 'DRY-RUN'}\n")

    session = requests.Session()
    session.headers.update(HEADERS)

    ok = failed = 0
    failures: list[tuple[str, str]] = []

    already = 0
    for i, row in enumerate(todo, 1):
        name = row["name"]
        target = REPO_ROOT / row["path"]
        url = row["url"]

        # Safe re-runs: if this slot already holds a genuine QP the work is done.
        # Without this a second pass would move the fixed paper into quarantine,
        # clobbering the original Model Answer stored there by the first pass.
        if target.exists():
            done, _ = looks_like_question_paper(
                target.read_bytes(), row["year"], row["season"],
                trusted=str(row.get("trusted", "")).strip().lower() in ("1", "true", "yes"),
            )
            if done:
                already += 1
                continue

        try:
            resp = session.get(url, timeout=60)
            resp.raise_for_status()
            payload = resp.content
        except Exception as exc:  # noqa: BLE001
            failed += 1
            failures.append((name, f"download failed: {type(exc).__name__}"))
            print(f"[{i:3}/{len(todo)}] FAIL {name} -- download {type(exc).__name__}")
            continue
        finally:
            time.sleep(REQUEST_DELAY_S)

        good, why = looks_like_question_paper(
            payload, row["year"], row["season"],
            trusted=str(row.get("trusted", "")).strip().lower() in ("1", "true", "yes"),
        )
        if not good:
            failed += 1
            failures.append((name, why))
            print(f"[{i:3}/{len(todo)}] SKIP {name} -- {why}")
            continue

        ms_path = target.parent / name.replace("_QP.pdf", "_MS.pdf")
        matched, unit_note = qp_matches_markscheme(payload, ms_path)
        if not matched:
            failed += 1
            failures.append((name, unit_note))
            print(f"[{i:3}/{len(todo)}] SKIP {name} -- {unit_note}")
            continue
        why = f"{why}, {unit_note}"

        cleaned, n_redactions = clean_and_stamp(payload)
        pmt_gone, gm_present = verify(cleaned)
        if not (pmt_gone and gm_present):
            failed += 1
            failures.append((name, f"clean/stamp check (pmt_gone={pmt_gone}, gm={gm_present})"))
            print(f"[{i:3}/{len(todo)}] SKIP {name} -- clean/stamp verification failed")
            continue

        if args.commit:
            QUARANTINE.mkdir(parents=True, exist_ok=True)
            if target.exists():
                dest = QUARANTINE / name
                if dest.exists():
                    # never clobber a previously quarantined original
                    dest = QUARANTINE / f"{target.stem}.dup{target.suffix}"
                shutil.move(str(target), str(dest))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(cleaned)

        ok += 1
        print(
            f"[{i:3}/{len(todo)}] OK   {name}  ({why}, redactions={n_redactions})"
            f"{'' if args.commit else '  [dry-run]'}"
        )

    print(f"\n{'=' * 60}")
    print(f"replaced : {ok}")
    print(f"already  : {already}  (slot already holds a genuine QP)")
    print(f"skipped  : {failed}")
    print(f"no URL   : {len(skipped_nourl)}  (still Model Answers -- source manually)")
    if failures:
        print("\nSkipped detail:")
        for nm, why in failures:
            print(f"  {nm:46} {why}")
    if not args.commit:
        print("\nDRY-RUN -- nothing written. Re-run with --commit to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
