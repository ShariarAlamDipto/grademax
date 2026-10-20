#!/usr/bin/env python3
"""Read-only audit: is every live Maths A (4MA1) paper row on R2 the sitting it claims?

The user's rule for onboarding Maths A into the test builder / worksheet
generator: R2 files must be tied to their session and year by what the FRONT
PAGE prints, not by their filename. The archive the R2 objects came from was
named from PMT's watermark, and for Maths A that label is known to be wrong in
a whole class of cases (every pre-June-2018 "1H"/"2H" is really a 4MA0 3H/4H --
see docs/workbook-mathsa-plan.md).

For each `papers` row of subject 4MA1 this downloads the QP and MS straight from
R2 (lib/live_paper_sources -> data/analysis/live_rebuild/4MA1/sources/, reused by
the rebuild) and reads the cover:

  QP  spec code + paper (4MA1/1H), exam date (Monday 14 May 2018), barcode P-number
  MS  "Summer 2018", spec code, "Paper 1H"

Verdict per document: OK / WRONG_SESSION / WRONG_PAPER / WRONG_KIND /
UNREADABLE (no legible cover -- rendered to PNG for reading by eye) / MISSING.
Also reports duplicate rows (same QP barcode under two rows).

Writes data/analysis/mathsa_r2_identity/report.json and covers/*.png only.

    python -X utf8 scripts/audit_mathsa_r2_paper_identity.py
    python -X utf8 scripts/audit_mathsa_r2_paper_identity.py --tier H     # Higher rows only
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_igcse_edexcel_labels as lab  # noqa: E402
from lib.live_paper_sources import load_live_papers  # noqa: E402

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "analysis" / "mathsa_r2_identity"
CODE = "4MA1"
SEASON_OF = {"Jan": "jan", "May-Jun": "may-jun", "Oct-Nov": "oct-nov"}
# Pearson reused the cancelled summer-2020 papers in November 2020.
COVID_REUSE = {(2020, "oct-nov", "may-jun")}


def cover_variant(info: dict) -> tuple[str | None, str | None]:
    """(spec code, paper token) the cover prints, preferring a 4MA reference."""
    for (code, var), _n in info["refs"]:
        if code.startswith("4MA"):
            return code, var
    code = next((c for c, _n in info["bare"] if c.startswith("4MA")), None)
    var = info["papers"][0][0] if info["papers"] else None
    return code, var


def judge(row_year: int, row_season: str, row_paper: str, kind: str, path: Path | None) -> dict:
    if path is None:
        return {"verdict": "MISSING"}
    info = lab.read_pdf(path)
    if "error" in info:
        return {"verdict": "UNREADABLE", "why": info["error"]}
    code, var = cover_variant(info)
    year = int(info["year"]) if info["year"] else None
    season = SEASON_OF.get(info["season"]) if info["season"] else None
    out = {"code": code, "paper": var, "year": year, "season": season,
           "evidence": info["evidence"], "barcode": info["barcode"], "kind": info["kind"],
           "pages": info["pages"]}
    problems = []
    if info["kind"] and info["kind"] != kind.upper():
        problems.append("WRONG_KIND")
    if var and var.upper().lstrip("0") != row_paper.upper():
        problems.append("WRONG_PAPER")
    if year and season and row_season != "specimen":
        if (year, season) != (row_year, row_season) and \
                (year, row_season, season) not in COVID_REUSE:
            problems.append("WRONG_SESSION")
    if not var or not year:
        problems.append("UNREADABLE")
    out["verdict"] = "OK" if not problems else "+".join(problems)
    return out


def render_cover(path: Path, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(path) as doc:
        doc[0].get_pixmap(dpi=70).save(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", choices=["H", "F", "all"], default="all")
    args = ap.parse_args()

    papers = load_live_papers(CODE)
    if args.tier != "all":
        papers = [p for p in papers if (args.tier in p.paper_number) or
                  (args.tier == "F" and not re.search(r"[FH]", p.paper_number))]
    rows = []
    for p in papers:
        qp = judge(p.year, p.season, p.paper_number, "qp", p.qp_path)
        ms = judge(p.year, p.season, p.paper_number, "ms", p.ms_path)
        # QP and MS must name the same paper, whatever the row says.
        agree = (qp.get("paper") and ms.get("paper") and qp.get("year") and ms.get("year")
                 and qp["paper"].lstrip("0") == ms["paper"].lstrip("0")
                 and (qp["year"], qp["season"]) == (ms["year"], ms["season"]))
        rows.append({"paper_id": p.paper_id, "key": p.key, "qp": qp, "ms": ms,
                     "qp_ms_agree": bool(agree), "qp_url": p.qp_url, "ms_url": p.ms_url})
        for kind, j, path in (("qp", qp, p.qp_path), ("ms", ms, p.ms_path)):
            if j["verdict"] != "OK" and path is not None:
                render_cover(path, OUT_DIR / "covers" / f"{p.key}_{kind}.png")

    by_barcode = defaultdict(list)
    for r in rows:
        if r["qp"].get("barcode"):
            by_barcode[r["qp"]["barcode"]].append(r["key"])
    dupes = {b: keys for b, keys in by_barcode.items() if len(keys) > 1}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "report.json").write_text(json.dumps(
        {"rows": rows, "duplicate_barcodes": dupes}, indent=1), encoding="utf-8")

    print(f"rows: {len(rows)}")
    print("QP:", dict(Counter(r["qp"]["verdict"] for r in rows)))
    print("MS:", dict(Counter(r["ms"]["verdict"] for r in rows)))
    print("QP/MS disagree:", sum(1 for r in rows if not r["qp_ms_agree"]))
    print(f"\n{'ROW':24} {'QP verdict':28} {'QP cover':30} {'MS verdict':28} MS cover")
    for r in rows:
        if r["qp"]["verdict"] == "OK" and r["ms"]["verdict"] == "OK" and r["qp_ms_agree"]:
            continue
        def show(j):
            return (f"{j.get('code') or '?'}/{j.get('paper') or '?'} "
                    f"{j.get('year') or '?'} {j.get('season') or '?'}")
        print(f"{r['key']:24} {r['qp']['verdict']:28} {show(r['qp']):30} "
              f"{r['ms']['verdict']:28} {show(r['ms'])}")
    print(f"\nduplicate QP barcodes: {len(dupes)}")
    for b, keys in sorted(dupes.items()):
        print(f"   {b}: {keys}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
