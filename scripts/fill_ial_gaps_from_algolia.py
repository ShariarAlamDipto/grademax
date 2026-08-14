#!/usr/bin/env python3
"""Fill missing Edexcel IAL question papers / mark schemes from the official
Pearson catalogue, discovered via Pearson's public Algolia search index.

Unlike blind CDN URL-guessing (the publication-date suffix is not derivable),
Algolia returns the *exact* asset URL plus structured metadata (unit, exam
series, document type) for every published IAL paper. For each `papers` row
whose `pdf_url` / `markscheme_pdf_url` is NULL we look up the matching hit,
download it, page-1-verify (kind + session + year), clean + stamp GradeMax
(reusing ingest_cambridge_papers.clean_and_stamp), upload to R2 at the subject's
existing key convention, and patch only the NULL column.

Dry-run by default; --commit to write. Idempotent (HEAD-skip R2, NULL-guarded
DB patch). Safe: the R2 URL builder is self-verified against the subject's
existing rows before any upload.

Usage:
    python -X utf8 scripts/fill_ial_gaps_from_algolia.py                 # dry-run all IAL gaps
    python -X utf8 scripts/fill_ial_gaps_from_algolia.py --subject "IAL Physics"
    python -X utf8 scripts/fill_ial_gaps_from_algolia.py --commit
"""
import argparse
import io
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

import httpx
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
_saved = sys.argv
sys.argv = [sys.argv[0]]
from ingest_cambridge_papers import clean_and_stamp  # noqa: E402
from fill_edexcel_paper_gaps import derive_shapes, fetch_subject_rows, fill_shape, r2_key_from_url  # noqa: E402
sys.argv = _saved

import fitz  # noqa: E402

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env.local")
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "grademax-papers")
H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}

APP_ID = "L639T95U5A"
API_KEY = "f79c7a8352e9ffbdaec387bf43612ee6"
INDEX = "qualifications-uk_LIVE_master-content"
ALGOLIA = f"https://{APP_ID.lower()}-dsn.algolia.net/1/indexes/{INDEX}/query?x-algolia-application-id={APP_ID}&x-algolia-api-key={API_KEY}"
PEARSON_HOST = "https://qualifications.pearson.com"

# DB subject name -> Pearson Algolia Qualification-Subject slug(s) (tried in order).
SUBJECT_SLUGS = {
    "IAL Accounting": ["Accounting"],
    "IAL Biology": ["Biology"],
    "IAL Chemistry": ["Chemistry"],
    "IAL Economics": ["Economics"],
    "IAL English Language": ["English-Language"],
    "IAL English Literature": ["English-Literature"],
    "IAL Greek": ["Greek"],
    "IAL History": ["History"],
    "IAL Physics": ["Physics"],
    "IAL Sociology": ["Sociology", "Applied-Psychology-and-Sociology"],
    # Single-unit maths subjects share the "Mathematics" catalogue; matched by code.
    "Mechanics 1 (M1)": ["Mathematics"],
    "Mechanics 2 (M2)": ["Mathematics"],
    "Mechanics 3 (M3)": ["Mathematics"],
    "Pure Mathematics 2 (P2)": ["Mathematics"],
    "Pure Mathematics 3 (P3)": ["Mathematics"],
    "Pure Mathematics 4 (P4)": ["Mathematics"],
    "Decision Mathematics 1 (D1)": ["Mathematics"],
}
# Maths unit -> Pearson paper code (to disambiguate within the Mathematics catalogue).
MATHS_CODE = {
    "Mechanics 1 (M1)": "WME01", "Mechanics 2 (M2)": "WME02", "Mechanics 3 (M3)": "WME03",
    "Pure Mathematics 2 (P2)": "WMA12", "Pure Mathematics 3 (P3)": "WMA13",
    "Pure Mathematics 4 (P4)": "WMA14", "Decision Mathematics 1 (D1)": "WDM11",
}

SEASON_FROM_SERIES = {
    "january": "jan", "february": "jan", "march": "jan",
    "may": "may-jun", "june": "may-jun", "summer": "may-jun",
    "october": "oct-nov", "november": "oct-nov", "winter": "oct-nov",
}


def algolia_hits(slug: str) -> list:
    filters = (f'category:"Pearson-UK:Qualification-Family/International-Advanced-Level"'
               f' AND category:"Pearson-UK:Qualification-Subject/{slug}"'
               ' AND type:"dam:Asset"')
    hits, page = [], 0
    while page < 20:
        payload = {"params": f"query=&filters={quote(filters, safe='')}&hitsPerPage=1000&page={page}"}
        r = httpx.post(ALGOLIA, json=payload, timeout=30)
        if r.status_code != 200:
            break
        data = r.json()
        hits.extend(data.get("hits", []))
        if page + 1 >= data.get("nbPages", 1):
            break
        page += 1
    return hits


def hit_kind(hit, url_l: str):
    cats = " ".join(str(c).lower() for c in (hit.get("category") or []))
    title = (hit.get("title") or "").lower()
    if "document-type/mark" in cats or "mark scheme" in title or any(x in url_l for x in ("-rms-", "-msc-", "_rms_", "_msc_")):
        return "MS"
    if "document-type/question" in cats or "question paper" in title or any(x in url_l for x in ("-que-", "_que_")):
        return "QP"
    return None


def hit_unit(hit):
    for c in hit.get("category") or []:
        m = re.search(r"Unit/Unit-(\d+)", str(c))
        if m:
            return m.group(1)
    m = re.search(r"unit\s*(\d+)", (hit.get("title") or "").lower())
    return m.group(1) if m else None


def hit_year_season(hit):
    for c in hit.get("category") or []:
        m = re.search(r"Exam-Series/([A-Za-z]+)-(\d{4})", str(c))
        if m:
            se = SEASON_FROM_SERIES.get(m.group(1).lower())
            if se:
                return int(m.group(2)), se
    return None, None


def verify_page1(pdf: bytes, want_kind: str, year: int, season: str, code: str | None) -> tuple[bool, str]:
    """Confirm a downloaded asset is the paper we asked for.

    Mark schemes print the session in plain text ("Mark Scheme (Results) Summer
    2021") so we verify kind + session + year + code. Question-paper *cover*
    sheets carry no month name — only the paper code (WEC12) and a "©{year}"
    copyright — so for QPs we verify kind + code + copyright-year and trust the
    (authoritative) Algolia Exam-Series tag for the season.
    """
    try:
        with fitz.open(stream=pdf, filetype="pdf") as d:
            page1 = d[0].get_text()
    except Exception as e:
        return False, f"unreadable {e}"
    flat = " ".join(page1.split())
    squashed = flat.upper().replace(" ", "")
    is_ms = bool(re.search(r"mark scheme|marking scheme", flat, re.I))
    kind = "MS" if is_ms else "QP"
    if kind != want_kind:
        return False, f"kind {kind}!={want_kind}"
    if code and code.upper() not in squashed:
        return False, f"code {code} absent from page-1"
    if want_kind == "MS":
        sm = re.search(r"(January|February|March|May|June|Summer|October|November|Winter)\s+(20\d{2})", flat, re.I)
        if not sm:
            return False, "no session in page-1 text"
        se = SEASON_FROM_SERIES.get(sm.group(1).lower())
        yr = int(sm.group(2))
        if yr != year or se != season:
            return False, f"session {se} {yr}!={season} {year}"
        return True, f"ok ({sm.group(0)}/{code})"
    # QP: verify the copyright year matches the exam year (cover has no month).
    cy = re.search(r"(20\d{2})\s*Pearson|©\s?(20\d{2})", flat)
    cyear = int(next(g for g in (cy.groups() if cy else []) if g)) if cy else None
    if cyear is not None and cyear != year:
        return False, f"copyright {cyear}!={year}"
    return True, f"ok (QP {code} ©{cyear})"


def code_from_url(url: str) -> str | None:
    m = re.search(r"(w[a-z]{2}\d{2})", url.lower())
    return m.group(1).upper() if m else None


def fetch_ial_gaps(subject_filter: str | None):
    subs = requests.get(f"{SUPABASE_URL}/rest/v1/subjects?select=id,name,code,level&level=eq.IAL",
                        headers=H, timeout=60).json()
    gaps = []
    for s in subs:
        if subject_filter and s["name"] != subject_filter:
            continue
        if s["name"] not in SUBJECT_SLUGS:
            continue
        rows = fetch_subject_rows(s["id"])
        for row in rows:
            miss = []
            if not row.get("pdf_url"):
                miss.append("QP")
            if not row.get("markscheme_pdf_url"):
                miss.append("MS")
            for kind in miss:
                gaps.append({"subject": s["name"], "subject_id": s["id"], "code": s["code"],
                             "kind": kind, "year": row["year"], "season": row["season"],
                             "paper_number": row["paper_number"], "paper_id": row["id"]})
    return gaps


def get_r2():
    import boto3
    from botocore.config import Config
    return boto3.client("s3", endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
                        aws_access_key_id=R2_ACCESS_KEY, aws_secret_access_key=R2_SECRET,
                        region_name="auto", config=Config(retries={"max_attempts": 3}))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--subject", default=None)
    args = ap.parse_args()

    gaps = fetch_ial_gaps(args.subject)
    by_subject = defaultdict(list)
    for g in gaps:
        by_subject[g["subject"]].append(g)
    print(f"IAL gaps to attempt: {len(gaps)} across {len(by_subject)} subjects\n")

    r2 = get_r2() if args.commit else None
    filled = miss = rejected = 0
    report = []

    for subject, its in sorted(by_subject.items()):
        slugs = SUBJECT_SLUGS[subject]
        hits = []
        for slug in slugs:
            hits = algolia_hits(slug)
            if hits:
                break
        is_maths = subject in MATHS_CODE
        want_code = MATHS_CODE.get(subject, "").lower()

        # index hits by (unit_or_code, year, season, kind) -> url
        idx = {}
        for h in hits:
            url = (h.get("url") or h.get("path") or "")
            if not url.lower().endswith(".pdf"):
                continue
            url_l = url.lower()
            kind = hit_kind(h, url_l)
            year, season = hit_year_season(h)
            if not kind or not year or not season:
                continue
            if is_maths:
                if want_code not in url_l:
                    continue
                key = ("_maths", year, season, kind)
            else:
                unit = hit_unit(h)
                if not unit:
                    continue
                key = (f"Unit_{unit}", year, season, kind)
            idx.setdefault(key, url)

        # derive R2 URL shape once for the subject
        rows = fetch_subject_rows(its[0]["subject_id"])
        qp_shape, ms_shape, errs = derive_shapes(rows)
        row_by_id = {r["id"]: r for r in rows}
        if errs:
            print(f"!! {subject}: URL builder self-check FAILED — skipping ({len(errs)} errors)")
            miss += len(its)
            continue

        print(f"=== {subject}  (algolia hits={len(hits)}) ===")
        for g in sorted(its, key=lambda x: (x["paper_number"], x["year"], x["season"], x["kind"])):
            ukey = ("_maths" if is_maths else g["paper_number"], g["year"], g["season"], g["kind"])
            src = idx.get(ukey)
            tag = f"{g['paper_number']:7} {g['year']} {g['season']:8} {g['kind']}"
            if not src:
                print(f"  MISS  {tag}  (no Algolia hit)")
                miss += 1
                continue
            full = (src if src.startswith("http") else PEARSON_HOST + src).replace(" ", "%20")

            # build target R2 url + confirm DB col still null
            shape = qp_shape if g["kind"] == "QP" else ms_shape
            target = fill_shape(shape, g["year"], g["season"], g["paper_number"])
            key = r2_key_from_url(target)
            col = "pdf_url" if g["kind"] == "QP" else "markscheme_pdf_url"
            cur = row_by_id.get(g["paper_id"])
            if cur and cur.get(col):
                print(f"  ~ already set {tag}")
                continue

            if not args.commit:
                print(f"  [DRY] FILL {tag}  <- {full.split('/')[-1]}")
                report.append({"subject": subject, **{k: g[k] for k in ('year', 'season', 'paper_number', 'kind')},
                               "source": full, "target": target})
                filled += 1
                continue

            # download + verify
            try:
                rr = requests.get(full, headers=UA, timeout=90)
            except Exception as e:
                print(f"  !! download error {tag}: {e}")
                miss += 1
                continue
            if rr.status_code != 200 or rr.content[:4] != b"%PDF":
                print(f"  !! not a pdf {tag}: status={rr.status_code}")
                miss += 1
                continue
            ok, why = verify_page1(rr.content, g["kind"], g["year"], g["season"], code_from_url(full))
            if not ok:
                print(f"  REJECT {tag}: {why}  ({full.split('/')[-1]})")
                rejected += 1
                continue

            out, _, _ = clean_and_stamp(rr.content)
            from botocore.exceptions import ClientError
            try:
                r2.head_object(Bucket=R2_BUCKET, Key=key)
            except ClientError:
                r2.put_object(Bucket=R2_BUCKET, Key=key, Body=out, ContentType="application/pdf")
            resp = requests.patch(f"{SUPABASE_URL}/rest/v1/papers?id=eq.{g['paper_id']}&{col}=is.null",
                                  headers={**H, "Content-Type": "application/json"}, json={col: target}, timeout=60)
            if resp.status_code not in (200, 204):
                print(f"  !! DB patch failed {tag}: {resp.status_code} {resp.text[:150]}")
                miss += 1
                continue
            print(f"  FILL  {tag}  <- {full.split('/')[-1]}  [{why}]")
            report.append({"subject": subject, **{k: g[k] for k in ('year', 'season', 'paper_number', 'kind')},
                           "source": full, "target": target})
            filled += 1
        print()

    print(f"{'COMMITTED' if args.commit else 'DRY-RUN'}: filled={filled} miss={miss} rejected={rejected}")
    (ROOT / "scripts" / "ial_algolia_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
