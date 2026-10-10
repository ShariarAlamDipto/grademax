"""
Fetch Pearson's own copy of every QP/MS the yearwise linkage audit could not
find a genuine candidate for, where Pearson serves it publicly.

Reads `data/yearwise_all/linkage/<book>.json`, takes each sitting whose problem
is "no acceptable QP/MS", looks the paper up in Pearson's Algolia catalogue
(plain variant only -- never the `-01a-` adapted or `R` time-zone papers), and
downloads it into `data/yearwise_all/pearson_cache`, indexed in
`paperlords_index.json` with source "pearson". The next collect + audit run
then judges it like any other candidate.

Local only: nothing is written to the site, the DB or R2. Gated assets
(`/content/dam/secure/...`, a ~995-byte login page) are reported, not fetched.

    python -X utf8 scripts/fill_yearwise_all_gaps_from_pearson.py [--dry-run]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ingest_2026_papers as ing  # noqa: E402
from lib.yearwise_all_catalogue import UNITS, WORK  # noqa: E402

INDEX = WORK / "paperlords_index.json"
CACHE = WORK / "pearson_cache"
SEASON_WORD = {"Jan": "Jan", "May-Jun": "June", "Oct-Nov": "Oct"}
PL_SUBJECT = {"WPH": "Physics", "WCH": "Chemistry", "WBI": "Biology"}


def wanted() -> list[tuple]:
    """(unit, year, season, kind) for every sitting missing a genuine document."""
    out = []
    for f in sorted((WORK / "linkage").glob("*.json")):
        for u in json.loads(f.read_text(encoding="utf-8")):
            for s in u["sittings"]:
                for p in s["problems"]:
                    m = re.match(r"no acceptable (QP|MS)", p)
                    if m:
                        year, season = s["sitting"].split(" ", 1)
                        out.append((u["unit"], int(year), season, m.group(1)))
    return out


def pearson_code(unit_key: str) -> tuple[str, str] | None:
    """Our unit key -> (Pearson asset code, plain variant), e.g. WPH11 -> (WPH11, 01)."""
    unit = next(u for u in UNITS if u.key == unit_key)
    if unit.level == "IAL":
        return unit.key, "01"
    m = re.match(r"(\w{4})_P(\d)", unit_key)
    return (m.group(1), f"0{m.group(2)}") if m else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    gaps = wanted()
    print(f"{len(gaps)} missing documents")
    hits = {fam: ing.algolia_hits(name) for fam, name in ing.FAMILIES.items()}
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    have = {e["url"] for e in index}
    CACHE.mkdir(parents=True, exist_ok=True)

    for unit_key, year, season, kind in gaps:
        code, variant = pearson_code(unit_key)
        found = []
        for fam_hits in hits.values():
            for h in fam_hits:
                url = h.get("url") or h.get("path") or ""
                c, v = ing.parse_asset_name(url)
                yr, se = ing.hit_series(h)
                if (c == code and (v or "").upper() == variant and ing.hit_kind(h) == kind
                        and (yr, ing.SEASON_FROM_SERIES.get(se, se)) == (year, season.lower())):
                    found.append(url)
        label = f"{unit_key} {year} {season} {kind}"
        if not found:
            print(f"  -    {label}: not in Pearson's catalogue")
            continue
        url = ing.PEARSON_HOST + found[0]
        if "/secure/" in url:
            print(f"  LOCK {label}: gated ({found[0].rsplit('/', 1)[-1]})")
            continue
        if url in have:
            print(f"  have {label}")
            continue
        if args.dry_run:
            print(f"  would {label}: {url}")
            continue
        resp = httpx.get(url, timeout=120, follow_redirects=True)
        if resp.status_code != 200 or not resp.content.startswith(b"%PDF"):
            print(f"  FAIL {label}: HTTP {resp.status_code}, {len(resp.content)} bytes")
            continue
        name = hashlib.sha1(url.encode()).hexdigest() + ".pdf"
        (CACHE / name).write_bytes(resp.content)
        unit = next(u for u in UNITS if u.key == unit_key)
        subject = PL_SUBJECT.get(unit.db_code, unit.db_code)
        title = f"U{unit_key[-1]} {kind}" if unit.level == "IAL" else f"P{unit_key[-1]} {kind}"
        index.append({"subject": subject, "session": f"{SEASON_WORD[season]} {year}",
                      "title": title, "url": url, "file": name,
                      "source": "pearson", "cache": "pearson_cache", "unit": unit_key})
        print(f"  got  {label}: {len(resp.content) // 1024}KB")

    if not args.dry_run:
        INDEX.write_text(json.dumps(index, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
