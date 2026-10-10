"""
Gather every candidate copy of every paper the 2018-2026 yearwise books need.

For each unit in `lib/yearwise_all_catalogue.py` this lists, per sitting and
kind (QP/MS), every file that CLAIMS to be that paper -- the live DB row (both
the plain and the lettered IGCSE slot), the local archive, and the Paperlords
gap harvest -- and downloads the DB copies from R2 into a local cache.

It decides nothing. Which candidate is genuine, and which mark scheme belongs
to which paper, is `audit_*_yearwise_linkage.py`'s job; this only makes sure
that audit sees everything there is to see.

Read-only towards production: it reads `papers` rows and public R2 objects.

    python -X utf8 scripts/collect_yearwise_all_sources.py            # all books
    python -X utf8 scripts/collect_yearwise_all_sources.py --book igcse_mathsb
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.yearwise_all_catalogue import (  # noqa: E402
    BOOKS, DB_SEASON, FIRST_YEAR, LAST_YEAR, PAPERLORDS_SEASON, ROOT, SEASONS,
    WORK, Unit, units_of)

load_dotenv(ROOT / ".env.local")
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
R2_CACHE = WORK / "r2_cache"
PL_CACHE = WORK / "paperlords_cache"
PL_INDEX = WORK / "paperlords_index.json"


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def db_rows(unit: Unit) -> list[dict]:
    if not (SUPABASE_URL and SUPABASE_KEY):
        raise SystemExit("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing from .env.local")
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    subject = httpx.get(f"{SUPABASE_URL}/rest/v1/subjects", headers=headers, timeout=60,
                        params={"select": "id", "code": f"eq.{unit.db_code}"}).json()
    if len(subject) != 1:
        raise SystemExit(f"{unit.key}: expected one subject with code {unit.db_code}, got {subject}")
    papers = ",".join(f'"{p}"' for p in unit.db_papers)
    rows = httpx.get(f"{SUPABASE_URL}/rest/v1/papers", headers=headers, timeout=60, params={
        "select": "year,season,paper_number,pdf_url,markscheme_pdf_url",
        "subject_id": f"eq.{subject[0]['id']}", "paper_number": f"in.({papers})",
        "year": f"gte.{FIRST_YEAR}"}).json()
    if not isinstance(rows, list):
        raise SystemExit(f"{unit.key}: papers query failed: {rows}")
    return rows


def fetch(url: str) -> tuple[str, Path | None, str]:
    path = R2_CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".pdf")
    if path.exists() and path.stat().st_size > 2048:
        return url, path, "cached"
    try:
        resp = httpx.get(url, timeout=120, follow_redirects=True)
    except httpx.HTTPError as exc:
        return url, None, f"error {exc.__class__.__name__}"
    if resp.status_code != 200 or not resp.content.startswith(b"%PDF"):
        return url, None, f"HTTP {resp.status_code}, {len(resp.content)} bytes, not a PDF"
    path.write_bytes(resp.content)
    return url, path, "downloaded"


def candidates_for(unit: Unit) -> tuple[list[dict], list[str]]:
    found, wanted = [], []

    for row in db_rows(unit):
        season = DB_SEASON.get(row["season"])
        if season is None or row["year"] > LAST_YEAR:
            continue
        for kind, col in (("QP", "pdf_url"), ("MS", "markscheme_pdf_url")):
            if row.get(col):
                wanted.append(row[col])
                found.append({"year": row["year"], "season": season, "kind": kind,
                              "source": f"db:{row['paper_number']}", "url": row[col]})

    base = ROOT / "data" / unit.local_dir
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        for season in SEASONS:
            for kind in ("QP", "MS"):
                for pattern in unit.local_names:
                    path = base / str(year) / season / pattern.format(
                        year=year, season=season, kind=kind)
                    if path.exists():
                        found.append({"year": year, "season": season, "kind": kind,
                                      "source": "local", "path": rel(path)})

    if PL_INDEX.exists():
        subject, label = unit.paperlords or (None, None)
        for item in json.loads(PL_INDEX.read_text(encoding="utf-8")):
            m = re.match(r"(\w+(?:/\w+)?) (\d{4})$", item["session"])
            t = re.search(r"(QP|MS)$", item["title"])
            # Pearson gap fills name their unit outright; Paperlords entries are
            # matched by subject + "U4 QP" label.
            mine = (item.get("unit") == unit.key if "unit" in item
                    else unit.paperlords is not None and item["subject"] == subject
                    and item["title"].startswith(f"{label} "))
            if not (mine and m and t):
                continue
            # Most entries are Paperlords harvests; a few are Pearson's own
            # public copies fetched for a gap (they name their source + cache).
            cache = WORK / item.get("cache", "paperlords_cache")
            found.append({"year": int(m.group(2)), "season": PAPERLORDS_SEASON[m.group(1)],
                          "kind": t.group(1), "source": item.get("source", "paperlords"),
                          "path": rel(cache / item["file"])})
    return found, wanted


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", choices=BOOKS, action="append")
    args = ap.parse_args()
    R2_CACHE.mkdir(parents=True, exist_ok=True)

    for book in args.book or BOOKS:
        index = {}
        for unit in units_of(book):
            found, wanted = candidates_for(unit)
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = {url: (path, note) for url, path, note in pool.map(fetch, wanted)}
            failed = 0
            for cand in found:
                if "url" in cand:
                    path, note = results[cand["url"]]
                    cand["path"] = rel(path) if path else None
                    if path is None:
                        cand["fetch_error"] = note
                        failed += 1
            index[unit.key] = found
            by_src = {}
            for c in found:
                by_src[c["source"]] = by_src.get(c["source"], 0) + 1
            print(f"{book:16} {unit.key:9} {len(found):4} candidates {by_src}"
                  + (f"  FETCH FAILED {failed}" if failed else ""))
        out = WORK / "candidates" / f"{book}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(index, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
