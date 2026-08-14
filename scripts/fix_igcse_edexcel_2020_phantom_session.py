#!/usr/bin/env python3
"""Collapse the phantom `2020 may-jun` session into the real `2020 oct-nov` one,
for every Edexcel IGCSE subject.

Why
---
The summer 2020 series was cancelled worldwide (COVID). Pearson reused the
already-printed summer papers for the **November 2020** series, so those papers
still carry "Monday 4 May 2020" / "Wednesday 10 June 2020" on the cover. The PMT
scrape read that printed date as the session and filed a second copy of the whole
November series under `2020/May-Jun` -- with the November mark schemes attached,
which is why the audit sees `2020/May-Jun/*_MS` announcing "November 2020".

Proof it is a duplicate, not a distinct series: the two folders share Pearson
barcodes (e.g. Accounting P63011A appears in both), and Pearson's catalogue lists
no summer-2020 asset of any kind for these subjects.

What this does, per subject
---------------------------
1. For every `may-jun` paper, find the `oct-nov` row with the same paper_number.
2. If `oct-nov` is missing a QP or MS that `may-jun` has, copy that file across
   (R2 object + DB column) so no unique content is lost.
3. Back up, then delete the `may-jun` R2 objects, DB rows and local archive folder.

A `may-jun` paper with no `oct-nov` counterpart is reported and left completely
untouched -- never deleted -- so anything unexpected survives for manual review.

Dry-run by default; --commit to write.

Usage:
    python -X utf8 scripts/fix_igcse_edexcel_2020_phantom_session.py
    python -X utf8 scripts/fix_igcse_edexcel_2020_phantom_session.py --subject Biology
    python -X utf8 scripts/fix_igcse_edexcel_2020_phantom_session.py --commit
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import fitz  # PyMuPDF
import requests
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
R2_PUBLIC = (os.getenv("NEXT_PUBLIC_R2_PUBLIC_URL")
             or "https://pub-b96af5a8f7044337bcb17a51b3fd4a60.r2.dev").rstrip("/")
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "grademax-papers")

ARCHIVE = REPO_ROOT / "data" / "Ultimate Final IGCSE"
BACKUP = REPO_ROOT / "data" / "quarantine" / "igcse_2020_phantom_session"

BAD_SEASON, GOOD_SEASON = "may-jun", "oct-nov"
BAD_FOLDER, GOOD_FOLDER = "May-Jun", "Oct-Nov"
YEAR = "2020"

# DB subject name -> archive folder
ARCHIVE_FOLDER = {
    "Accounting": "Accounting", "Bangla": "Bangla", "Biology": "Biology",
    "Business Studies": "Business_Studies", "Chemistry": "Chemistry",
    "Commerce": "Commerce", "Computer Science": "Computer_Science",
    "Economics": "Economics", "English Language A": "English_A",
    "English Language B": "English_B", "Further Pure Mathematics": "Further_Pure_Maths",
    "Geography": "Geography", "Human Biology": "Human_Biology", "ICT": "ICT",
    "Mathematics A": "Mathematics_A", "Mathematics B": "Mathematics_B",
    "Mechanics 1": "Mechanics_1", "Physics": "Physics",
}
# Chemistry duplicates its own papers under two naming schemes (1 vs 1C) and its
# oct-nov rows are incomplete; Mathematics A's oct-nov folder holds January papers.
# Both need their own treatment, so they are excluded from this bulk pass.
NEEDS_MANUAL = {"Chemistry", "Mathematics A"}

MS_RE = re.compile(r"mark scheme|marking scheme", re.I)
SESSION_RE = re.compile(r"\b(January|February|March|May|June|Summer|October|November|Winter)\s+(20\d{2})\b", re.I)


def r2_client():
    import boto3
    from botocore.config import Config
    return boto3.client(
        "s3", endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY, aws_secret_access_key=R2_SECRET,
        region_name="auto", config=Config(retries={"max_attempts": 3}))


def key_of(url: str) -> str | None:
    if not url:
        return None
    m = re.search(r"\.r2\.dev/(.+)$", url)
    return m.group(1) if m else None


def verify_for_november(body: bytes, kind: str) -> tuple[bool, str]:
    """A file may only be promoted into the oct-nov slot if its own cover is
    consistent with the November 2020 series.

    Mark schemes must say "November 2020" outright. Question papers print the
    original (cancelled) May/June date because Pearson reprinted them unchanged,
    so for those we require only that the cover names 2020.
    """
    try:
        with fitz.open(stream=body, filetype="pdf") as d:
            if d.page_count < 3:
                return False, f"only {d.page_count} pages"
            page1 = " ".join(d[0].get_text().split())
    except Exception as exc:  # noqa: BLE001
        return False, f"unreadable ({type(exc).__name__})"

    is_ms = bool(MS_RE.search(page1))
    if kind == "MS":
        if not is_ms:
            return False, "no mark-scheme text on cover"
        m = SESSION_RE.search(page1)
        if not m:
            return False, "no session on cover"
        if m.group(1).lower() != "november" or m.group(2) != YEAR:
            return False, f"session says {m.group(0)}, expected November 2020"
        return True, m.group(0)
    if is_ms:
        return False, "mark scheme in a QP slot"
    if YEAR not in page1:
        return False, "cover does not mention 2020"
    return True, "QP ©2020 (reprinted Nov 2020)"


def fetch(path: str):
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{path}", headers=H, timeout=60)
    r.raise_for_status()
    return r.json()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--subject", help="one DB subject name")
    args = ap.parse_args()

    subjects = [s for s in fetch("subjects?select=id,name,level&limit=300")
                if (s.get("level") or "").lower() == "igcse"
                and not s["name"].startswith("Cambridge")]
    if args.subject:
        subjects = [s for s in subjects if s["name"].lower() == args.subject.lower()]

    client = r2_client()
    manifest = {"generated": datetime.now(timezone.utc).isoformat(),
                "committed": args.commit, "subjects": []}
    tot_promoted = tot_deleted_rows = tot_deleted_objs = 0
    skipped_subjects, orphans = [], []

    for s in sorted(subjects, key=lambda s: s["name"]):
        name = s["name"]
        rows = fetch(f"papers?select=id,year,season,paper_number,pdf_url,markscheme_pdf_url"
                     f"&subject_id=eq.{s['id']}&year=eq.{YEAR}")
        bad = {str(r["paper_number"]): r for r in rows if r["season"] == BAD_SEASON}
        good = {str(r["paper_number"]): r for r in rows if r["season"] == GOOD_SEASON}
        if not bad:
            continue
        if name in NEEDS_MANUAL:
            skipped_subjects.append(name)
            print(f"\n{name}: {len(bad)} may-jun row(s) -- SKIPPED (needs individual handling)")
            continue

        print(f"\n{name}")
        promoted, subject_orphans = [], []
        for pn, brow in sorted(bad.items()):
            grow = good.get(pn)
            if not grow:
                subject_orphans.append(pn)
                print(f"   paper {pn:4} -- no oct-nov counterpart; LEFT UNTOUCHED")
                continue
            for col, kind in (("pdf_url", "QP"), ("markscheme_pdf_url", "MS")):
                if grow.get(col) or not brow.get(col):
                    continue
                src_key = key_of(brow[col])
                if not src_key:
                    continue
                dst_key = src_key.replace(f"/{YEAR}/{BAD_SEASON}/", f"/{YEAR}/{GOOD_SEASON}/")
                dst_key = dst_key.replace(f"_{YEAR}_{BAD_FOLDER}_", f"_{YEAR}_{GOOD_FOLDER}_")
                try:
                    body = client.get_object(Bucket=R2_BUCKET, Key=src_key)["Body"].read()
                except Exception as exc:  # noqa: BLE001
                    print(f"   paper {pn:4} {kind}: cannot read source ({exc}); skipped")
                    continue
                ok, why = verify_for_november(body, kind)
                if not ok:
                    print(f"   paper {pn:4} {kind}: NOT promoted -- {why}")
                    continue
                print(f"   paper {pn:4} {kind}: fills empty oct-nov slot  ({why})")
                promoted.append({"paper": pn, "kind": kind, "key": dst_key})
                if args.commit:
                    client.put_object(Bucket=R2_BUCKET, Key=dst_key, Body=body,
                                      ContentType="application/pdf")
                    resp = requests.patch(
                        f"{SUPABASE_URL}/rest/v1/papers?id=eq.{grow['id']}&{col}=is.null",
                        headers={**H, "Content-Type": "application/json"},
                        json={col: f"{R2_PUBLIC}/{dst_key}"}, timeout=60)
                    if resp.status_code not in (200, 204):
                        print(f"      DB patch failed: {resp.status_code} {resp.text[:120]}")

        deletable = {pn: r for pn, r in bad.items() if pn not in subject_orphans}
        keys = []
        for r in deletable.values():
            keys += [k for k in (key_of(r.get("pdf_url")), key_of(r.get("markscheme_pdf_url"))) if k]
        print(f"   -> delete {len(deletable)} may-jun row(s), {len(keys)} R2 object(s)"
              f"{'' if not subject_orphans else f'; keeping {len(subject_orphans)} orphan row(s)'}")

        if args.commit and deletable:
            dest = BACKUP / ARCHIVE_FOLDER.get(name, name)
            dest.mkdir(parents=True, exist_ok=True)
            for k in keys:
                try:
                    body = client.get_object(Bucket=R2_BUCKET, Key=k)["Body"].read()
                    (dest / k.split("/")[-1]).write_bytes(body)
                except Exception as exc:  # noqa: BLE001
                    print(f"      backup failed for {k}: {exc}")
            for k in keys:
                client.delete_object(Bucket=R2_BUCKET, Key=k)
            for r in deletable.values():
                resp = requests.delete(f"{SUPABASE_URL}/rest/v1/papers?id=eq.{r['id']}",
                                       headers=H, timeout=60)
                if resp.status_code not in (200, 204):
                    print(f"      DB delete failed {r['id']}: {resp.status_code}")
            local = ARCHIVE / ARCHIVE_FOLDER.get(name, name) / YEAR / BAD_FOLDER
            if local.exists():
                tgt = dest / "archive"
                if tgt.exists():
                    shutil.rmtree(tgt)
                shutil.move(str(local), str(tgt))

        tot_promoted += len(promoted)
        tot_deleted_rows += len(deletable) if args.commit else 0
        tot_deleted_objs += len(keys) if args.commit else 0
        orphans += [(name, pn) for pn in subject_orphans]
        manifest["subjects"].append({
            "subject": name, "promoted": promoted,
            "deleted_rows": [r["id"] for r in deletable.values()],
            "deleted_keys": keys, "orphans": subject_orphans,
        })

    BACKUP.mkdir(parents=True, exist_ok=True)
    (BACKUP / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("\n" + "=" * 70)
    print(f"{'COMMITTED' if args.commit else 'DRY-RUN'}: promoted={tot_promoted} "
          f"rows_deleted={tot_deleted_rows} objects_deleted={tot_deleted_objs}")
    if skipped_subjects:
        print(f"skipped (handled separately): {', '.join(skipped_subjects)}")
    if orphans:
        print(f"orphan papers left untouched: {orphans}")
    print(f"manifest -> {(BACKUP / 'manifest.json').relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
