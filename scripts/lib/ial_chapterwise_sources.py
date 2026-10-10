"""
Assemble the verified source papers for an IAL chapterwise workbook.

The chapterwise segmenters used to read whatever `data/Ultimate Final IAL/
Mathematics` held under a unit's filename. That archive is wrong in places that
no filename or cover check reveals (measured 2026-10-06):

  * P1 "2024 Jan" mark scheme is really October 2023's.
  * P1 and P2 "2024 May-Jun" hold a different paper from the one Pearson sat.
  * "2020 May-Jun" was a cancelled series; its paper was sat in October 2020.
  * 2025 June / 2025 October / 2026 papers were not in the archive at all.

So each unit's book now reads from ONE folder, data/workbook/ial_sources/<unit>/,
filled here from the best verified source for each sitting:

  P1, P2   the verified QP<->MS linkage (data/yearwise_all/linkage/ial_pure.json,
           LINKED sittings only)
  S1, M1   the yearwise source audits (verdict OK, to 2023), then the archive
  any      Pearson (June 2025, from its own catalogue), Paperlords (October
           2025), our database/R2 (2026)

and EVERY file is checked against its own printed identity before it is used:

  question paper  prints "<CODE>/01" (not the 01A adapted paper), and where the
                  cover date is text, it falls in the right season and year
  mark scheme     prints its Pearson publication code "<CODE>_01_<YYMM>" naming
                  this session, or a title "Summer 2025 ... (<CODE>)"

and no two question papers in a unit may be the same paper (the duplicate that
defeats every cover check -- see lib/yearwise_repair.py).

A sitting that fails any check is left out and reported; nothing is guessed.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import fitz
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "workbook" / "ial_sources"
DOWNLOADS = OUT / "_downloads"
LINKAGE = ROOT / "data" / "yearwise_all" / "linkage" / "ial_pure.json"
ARCHIVE = ROOT / "data" / "Ultimate Final IAL" / "Mathematics"
PEARSON = ("https://qualifications.pearson.com/content/dam/pdf/International-Advanced-Level/"
           "Mathematics/2018/Exam-materials")
PAPERLORDS = "https://archive.paperlords.org/library/IAL/Maths"
UA = {"User-Agent": "Mozilla/5.0"}

SEASONS = ("jan", "may-jun", "oct-nov")
LINK_SEASON = {"jan": "Jan", "may-jun": "May-Jun", "oct-nov": "Oct-Nov"}
YYMM = {"jan": "01", "may-jun": "06", "oct-nov": "10"}
COVER_MONTHS = {"january": "jan", "may": "may-jun", "june": "may-jun",
                "october": "oct-nov", "november": "oct-nov"}
TITLE_SEASON = {"january": "jan", "summer": "may-jun", "october": "oct-nov",
                "autumn": "oct-nov", "winter": "oct-nov"}
WINDOW = ((2019, "jan"), (2026, "may-jun"))
CANCELLED = {(2020, "may-jun")}  # sat as October 2020

# The October 2020 paper is the one printed for the cancelled June series, so
# its cover is dated May/June 2020. That, and only that, is accepted.
REISSUED_AS = {(2020, "oct-nov"): (2020, "may-jun")}


@dataclass(frozen=True)
class Unit:
    token: str        # "S1"
    code: str         # "WST01"
    first: tuple[int, str] = WINDOW[0]
    yearwise_audit: Path | None = None
    linkage: bool = False
    # Pearson June 2025 file stems (que, rms)
    june_2025: tuple[str, str] | None = None


def _sittings(unit: Unit) -> list[tuple[int, str]]:
    out = []
    for year in range(WINDOW[0][0], WINDOW[1][0] + 1):
        for season in SEASONS:
            key = (year, season)
            rank = (year, SEASONS.index(season))
            lo = (unit.first[0], SEASONS.index(unit.first[1]))
            hi = (WINDOW[1][0], SEASONS.index(WINDOW[1][1]))
            if lo <= rank <= hi and key not in CANCELLED:
                out.append(key)
    return out


def _text(path: Path, pages: int = 3) -> str:
    with fitz.open(path) as doc:
        return " ".join(doc[i].get_text() for i in range(min(pages, doc.page_count)))


def check_qp(path: Path, unit: Unit, year: int, season: str) -> list[str]:
    text = _text(path, 2)
    problems = []
    codes = set(re.findall(rf"{unit.code}\s*/\s*(01A?)", text))
    if "01A" in codes:
        problems.append("cover is the 01A adapted paper")
    if "01" not in codes:
        problems.append(f"cover does not print {unit.code}/01")
    date = re.search(r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)\s+\d{1,2}\s+"
                     r"(January|May|June|October|November)\s+(20\d\d)", text)
    if date:
        got = (int(date.group(2)), COVER_MONTHS[date.group(1).lower()])
        if got not in ((year, season), REISSUED_AS.get((year, season))):
            problems.append(f"cover date says {date.group(0)}")
    return problems


def check_ms(path: Path, unit: Unit, year: int, season: str) -> list[str]:
    text = _text(path, 3)
    # A year-only code ("WMA11_01_2021", a Pearson slip seen on January 2021)
    # names no session, so it is not evidence either way: use the title.
    pub = [p for p in re.findall(rf"{unit.code}_01_(\d{{4}})", text) if p != str(year)]
    if pub:
        want = f"{year % 100:02d}{YYMM[season]}"
        if want not in pub and not any(p[:2] == want[:2] and _season_of(p) == season for p in pub):
            return [f"publication code {pub} is not {want}"]
        return []
    title = re.search(r"(January|Summer|October|Autumn|Winter)\s+(20\d\d)", text)
    if title and unit.code in text:
        got = (int(title.group(2)), TITLE_SEASON[title.group(1).lower()])
        return [] if got == (year, season) else [f"title says {title.group(0)}"]
    return ["no publication code or dated title naming the unit"]


def _season_of(yymm: str) -> str:
    month = int(yymm[2:])
    return "jan" if month <= 3 else "may-jun" if month <= 8 else "oct-nov"


def _download(url: str, target: Path) -> Path | None:
    if target.is_file() and target.stat().st_size > 10_000:
        return target
    response = requests.get(url, headers=UA, timeout=60)
    if response.status_code != 200 or not response.content.startswith(b"%PDF"):
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(response.content)
    return target


def _from_db(unit: Unit, year: int, season: str) -> tuple[Path | None, Path | None]:
    import os

    from dotenv import load_dotenv
    from supabase import create_client

    load_dotenv(ROOT / ".env.local")
    sb = create_client(os.environ["NEXT_PUBLIC_SUPABASE_URL"],
                       os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    sid = sb.table("subjects").select("id").eq("code", unit.code).execute().data[0]["id"]
    rows = (sb.table("papers").select("pdf_url,markscheme_pdf_url").eq("subject_id", sid)
            .eq("year", year).eq("season", season).execute().data)
    if not rows:
        return None, None
    stem = DOWNLOADS / f"db_{unit.token}_{year}_{season}"
    qp = _download(rows[0]["pdf_url"], Path(f"{stem}_QP.pdf")) if rows[0]["pdf_url"] else None
    ms = (_download(rows[0]["markscheme_pdf_url"], Path(f"{stem}_MS.pdf"))
          if rows[0]["markscheme_pdf_url"] else None)
    return qp, ms


def candidates(unit: Unit, year: int, season: str) -> list[tuple[str, Path | None, Path | None]]:
    """(origin, qp, ms) in priority order."""
    out: list[tuple[str, Path | None, Path | None]] = []
    if unit.linkage:
        link = {u["unit"]: u for u in json.loads(LINKAGE.read_text(encoding="utf-8"))}[unit.code]
        for s in link["sittings"]:
            if s["sitting"] == f"{year} {LINK_SEASON[season]}" and s["verdict"] == "LINKED":
                out.append(("verified linkage", ROOT / s["qp"]["path"], ROOT / s["ms"]["path"]))
    if unit.yearwise_audit and unit.yearwise_audit.is_file():
        rows = json.loads(unit.yearwise_audit.read_text(encoding="utf-8"))
        got = {r["kind"]: r for r in rows if r["year"] == year
               and r["season"] == LINK_SEASON[season] and r.get("verdict") == "OK"
               and r["path"] != "-"}
        if "QP" in got and "MS" in got:
            out.append(("yearwise source audit", ROOT / got["QP"]["path"], ROOT / got["MS"]["path"]))
    folder = ARCHIVE / str(year) / LINK_SEASON[season]
    qp = folder / f"Mathematics_{unit.token}_{year}_{LINK_SEASON[season]}_QP.pdf"
    if qp.is_file():
        ms = qp.with_name(qp.name.replace("_QP", "_MS"))
        out.append(("archive", qp, ms if ms.is_file() else None))
    if (year, season) == (2025, "may-jun") and unit.june_2025:
        que, rms = unit.june_2025
        out.append(("Pearson",
                    _download(f"{PEARSON}/{que}.pdf", DOWNLOADS / f"pearson_{que}.pdf"),
                    _download(f"{PEARSON}/{rms}.pdf", DOWNLOADS / f"pearson_{rms}.pdf")))
    if season in ("oct-nov", "jan") and year >= 2025:
        mon = {"oct-nov": "Oct", "jan": "Jan"}[season]
        base = f"{PAPERLORDS}/{mon}%20{year}/IAL_MATHS_{year}_{mon}_{unit.token}"
        stem = DOWNLOADS / f"paperlords_{unit.token}_{year}_{mon}"
        out.append(("Paperlords",
                    _download(f"{base}_QP.pdf", Path(f"{stem}_QP.pdf")),
                    _download(f"{base}_MS.pdf", Path(f"{stem}_MS.pdf"))))
    if year >= 2026:
        qp_db, ms_db = _from_db(unit, year, season)
        out.append(("GradeMax database", qp_db, ms_db))
    return out


def _shingles(path: Path) -> set[str]:
    with fitz.open(path) as doc:
        text = " ".join(page.get_text() for page in doc)
    text = re.sub(r"GradeMax|\b(?:Turn over|DO NOT WRITE IN THIS AREA)\b", " ", text)
    words = re.findall(r"[a-z]{3,}|\d+(?:\.\d+)?", text.lower())
    return {" ".join(words[i:i + 5]) for i in range(len(words) - 4)}


def collect(unit: Unit, execute: bool) -> int:
    root = OUT / unit.token.lower()
    chosen: list[dict] = []
    failures: list[str] = []
    for year, season in _sittings(unit):
        notes = []
        picked = None
        for origin, qp, ms in candidates(unit, year, season):
            if qp is None or ms is None:
                notes.append(f"{origin}: {'QP' if qp is None else 'MS'} not available")
                continue
            problems = check_qp(qp, unit, year, season) + check_ms(ms, unit, year, season)
            if problems:
                notes.append(f"{origin}: " + "; ".join(problems))
                continue
            picked = {"key": f"{year}_{season}", "year": year, "season": season,
                      "origin": origin, "qp_from": str(qp.relative_to(ROOT)),
                      "ms_from": str(ms.relative_to(ROOT))}
            break
        if picked is None:
            failures.append(f"{year} {season}: " + (" | ".join(notes) or "no source found"))
        else:
            if notes:
                picked["passed_over"] = notes
            chosen.append(picked)

    # No two question papers may be the same paper.
    shingles = {c["key"]: _shingles(ROOT / c["qp_from"]) for c in chosen}
    keys = sorted(shingles)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            union = shingles[a] | shingles[b]
            if union and len(shingles[a] & shingles[b]) / len(union) > 0.5:
                failures.append(f"{a} and {b} are the same paper "
                                f"({len(shingles[a] & shingles[b]) / len(union):.2f})")

    print(f"{unit.token} ({unit.code}): {len(chosen)} sittings verified")
    for c in chosen:
        print(f"  {c['key']:14} {c['origin']}")
    for f in failures:
        print(f"  !! {f}")

    if execute and not failures:
        if root.is_dir():
            shutil.rmtree(root)
        for c in chosen:
            folder = root / c["key"]
            folder.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / c["qp_from"], folder / "QP.pdf")
            shutil.copy2(ROOT / c["ms_from"], folder / "MS.pdf")
        (root / "sources.json").write_text(json.dumps(chosen, indent=2), encoding="utf-8")
        print(f"  written: {root.relative_to(ROOT)}")
    elif execute:
        print("  NOT written -- resolve the failures above first")
    return 1 if failures else 0
