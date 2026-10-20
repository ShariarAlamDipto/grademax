#!/usr/bin/env python3
"""
Second identity proof for the questions audit_tool_question_identity.py left
QP_UNPROVEN (no readable barcode on the cut -- the cuts are trimmed to the
question, which usually crops away the page footer that carries it).

    python -X utf8 scripts/audit_tool_question_identity_source.py

For each such question:
  1. DERIVATION -- the cut is part of its source question paper: at least
     SUBSET_MIN of the cut's words (OCR when the cut has no text layer) occur
     in that source paper's text (OCR'd copy when it is a scan). This fixes
     which printed paper the question came from.
  2. COVER -- that source paper's own cover (exam date / paper reference /
     barcode, OCR'd when drawn as outlines) names the row's year and season.
Both must hold for SOURCE_PROVEN. Specimens (no exam date) are proven by the
cover naming "Sample Assessment Material(s)" and the row being a specimen.

Writes data/analysis/tool_identity_source.json; read-only otherwise.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_tool_question_identity as base  # noqa: E402
from lib.live_paper_sources import ROOT  # noqa: E402

IN = ROOT / "data" / "analysis" / "tool_identity_audit.json"
PAIRING = ROOT / "data" / "analysis" / "qp_ms_content_pairing.json"
OUT = ROOT / "data" / "analysis" / "tool_identity_source.json"
SUBSET_MIN = 0.85
WORD = re.compile(r"[a-z]{4,}")
# Page furniture, read differently by OCR (run-together) than by the text layer,
# and our own stamp line: never evidence either way.
FURNITURE = re.compile(r"donot|notwrite|writei|thisare|inthis|grademax|turnover|"
                       r"mathematics|physics|chemistry|biology|further|pure|paper|blank", re.I)
SPECIMEN_RE = re.compile(r"Sample\s+Assessment\s+Material|Specimen", re.I)
_text_cache: dict[str, set[str]] = {}
_cover_cache: dict[str, dict] = {}


def words_of(pdf: Path, max_pages: int = 60) -> set[str]:
    key = str(pdf)
    if key in _text_cache:
        return _text_cache[key]
    with fitz.open(pdf) as doc:
        n = min(doc.page_count, max_pages)
        text = " ".join(doc[i].get_text() for i in range(n))
    if len(WORD.findall(text.lower())) < 20 * n:  # scan or scrambled text layer
        text = " ".join(base.ocr_page(pdf, i) for i in range(n))
    _text_cache[key] = {w for w in WORD.findall(text.lower()) if not FURNITURE.search(w)}
    return _text_cache[key]


def source_qp(code: str, live_key: str) -> Path | None:
    folder = base.REBUILD / code / "sources"
    # the copy the cut was made from: decoded / OCR'd copies take precedence
    for suffix in ("_qp.dec.pdf", "_qp.ocrp.pdf", "_qp.ocr.pdf", "_qp.pdf"):
        p = folder / f"{live_key}{suffix}"
        if p.is_file():
            return p
    return None


def cover(pdf: Path) -> dict:
    key = str(pdf)
    if key not in _cover_cache:
        ident = base.cover_identity(pdf)
        with fitz.open(pdf) as doc:
            head = " ".join(doc[i].get_text() for i in range(min(2, doc.page_count)))
        ident["specimen"] = bool(SPECIMEN_RE.search(head)) or bool(
            SPECIMEN_RE.search(base.ocr_page(pdf) if not head.strip() else ""))
        _cover_cache[key] = ident
    return _cover_cache[key]


def ms_chain(code: str, live_key: str, rec: dict, pairing: dict) -> bool | None:
    """
    Newer Pearson covers print no exam date. Then: the paper's own scheme is
    the clear best CONTENT match among every scheme in the subject (pairing
    audit verdict OK for the URLs we serve), and that scheme's own title /
    publication code names the row's sitting.
    """
    p = pairing.get((code, rec["year"], rec["season"], str(rec["paper"])))
    if not p or p.get("verdict") != "OK":
        return None
    ms = p.get("ms_ident") or {}
    cands = []
    if ms.get("year"):
        cands.append((ms["year"], ms["season"]))
    if ms.get("pub_year") and not ms.get("pub_is_date"):
        cands.append((ms["pub_year"], ms["pub_season"]))
    if not cands:
        return None
    return any(base.session_eq(y, s_, rec["year"], rec["season"]) for y, s_ in cands)


def main() -> int:
    report = json.loads(IN.read_text(encoding="utf-8"))
    pairing = {(r["code"], r["year"], r["season"], str(r["paper_number"])): r
               for r in json.loads(PAIRING.read_text(encoding="utf-8"))}
    verdicts_by_code: dict[str, dict] = {}
    results, counts = [], Counter()
    for rec in report["rows"]:
        if rec["verdict"] != "QP_UNPROVEN":
            continue
        code = rec["code"]
        if code not in verdicts_by_code:
            v = json.loads((base.REBUILD / code / "verdicts.json").read_text(encoding="utf-8"))
            verdicts_by_code[code] = {(r["live_key"], str(r["question"])): r for r in v["rows"]}
        live_key = f"{rec['year']}_{rec['season']}_P{rec['paper']}"
        staged = verdicts_by_code[code].get((live_key, str(rec["question"])))
        out = {**rec, "live_key": live_key}
        src = source_qp(code, live_key)
        if staged is None or src is None:
            out["source_verdict"] = "NO_SOURCE"
        else:
            cut_words = words_of(ROOT / staged["qp"])
            src_words = words_of(src)
            share = len(cut_words & src_words) / len(cut_words) if cut_words else 0.0
            ident = cover(src)
            out.update(source=str(src.relative_to(ROOT)), subset=round(share, 3),
                       cover=ident.get("evidence") or ("specimen" if ident.get("specimen") else None),
                       cover_ref=f"{ident.get('unit')}/{ident.get('paper')}")
            if len(cut_words) < 5:
                out["source_verdict"] = "CUT_UNREADABLE"
            elif share < SUBSET_MIN:
                out["source_verdict"] = "NOT_FROM_SOURCE"
            elif rec["season"] == "specimen":
                out["source_verdict"] = "SOURCE_PROVEN" if ident.get("specimen") else "COVER_UNPROVEN"
            else:
                same = base.session_eq(ident.get("year"), ident.get("season"), rec["year"], rec["season"])
                if same is None:  # cover prints no date: prove the sitting through its scheme
                    chain = ms_chain(code, live_key, rec, pairing)
                    out["source_verdict"] = {True: "MS_CHAIN_PROVEN", False: "MS_CHAIN_SITTING",
                                             None: "COVER_UNPROVEN"}[chain]
                else:
                    out["source_verdict"] = "SOURCE_PROVEN" if same else "COVER_SITTING"
        counts[(code, out["source_verdict"])] += 1
        results.append(out)
    OUT.write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
    for (code, verdict), n in sorted(counts.items()):
        print(f"{code:6} {verdict:16} {n}")
    total = Counter(r["source_verdict"] for r in results)
    print(f"\nALL {len(results)}  {dict(total)}\nreport -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
