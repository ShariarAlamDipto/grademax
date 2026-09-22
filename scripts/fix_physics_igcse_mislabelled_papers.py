#!/usr/bin/env python3
"""Fix Edexcel IGCSE Physics papers whose year/session/paper label does not match
the PDF's own front page.

Background
----------
`data/Ultimate Final IGCSE/Physics` was built by scraping Physics & Maths Tutor.
Each PMT PDF carries a watermark of the form

    PMT
    Physics · 2024 · May/Jun · Paper 1 · QP

and the scraper derived the archive filename from that watermark rather than from
the paper's own Edexcel cover page. Wherever PMT's label was wrong the error was
inherited verbatim, so the archive (and R2, and therefore grademax.me) serves a
file whose cover page contradicts the slot it sits in.

The dominant failure is a variant swap: the plain `Paper 1` / `Paper 2` slot holds
the **R variant** (1PR / 2PR). A handful of slots hold an entirely different
session (e.g. `2018/Jan/Paper_1_QP` is the 10 January **2019** paper).

Ground truth
------------
The Edexcel cover page. Every genuine paper prints its own paper reference
(`4PH1/2PR`) and exam date (`Friday 14 June 2024`); every genuine mark scheme
prints `Mark Scheme (Results) Summer 2024` plus `Paper 1P`. That is what this
script trusts -- never the filename, never the PMT watermark.

Replacement source
------------------
Pearson's own asset catalogue, discovered through their public Algolia index
(the same mechanism as `fill_ial_gaps_from_algolia.py`). Algolia returns the
exact CDN URL plus a structured title (`Mark scheme - Paper 1P - June 2022`), so
no URL guessing is involved.

Safety
------
Every download must pass `verify_replacement()` -- correct document kind, correct
paper variant, correct session and year, read from page 1 -- before it is allowed
to replace anything. A file that fails is skipped and reported, never written.
Replaced originals are moved to `data/quarantine/physics_igcse_mislabelled/`.

Filenames and R2 keys are unchanged, so no `papers` rows need patching; only the
R2 objects are re-uploaded.

Usage:
    python -X utf8 scripts/fix_physics_igcse_mislabelled_papers.py               # audit only
    python -X utf8 scripts/fix_physics_igcse_mislabelled_papers.py --commit      # fix locally
    python -X utf8 scripts/fix_physics_igcse_mislabelled_papers.py --commit --upload
    python -X utf8 scripts/fix_physics_igcse_mislabelled_papers.py --commit --only 2024
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from urllib.parse import quote

import fitz  # PyMuPDF
import httpx
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from source_m1_question_papers import clean_and_stamp, verify  # noqa: E402

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env.local")

ARCHIVE = REPO_ROOT / "data" / "Ultimate Final IGCSE" / "Physics"
QUARANTINE = REPO_ROOT / "data" / "quarantine" / "physics_igcse_mislabelled"
REPORT = REPO_ROOT / "data" / "analysis" / "physics_igcse_label_audit.json"

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "grademax-papers")

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}
REQUEST_DELAY_S = 1.0  # be polite to the Pearson CDN

APP_ID = "L639T95U5A"
ALGOLIA_KEY = "f79c7a8352e9ffbdaec387bf43612ee6"
ALGOLIA_INDEX = "qualifications-uk_LIVE_master-content"
ALGOLIA = (
    f"https://{APP_ID.lower()}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"
    f"?x-algolia-application-id={APP_ID}&x-algolia-api-key={ALGOLIA_KEY}"
)
PEARSON_HOST = "https://qualifications.pearson.com"

# Month -> archive season folder. "Summer"/"Winter" appear on mark-scheme covers.
MONTH_SEASON = {
    "january": "Jan", "february": "Jan", "march": "Jan", "winter": "Jan",
    "april": "May-Jun", "may": "May-Jun", "june": "May-Jun", "july": "May-Jun",
    "summer": "May-Jun",
    "august": "Oct-Nov", "september": "Oct-Nov", "october": "Oct-Nov",
    "november": "Oct-Nov", "december": "Oct-Nov", "autumn": "Oct-Nov",
}

# Paper reference on a QP cover: "4PH1/2PR". `R` only ever directly follows `P`,
# and must not be the first letter of the next word -- hence the lookahead.
REF_RE = re.compile(r"\b(4PH[01]|4SC0)\s*/\s*([12]PR?)(?![A-Za-z0-9])", re.I)
# Mark-scheme / cover restatement: "Paper: 2PR", "Paper 1P".
PAPER_RE = re.compile(r"\bPAPER\s*:?\s*([12]PR?)(?![A-Za-z0-9])", re.I)
# QP cover exam date: "Friday 14 June 2024".
EXAM_DATE_RE = re.compile(
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{1,2})\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(20\d{2})\b", re.I)
# Mark-scheme cover session: "Summer 2024", "January 2020", "November 2023".
SESSION_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|"
    r"November|December|Summer|Winter|Autumn)\s+(20\d{2})\b", re.I)
MS_RE = re.compile(r"mark scheme|marking scheme", re.I)

# Slots that legitimately have no exam month on the cover, so the session gate
# cannot apply. Specimen papers are published (not sat) and print only their
# release month.
NO_SESSION_GATE = {"Specimen"}

# Slots whose cover date genuinely disagrees with the session they belong to.
# The summer 2020 series was cancelled (COVID) and Pearson reused the papers,
# already printed, for November 2020 -- so Pearson's own November 2020 assets
# still read "Wednesday 20 May 2020" / "Friday 12 June 2020". These are the
# correct files for the November slot; the printed date is the anomaly.
# key: (year, season, paper) -> the date the cover prints instead.
SESSION_EXCEPTIONS = {
    ("2020", "Oct-Nov", "1"): "2020/May-Jun",
    ("2020", "Oct-Nov", "1R"): "2020/May-Jun",
    ("2020", "Oct-Nov", "2"): "2020/May-Jun",
    ("2020", "Oct-Nov", "2R"): "2020/May-Jun",
}


# --------------------------------------------------------------------------- #
# Reading what a PDF actually is
# --------------------------------------------------------------------------- #

def read_identity(pdf_bytes: bytes) -> dict:
    """Extract (kind, paper, year, season) from a PDF's own front matter.

    Reads the whole document because older mark schemes restate the paper code a
    few pages in, but prefers page-1 evidence, which is the authoritative cover.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        return {"error": f"unreadable pdf ({type(exc).__name__})"}

    try:
        pages = [p.get_text() for p in doc]
    finally:
        doc.close()

    if not pages:
        return {"error": "no pages"}

    head = " ".join(" ".join(pages[:3]).split())
    whole = " ".join(" ".join(pages).split())

    kind = "MS" if MS_RE.search(head) else "QP"

    paper = None
    for pattern, text in ((REF_RE, head), (PAPER_RE, head), (REF_RE, whole), (PAPER_RE, whole)):
        m = pattern.search(text)
        if m:
            paper = (m.group(2) if pattern is REF_RE else m.group(1)).upper()
            break

    year = season = evidence = None
    m = EXAM_DATE_RE.search(head)
    if m:
        year, season = m.group(3), MONTH_SEASON[m.group(2).lower()]
        evidence = m.group(0)
    else:
        m = SESSION_RE.search(head)
        if m:
            year, season = m.group(2), MONTH_SEASON[m.group(1).lower()]
            evidence = m.group(0)

    return {"kind": kind, "paper": paper, "year": year, "season": season,
            "evidence": evidence, "pages": len(pages)}


def slot_of(path: Path, season_from_name: bool = False) -> dict | None:
    """Parse the archive slot a file claims to occupy.

    The containing season folder is authoritative for files sitting in the
    archive tree. Set `season_from_name` for files read from the quarantine
    folder, whose parent directory is no longer a season.
    """
    m = re.match(r"Physics_(\d{4})_([A-Za-z-]+)_Paper_([12]R?)_(QP|MS)\.pdf$", path.name)
    if not m:
        return None
    year, season_in_name, paper, kind = m.groups()
    season = season_in_name if season_from_name else path.parent.name
    return {
        "year": year, "season": season, "paper": paper, "kind": kind,
        "want_code": paper[0] + "P" + ("R" if paper.endswith("R") else ""),
    }


def audit() -> list[dict]:
    """Every archive file whose own front page contradicts its slot."""
    broken = []
    for path in sorted(ARCHIVE.rglob("*.pdf")):
        slot = slot_of(path)
        if slot is None:
            print(f"  ?? unparseable filename: {path.relative_to(REPO_ROOT)}")
            continue
        ident = read_identity(path.read_bytes())
        if "error" in ident:
            print(f"  !! {path.relative_to(REPO_ROOT)}: {ident['error']}")
            continue

        issues = []
        if ident["paper"] and ident["paper"] != slot["want_code"]:
            issues.append(f"paper {slot['want_code']}->{ident['paper']}")
        exception = SESSION_EXCEPTIONS.get((slot["year"], slot["season"], slot["paper"]))
        printed = f"{ident['year']}/{ident['season']}" if ident["year"] else None
        gate_session = slot["season"] not in NO_SESSION_GATE and printed != exception
        if gate_session and ident["year"] and (
            ident["year"] != slot["year"] or ident["season"] != slot["season"]
        ):
            issues.append(
                f"session {slot['year']}/{slot['season']}->{ident['year']}/{ident['season']}")

        if issues:
            broken.append({
                "path": str(path.relative_to(REPO_ROOT)),
                "slot": f"{slot['year']}/{slot['season']}/Paper_{slot['paper']}_{slot['kind']}",
                **slot,
                "found_paper": ident["paper"], "found_year": ident["year"],
                "found_season": ident["season"], "evidence": ident["evidence"] or "",
                "issues": "; ".join(issues),
            })
    return broken


# --------------------------------------------------------------------------- #
# Pearson catalogue
# --------------------------------------------------------------------------- #

CATALOG_TITLE_RE = re.compile(
    r"(mark scheme|question paper)"
    r".*?paper\s*([12]PR?)\b"
    r".*?(january|february|march|april|may|june|july|summer|"
    r"september|october|november|winter)\s*(20\d{2})", re.I)


def pearson_catalog() -> dict[tuple, str]:
    """(year, season, paper, kind) -> absolute Pearson CDN URL."""
    filters = ('category:"Pearson-UK:Qualification-Family/International-GCSE"'
               ' AND category:"Pearson-UK:Qualification-Subject/Physics"'
               ' AND type:"dam:Asset"')
    hits, page = [], 0
    while page < 20:
        payload = {"params": f"query=&filters={quote(filters, safe='')}&hitsPerPage=1000&page={page}"}
        resp = httpx.post(ALGOLIA, json=payload, timeout=40)
        if resp.status_code != 200:
            break
        data = resp.json()
        hits.extend(data.get("hits", []))
        if page + 1 >= data.get("nbPages", 1):
            break
        page += 1

    catalog: dict[tuple, str] = {}
    for hit in hits:
        url = hit.get("url") or hit.get("path") or ""
        if "/Physics/" not in url:
            continue
        m = CATALOG_TITLE_RE.search(" ".join((hit.get("title") or "").split()))
        if not m:
            continue
        doctype, paper, month, year = m.groups()
        kind = "MS" if doctype.lower().startswith("mark") else "QP"
        key = (year, MONTH_SEASON[month.lower()], paper.upper(), kind)
        # first hit wins; the index lists newest first and duplicates are re-issues
        catalog.setdefault(key, PEARSON_HOST + quote(url) if url.startswith("/") else url)
    return catalog


# Cover copyright line: "©2022 Pearson Education Ltd." / "2024 Pearson Education Ltd".
COPYRIGHT_RE = re.compile(r"(?:©|\(c\)|\bcopyright\b)\s*(20\d{2})|\b(20\d{2})\s+Pearson\s+Education", re.I)
# Pearson CDN filenames end in the asset date: 4ph1-1p-que-20220610.pdf
URL_DATE_RE = re.compile(r"[-_](que|rms|msc)[-_](\d{4})(\d{2})(\d{2})\.pdf$", re.I)


def _url_date_season(url: str) -> tuple[str, str] | None:
    """(year, season) from a Pearson QP filename's exam-date suffix.

    Only meaningful for `que` (question paper) assets, where the suffix is the
    exam date. For `rms`/`msc` it is the mark scheme's *publication* date, which
    falls in a different season than the exam, so callers must not use it there.
    """
    m = URL_DATE_RE.search(url)
    if not m or m.group(1).lower() != "que":
        return None
    year, month = m.group(2), int(m.group(3))
    month_name = ["january", "february", "march", "april", "may", "june", "july",
                  "august", "september", "october", "november", "december"][month - 1]
    return year, MONTH_SEASON[month_name]


def verify_replacement(pdf_bytes: bytes, slot: dict, url: str = "") -> tuple[bool, str]:
    """Gate a download before it may overwrite an archive file.

    Rejects on any positive contradiction of kind, paper variant, year or season.

    Some Pearson QP covers print no exam date (only the paper reference and a
    copyright line). For those the session is confirmed instead by two
    independent signals that must agree with each other and with the slot: the
    cover's copyright year, and the exam-date suffix on the CDN filename. That is
    on top of the paper-reference match, so a wrong-session file still cannot
    pass. Mark schemes always print their session and never take this path.
    """
    ident = read_identity(pdf_bytes)
    if "error" in ident:
        return False, ident["error"]
    if ident["pages"] < 3:
        return False, f"only {ident['pages']} pages"
    if ident["kind"] != slot["kind"]:
        return False, f"kind {ident['kind']} != {slot['kind']}"
    if ident["paper"] is None:
        return False, "no paper code on cover"
    if ident["paper"] != slot["want_code"]:
        return False, f"paper {ident['paper']} != {slot['want_code']}"

    if slot["season"] in NO_SESSION_GATE:
        return True, f"{ident['paper']} {slot['season']} ({ident['pages']}pp)"

    if ident["year"] is not None:
        if ident["year"] != slot["year"] or ident["season"] != slot["season"]:
            return False, (f"session {ident['year']}/{ident['season']} "
                           f"!= {slot['year']}/{slot['season']}")
        return True, f"{ident['paper']} {ident['evidence']} ({ident['pages']}pp)"

    # Cover carries no session -- fall back to copyright year + CDN exam date.
    if ident["kind"] != "QP":
        return False, "no session on mark-scheme cover"
    url_ds = _url_date_season(url)
    if url_ds is None:
        return False, "no session on cover and no exam date in source URL"
    if url_ds != (slot["year"], slot["season"]):
        return False, f"source exam date {url_ds[0]}/{url_ds[1]} != {slot['year']}/{slot['season']}"

    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            cover = " ".join(doc[0].get_text().split())
    except Exception as exc:  # noqa: BLE001
        return False, f"unreadable cover ({type(exc).__name__})"
    m = COPYRIGHT_RE.search(cover)
    cyear = (m.group(1) or m.group(2)) if m else None
    if cyear is None:
        return False, "no session, no copyright year on cover"
    if cyear != slot["year"]:
        return False, f"copyright {cyear} != {slot['year']}"

    return True, (f"{ident['paper']} ©{cyear} + CDN exam date "
                  f"{url_ds[0]}/{url_ds[1]} ({ident['pages']}pp)")


# --------------------------------------------------------------------------- #
# R2
# --------------------------------------------------------------------------- #

def r2_client():
    import boto3
    from botocore.config import Config
    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY, aws_secret_access_key=R2_SECRET,
        region_name="auto", config=Config(retries={"max_attempts": 3}),
    )


def r2_key_for(slot: dict, filename: str) -> str:
    """Existing key convention: igcse/physics/<year>/<season-lower>/<filename>."""
    return f"igcse/physics/{slot['year']}/{slot['season'].lower()}/{filename}"


# --------------------------------------------------------------------------- #

def resync(commit: bool, only: str | None) -> int:
    """Upload already-corrected archive files to R2.

    The set to upload is exactly the files whose originals sit in the quarantine
    folder -- i.e. the ones a previous `--commit` replaced. Each one is
    re-verified against its slot before upload, so a file that is still wrong can
    never be pushed to production.
    """
    if not QUARANTINE.exists():
        print(f"nothing to resync: {QUARANTINE.relative_to(REPO_ROOT)} does not exist")
        return 0

    client = r2_client() if commit else None
    uploaded = failed = 0
    for original in sorted(QUARANTINE.glob("*.pdf")):
        slot = slot_of(original, season_from_name=True)
        if slot is None:
            print(f"  ?? cannot parse {original.name}")
            failed += 1
            continue
        if only and slot["year"] != only:
            continue

        target = ARCHIVE / slot["year"] / slot["season"] / original.name
        if not target.exists():
            print(f"  !! missing corrected file: {target.relative_to(REPO_ROOT)}")
            failed += 1
            continue

        data = target.read_bytes()
        ok, why = verify_replacement(data, slot, "")
        if not ok:
            # A corrected QP whose cover prints no date cannot re-derive its
            # session without the source URL, so accept the weaker guarantee that
            # kind + paper reference still match; that is what was wrong before.
            ident = read_identity(data)
            if ident.get("paper") == slot["want_code"] and ident.get("kind") == slot["kind"]:
                why = f"{ident['paper']} (session not on cover)"
            else:
                print(f"  {slot['year']}/{slot['season']}/{original.name}  NOT UPLOADED: {why}")
                failed += 1
                continue

        key = r2_key_for(slot, original.name)
        if not commit:
            uploaded += 1
            print(f"  [DRY] {key}   ({why})")
            continue
        try:
            client.put_object(Bucket=R2_BUCKET, Key=key, Body=data, ContentType="application/pdf")
            uploaded += 1
            print(f"  uploaded {key}   ({why})")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"  FAILED {key}: {exc}")

    print(f"\n{'UPLOADED' if commit else 'DRY-RUN'}: {uploaded} file(s), failed={failed}")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true", help="write replacements to the archive")
    ap.add_argument("--upload", action="store_true", help="also re-upload fixed files to R2")
    ap.add_argument("--resync", action="store_true",
                    help="upload already-corrected files (those in quarantine) to R2")
    ap.add_argument("--only", help="restrict to a year, e.g. 2024")
    ap.add_argument("--limit", type=int, help="cap the number of files fixed")
    args = ap.parse_args()

    if args.resync:
        return resync(args.commit, args.only)

    if not ARCHIVE.exists():
        print(f"ERROR: archive not found: {ARCHIVE}", file=sys.stderr)
        return 1

    print(f"Auditing {ARCHIVE.relative_to(REPO_ROOT)} ...")
    broken = audit()
    if args.only:
        broken = [b for b in broken if b["year"] == args.only]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(broken, indent=2), encoding="utf-8")
    print(f"\n{len(broken)} mislabelled file(s); report -> {REPORT.relative_to(REPO_ROOT)}\n")
    for b in broken:
        print(f"  {b['slot']:<40} {b['issues']}   [{b['evidence']}]")

    if not broken:
        return 0

    print("\nFetching Pearson catalogue ...")
    catalog = pearson_catalog()
    print(f"  {len(catalog)} catalogued assets\n")

    fixed = skipped = unavailable = 0
    for b in broken:
        if args.limit and fixed >= args.limit:
            break
        key = (b["year"], b["season"], b["want_code"], b["kind"])
        url = catalog.get(key)
        tag = f"{b['slot']:<40}"
        if not url:
            unavailable += 1
            print(f"  {tag} NO OFFICIAL SOURCE (not published by Pearson)")
            continue

        try:
            resp = requests.get(url, headers=UA, timeout=120)
        except Exception as exc:  # noqa: BLE001
            skipped += 1
            print(f"  {tag} download failed: {exc}")
            continue
        time.sleep(REQUEST_DELAY_S)
        if resp.status_code != 200 or resp.content[:4] != b"%PDF":
            skipped += 1
            print(f"  {tag} not a PDF (http {resp.status_code})")
            continue

        ok, why = verify_replacement(resp.content, b, url)
        if not ok:
            skipped += 1
            print(f"  {tag} REJECTED: {why}")
            continue

        if not args.commit:
            fixed += 1
            print(f"  {tag} [DRY] would replace <- {url.split('/')[-1]}  ({why})")
            continue

        cleaned, _ = clean_and_stamp(resp.content)
        pmt_gone, gm_present = verify(cleaned)
        if not (pmt_gone and gm_present):
            skipped += 1
            print(f"  {tag} REJECTED: stamp check (pmt_gone={pmt_gone}, grademax={gm_present})")
            continue

        target = REPO_ROOT / b["path"]
        QUARANTINE.mkdir(parents=True, exist_ok=True)
        shutil.move(str(target), str(QUARANTINE / target.name))
        target.write_bytes(cleaned)
        fixed += 1
        print(f"  {tag} FIXED <- {url.split('/')[-1]}  ({why})")

        if args.upload:
            try:
                r2_client().put_object(
                    Bucket=R2_BUCKET, Key=r2_key_for(b, target.name),
                    Body=cleaned, ContentType="application/pdf",
                )
                print(f"  {'':<40} uploaded -> {r2_key_for(b, target.name)}")
            except Exception as exc:  # noqa: BLE001
                print(f"  {'':<40} R2 upload FAILED: {exc}")

    mode = "COMMITTED" if args.commit else "DRY-RUN"
    print(f"\n{mode}: fixed={fixed} skipped={skipped} no-official-source={unavailable}")
    if not args.commit and fixed:
        print("Re-run with --commit (and --upload to push to R2).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
