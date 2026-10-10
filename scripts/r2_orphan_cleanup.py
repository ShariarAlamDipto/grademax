#!/usr/bin/env python3
"""
Keep R2 to ONE copy of everything the site serves: find objects no database
row references and retire them in two recoverable steps.

    python scripts/r2_orphan_cleanup.py plan                       # read-only report
    python scripts/r2_orphan_cleanup.py trash --execute            # move orphans to _trash/<date>/
    python scripts/r2_orphan_cleanup.py purge --days 7 --execute   # delete trash older than N days
    python scripts/r2_orphan_cleanup.py restore --date 20261010 --execute

"Referenced" = any URL in papers.pdf_url / markscheme_pdf_url / data_file_url,
pages.qp_page_url / ms_page_url, questions.page_pdf_url / ms_pdf_url,
workbook_questions.qp_pdf_url / ms_pdf_url, store_products.cover_image_url,
lectures.file_url (raw or %-decoded). Never touched, whatever the scan says:
  * store/ and lectures/ -- the app also reads these by key, not by URL;
  * _trash/ itself (only `purge` deletes there);
  * anything modified in the last GRACE_HOURS -- a publish uploads its files
    BEFORE it writes the rows that reference them, so a fresh object may be
    referenced a minute later (a peer session publishes the science/IAL
    subjects today).
Every move is logged to data/analysis/r2_inventory/cleanup_<date>.jsonl.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env.local")
import ingest_2026_papers as ing  # noqa: E402

OUT = ROOT / "data" / "analysis" / "r2_inventory"
PROTECTED = ("store/", "lectures/", "_trash/")
GRACE_HOURS = 48
URL_COLUMNS = {
    "papers": ("pdf_url", "markscheme_pdf_url", "data_file_url"),
    "pages": ("qp_page_url", "ms_page_url"),
    "questions": ("page_pdf_url", "ms_pdf_url"),
    "workbook_questions": ("qp_pdf_url", "ms_pdf_url"),
    "store_products": ("cover_image_url",),
    "lectures": ("file_url",),
}


def list_objects(r2, prefix: str = "") -> list[dict]:
    out, token = [], None
    while True:
        kw = {"Bucket": ing.R2_BUCKET, "MaxKeys": 1000, "Prefix": prefix}
        if token:
            kw["ContinuationToken"] = token
        resp = r2.list_objects_v2(**kw)
        out += resp.get("Contents", [])
        if not resp.get("IsTruncated"):
            return out
        token = resp["NextContinuationToken"]


def referenced_keys() -> set[str]:
    import psycopg2  # noqa: PLC0415
    public = ing.R2_PUBLIC_URL.rstrip("/") + "/"
    keys: set[str] = set()
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
        for table, cols in URL_COLUMNS.items():
            for col in cols:
                cur.execute(f'select "{col}" from "{table}" where "{col}" like %s', (public + "%",))
                for (url,) in cur.fetchall():
                    key = url[len(public):].split("?")[0]
                    keys.add(key)
                    keys.add(unquote(key))
    return keys


def orphans(r2) -> list[dict]:
    refs = referenced_keys()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=GRACE_HOURS)
    return [o for o in list_objects(r2)
            if o["Key"] not in refs and not o["Key"].startswith(PROTECTED)
            and o["LastModified"] < cutoff]


def group(key: str) -> str:
    parts = key.split("/")
    return "/".join(parts[:3]) if parts[0] == "subjects" else "/".join(parts[:2])


def cmd_plan(r2) -> list[dict]:
    found = orphans(r2)
    totals: dict[str, list] = {}
    for o in found:
        t = totals.setdefault(group(o["Key"]), [0, 0])
        t[0] += 1
        t[1] += o["Size"]
    for g, (n, size) in sorted(totals.items(), key=lambda x: -x[1][0]):
        print(f"{g:50} {n:6} {size / 1e9:6.2f} GB")
    print(f"orphans: {len(found)}  {sum(o['Size'] for o in found) / 1e9:.2f} GB")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"orphans_{datetime.now():%Y%m%d}.json").write_text(
        json.dumps([[o["Key"], o["Size"]] for o in found]), encoding="utf-8")
    return found


def cmd_trash(r2, execute: bool) -> None:
    found = cmd_plan(r2)
    if not execute:
        print("Dry run only. Re-run with --execute to move them to _trash/.")
        return
    stamp = datetime.now().strftime("%Y%m%d")
    log = (OUT / f"cleanup_{stamp}.jsonl").open("a", encoding="utf-8")

    def move(o: dict) -> None:
        dest = f"_trash/{stamp}/{o['Key']}"
        r2.copy_object(Bucket=ing.R2_BUCKET, Key=dest,
                       CopySource={"Bucket": ing.R2_BUCKET, "Key": o["Key"]})
        r2.delete_object(Bucket=ing.R2_BUCKET, Key=o["Key"])
        log.write(json.dumps({"from": o["Key"], "to": dest, "size": o["Size"]}) + "\n")

    with ThreadPoolExecutor(16) as pool:
        list(pool.map(move, found))
    log.close()
    print(f"moved {len(found)} objects to _trash/{stamp}/")


def cmd_purge(r2, days: int, execute: bool) -> None:
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    old = [o for o in list_objects(r2, "_trash/") if o["Key"].split("/")[1] <= cutoff]
    print(f"trash older than {days} days: {len(old)} objects, {sum(o['Size'] for o in old) / 1e9:.2f} GB")
    if not execute:
        print("Dry run only.")
        return
    for i in range(0, len(old), 1000):
        r2.delete_objects(Bucket=ing.R2_BUCKET,
                          Delete={"Objects": [{"Key": o["Key"]} for o in old[i:i + 1000]]})
    print(f"purged {len(old)}")


def cmd_restore(r2, date: str, execute: bool) -> None:
    items = list_objects(r2, f"_trash/{date}/")
    print(f"restorable from _trash/{date}/: {len(items)}")
    if not execute:
        return
    for o in items:
        original = o["Key"][len(f"_trash/{date}/"):]
        r2.copy_object(Bucket=ing.R2_BUCKET, Key=original,
                       CopySource={"Bucket": ing.R2_BUCKET, "Key": o["Key"]})
    print(f"restored {len(items)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "trash", "purge", "restore"])
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--date")
    args = parser.parse_args()
    r2 = ing.get_r2()
    if args.command == "plan":
        cmd_plan(r2)
    elif args.command == "trash":
        cmd_trash(r2, args.execute)
    elif args.command == "purge":
        cmd_purge(r2, args.days, args.execute)
    else:
        cmd_restore(r2, args.date, args.execute)
    return 0


if __name__ == "__main__":
    sys.exit(main())
