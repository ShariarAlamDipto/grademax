#!/usr/bin/env python3
"""Remove two Edexcel IGCSE Physics sessions that Edexcel never ran.

Both are duplicates of a real session that stays intact, so no unique paper is
lost.

`2020/May-Jun` -- the summer 2020 series was cancelled (COVID). Pearson reused
    the already-printed summer papers for the **November 2020** series, which is
    why they still carry "Wednesday 20 May 2020" / "Friday 12 June 2020" on the
    cover. Pearson's own November 2020 assets are byte-identical to these
    (barcodes P65064A / P65065A / P65066A / P65067A), and `2020/Oct-Nov` already
    serves all four. Pearson published no summer-2020 asset of any kind -- no
    question paper, no mark scheme, no examiner report.

`2017/Oct-Nov` -- there was no November 2017 series for 4PH1; the first was 2020.
    Both files are the **specimen** papers (barcodes S52917A / S52918A, published
    September 2017) and are already served under `2017/Specimen`.

Everything is backed up before deletion: the `papers` rows to a JSON file and
every R2 object to `data/quarantine/physics_igcse_phantom_sessions/`.

Dry-run by default; --commit to delete.

Usage:
    python -X utf8 scripts/remove_physics_igcse_phantom_sessions.py
    python -X utf8 scripts/remove_physics_igcse_phantom_sessions.py --commit
"""

from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import sys
from datetime import datetime, timezone
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

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "grademax-papers")

PHYSICS_SUBJECT_ID = "0b142517-d35d-4942-91aa-b4886aaabca3"

BACKUP = REPO_ROOT / "data" / "quarantine" / "physics_igcse_phantom_sessions"
ARCHIVE = REPO_ROOT / "data" / "Ultimate Final IGCSE" / "Physics"

# (year, db season, R2 prefix, local archive folder, why)
TARGETS = [
    ("2020", "may-jun", "igcse/physics/2020/may-jun/", ("2020", "May-Jun"),
     "summer 2020 cancelled; these are the November 2020 papers, already at 2020/Oct-Nov"),
    ("2017", "oct-nov", "igcse/physics/2017/oct-nov/", ("2017", "Oct-Nov"),
     "no November 2017 series; these are the specimen papers, already at 2017/Specimen"),
]


def r2_client():
    import boto3
    from botocore.config import Config
    return boto3.client(
        "s3", endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY, aws_secret_access_key=R2_SECRET,
        region_name="auto", config=Config(retries={"max_attempts": 3}),
    )


def db_rows(year: str, season: str) -> list[dict]:
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/papers"
        f"?select=*&subject_id=eq.{PHYSICS_SUBJECT_ID}&year=eq.{year}&season=eq.{season}",
        headers=H, timeout=60)
    resp.raise_for_status()
    return resp.json()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true", help="actually delete")
    args = ap.parse_args()

    client = r2_client()
    manifest: dict = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "committed": args.commit,
        "sessions": [],
    }

    for year, season, prefix, (arc_year, arc_season), why in TARGETS:
        print(f"\n{year} {season}  --  {why}")
        rows = db_rows(year, season)
        listing = client.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
        keys = [o["Key"] for o in listing.get("Contents", [])]
        print(f"  {len(rows)} DB row(s), {len(keys)} R2 object(s)")
        for k in keys:
            print(f"     {k.split('/')[-1]}")

        session_backup = BACKUP / f"{year}_{season}"
        if args.commit:
            session_backup.mkdir(parents=True, exist_ok=True)
            # 1. back up every object before anything is removed
            for k in keys:
                body = client.get_object(Bucket=R2_BUCKET, Key=k)["Body"].read()
                (session_backup / k.split("/")[-1]).write_bytes(body)
            print(f"  backed up {len(keys)} object(s) -> {session_backup.relative_to(REPO_ROOT)}")

            # 2. delete R2 objects
            for k in keys:
                client.delete_object(Bucket=R2_BUCKET, Key=k)
            print(f"  deleted {len(keys)} R2 object(s)")

            # 3. delete DB rows (id-scoped, one at a time, so a failure is partial not total)
            deleted = 0
            for row in rows:
                resp = requests.delete(f"{SUPABASE_URL}/rest/v1/papers?id=eq.{row['id']}",
                                       headers=H, timeout=60)
                if resp.status_code in (200, 204):
                    deleted += 1
                else:
                    print(f"     DB delete failed for {row['id']}: "
                          f"{resp.status_code} {resp.text[:120]}")
            print(f"  deleted {deleted}/{len(rows)} DB row(s)")

            # 4. move the local archive folder aside too, so a re-ingest cannot
            #    resurrect the phantom session
            local = ARCHIVE / arc_year / arc_season
            if local.exists():
                dest = session_backup / "archive"
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.move(str(local), str(dest))
                print(f"  moved local archive folder -> {dest.relative_to(REPO_ROOT)}")

        manifest["sessions"].append({
            "year": year, "season": season, "reason": why,
            "r2_keys": keys, "db_rows": rows,
        })

    BACKUP.mkdir(parents=True, exist_ok=True)
    manifest_path = BACKUP / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nmanifest -> {manifest_path.relative_to(REPO_ROOT)}")
    print("COMMITTED" if args.commit else "DRY-RUN (re-run with --commit to delete)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
