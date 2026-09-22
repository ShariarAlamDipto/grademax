#!/usr/bin/env python3
"""Replace individual Edexcel IGCSE files whose cover page contradicts their slot.

This is the generalised form of `fix_physics_igcse_mislabelled_papers.py`, which
fixed Physics. It handles the per-file defects the structural passes leave behind:

  * a non-R slot holding the R variant (`Paper_1_QP` containing `2BR`)
  * a wrong paper number (`2025/Oct-Nov/Paper_1_MS` containing paper 2)
  * a wrong year or session (`2016/Jan/Paper_1_QP` being the January 2015 paper)

Ground truth is the cover page; replacements come from Pearson's official asset
catalogue, discovered through their public Algolia index (no URL guessing). Every
download is gated on its own cover before it may overwrite anything, and the
replaced original is quarantined.

Filenames and R2 keys never change, so no `papers` rows need patching -- only the
R2 object and the archive file are rewritten.

Note on Pearson's CDN: a wrong path returns **HTTP 200 with `text/html`**, so the
content-type and `%PDF` magic are both checked.

Dry-run by default; --commit writes the archive, --upload also pushes to R2.

Usage:
    python -X utf8 scripts/fix_igcse_edexcel_mislabelled_files.py --subject Biology
    python -X utf8 scripts/fix_igcse_edexcel_mislabelled_files.py --subject Biology --commit --upload
    python -X utf8 scripts/fix_igcse_edexcel_mislabelled_files.py --all --commit --upload
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
from audit_igcse_edexcel_labels import (  # noqa: E402
    ARCHIVE_ROOT, FILENAME_RE, MONTH_SEASON, accepted_codes, inspect,
    is_convention, parse_variant, variants_compatible,
)

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env.local")

R2_BUCKET = os.getenv("R2_BUCKET_NAME", "grademax-papers")
QUARANTINE = REPO_ROOT / "data" / "quarantine" / "igcse_mislabelled_files"

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")}
REQUEST_DELAY_S = 1.0

APP_ID = "L639T95U5A"
ALGOLIA_KEY = "f79c7a8352e9ffbdaec387bf43612ee6"
ALGOLIA_INDEX = "qualifications-uk_LIVE_master-content"
ALGOLIA = (f"https://{APP_ID.lower()}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"
           f"?x-algolia-application-id={APP_ID}&x-algolia-api-key={ALGOLIA_KEY}")
PEARSON_HOST = "https://qualifications.pearson.com"

# archive folder -> Pearson Qualification-Subject slug
PEARSON_SLUG = {
    "Accounting": "Accounting", "Bangla": "Bangla", "Biology": "Biology",
    "Business_Studies": "Business", "Chemistry": "Chemistry", "Commerce": "Commerce",
    "Computer_Science": "Computer-Science", "Economics": "Economics",
    "English_A": "English-Language-A", "English_B": "English-Language-B",
    "Geography": "Geography", "Human_Biology": "Human-Biology",
    "ICT": "Information-and-Communication-Technology", "Physics": "Physics",
    # The shared "Mathematics" catalogue carries only 8 current-spec assets (all
    # training material), so maths subjects cannot be sourced this way.
}

CATALOG_TITLE_RE = re.compile(
    r"(mark scheme|question paper)"
    r".*?paper\s*([0-9]{1,2}[A-Z]{0,3})\b"
    r".*?(january|february|march|april|may|june|july|summer|"
    r"september|october|november|winter)\s*(20\d{2})", re.I)

MS_RE = re.compile(r"mark scheme|marking scheme", re.I)
SESSION_RE = re.compile(r"\b(January|February|March|April|May|June|July|August|September|"
                        r"October|November|December|Summer|Winter|Autumn)\s+(20\d{2})\b", re.I)
EXAM_DATE_RE = re.compile(
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{1,2})\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(20\d{2})\b", re.I)
PAPER_RE = re.compile(r"\bPAPER\s*:?\s*([0-9]{1,2}[A-Z]{0,3})(?![A-Za-z0-9])", re.I)
REF_RE = re.compile(r"\b4[A-Z]{2}[01]\s*/\s*([0-9]{1,2}[A-Z]{0,3})(?![A-Za-z0-9])")
URL_DATE_RE = re.compile(r"[-_](que|rms|msc)[-_](\d{4})(\d{2})(\d{2})\.pdf$", re.I)


def r2_client():
    import boto3
    from botocore.config import Config
    return boto3.client(
        "s3", endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        region_name="auto", config=Config(retries={"max_attempts": 3}))


def pearson_catalog(slug: str) -> dict[tuple, str]:
    """(year, season, paper, kind) -> CDN url."""
    filters = ('category:"Pearson-UK:Qualification-Family/International-GCSE"'
               f' AND category:"Pearson-UK:Qualification-Subject/{slug}"'
               ' AND type:"dam:Asset"')
    hits, page = [], 0
    while page < 20:
        payload = {"params": f"query=&filters={quote(filters, safe='')}"
                             f"&hitsPerPage=1000&page={page}"}
        resp = httpx.post(ALGOLIA, json=payload, timeout=45)
        if resp.status_code != 200:
            break
        data = resp.json()
        hits.extend(data.get("hits", []))
        if page + 1 >= data.get("nbPages", 1):
            break
        page += 1
    out: dict[tuple, str] = {}
    for hit in hits:
        url = hit.get("url") or hit.get("path") or ""
        m = CATALOG_TITLE_RE.search(" ".join((hit.get("title") or "").split()))
        if not m:
            continue
        doctype, paper, month, year = m.groups()
        kind = "MS" if doctype.lower().startswith("mark") else "QP"
        key = (year, MONTH_SEASON[month.lower()], paper.upper(), kind)
        out.setdefault(key, PEARSON_HOST + quote(url) if url.startswith("/") else url)
    return out


def cover_of(body: bytes) -> dict:
    try:
        with fitz.open(stream=body, filetype="pdf") as d:
            page1 = " ".join(d[0].get_text().split())
            head = " ".join(" ".join(d[i].get_text()
                                     for i in range(min(3, d.page_count))).split())
            pages = d.page_count
    except Exception as exc:  # noqa: BLE001
        return {"error": f"unreadable ({type(exc).__name__})"}
    pm = REF_RE.search(head) or PAPER_RE.search(head)
    year = season = evidence = None
    m = EXAM_DATE_RE.search(page1)
    if m:
        year, season, evidence = m.group(3), MONTH_SEASON[m.group(2).lower()], m.group(0)
    else:
        m = SESSION_RE.search(page1)
        if m:
            year, season, evidence = m.group(2), MONTH_SEASON[m.group(1).lower()], m.group(0)
    return {"kind": "MS" if MS_RE.search(page1) else "QP",
            "paper": pm.group(1).upper() if pm else None,
            "year": year, "season": season, "evidence": evidence,
            "pages": pages, "page1": page1}


def url_exam_season(url: str):
    m = URL_DATE_RE.search(url)
    if not m or m.group(1).lower() != "que":
        return None
    months = ["january", "february", "march", "april", "may", "june", "july",
              "august", "september", "october", "november", "december"]
    return m.group(2), MONTH_SEASON[months[int(m.group(3)) - 1]]


def verify_replacement(body: bytes, want_paper: str, year: str, season: str,
                       kind: str, url: str) -> tuple[bool, str]:
    """Gate a download: it must positively be the paper the slot asks for."""
    c = cover_of(body)
    if c.get("error"):
        return False, c["error"]
    if c["pages"] < 3:
        return False, f"only {c['pages']} pages"
    if c["kind"] != kind:
        return False, f"kind {c['kind']} != {kind}"
    if not c["paper"]:
        return False, "no paper code on cover"
    if variants_compatible(want_paper, c["paper"], subject_uses_tiers=True) is False:
        return False, f"paper {c['paper']} != {want_paper}"
    if season == "Specimen":
        return True, f"{c['paper']} specimen ({c['pages']}pp)"
    if c["year"]:
        if c["year"] != year or c["season"] != season:
            return False, f"session {c['year']}/{c['season']} != {year}/{season}"
        return True, f"{c['paper']} {c['evidence']} ({c['pages']}pp)"
    # cover prints no session: confirm via CDN exam date + copyright year
    if kind != "QP":
        return False, "no session on mark-scheme cover"
    ues = url_exam_season(url)
    if not ues:
        return False, "no session on cover and no exam date in source URL"
    if ues != (year, season):
        return False, f"source exam date {ues[0]}/{ues[1]} != {year}/{season}"
    cy = re.search(r"(?:©|\(c\))\s*(20\d{2})|\b(20\d{2})\s+Pearson\s+Education",
                   c["page1"], re.I)
    cyear = (cy.group(1) or cy.group(2)) if cy else None
    if cyear != year:
        return False, f"copyright {cyear} != {year}"
    return True, f"{c['paper']} ©{cyear} + CDN date {ues[0]}/{ues[1]} ({c['pages']}pp)"


def wanted_codes(slot_paper: str, found: str | None, subject_letters: set[str]) -> list[str]:
    """Candidate paper codes for this slot, best first.

    Edexcel writes the same paper several ways: bare (`2`), zero-padded (`02`) and
    with a subject letter the filename omits (`1B`, `1C`). The slot fixes only the
    paper *number* and the R flag; the letter has to be borrowed -- from the file
    currently (wrongly) in the slot, or from the letters this subject is known to
    use elsewhere. Returning several candidates lets the catalogue lookup settle
    which spelling Pearson used.
    """
    a = parse_variant(slot_paper)
    if not a:
        return []
    num, _letters, is_r = a
    suffix = "R" if is_r else ""
    letters: list[str] = []
    b = parse_variant(found or "")
    if b and b[1]:
        letters.append(b[1])
    letters += [l for l in sorted(subject_letters) if l not in letters]
    out = [f"{num}{l}{suffix}" for l in letters]
    out += [f"{num}{suffix}", f"0{num}{suffix}"]
    seen, uniq = set(), []
    for c in out:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq


def subject_paper_letters(results: list[dict]) -> set[str]:
    """Subject letters seen on this subject's own covers (Biology 'B', Chemistry 'C')."""
    letters = set()
    for r in results:
        v = parse_variant(r.get("found") or "")
        if v and v[1]:
            letters.add(v[1])
    return letters


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", help="archive folder name, e.g. Biology")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--upload", action="store_true")
    args = ap.parse_args()

    if not args.subject and not args.all:
        print("give --subject <folder> or --all", file=sys.stderr)
        return 1
    subjects = ([args.subject] if args.subject
                else sorted(d.name for d in ARCHIVE_ROOT.iterdir() if d.is_dir()))

    client = r2_client() if args.upload else None
    grand_fixed = grand_skipped = grand_nosource = 0

    for subject in subjects:
        folder = ARCHIVE_ROOT / subject
        if not folder.exists():
            print(f"no such subject folder: {subject}", file=sys.stderr)
            continue
        files = sorted(folder.rglob("*.pdf"))
        tokens = [FILENAME_RE.match(f.name) for f in files]
        uses_tiers = any(m and re.search(r"[FH]", m.group("paper").upper()) for m in tokens)
        results = [inspect((str(f.relative_to(REPO_ROOT)), subject, uses_tiers)) for f in files]
        bad = [r for r in results if r["status"] == "MISMATCH"]
        if not bad:
            continue

        slug = PEARSON_SLUG.get(subject)
        print(f"\n{'=' * 72}\n{subject}: {len(bad)} mislabelled file(s)")
        if not slug:
            print("   no Pearson catalogue for this subject (maths share an index "
                  "that holds no exam papers) -- reported only")
            for r in bad:
                print(f"   {r['slot']:<38} {'; '.join(r['issues'])}")
            grand_nosource += len(bad)
            continue

        catalog = pearson_catalog(slug)
        letters = subject_paper_letters(results)
        print(f"   Pearson catalogue: {len(catalog)} assets"
              f"{f'; subject letters {sorted(letters)}' if letters else ''}")
        for r in bad:
            path = REPO_ROOT / r["file"]
            fn = FILENAME_RE.match(path.name)
            year, season = fn.group("year"), path.parent.name
            slot_paper, kind = fn.group("paper").upper(), fn.group("kind")
            candidates = wanted_codes(slot_paper, r.get("found"), letters)
            tag = f"   {r['slot']:<38}"
            if not candidates:
                print(f"{tag} cannot derive wanted paper code")
                grand_skipped += 1
                continue
            want = url = None
            for cand in candidates:
                u = catalog.get((year, season, cand, kind))
                if u:
                    want, url = cand, u
                    break
            if not url:
                print(f"{tag} no Pearson asset for {year}/{season} "
                      f"{'/'.join(candidates)} {kind}")
                grand_nosource += 1
                continue
            try:
                resp = requests.get(url, headers=UA, timeout=120)
            except Exception as exc:  # noqa: BLE001
                print(f"{tag} download failed: {exc}")
                grand_skipped += 1
                continue
            time.sleep(REQUEST_DELAY_S)
            ctype = resp.headers.get("content-type", "").lower()
            if resp.status_code != 200 or resp.content[:4] != b"%PDF" or "html" in ctype:
                print(f"{tag} not a PDF (http {resp.status_code}, {ctype[:24]})")
                grand_skipped += 1
                continue
            ok, why = verify_replacement(resp.content, want, year, season, kind, url)
            if not ok:
                print(f"{tag} REJECTED: {why}")
                grand_skipped += 1
                continue
            if not args.commit:
                print(f"{tag} [DRY] <- {url.split('/')[-1]}  ({why})")
                grand_fixed += 1
                continue
            cleaned, _ = clean_and_stamp(resp.content)
            pmt_gone, gm = verify(cleaned)
            if not (pmt_gone and gm):
                print(f"{tag} REJECTED: stamp check (pmt_gone={pmt_gone}, grademax={gm})")
                grand_skipped += 1
                continue
            QUARANTINE.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(QUARANTINE / path.name))
            path.write_bytes(cleaned)
            print(f"{tag} FIXED <- {url.split('/')[-1]}  ({why})")
            grand_fixed += 1
            if args.upload:
                key = (f"igcse/{subject.lower()}/{year}/{season.lower()}/{path.name}")
                try:
                    client.put_object(Bucket=R2_BUCKET, Key=key, Body=cleaned,
                                      ContentType="application/pdf")
                    print(f"{' ' * 41}uploaded -> {key}")
                except Exception as exc:  # noqa: BLE001
                    print(f"{' ' * 41}R2 upload FAILED: {exc}")

    print(f"\n{'=' * 72}")
    print(f"{'COMMITTED' if args.commit else 'DRY-RUN'}: fixed={grand_fixed} "
          f"skipped={grand_skipped} no-source={grand_nosource}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
