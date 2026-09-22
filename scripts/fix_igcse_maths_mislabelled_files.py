#!/usr/bin/env python3
"""Fix mislabelled Edexcel IGCSE Mathematics A / Mathematics B files.

The maths subjects cannot use `fix_igcse_edexcel_mislabelled_files.py`: Pearson's
public Algolia catalogue lists only 8 current-spec (4MA1) assets, all training
material, so there is no official source to pull from. Two other routes exist:

1. **A correct twin in the same session.** Mathematics A lists every paper twice
   under parallel names (`1` == `1F`, `1H` == `3H`), and the defect is usually on
   only one of the pair. Where the twin's file is demonstrably right, copy it --
   no download, no watermark handling, and the provenance is the archive's own.

2. **Physics & Maths Tutor**, indexed from its per-paper listing pages. PMT's
   `Paper-1H` folder holds what Edexcel prints as `3H`, so the mapping below
   records both the PMT token and the Edexcel cover code to verify against.
   PMT's sibling `MA/` folders are **Model Answers**, not question papers -- the
   original source of this whole contamination -- and are never indexed.

Every candidate is gated on its own cover (paper code + session) before it may
replace anything, and replaced originals are quarantined.

Dry-run by default; --commit writes the archive, --upload also pushes to R2.

Usage:
    python -X utf8 scripts/fix_igcse_maths_mislabelled_files.py
    python -X utf8 scripts/fix_igcse_maths_mislabelled_files.py --commit --upload
"""

from __future__ import annotations

import argparse
import collections
import io
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from urllib.parse import unquote

import fitz  # PyMuPDF
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from source_m1_question_papers import clean_and_stamp, verify  # noqa: E402
from audit_igcse_edexcel_labels import (  # noqa: E402
    ARCHIVE_ROOT, FILENAME_RE, MONTH_SEASON, inspect, parse_variant,
    variants_compatible,
)
from fix_igcse_edexcel_mislabelled_files import pearson_catalog  # noqa: E402
from repair_igcse_edexcel_label_mismatches import live_keys  # noqa: E402

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env.local")
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "grademax-papers")
QUARANTINE = REPO_ROOT / "data" / "quarantine" / "igcse_maths_mislabelled"

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")}
PMT_PAGES = ["gcse-maths/edexcel-igcse-a-paper-1", "gcse-maths/edexcel-igcse-a-paper-2",
             "gcse-maths/edexcel-igcse-b-paper-1", "gcse-maths/edexcel-igcse-b-paper-2"]
PMT_LINK_RE = re.compile(r'(https://pmt\.physicsandmathstutor\.com/download/Maths/[^"\'<>]+\.pdf)')
PMT_PATH_RE = re.compile(
    r"/Edexcel-IGCSE-(A|B)/Paper-([12][FH]?)/(QP|MS|MA)/"
    r"(January|June|November|May)\s+(20\d{2})(\s+\(R\))?\s+(QP|MS|MA)\.pdf$")
PMT_DELAY_S = 4.0   # PMT resets the connection if pushed harder than this

# archive slot token -> (PMT paper token, Edexcel code printed on the cover)
MATHS_A_MAP = {
    "1": ("1F", "1F"), "1R": ("1FR", "1FR"), "1F": ("1F", "1F"), "1FR": ("1FR", "1FR"),
    "2": ("2F", "2F"), "2R": ("2FR", "2FR"), "2F": ("2F", "2F"), "2FR": ("2FR", "2FR"),
    "1H": ("1H", "3H"), "1HR": ("1HR", "3HR"), "3H": ("1H", "3H"), "3HR": ("1HR", "3HR"),
    "2H": ("2H", "4H"), "2HR": ("2HR", "4HR"), "4H": ("2H", "4H"), "4HR": ("2HR", "4HR"),
}
MATHS_B_MAP = {t: (t, t) for t in ("1", "1R", "2", "2R")}
SUBJECTS = {"Mathematics_A": ("A", MATHS_A_MAP), "Mathematics_B": ("B", MATHS_B_MAP)}
# Pearson Qualification-Subject slugs. NOT the generic "Mathematics" one, which
# carries 244 assets of training material and no exam papers.
PEARSON_MATHS_SLUG = {"Mathematics_A": "Mathematics-A", "Mathematics_B": "Mathematics-B"}

MS_RE = re.compile(r"mark scheme|marking scheme", re.I)
SESSION_RE = re.compile(r"\b(January|February|March|April|May|June|July|Summer|"
                        r"September|October|November|December|Winter)\s+(20\d{2})\b", re.I)
EXAM_DATE_RE = re.compile(
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{1,2})\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(20\d{2})\b", re.I)
PAPER_RE = re.compile(r"\bPAPER\s*:?\s*([0-9]{1,2}[A-Z]{0,3})(?![A-Za-z0-9])", re.I)
REF_RE = re.compile(r"\b4M[AB][01]\s*/\s*([0-9]{1,2}[A-Z]{0,3})(?![A-Za-z0-9])")


def r2_client():
    import boto3
    from botocore.config import Config
    return boto3.client(
        "s3", endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        region_name="auto", config=Config(retries={"max_attempts": 3}))


def pmt_index() -> dict:
    """(spec, paper, year, season, kind) -> url, excluding Model Answers."""
    links, skipped = set(), collections.Counter()
    for page in PMT_PAGES:
        for attempt in range(3):
            try:
                r = requests.get(
                    f"https://www.physicsandmathstutor.com/past-papers/{page}/",
                    headers=UA, timeout=60)
                links |= set(PMT_LINK_RE.findall(r.text))
                break
            except Exception:  # noqa: BLE001
                time.sleep(8)
        time.sleep(PMT_DELAY_S)
    idx = {}
    for link in sorted(links):
        m = PMT_PATH_RE.search(unquote(link))
        if not m:
            continue
        spec, paper, folder, month, year, rflag, _kind = m.groups()
        if folder == "MA":
            skipped["model-answers"] += 1
            continue
        season = {"January": "Jan", "June": "May-Jun", "May": "May-Jun",
                  "November": "Oct-Nov"}[month]
        idx[(spec, paper + ("R" if rflag else ""), year, season, folder)] = link
    print(f"PMT index: {len(idx)} assets "
          f"({skipped['model-answers']} Model Answers excluded)")
    return idx


def cover(body: bytes) -> dict:
    try:
        with fitz.open(stream=body, filetype="pdf") as d:
            page1 = " ".join(d[0].get_text().split())
            head = " ".join(" ".join(d[i].get_text()
                                     for i in range(min(3, d.page_count))).split())
            pages = d.page_count
    except Exception as exc:  # noqa: BLE001
        return {"error": f"unreadable ({type(exc).__name__})"}
    pm = REF_RE.search(head) or PAPER_RE.search(head)
    year = season = ev = None
    m = EXAM_DATE_RE.search(page1)
    if m:
        year, season, ev = m.group(3), MONTH_SEASON[m.group(2).lower()], m.group(0)
    else:
        m = SESSION_RE.search(page1)
        if m:
            year, season, ev = m.group(2), MONTH_SEASON[m.group(1).lower()], m.group(0)
    return {"kind": "MS" if MS_RE.search(page1) else "QP",
            "paper": pm.group(1).upper() if pm else None,
            "year": year, "season": season, "evidence": ev, "pages": pages}


def acceptable(body: bytes, want_code: str, year: str, season: str,
               kind: str) -> tuple[bool, str]:
    c = cover(body)
    if c.get("error"):
        return False, c["error"]
    if c["pages"] < 3:
        return False, f"only {c['pages']} pages"
    if c["kind"] != kind:
        return False, f"kind {c['kind']} != {kind}"
    if not c["paper"]:
        return False, "no paper code on cover"
    if variants_compatible(want_code, c["paper"], subject_uses_tiers=True) is False:
        return False, f"paper {c['paper']} != {want_code}"
    if c["year"] and (c["year"] != year or c["season"] != season):
        return False, f"session {c['year']}/{c['season']} != {year}/{season}"
    if not c["year"]:
        return False, "no session on cover"
    return True, f"{c['paper']} {c['evidence']} ({c['pages']}pp)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--upload", action="store_true")
    args = ap.parse_args()

    index = pmt_index()
    client = r2_client() if args.upload else None
    keys = live_keys() if args.upload else {}
    pearson_catalogs: dict[str, dict] = {}
    fixed = skipped = nosource = 0

    for subject, (spec, mapping) in SUBJECTS.items():
        folder = ARCHIVE_ROOT / subject
        files = sorted(folder.rglob("*.pdf"))
        results = [inspect((str(f.relative_to(REPO_ROOT)), subject, True)) for f in files]
        bad = [r for r in results if r["status"] == "MISMATCH"]
        if not bad:
            continue
        print(f"\n{'=' * 72}\n{subject}: {len(bad)} mislabelled file(s)")

        # everything currently in the archive, by (year, season, kind) -> [(path, cover)]
        by_slot: dict[tuple, list] = {}
        for f in files:
            fn = FILENAME_RE.match(f.name)
            if fn:
                by_slot.setdefault((fn.group("year"), f.parent.name,
                                    fn.group("kind")), []).append(f)

        for r in bad:
            path = REPO_ROOT / r["file"]
            fn = FILENAME_RE.match(path.name)
            year, season = fn.group("year"), path.parent.name
            slot, kind = fn.group("paper").upper(), fn.group("kind")
            tag = f"   {r['slot']:<36}"
            entry = mapping.get(slot)
            if not entry:
                print(f"{tag} no mapping for slot {slot}")
                skipped += 1
                continue
            pmt_token, want_code = entry

            # --- strategy 1: a correct twin already in this session
            body = why = None
            for sib in by_slot.get((year, season, kind), []):
                if sib == path:
                    continue
                ok, note = acceptable(sib.read_bytes(), want_code, year, season, kind)
                if ok:
                    body, why = sib.read_bytes(), f"copied from {sib.name} ({note})"
                    break

            # --- strategy 2: Pearson's own catalogue.
            # The maths subjects DO have one; it just is not under the generic
            # "Mathematics" slug (244 assets, none of them exam papers) but under
            # "Mathematics-A" / "Mathematics-B" (452 / 220 assets). Preferred over
            # PMT because it is the publisher's copy and carries no watermark.
            # The lookup uses want_code -- the code Edexcel actually prints -- so a
            # `Paper_1` slot resolves to Foundation 1F rather than Higher 1H.
            if body is None:
                slug = PEARSON_MATHS_SLUG.get(subject)
                pcat = pearson_catalogs.setdefault(
                    slug, pearson_catalog(slug)) if slug else {}
                for cand in (want_code, pmt_token):
                    purl = pcat.get((year, season, cand, kind))
                    if not purl:
                        continue
                    presp = requests.get(purl, headers=UA, timeout=120)
                    ctype = presp.headers.get("content-type", "").lower()
                    if (presp.status_code != 200 or presp.content[:4] != b"%PDF"
                            or "html" in ctype):
                        continue
                    ok, note = acceptable(presp.content, want_code, year, season, kind)
                    if ok:
                        body = presp.content
                        why = f"Pearson {purl.split('/')[-1]} ({note})"
                        break

            # --- strategy 3: PMT
            if body is None:
                url = index.get((spec, pmt_token, year, season, kind))
                if not url:
                    print(f"{tag} not on PMT or Pearson for {year}/{season} "
                          f"{pmt_token} {kind}")
                    nosource += 1
                    continue
                try:
                    resp = requests.get(url, headers=UA, timeout=120)
                except Exception as exc:  # noqa: BLE001
                    print(f"{tag} download failed: {exc}")
                    skipped += 1
                    continue
                time.sleep(PMT_DELAY_S)
                if resp.status_code != 200 or resp.content[:4] != b"%PDF":
                    print(f"{tag} not a PDF (http {resp.status_code})")
                    skipped += 1
                    continue
                ok, note = acceptable(resp.content, want_code, year, season, kind)
                if not ok:
                    print(f"{tag} REJECTED: {note}")
                    skipped += 1
                    continue
                body, why = resp.content, f"PMT {url.split('/')[-1]} ({note})"

            if not args.commit:
                print(f"{tag} [DRY] <- {why}")
                fixed += 1
                continue
            cleaned, _ = clean_and_stamp(body)
            pmt_gone, gm = verify(cleaned)
            if not (pmt_gone and gm):
                print(f"{tag} REJECTED: stamp check (pmt_gone={pmt_gone}, grademax={gm})")
                skipped += 1
                continue
            QUARANTINE.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(QUARANTINE / path.name))
            path.write_bytes(cleaned)
            print(f"{tag} FIXED <- {why}")
            fixed += 1
            if args.upload:
                # The key must come from the row that serves this file. Building
                # it from the folder name gives `igcse/mathematics_a/...` while
                # production serves `igcse/maths-a/...`, so a built key uploads a
                # correct paper to a URL nothing reads and leaves the wrong one live.
                key = keys.get(path.name)
                if not key:
                    print(f"{' ' * 39}no papers row -- not uploaded")
                    continue
                try:
                    client.put_object(Bucket=R2_BUCKET, Key=key, Body=cleaned,
                                      ContentType="application/pdf")
                    print(f"{' ' * 39}uploaded -> {key}")
                except Exception as exc:  # noqa: BLE001
                    print(f"{' ' * 39}R2 upload FAILED: {exc}")

    print(f"\n{'COMMITTED' if args.commit else 'DRY-RUN'}: "
          f"fixed={fixed} skipped={skipped} no-source={nosource}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
