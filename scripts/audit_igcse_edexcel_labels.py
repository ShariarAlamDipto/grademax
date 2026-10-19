#!/usr/bin/env python3
"""Read-only audit: does every Edexcel IGCSE PDF match the year/session/paper it
is filed under?

Why this exists
---------------
`data/Ultimate Final IGCSE` was built by scraping Physics & Maths Tutor, and the
archive filenames were derived from PMT's watermark
(`PMT / Physics · 2024 · May/Jun · Paper 1 · QP`) rather than from the paper's own
Edexcel cover page. Wherever PMT's label was wrong the error was inherited. That
was proven and fixed for Physics (38 of 198 files bad, mostly the plain
`Paper 1`/`Paper 2` slot holding the R variant). Since the cause is the scraping
method, every PMT-sourced subject is suspect.

Ground truth is the cover page:
  * QP  -- paper reference `4BI1/1B`, cover `PAPER: 1B`, exam date `Friday 14 June 2024`
  * MS  -- `Mark Scheme (Results) Summer 2024` plus `Paper 1B`

This script only reads and reports. Nothing is written except the report files.

Usage:
    python -X utf8 scripts/audit_igcse_edexcel_labels.py
    python -X utf8 scripts/audit_igcse_edexcel_labels.py --subject Biology
    python -X utf8 scripts/audit_igcse_edexcel_labels.py --workers 8
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import fitz  # PyMuPDF

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_ROOT = REPO_ROOT / "data" / "Ultimate Final IGCSE"
OUT_JSON = REPO_ROOT / "data" / "analysis" / "igcse_edexcel_label_audit.json"
OUT_CSV = REPO_ROOT / "data" / "analysis" / "igcse_edexcel_label_audit.csv"

# archive folder -> Edexcel subject code stem (spec digit 0/1 varies by era)
SUBJECT_CODE = {
    "Accounting": "4AC", "Bangla": "4BN", "Biology": "4BI",
    "Business_Studies": "4BS", "Chemistry": "4CH", "Commerce": "4CM",
    "Computer_Science": "4CP", "Economics": "4EC", "English_A": "4EA",
    "English_B": "4EB", "Further_Pure_Maths": "4PM", "Geography": "4GE",
    "Human_Biology": "4HB", "ICT": "4IT", "Mathematics_A": "4MA",
    "Mathematics_B": "4MB", "Mechanics_1": "4ME", "Physics": "4PH",
}
# A few subjects were re-coded mid-history, so more than one stem is legitimate.
# Bangla ran as "Bengali" 4BE0 before becoming "Bangla" 4BA0; both appear in the
# archive. (`subjects.code` says 4BN1, which matches neither -- a DB label issue,
# not a paper defect.)
SUBJECT_ALT_CODES = {
    "Bangla": ("4BE", "4BA"),
    # Pearson mistyped their own code on the June 2011 Paper 01 mark scheme:
    # it reads "International GCSE Mathematics (4MP0) Paper 01 Further Pure
    # Mathematics". The document is the right paper; only the code is a typo,
    # and the sibling Paper 02 mark scheme from the same session says 4PM0.
    "Further_Pure_Maths": ("4PM", "4MP"),
}


def accepted_codes(subject: str) -> tuple:
    alt = SUBJECT_ALT_CODES.get(subject)
    if alt:
        return alt
    stem = SUBJECT_CODE.get(subject)
    return (stem,) if stem else ()
# Science papers legitimately cite the Double Award code alongside their own.
CO_CODES = {"4SC"}

MONTH_SEASON = {
    "january": "Jan", "february": "Jan", "march": "Jan", "winter": "Jan",
    "april": "May-Jun", "may": "May-Jun", "june": "May-Jun", "july": "May-Jun",
    "summer": "May-Jun",
    "august": "Oct-Nov", "september": "Oct-Nov", "october": "Oct-Nov",
    "november": "Oct-Nov", "december": "Oct-Nov", "autumn": "Oct-Nov",
}

ANY_CODE_RE = re.compile(r"\b(4[A-Z]{2})([01])\s*/\s*([0-9]{1,2}[A-Z]{0,3})(?![A-Za-z0-9])")
BARE_CODE_RE = re.compile(r"\b(4[A-Z]{2})([01])\b")
PAPER_LINE_RE = re.compile(r"\bPAPER\s*:?\s*([0-9]{1,2}[A-Z]{0,3})(?![A-Za-z0-9])", re.I)
EXAM_DATE_RE = re.compile(
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{1,2})\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(20\d{2})\b", re.I)
SESSION_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|"
    r"November|December|Summer|Winter|Autumn)\s+(20\d{2})\b", re.I)
MS_RE = re.compile(r"mark scheme|marking scheme", re.I)
# A corrected mark scheme is re-titled "Mark Scheme - Results (updated October
# 2023) Summer 2022 ...". That parenthetical is the reissue date, not the exam
# session, and it sits before the real one -- so it must go before any session
# is read off the cover.
REISSUE_RE = re.compile(r"\((?:updated|revised|amended)[^)]{0,40}\)", re.I)
BARCODE_RE = re.compile(r"\*([A-Z]\d{5,6}[A-Z]?)\d{4}\*")
# Positive question-paper evidence: the candidate-details block only ever appears
# on a QP front cover.
QP_COVER_RE = re.compile(
    r"candidate surname|centre number|please check the examination details|"
    r"total marks|you must have", re.I)

FILENAME_RE = re.compile(
    r"^(?P<subject>.+)_(?P<year>\d{4})_(?P<season>[A-Za-z-]+)_Paper_(?P<paper>[0-9]{1,2}[A-Z]{0,3})_(?P<kind>QP|MS)\.pdf$")

# Provenance strips that are NOT part of the paper and must never be read as
# cover evidence. PMT stamps every page `4MA1 | 2015 | May/June | Paper 1H |
# PhysicsAndMathsTutor.com`; our cleaner redacts only the URL span, so the
# label half survives -- and it carries PMT's own (sometimes wrong) opinion of
# what the paper is. Our GradeMax stamp adds a similar trailer. Reading either
# one is how the archive's labels got corrupted in the first place, so strip
# both before looking for a cover.
WATERMARK_RE = re.compile(
    # PMT's pipe form: "4MA1 | 2015 | May/June | Paper 1H |"
    r"(?<![0-9A-Za-z])4[A-Z]{2}[01]\s*\|\s*20\d{2}\s*\|\s*[A-Za-z/]+\s*\|\s*"
    r"Paper\s*[0-9A-Za-z]+\s*\|?"
    # Our own middot trailer: "GradeMax Physics · 2019 · May/Jun · Paper 1 · MS".
    # The "GradeMax" word is optional -- some files carry only the bare subject
    # form ("Mathematics A · 2022 · Jan · Paper 1 · MS"), and because it repeats
    # on every page it outvotes the real cover when counting paper tokens.
    # The leading guard matters: without it the subject-name group starts on the
    # "F" of a genuine "Paper 1F" immediately before the trailer and eats the
    # tier letter off the real cover.
    r"|(?<![0-9A-Za-z])(?:GradeMax\s*)?[A-Za-z_][A-Za-z_ ]{0,28}·\s*20\d{2}\s*·"
    r"[^·]{2,12}·\s*Paper\s*[0-9A-Za-z]+\s*·\s*(?:QP|MS)"
    r"|(?<![0-9A-Za-z])GradeMax",
    re.I)

# Pearson reused the cancelled summer-2020 papers for November 2020, so those
# covers print a May/June date under an Oct-Nov slot. Not a defect.
COVID_REUSE_YEARS = {"2020"}


def parse_variant(token: str):
    """'1PR' -> (1, 'P', True). Returns None if unparseable."""
    m = re.match(r"^0*(\d+)([A-Z]*)$", (token or "").upper().replace(" ", ""))
    if not m:
        return None
    num = int(m.group(1))
    letters = m.group(2)
    is_r = letters.endswith("R")
    if is_r:
        letters = letters[:-1]
    return num, letters, is_r


# Archive naming conventions that differ from Edexcel's official paper numbers
# without being wrong. Mathematics A Foundation papers are 1F/2F but the archive
# often drops the tier letter; Higher papers are officially 3H/4H but the archive
# numbers them 1H/2H. Both are applied consistently, so the student still gets the
# paper the label promises -- it is a labelling convention, not contamination.
CONVENTION_EQUIV = {
    "Mathematics_A": [
        ({"1"}, {"1F"}), ({"2"}, {"2F"}),
        ({"1R"}, {"1FR"}), ({"2R"}, {"2FR"}),
        ({"1H"}, {"3H"}), ({"2H"}, {"4H"}),
        ({"1HR"}, {"3HR"}), ({"2HR"}, {"4HR"}),
    ],
}


def is_convention(subject: str, fn_token: str, cover_token: str) -> bool:
    for left, right in CONVENTION_EQUIV.get(subject, []):
        if fn_token in left and cover_token in right:
            return True
    return False


def variants_compatible(fn_token: str, cover_token: str, subject_uses_tiers: bool,
                        kind: str | None = None):
    """Is the cover's paper variant consistent with the filename's?

    The cover may carry a subject letter the filename omits (`1` vs `1P`), which
    is fine. What must agree is the paper number, the R-variant flag, and — for
    tiered subjects only — the F/H tier. `H` is a tier in Mathematics but part of
    the subject letters elsewhere, hence the flag.

    Returns None for "cannot tell", which the caller must not read as a defect.
    """
    a = parse_variant(fn_token)
    b = parse_variant(cover_token)
    if not a or not b:
        return None
    if a[0] != b[0]:
        return False
    if a[2] != b[2]:
        # Mark-scheme covers for several subjects print the plain paper number
        # for the R series too -- Business and Accounting both title their
        # Summer 2022 `2R` mark scheme "Paper 02". When the cover token carries
        # no letters at all there is simply no variant information on it, so the
        # honest answer is "unknown" rather than "mismatch".
        if kind == "MS" and a[2] and not b[2] and not b[1]:
            return None
        return False
    if subject_uses_tiers:
        a_tier = {c for c in a[1] if c in "FH"}
        b_tier = {c for c in b[1] if c in "FH"}
        if a_tier != b_tier:
            return False
    return True


def read_pdf(path: Path, max_pages: int = 4) -> dict:
    try:
        doc = fitz.open(path)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"unreadable ({type(exc).__name__})"}
    try:
        n = doc.page_count
        pages = [doc[i].get_text() for i in range(min(max_pages, n))]
    finally:
        doc.close()

    head = REISSUE_RE.sub(" ", WATERMARK_RE.sub(" ", " ".join(" ".join(pages).split())))
    page1 = (REISSUE_RE.sub(" ", WATERMARK_RE.sub(" ", " ".join(pages[0].split())))
             if pages else "")
    # Only claim a document type when the text positively says so. Some PDFs use
    # fonts with no usable ToUnicode map and extract as mojibake, where absence of
    # "mark scheme" proves nothing.
    if MS_RE.search(head):
        kind = "MS"
    elif QP_COVER_RE.search(head):
        kind = "QP"
    else:
        kind = None

    refs = Counter()
    for m in ANY_CODE_RE.finditer(head):
        refs[(m.group(1) + m.group(2), m.group(3).upper())] += 1
    bare = Counter(m.group(1) + m.group(2) for m in BARE_CODE_RE.finditer(head))
    papers = Counter(m.group(1).upper() for m in PAPER_LINE_RE.finditer(head))

    # Session, from page 1 only. Beyond the cover, Economics/Business/Geography
    # papers quote dated source articles ("August 2019") and English papers quote
    # dated extracts -- reading those as the exam session produces false alarms.
    # A question paper must therefore show a full weekday exam date; a mark scheme
    # prints its session on the cover, where a bare "Summer 2024" is trustworthy.
    year = season = evidence = None
    m = EXAM_DATE_RE.search(page1)
    if m:
        year, season, evidence = m.group(3), MONTH_SEASON[m.group(2).lower()], m.group(0)
    elif kind == "MS":
        m = SESSION_RE.search(page1)
        if m:
            year, season, evidence = m.group(2), MONTH_SEASON[m.group(1).lower()], m.group(0)

    bc = BARCODE_RE.search(head)
    return {
        "kind": kind, "refs": refs.most_common(4), "bare": bare.most_common(4),
        "papers": papers.most_common(3), "year": year, "season": season,
        "evidence": evidence, "pages": n, "textlen": len(head),
        "barcode": bc.group(1) if bc else None,
    }


def inspect(job) -> dict:
    rel, subject, uses_tiers = job
    path = REPO_ROOT / rel
    fn = FILENAME_RE.match(path.name)
    row = {"file": rel, "subject": subject, "status": "OK", "issues": [],
           "slot": None, "found": None, "evidence": "", "barcode": None,
           "convention": ""}
    if not fn:
        row["status"] = "UNPARSEABLE_NAME"
        return row

    slot_year, slot_season, slot_paper, slot_kind = (
        fn.group("year"), path.parent.name, fn.group("paper").upper(), fn.group("kind"))
    row["slot"] = f"{slot_year}/{slot_season}/Paper_{slot_paper}_{slot_kind}"

    info = read_pdf(path)
    if "error" in info:
        row["status"] = "UNREADABLE"
        row["issues"] = [info["error"]]
        return row

    row["barcode"] = info["barcode"]
    row["pages"] = info["pages"]
    expect_codes = accepted_codes(subject)

    # --- paper variant, preferring a reference that carries this subject's code
    cover_variant = None
    for (code, var), _n in info["refs"]:
        if expect_codes and code.startswith(expect_codes):
            cover_variant = var
            break
    if cover_variant is None and info["refs"]:
        cover_variant = info["refs"][0][0][1]
    if cover_variant is None and info["papers"]:
        cover_variant = info["papers"][0][0]

    # --- subject: flag only when this subject's code is absent AND another is present
    codes_seen = {c for (c, _v), _n in info["refs"]} | {c for c, _n in info["bare"]}
    if expect_codes and codes_seen:
        mine = {c for c in codes_seen if c.startswith(expect_codes)}
        others = {c for c in codes_seen if not c.startswith(expect_codes)
                  and c[:3] not in CO_CODES}
        if not mine and others:
            row["issues"].append(f"subject {'/'.join(expect_codes)}x -> {sorted(others)}")

    # --- kind (only when the text gave positive evidence either way)
    if info["kind"] and info["kind"] != slot_kind:
        row["issues"].append(f"kind {slot_kind}->{info['kind']}")

    # --- paper variant
    if cover_variant:
        ok = variants_compatible(slot_paper, cover_variant, uses_tiers, slot_kind)
        if ok is False:
            if is_convention(subject, slot_paper, cover_variant):
                row["convention"] = f"paper {slot_paper}={cover_variant}"
            else:
                row["issues"].append(f"paper {slot_paper}->{cover_variant}")
        row["found"] = cover_variant

    # --- session
    row["evidence"] = info["evidence"] or ""
    if info["year"] and slot_season.lower() not in ("specimen", "sample"):
        if info["year"] != slot_year or info["season"] != slot_season:
            covid_reuse = (slot_year in COVID_REUSE_YEARS
                           and info["year"] == slot_year
                           and slot_season == "Oct-Nov" and info["season"] == "May-Jun")
            if not covid_reuse:
                row["issues"].append(
                    f"session {slot_year}/{slot_season}->{info['year']}/{info['season']}")

    if row["issues"]:
        row["status"] = "MISMATCH"
    elif row.get("convention"):
        row["status"] = "CONVENTION"
    elif not info["year"] and not cover_variant:
        # nothing legible to check against -- report separately, never as clean
        row["status"] = "UNVERIFIED"
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", help="audit one archive folder only")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    subjects = sorted(d.name for d in ARCHIVE_ROOT.iterdir() if d.is_dir())
    if args.subject:
        subjects = [s for s in subjects if s.lower() == args.subject.lower()]
        if not subjects:
            print(f"no such subject folder: {args.subject}", file=sys.stderr)
            return 1

    jobs = []
    for subject in subjects:
        files = sorted((ARCHIVE_ROOT / subject).rglob("*.pdf"))
        tokens = [FILENAME_RE.match(f.name) for f in files]
        uses_tiers = any(m and re.search(r"[FH]", m.group("paper").upper())
                         for m in tokens)
        for f in files:
            jobs.append((str(f.relative_to(REPO_ROOT)), subject, uses_tiers))

    print(f"auditing {len(jobs)} PDFs across {len(subjects)} subject(s) ...\n")
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for i, row in enumerate(ex.map(inspect, jobs, chunksize=8), 1):
            results.append(row)
            if i % 200 == 0:
                print(f"  ... {i}/{len(jobs)}")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(results, indent=1), encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["subject", "file", "status", "slot", "found", "evidence", "issues", "convention", "barcode"])
        for r in results:
            w.writerow([r["subject"], r["file"], r["status"], r.get("slot") or "",
                        r.get("found") or "", r.get("evidence") or "",
                        "; ".join(r["issues"]), r.get("convention") or "", r.get("barcode") or ""])

    by_subject = defaultdict(Counter)
    for r in results:
        by_subject[r["subject"]][r["status"]] += 1

    print(f"\n{'SUBJECT':<22} {'FILES':>6} {'OK':>6} {'MISMATCH':>9} {'CONVENTION':>11} {'UNVERIFIED':>11}")
    print("-" * 70)
    total = Counter()
    for subject in sorted(by_subject):
        c = by_subject[subject]
        n = sum(c.values())
        total.update(c)
        flag = "  <<<" if c["MISMATCH"] else ""
        print(f"{subject:<22} {n:>6} {c['OK']:>6} {c['MISMATCH']:>9} "
              f"{c['CONVENTION']:>11} {c['UNVERIFIED']:>11}{flag}")
    n = sum(total.values())
    print("-" * 70)
    print(f"{'TOTAL':<22} {n:>6} {total['OK']:>6} {total['MISMATCH']:>9} "
          f"{total['CONVENTION']:>11} {total['UNVERIFIED']:>11}")

    print("\n\nMISMATCHES")
    print("=" * 78)
    for subject in sorted(by_subject):
        bad = [r for r in results if r["subject"] == subject and r["status"] == "MISMATCH"]
        if not bad:
            continue
        print(f"\n{subject}  ({len(bad)})")
        for r in bad:
            print(f"   {r['slot']:<38} {'; '.join(r['issues'])}   [{r['evidence']}]")

    print(f"\nreports -> {OUT_JSON.relative_to(REPO_ROOT)} , {OUT_CSV.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
