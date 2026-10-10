#!/usr/bin/env python3
"""
Download the practical-paper SOURCE FILES (candidates' data files) for
Cambridge IGCSE ICT (0417) and A Level IT (9626), one zip per paper, from the
PapaCambridge public mirror ("<code>_<s|w|m><yy>_sf_<paper>.zip").

    python scripts/fetch_cambridge_ict_source_files.py

Writes data/ict_data_files/cambridge/<code>/<year>_<season>_P<paper>.zip and
a manifest.json. Only validated zips (PK header + zipfile.testzip clean) are
kept; papers without source files (theory papers) simply 404. Read-only on
the database.
"""

from __future__ import annotations

import io
import json
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.live_paper_sources import ROOT, fetch_rows, supabase_client  # noqa: E402

OUT = ROOT / "data" / "ict_data_files" / "cambridge"
MIRROR = "https://pastpapers.papacambridge.com/directories/CAIE/CAIE-pastpapers/upload/"
SESSION = {"feb-mar": "m", "may-jun": "s", "oct-nov": "w"}
CODES = ("0417", "9626")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}


def fetch(paper: dict) -> dict:
    letter = SESSION.get(paper["season"])
    if not letter:
        return {**paper, "status": "no-session-letter"}
    name = f"{paper['code']}_{letter}{paper['year'] % 100:02d}_sf_{paper['paper_number']}.zip"
    target = OUT / paper["code"] / f"{paper['year']}_{paper['season']}_P{paper['paper_number']}.zip"
    if target.is_file():
        return {**paper, "status": "ok", "file": str(target.relative_to(ROOT)), "source": MIRROR + name}
    try:
        r = httpx.get(MIRROR + name, headers=UA, timeout=120, follow_redirects=True)
    except httpx.HTTPError as exc:
        return {**paper, "status": f"error {exc.__class__.__name__}"}
    if r.status_code != 200 or r.content[:2] != b"PK":
        return {**paper, "status": f"absent {r.status_code}"}
    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            if z.testzip() is not None:
                return {**paper, "status": "corrupt"}
    except zipfile.BadZipFile:
        return {**paper, "status": "corrupt"}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(r.content)
    return {**paper, "status": "ok", "file": str(target.relative_to(ROOT)), "source": MIRROR + name}


def main() -> int:
    sb = supabase_client()
    subjects = {s["id"]: s["code"] for s in sb.table("subjects").select("id,code").in_("code", list(CODES)).execute().data}
    papers = fetch_rows(lambda o: sb.table("papers").select("id,subject_id,year,season,paper_number")
                        .in_("subject_id", list(subjects)).range(o, o + 999))
    rows = [{"paper_id": p["id"], "code": subjects[p["subject_id"]], "year": p["year"],
             "season": p["season"], "paper_number": p["paper_number"]} for p in papers]
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(fetch, rows))
    (OUT / "manifest.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    ok = [r for r in results if r["status"] == "ok"]
    print(f"{len(rows)} papers checked; source files found for {len(ok)}")
    for code in CODES:
        mine = [r for r in ok if r["code"] == code]
        print(f"  {code}: {len(mine)}  papers {sorted({r['paper_number'] for r in mine})}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
