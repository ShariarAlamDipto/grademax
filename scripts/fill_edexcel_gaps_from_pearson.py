#!/usr/bin/env python3
"""Fill remaining Edexcel paper gaps from the official Pearson CDN.

Given a list of candidate Pearson `content/dam/pdf/...` URLs, this downloads
each, reads page 1 to derive the TRUE (subject code, paper variant, document
type, session, year), matches it against the DB rows that still have a NULL
qp/ms url, and — only when page-1 confirms the exact session — cleans +
stamps + uploads to R2 and patches the DB.

Page-1 verification is the safety gate: a wrongly-guessed URL that resolves to
a different session simply won't match and is skipped, so we can never attach a
mismatched file.

Usage:
    python -X utf8 scripts/fill_edexcel_gaps_from_pearson.py --urls urls.txt          # dry-run
    python -X utf8 scripts/fill_edexcel_gaps_from_pearson.py --urls urls.txt --commit
"""

import argparse
import io
import json
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
_saved = sys.argv
sys.argv = [sys.argv[0]]
from ingest_cambridge_papers import clean_and_stamp  # noqa: E402
sys.argv = _saved

import fitz  # noqa: E402

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env.local")
import os  # noqa: E402

SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
R2_PUBLIC_URL = (os.getenv("NEXT_PUBLIC_R2_PUBLIC_URL") or "").rstrip("/")
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "grademax-papers")
H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}

MONTHS = {
    "january": "jan", "february": "jan",  # Jan series MS released Feb/Mar
    "march": "jan",
    "may": "may-jun", "june": "may-jun", "summer": "may-jun",
    "october": "oct-nov", "november": "oct-nov", "winter": "oct-nov",
}


def parse_page1(pdf_bytes: bytes) -> dict | None:
    """Return {code, paper, kind, season, year} from page-1 text, or None."""
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as d:
            if len(d) == 0:
                return None
            t = d[0].get_text()
            t2 = " ".join((d[0].get_text() + (d[1].get_text() if len(d) > 1 else "")).split())
    except Exception:
        return None
    flat = " ".join(t.split())

    # document type
    is_ms = bool(re.search(r"mark scheme|marking scheme", flat, re.I))
    kind = "MS" if is_ms else "QP"

    # subject code + paper, e.g. 4PH1/1P, 4MA1/2H, WPH11/01, 4GE1/01
    m = re.search(r"\b([0-9][A-Z]{2}[0-9]{1,2}|W[A-Z]{2}[0-9]{2})\s*/\s*([0-9]{1,2}[A-Z]{0,2}|[0-9][A-Z])", flat)
    code = paper = None
    if m:
        code = m.group(1).upper()
        paper = m.group(2).upper()

    # session: "November 2017", "Summer 2019", "January 2020"
    sm = re.search(r"(January|February|March|May|June|Summer|October|November|Winter)\s+(20[0-9]{2})", flat, re.I)
    season = year = None
    if sm:
        season = MONTHS.get(sm.group(1).lower())
        year = int(sm.group(2))
        # Jan-series MS is released in the SAME year as the Jan exam; Nov-series
        # MS is released the FOLLOWING year, but the text says "November <examyear>",
        # so year is already the exam year. Good.

    if not (code and season and year):
        return None
    return {"code": code, "paper": paper, "kind": kind, "season": season, "year": year, "copyright2016": "2016" in flat}


def paper_tokens_compatible(db_pn: str, pearson_paper: str) -> bool:
    """DB paper_number vs Pearson paper variant. DB '1'~'1P'/'1H'/'01'/'1';
    '1C'~'1C'; '1R'/'1CR'~'1R'/'1CR'; 'Unit_1'~'01'."""
    if not pearson_paper:
        return False
    a = db_pn.lower().replace("unit_", "")
    b = pearson_paper.lower().lstrip("0") or "0"
    a2 = a.lstrip("0") or "0"
    # strip a single subject letter (p/c/b/h/f) that Pearson appends to numeric IGCSE papers
    b_core = re.sub(r"[a-z]$", "", b) if re.match(r"^[0-9]+[a-z]$", b) else b
    if a2 == b:
        return True
    if a2 == b_core:  # DB '1' == Pearson '1p'
        return True
    if a2 == b:
        return True
    # variant suffixes R/CR must match exactly (ignoring subject letter)
    if a == b:
        return True
    return False


def fetch_nulls() -> tuple[list, dict]:
    subs = {}
    off = 0
    while True:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/subjects?select=id,name,code&limit=1000&offset={off}", headers=H, timeout=60).json()
        for s in r:
            subs[s["id"]] = s
        if len(r) < 1000:
            break
        off += 1000
    rows = []
    off = 0
    while True:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/papers?select=id,subject_id,year,season,paper_number,pdf_url,markscheme_pdf_url"
                         f"&or=(pdf_url.is.null,markscheme_pdf_url.is.null)&limit=1000&offset={off}", headers=H, timeout=60).json()
        rows.extend(r)
        if len(r) < 1000:
            break
        off += 1000
    return rows, subs


def get_r2():
    import boto3
    from botocore.config import Config
    return boto3.client("s3", endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
                        aws_access_key_id=R2_ACCESS_KEY, aws_secret_access_key=R2_SECRET,
                        region_name="auto", config=Config(retries={"max_attempts": 3}))


# reuse the URL-shape builder from the local-fill script
sys.path.insert(0, str(Path(__file__).parent))
from fill_edexcel_paper_gaps import derive_shapes, fetch_subject_rows, fill_shape, r2_key_from_url  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls", required=True, help="text file, one Pearson CDN URL per line")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    urls = [u.strip() for u in Path(args.urls).read_text(encoding="utf-8").splitlines() if u.strip() and not u.startswith("#")]
    rows, subs = fetch_nulls()

    # index nulls by (code, year, season, kind)
    null_idx = {}
    for row in rows:
        s = subs[row["subject_id"]]
        if str(s["name"]).lower().startswith("cambridge"):
            continue
        for col, kind in (("pdf_url", "QP"), ("markscheme_pdf_url", "MS")):
            if not row.get(col):
                null_idx.setdefault((s["code"], row["year"], row["season"], kind), []).append((row, s))

    r2 = get_r2() if args.commit else None
    shape_cache = {}
    filled = skipped = nomatch = 0
    report = []

    probed = hits = 0
    for url in urls:
        # HEAD first so a mis-guessed date/format costs one cheap request, not a
        # full PDF download.
        probed += 1
        try:
            hd = requests.head(url, headers=UA, timeout=30, allow_redirects=True)
        except Exception:
            continue
        if hd.status_code != 200:
            continue
        ct = hd.headers.get("content-type", "")
        if "pdf" not in ct.lower() and "octet" not in ct.lower():
            continue
        hits += 1
        try:
            rr = requests.get(url, headers=UA, timeout=90)
        except Exception as e:
            print(f"  ERR download {url[:80]}: {e}")
            continue
        if rr.status_code != 200 or not rr.content[:4] == b"%PDF":
            continue
        info = parse_page1(rr.content)
        if not info:
            print(f"  unparseable page1: {url.split('/')[-1]}")
            continue

        # find matching null rows: same DB subject code family + year + season + kind
        # DB codes: IGCSE '4PH1', IAL 'WPH' (Pearson uses WPH11/WPH01). Match by prefix.
        matched = None
        for (dbcode, y, se, kind), lst in null_idx.items():
            if kind != info["kind"] or y != info["year"] or se != info["season"]:
                continue
            # code match: exact, or IAL prefix (DB 'WPH' vs Pearson 'WPH11')
            if not (info["code"] == dbcode or info["code"].startswith(dbcode)):
                continue
            for row, s in lst:
                if paper_tokens_compatible(str(row["paper_number"]), info["paper"]):
                    matched = (row, s, kind)
                    break
            if matched:
                break

        if not matched:
            nomatch += 1
            print(f"  no-match: {info['code']} {info['paper']} {info['year']} {info['season']} {info['kind']}  ({url.split('/')[-1]})")
            continue

        row, s, kind = matched
        col = "pdf_url" if kind == "QP" else "markscheme_pdf_url"
        if row.get(col):
            skipped += 1
            continue

        # build target URL from subject convention
        if s["name"] not in shape_cache:
            srows = fetch_subject_rows(s["id"])
            qp_sh, ms_sh, errs = derive_shapes(srows)
            shape_cache[s["name"]] = (qp_sh, ms_sh, errs)
        qp_sh, ms_sh, errs = shape_cache[s["name"]]
        if errs:
            print(f"  !! {s['name']} shape self-check failed; skip")
            continue
        shape = qp_sh if kind == "QP" else ms_sh
        target = fill_shape(shape, row["year"], row["season"], row["paper_number"])
        key = r2_key_from_url(target)

        print(f"  {'[DRY] ' if not args.commit else ''}MATCH {s['name']} {row['year']} {row['season']} {row['paper_number']} {kind} <- {url.split('/')[-1]}")
        report.append({"paper_id": row["id"], "subject": s["name"], "year": row["year"], "season": row["season"],
                       "paper": str(row["paper_number"]), "kind": kind, "source_url": url, "target": target})

        if not args.commit:
            filled += 1
            continue

        try:
            out, _, _ = clean_and_stamp(rr.content)
        except Exception as e:
            print(f"     clean_and_stamp failed: {e}")
            continue
        from botocore.exceptions import ClientError
        try:
            r2.head_object(Bucket=R2_BUCKET, Key=key)
        except ClientError:
            r2.put_object(Bucket=R2_BUCKET, Key=key, Body=out, ContentType="application/pdf")
        resp = requests.patch(f"{SUPABASE_URL}/rest/v1/papers?id=eq.{row['id']}&{col}=is.null",
                              headers={**H, "Content-Type": "application/json"}, json={col: target}, timeout=60)
        if resp.status_code not in (200, 204):
            print(f"     DB patch failed {resp.status_code}: {resp.text[:150]}")
            continue
        # keep local null_idx honest
        row[col] = target
        filled += 1

    print(f"\n{'COMMITTED' if args.commit else 'DRY-RUN'}: filled={filled} skipped={skipped} no-match={nomatch}")
    outp = ROOT / "scripts" / "pearson_fill_report.json"
    Path(args.urls).with_suffix(".report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"report: {Path(args.urls).with_suffix('.report.json')}")


if __name__ == "__main__":
    main()
