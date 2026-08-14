#!/usr/bin/env python3
"""Probe the official Pearson CDN for a shortlist of obtainable mark-scheme gaps.

For each gap it builds a tight set of candidate CDN URLs (date clusters x format
variants), HEAD-probes them concurrently, stops at the first that returns a PDF,
downloads it, and page-1-verifies the session/paper/type before cleaning +
stamping + uploading to R2 and patching the DB. Early-exit per gap keeps the
request count small and never hammers Pearson.

Dry-run by default; --commit to write.
"""
import argparse
import io
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
_saved = sys.argv
sys.argv = [sys.argv[0]]
from ingest_cambridge_papers import clean_and_stamp  # noqa: E402
from fill_edexcel_paper_gaps import derive_shapes, fetch_subject_rows, fill_shape, r2_key_from_url  # noqa: E402
sys.argv = _saved

import fitz  # noqa: E402

sys.path.insert(0, r"C:\Users\shari\AppData\Local\Temp\claude\c--Users-shari-grademax\46c7b089-85b6-4d9b-8624-440672e63170\scratchpad")
from gen_pearson_candidates import SHORTLIST, ms_dates, IGCSE, IAL, folders_igcse, folders_ial  # noqa: E402

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env.local")
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
R2_PUBLIC_URL = (os.getenv("NEXT_PUBLIC_R2_PUBLIC_URL") or "").rstrip("/")
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "grademax-papers")
H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}

MONTHS = {"january": "jan", "february": "jan", "march": "jan", "may": "may-jun",
          "june": "may-jun", "summer": "may-jun", "october": "oct-nov",
          "november": "oct-nov", "winter": "oct-nov"}


def candidates_for(subj, year, season, pn, kind) -> list[str]:
    dates = ms_dates(season, year)
    urls = []
    if subj in IGCSE:
        folder, spec, code, _ = IGCSE[subj]
        pv = pn.lower()
        for d in dates:
            for t in ("rms", "msc"):
                for nm in (f"{code.lower()}-{pv}-{t}-{d}.pdf", f"{code}_{pv.upper()}_{t}_{d}.pdf"):
                    for fo in folders_igcse(folder, spec):
                        urls.append(f"{fo}/{nm}")
    elif subj in IAL:
        folder, specs, codepfx = IAL[subj]
        if pn.lower().startswith("unit_"):
            unit = pn.split("_")[1]
            codes = [f"{codepfx}1{unit}", f"{codepfx}0{unit}"]
        else:
            codes = [codepfx]
        for code in codes:
            for spec in specs:
                for d in dates:
                    for t in ("rms", "msc"):
                        for nm in (f"{code.lower()}-01-{t}-{d}.pdf", f"{code}_01_{t}_{d}.pdf"):
                            for fo in folders_ial(folder, spec):
                                urls.append(f"{fo}/{nm}")
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u); out.append(u)
    return out


def head_ok(url: str) -> str | None:
    try:
        r = requests.head(url, headers=UA, timeout=20, allow_redirects=True)
        if r.status_code == 200 and "pdf" in r.headers.get("content-type", "").lower():
            return url
    except Exception:
        return None
    return None


def verify_page1(pdf: bytes, want_kind: str, year: int, season: str) -> tuple[bool, str]:
    try:
        with fitz.open(stream=pdf, filetype="pdf") as d:
            flat = " ".join(d[0].get_text().split())
    except Exception as e:
        return False, f"unreadable {e}"
    is_ms = bool(re.search(r"mark scheme|marking scheme", flat, re.I))
    kind = "MS" if is_ms else "QP"
    if kind != want_kind:
        return False, f"kind {kind}!={want_kind}"
    sm = re.search(r"(January|February|March|May|June|Summer|October|November|Winter)\s+(20[0-9]{2})", flat, re.I)
    if not sm:
        return False, "no session in text"
    se = MONTHS.get(sm.group(1).lower()); yr = int(sm.group(2))
    if yr != year or se != season:
        return False, f"session {se} {yr}!={season} {year}"
    return True, f"ok ({sm.group(0)})"


def get_subject_id(name: str, cache: dict) -> str | None:
    if not cache:
        off = 0
        while True:
            r = requests.get(f"{SUPABASE_URL}/rest/v1/subjects?select=id,name&limit=1000&offset={off}", headers=H, timeout=60).json()
            for s in r:
                cache[s["name"]] = s["id"]
            if len(r) < 1000:
                break
            off += 1000
    return cache.get(name)


def find_null_row(sid, year, season, pn) -> dict | None:
    rows = requests.get(f"{SUPABASE_URL}/rest/v1/papers?select=id,year,season,paper_number,pdf_url,markscheme_pdf_url"
                        f"&subject_id=eq.{sid}&year=eq.{year}&season=eq.{season}&paper_number=eq.{requests.utils.quote(pn)}",
                        headers=H, timeout=60).json()
    return rows[0] if rows else None


def get_r2():
    import boto3
    from botocore.config import Config
    return boto3.client("s3", endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
                        aws_access_key_id=R2_ACCESS_KEY, aws_secret_access_key=R2_SECRET,
                        region_name="auto", config=Config(retries={"max_attempts": 3}))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    subj_cache: dict = {}
    shape_cache: dict = {}
    r2 = get_r2() if args.commit else None
    filled = missing = 0
    report = []

    for subj, year, season, pn, kind in SHORTLIST:
        cands = candidates_for(subj, year, season, pn, kind)
        print(f"probing {subj} {year} {season} {pn} {kind} ({len(cands)} candidates)...", flush=True)
        hit_url = hit_bytes = None
        # probe concurrently, stop at first pdf hit
        with ThreadPoolExecutor(max_workers=12) as ex:
            for res in ex.map(head_ok, cands):
                if res:
                    hit_url = res
                    break
        # ThreadPoolExecutor.map returns in order; the first truthy is our earliest hit
        if hit_url:
            rr = requests.get(hit_url, headers=UA, timeout=90)
            if rr.status_code == 200 and rr.content[:4] == b"%PDF":
                ok, why = verify_page1(rr.content, kind, year, season)
                if ok:
                    hit_bytes = rr.content
                else:
                    print(f"  reject {subj} {year} {season} {pn} {kind}: {why}  ({hit_url.split('/')[-1]})")
                    hit_url = None

        if not hit_bytes:
            missing += 1
            print(f"  MISS  {subj} {year} {season} {pn} {kind}  (probed {len(cands)})")
            continue

        # locate DB row + build target url
        sid = get_subject_id(subj, subj_cache)
        row = find_null_row(sid, year, season, pn) if sid else None
        if not row:
            print(f"  !! no DB row for {subj} {year} {season} {pn}")
            continue
        col = "pdf_url" if kind == "QP" else "markscheme_pdf_url"
        if row.get(col):
            print(f"  ~ already set {subj} {year} {season} {pn} {kind}")
            continue
        if subj not in shape_cache:
            shape_cache[subj] = derive_shapes(fetch_subject_rows(sid))
        qp_sh, ms_sh, errs = shape_cache[subj]
        if errs:
            print(f"  !! shape self-check failed {subj}")
            continue
        shape = qp_sh if kind == "QP" else ms_sh
        target = fill_shape(shape, year, season, pn)
        key = r2_key_from_url(target)

        print(f"  {'[DRY] ' if not args.commit else ''}FILL  {subj} {year} {season} {pn} {kind}  <- {hit_url.split('/')[-1]}")
        report.append({"subject": subj, "year": year, "season": season, "paper": pn, "kind": kind,
                       "source": hit_url, "target": target})
        if not args.commit:
            filled += 1
            continue
        out, _, _ = clean_and_stamp(hit_bytes)
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
        filled += 1

    print(f"\n{'COMMITTED' if args.commit else 'DRY-RUN'}: filled={filled} missing={missing}")
    (ROOT / "scripts" / "probe_pearson_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
