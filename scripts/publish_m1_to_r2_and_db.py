#!/usr/bin/env python3
"""Publish the re-segmented Mechanics 1 (WME01) questions to R2 and Supabase.

Source of truth is `data/processed/Mechanics_1_resegmented/` (produced by
`scripts/resegment_m1_all.py`). This script makes R2 and the `pages` table match
that folder exactly:

  * upload every per-question QP/MS PDF whose bytes differ from what R2 holds
  * delete R2 objects that no longer correspond to a local file
  * upsert one `pages` row per question with the public QP/MS URLs
  * delete `pages` rows whose PDF no longer exists (these render as 404s)

Existing `topics` values are preserved -- classification is a separate step
(`scripts/classify_m1_and_publish.py`).

Dry-run by default; pass --commit to write.

Usage:
    python -X utf8 scripts/publish_m1_to_r2_and_db.py            # dry-run
    python -X utf8 scripts/publish_m1_to_r2_and_db.py --commit
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

import boto3
import requests
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "data" / "processed" / "Mechanics_1_resegmented"
QP_DIR = SRC / "pages"
MS_DIR = SRC / "markschemes"

SUBJECT_ID = "4d54f2aa-ee9c-470a-814b-8f6095ec9278"  # WME01 (IAL M1), NOT 4ME1
R2_PREFIX = "subjects/Mechanics_1/pages"
QP_PREFIX = f"{R2_PREFIX}/pages"
MS_PREFIX = f"{R2_PREFIX}/markschemes"

# local season token -> `papers.season` value
SEASON_DB = {"Jan": "jan", "Jun": "may-jun", "Oct": "oct-nov", "Specimen": "specimen"}
NAME_RE = re.compile(r"^(\d{4})_(Jan|Jun|Oct|Specimen)_P(\d+)_Q(\d+)\.pdf$")


def env() -> dict[str, str]:
    load_dotenv(REPO_ROOT / ".env.local")
    cfg = {
        "sb": (os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL") or "").rstrip("/"),
        "key": os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "",
        "public": (os.getenv("NEXT_PUBLIC_R2_PUBLIC_URL") or "").rstrip("/"),
        "account": os.getenv("R2_ACCOUNT_ID") or "",
        "access": os.getenv("R2_ACCESS_KEY_ID") or "",
        "secret": os.getenv("R2_SECRET_ACCESS_KEY") or "",
        "bucket": os.getenv("R2_BUCKET_NAME") or "grademax-papers",
    }
    missing = [k for k, v in cfg.items() if not v]
    if missing:
        raise SystemExit(f"ERROR: missing env values: {', '.join(missing)}")
    return cfg


def r2_client(cfg: dict[str, str]):
    return boto3.client(
        "s3",
        endpoint_url=f"https://{cfg['account']}.r2.cloudflarestorage.com",
        aws_access_key_id=cfg["access"],
        aws_secret_access_key=cfg["secret"],
        region_name="auto",
    )


def list_r2(s3, bucket: str, prefix: str) -> dict[str, str]:
    """key -> ETag (md5 for non-multipart uploads)."""
    out: dict[str, str] = {}
    token = None
    while True:
        kw = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": 1000}
        if token:
            kw["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kw)
        for obj in resp.get("Contents", []):
            out[obj["Key"]] = obj["ETag"].strip('"')
        if not resp.get("IsTruncated"):
            return out
        token = resp["NextContinuationToken"]


def sync_r2(s3, cfg, commit: bool) -> tuple[int, int, int]:
    uploaded = skipped = deleted = 0
    remote = list_r2(s3, cfg["bucket"], R2_PREFIX + "/")
    wanted: set[str] = set()

    for folder, prefix in ((QP_DIR, QP_PREFIX), (MS_DIR, MS_PREFIX)):
        for pdf in sorted(folder.glob("*.pdf")):
            key = f"{prefix}/{pdf.name}"
            wanted.add(key)
            digest = hashlib.md5(pdf.read_bytes()).hexdigest()
            if remote.get(key) == digest:
                skipped += 1
                continue
            if commit:
                s3.put_object(Bucket=cfg["bucket"], Key=key,
                              Body=pdf.read_bytes(), ContentType="application/pdf")
            uploaded += 1

    for key in remote:
        if key not in wanted:
            if commit:
                s3.delete_object(Bucket=cfg["bucket"], Key=key)
            deleted += 1
    return uploaded, skipped, deleted


def sync_db(cfg, commit: bool) -> tuple[int, int, int]:
    h = {"apikey": cfg["key"], "Authorization": f"Bearer {cfg['key']}",
         "Content-Type": "application/json"}
    papers = requests.get(
        f"{cfg['sb']}/rest/v1/papers", headers=h,
        params={"select": "id,year,season", "subject_id": f"eq.{SUBJECT_ID}", "limit": "500"},
        timeout=60,
    ).json()
    by_key = {(int(p["year"]), str(p["season"])): p["id"] for p in papers}

    ids = ",".join(p["id"] for p in papers)
    rows: list[dict] = []
    start = 0
    while ids:
        resp = requests.get(
            f"{cfg['sb']}/rest/v1/pages", headers={**h, "Range": f"{start}-{start+999}"},
            params={"select": "id,paper_id,question_number,qp_page_url", "paper_id": f"in.({ids})"},
            timeout=90,
        )
        chunk = resp.json()
        if not isinstance(chunk, list):
            raise SystemExit(f"pages query failed: {str(chunk)[:200]}")
        rows += chunk
        if len(chunk) < 1000:
            break
        start += 1000
    existing = {(r.get("qp_page_url") or "").split("/")[-1]: r for r in rows}

    inserted = updated = removed = 0
    local_names: set[str] = set()

    for pdf in sorted(QP_DIR.glob("*.pdf")):
        m = NAME_RE.match(pdf.name)
        if not m:
            print(f"   [warn] unparseable name: {pdf.name}")
            continue
        year, season_tok, paper_no, qnum = m.groups()
        local_names.add(pdf.name)
        paper_id = by_key.get((int(year), SEASON_DB[season_tok]))
        if not paper_id:
            print(f"   [warn] no papers row for {year} {SEASON_DB[season_tok]} -- {pdf.name}")
            continue

        qp_url = f"{cfg['public']}/{QP_PREFIX}/{pdf.name}"
        ms_url = (f"{cfg['public']}/{MS_PREFIX}/{pdf.name}"
                  if (MS_DIR / pdf.name).exists() else None)
        payload = {
            "paper_id": paper_id,
            "question_number": str(int(qnum)),
            "page_number": int(qnum),
            "is_question": True,
            "qp_page_url": qp_url,
            "ms_page_url": ms_url,
        }
        row = existing.get(pdf.name)
        if row:
            if commit:
                requests.patch(f"{cfg['sb']}/rest/v1/pages", headers=h,
                               params={"id": f"eq.{row['id']}"}, json=payload, timeout=60)
            updated += 1
        else:
            if commit:
                r = requests.post(f"{cfg['sb']}/rest/v1/pages", headers=h,
                                  json={**payload, "topics": ["1"]}, timeout=60)
                if r.status_code not in (200, 201, 204):
                    print(f"   [err] insert {pdf.name}: {r.status_code} {r.text[:120]}")
                    continue
            inserted += 1

    for fname, row in existing.items():
        if fname and fname not in local_names:
            if commit:
                requests.delete(f"{cfg['sb']}/rest/v1/pages", headers=h,
                                params={"id": f"eq.{row['id']}"}, timeout=60)
            removed += 1
    return inserted, updated, removed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true", help="actually write to R2 + Supabase")
    args = ap.parse_args()

    if not QP_DIR.exists():
        raise SystemExit(f"ERROR: missing {QP_DIR} -- run scripts/resegment_m1_all.py first")

    cfg = env()
    print(f"local QP PDFs : {len(list(QP_DIR.glob('*.pdf')))}")
    print(f"local MS PDFs : {len(list(MS_DIR.glob('*.pdf')))}")
    print(f"mode          : {'COMMIT' if args.commit else 'DRY-RUN'}\n")

    s3 = r2_client(cfg)
    up, skip, dele = sync_r2(s3, cfg, args.commit)
    print(f"R2  uploaded/changed : {up}")
    print(f"R2  unchanged        : {skip}")
    print(f"R2  deleted (orphan) : {dele}")

    ins, upd, rem = sync_db(cfg, args.commit)
    print(f"\nDB  inserted : {ins}")
    print(f"DB  updated  : {upd}")
    print(f"DB  deleted  : {rem}")

    if not args.commit:
        print("\nDRY-RUN -- nothing written. Re-run with --commit to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
