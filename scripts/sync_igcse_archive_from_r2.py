#!/usr/bin/env python3
"""Make the local Edexcel IGCSE archive match what production actually serves.

Some repairs are applied directly to R2 and the `papers` rows (because the fix is
"point this row at the correct document"), which leaves `data/Ultimate Final IGCSE`
holding the old, wrong file. Since that archive is the input to the label audit and
to any future re-ingest, a stale copy would make the audit report defects that are
already fixed in production -- or, worse, let a re-ingest reintroduce them.

This walks every Edexcel IGCSE `papers` row, and where the local archive file
differs from the R2 object the row points at, overwrites the local copy. Files
absent locally are created; files with no row are left alone and reported.

Dry-run by default; --commit to write.

Usage:
    python -X utf8 scripts/sync_igcse_archive_from_r2.py
    python -X utf8 scripts/sync_igcse_archive_from_r2.py --commit --subject "Mathematics A"
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "grademax-papers")
ARCHIVE = REPO_ROOT / "data" / "Ultimate Final IGCSE"

# DB subject name -> archive folder
FOLDER = {
    "Accounting": "Accounting", "Bangla": "Bangla", "Biology": "Biology",
    "Business Studies": "Business_Studies", "Chemistry": "Chemistry",
    "Commerce": "Commerce", "Computer Science": "Computer_Science",
    "Economics": "Economics", "English Language A": "English_A",
    "English Language B": "English_B", "Further Pure Mathematics": "Further_Pure_Maths",
    "Geography": "Geography", "Human Biology": "Human_Biology", "ICT": "ICT",
    "Mathematics A": "Mathematics_A", "Mathematics B": "Mathematics_B",
    "Mechanics 1": "Mechanics_1", "Physics": "Physics",
}
SEASON_FOLDER = {"jan": "Jan", "may-jun": "May-Jun", "oct-nov": "Oct-Nov",
                 "specimen": "Specimen"}


def r2_client():
    import boto3
    from botocore.config import Config
    return boto3.client(
        "s3", endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        region_name="auto", config=Config(retries={"max_attempts": 3}))


def key_of(url):
    m = re.search(r"\.r2\.dev/(.+)$", url or "")
    return m.group(1) if m else None


def fetch_all(path):
    out, off = [], 0
    while True:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/{path}&limit=1000&offset={off}",
                         headers=H, timeout=60)
        r.raise_for_status()
        b = r.json()
        out += b
        if len(b) < 1000:
            return out
        off += 1000


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--subject")
    args = ap.parse_args()

    subjects = [s for s in fetch_all("subjects?select=id,name,level")
                if (s.get("level") or "").lower() == "igcse"
                and not s["name"].startswith("Cambridge")]
    if args.subject:
        subjects = [s for s in subjects if s["name"].lower() == args.subject.lower()]

    client = r2_client()
    updated = created = same = missing = 0

    for s in sorted(subjects, key=lambda s: s["name"]):
        folder = FOLDER.get(s["name"])
        if not folder:
            continue
        rows = fetch_all(f"papers?select=year,season,paper_number,pdf_url,"
                         f"markscheme_pdf_url&subject_id=eq.{s['id']}&order=year")
        changes = []
        for r in rows:
            season_dir = SEASON_FOLDER.get(r["season"])
            if not season_dir:
                continue
            for col, kind in (("pdf_url", "QP"), ("markscheme_pdf_url", "MS")):
                key = key_of(r.get(col))
                if not key:
                    continue
                local = (ARCHIVE / folder / str(r["year"]) / season_dir /
                         key.split("/")[-1])
                try:
                    body = client.get_object(Bucket=R2_BUCKET, Key=key)["Body"].read()
                except Exception as exc:  # noqa: BLE001
                    print(f"   !! {key}: {exc}")
                    missing += 1
                    continue
                if local.exists():
                    if hashlib.md5(local.read_bytes()).hexdigest() == \
                       hashlib.md5(body).hexdigest():
                        same += 1
                        continue
                    action = "update"
                    updated += 1
                else:
                    action = "create"
                    created += 1
                changes.append((action, local, body))
        if changes:
            print(f"\n{s['name']}: {len(changes)} file(s) out of sync")
            for action, local, _b in changes[:8]:
                print(f"   {action:7} {local.relative_to(REPO_ROOT)}")
            if len(changes) > 8:
                print(f"   ... +{len(changes) - 8} more")
            if args.commit:
                for _action, local, body in changes:
                    local.parent.mkdir(parents=True, exist_ok=True)
                    local.write_bytes(body)

    print(f"\n{'COMMITTED' if args.commit else 'DRY-RUN'}: "
          f"updated={updated} created={created} already-identical={same} unreadable={missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
