#!/usr/bin/env python3
"""
Does every question the worksheet generator / test builder serves carry the
year, session and paper it is LABELLED with -- judged from the printed paper,
not from our labels -- and is its mark scheme from that same sitting?

    python -X utf8 scripts/audit_tool_question_identity.py

Read-only. Report: data/analysis/tool_identity_audit.json (+ summary on stdout).

Why this exists: the per-question proof gate matches a question to a scheme
WITHIN one paper. If the paper itself was filed under the wrong sitting (the
original segmentation's failure), the pair can be internally consistent and
still shown with the wrong year/session -- or a scheme from another sitting
can coincide on number and marks. So identity is proven separately:

QP side, per question:
  every Edexcel QP page prints the paper's barcode ("*P75707A0132*" = paper
  P75707A, page 1). A barcode -> sitting map is built from the COVERS of every
  source question paper (exam date + paper reference; OCR'd when the cover
  is drawn as outlines). Each live question cut's own barcode is looked up and
  compared with its row's year / season / paper.
MS side, per paper:
  the scheme document the cuts came from (the staged source, or a reviewed
  `ms_source` override) must name the same sitting in its title / publication
  code (Pearson copies codes between sibling papers, so either reading counts).

Verdicts per question:
  OK            QP barcode's sitting == row, and the paper's MS doc names the row's sitting
  QP_SITTING    the question's own barcode belongs to another sitting  -> wrong label
  MS_SITTING    the scheme document names another sitting               -> wrong scheme
  QP_UNPROVEN   no barcode readable / barcode on no known cover
  MS_UNPROVEN   the scheme document names no sitting (specimens, scans)
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.live_paper_sources import ROOT, fetch_rows, supabase_client  # noqa: E402
from lib.paper_fingerprint import BARCODE_RE, PAPER_REF_RE, identify  # noqa: E402

REBUILD = ROOT / "data" / "analysis" / "live_rebuild"
EXTRA_SOURCES = [ROOT / "data" / "workbook" / "ial_sources"]
CODES = ["4PH1", "4MB1", "4PM1", "4CH1", "4BI1", "4HB1",
         "WME01", "WMA11", "WMA12", "WMA13", "WMA14", "WST01"]
OUT = ROOT / "data" / "analysis" / "tool_identity_audit.json"
BARCODE_CACHE = ROOT / "data" / "analysis" / "tool_identity_barcodes.json"
PARTIAL = ROOT / "data" / "analysis" / "tool_identity_audit.partial.json"
COVID_YEAR = 2020
PUBLISHABLE = {"PROVEN", "SEQUENCE_PROVEN", "LABEL_PROVEN", "MANUAL_PROVEN", "REVIEWED_PROVEN"}

_OCR = None


def ocr_page(pdf: Path, index: int = 0) -> str:
    global _OCR
    if _OCR is None:
        from rapidocr_onnxruntime import RapidOCR
        _OCR = RapidOCR()
    with fitz.open(pdf) as doc:
        if index >= doc.page_count:
            return ""
        pix = doc[index].get_pixmap(dpi=150)
    result, _ = _OCR(pix.tobytes("png"))
    return " ".join(item[1] for item in (result or []) if "GradeMax" not in item[1])


def texts(pdf: Path, pages: int = 3) -> list[str]:
    with fitz.open(pdf) as doc:
        return [doc[i].get_text() for i in range(min(pages, doc.page_count))]


def session_eq(y1, s1, y2, s2) -> bool | None:
    if not (y1 and s1 and y2 and s2):
        return None
    if (y1, s1) == (y2, s2):
        return True
    return y1 == y2 == COVID_YEAR and {s1, s2} == {"may-jun", "oct-nov"}


def cover_identity(pdf: Path) -> dict:
    """identify() on the cover; OCR page 1 when the date/reference are outlines."""
    pages = texts(pdf)
    ident = identify(pages)
    if ident.get("year") is None or ident.get("barcode") is None:
        ocr = ocr_page(pdf)
        if ocr:
            o = identify([ocr] + pages[1:])
            for key in ("year", "season", "evidence", "barcode", "unit", "paper"):
                if ident.get(key) is None and o.get(key) is not None:
                    ident[key] = o[key]
    return ident


def build_barcode_map() -> dict[str, dict]:
    """barcode -> cover identity, from every question paper we hold."""
    roots = [REBUILD / c / "sources" for c in CODES] + EXTRA_SOURCES
    out: dict[str, dict] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for pdf in root.rglob("*.pdf"):
            name = pdf.name.lower()
            if "_ms" in name or "mark" in name or ".ocr" in name or ".dec" in name:
                continue
            try:
                ident = cover_identity(pdf)
            except Exception as exc:  # noqa: BLE001 -- reported, never fatal
                print(f"  cannot read {pdf}: {exc}")
                continue
            if ident.get("barcode") and ident.get("year"):
                out.setdefault(ident["barcode"], {**ident, "source": str(pdf.relative_to(ROOT))})
    return out


def cut_barcodes(pdf: Path) -> set[str]:
    with fitz.open(pdf) as doc:
        text = " ".join(page.get_text() for page in doc)
    found = {m.group(1) for m in BARCODE_RE.finditer(text)}
    if not found:  # scanned / scrambled cut: read the page footers by OCR
        with fitz.open(pdf) as doc:
            n = doc.page_count
        for i in range(n):
            found |= {m.group(1) for m in BARCODE_RE.finditer(ocr_page(pdf, i).replace(" ", ""))}
    return found


def retry(fn, attempts: int = 6):
    """Network calls (Supabase) survive a dropped connection / DNS blip."""
    import time
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 -- retried, then re-raised
            if i == attempts - 1:
                raise
            print(f"  network error ({exc.__class__.__name__}); retry {i + 1} in {10 * (i + 1)}s")
            time.sleep(10 * (i + 1))


def ms_doc_for(code: str, live_key: str, question: int, decisions: dict, seg_key: str) -> Path | None:
    d = decisions.get(f"{seg_key}|{question}") or {}
    if d.get("ms_source"):
        return ROOT / d["ms_source"]
    src = REBUILD / code / "sources" / f"{live_key}_ms.pdf"
    return src if src.is_file() else None


def main() -> int:
    sb = supabase_client()
    if BARCODE_CACHE.is_file():
        barcodes = json.loads(BARCODE_CACHE.read_text(encoding="utf-8"))
        print(f"barcode map from cache ({BARCODE_CACHE.name})")
    else:
        print("building barcode -> sitting map from source covers ...")
        barcodes = build_barcode_map()
        BARCODE_CACHE.write_text(json.dumps(barcodes, indent=1, default=str), encoding="utf-8")
    print(f"  {len(barcodes)} papers identified by barcode")
    subs = {s["code"]: s["id"] for s in retry(lambda: sb.table("subjects").select("id,code").in_("code", CODES).execute().data)}
    report: dict = {"barcodes": barcodes, "rows": []}
    done: set[str] = set()
    if PARTIAL.is_file():
        report["rows"] = json.loads(PARTIAL.read_text(encoding="utf-8"))
        done = {r["code"] for r in report["rows"]}
        print(f"resuming; already done: {sorted(done)}")
    ms_cache: dict[str, dict] = {}
    for code in CODES:
        if code in done:
            continue
        verdicts = json.loads((REBUILD / code / "verdicts.json").read_text(encoding="utf-8"))
        decisions_path = REBUILD / code / "manual_review.json"
        decisions = json.loads(decisions_path.read_text(encoding="utf-8")) if decisions_path.is_file() else {}
        by_id = {r["paper_id"]: [] for r in verdicts["rows"]}
        for r in verdicts["rows"]:
            by_id[r["paper_id"]].append(r)
        papers = {p["id"]: p for p in retry(lambda: fetch_rows(lambda o, sid=subs[code]: sb.table("papers")
                 .select("id,year,season,paper_number").eq("subject_id", sid).range(o, o + 999)))}
        live = []
        ids = list(papers)
        for i in range(0, len(ids), 50):
            live += retry(lambda part=ids[i:i + 50]: fetch_rows(lambda o: sb.table("pages")
                               .select("paper_id,question_number").in_("paper_id", part)
                               .not_.is_("qp_page_url", "null").eq("is_question", True).range(o, o + 999)))
        counts: Counter = Counter()
        for row in live:
            paper = papers[row["paper_id"]]
            staged = {str(r["question"]): r for r in by_id.get(row["paper_id"], [])}
            s = staged.get(str(row["question_number"]))
            rec = {"code": code, "year": paper["year"], "season": paper["season"],
                   "paper": paper["paper_number"], "question": row["question_number"]}
            if s is None or s["verdict"] not in PUBLISHABLE:
                rec["verdict"] = "NOT_STAGED"
                counts[rec["verdict"]] += 1
                report["rows"].append(rec)
                continue
            # QP side: the cut's own barcode
            qp_cut = ROOT / s["qp"]
            codes_seen = cut_barcodes(qp_cut)
            known = [barcodes[b] for b in codes_seen if b in barcodes]
            rec["qp_barcodes"] = sorted(codes_seen)
            if not known:
                qp_ok = None
            else:
                qp_ok = all(session_eq(k["year"], k["season"], paper["year"], paper["season"]) for k in known)
                rec["qp_sitting"] = [f"{k['year']} {k['season']} {k.get('unit')}/{k.get('paper')}" for k in known]
            # MS side: the scheme document's own title
            ms_doc = ms_doc_for(code, s["live_key"], s["question"], decisions, s["paper"])
            ms_ok = None
            if ms_doc and ms_doc.is_file():
                key = str(ms_doc)
                if key not in ms_cache:
                    with fitz.open(ms_doc) as doc:
                        pages = [doc[i].get_text() for i in range(doc.page_count)]
                    ms_cache[key] = identify(pages[:3] + pages[-1:])
                ident = ms_cache[key]
                cands = []
                if ident.get("year"):
                    cands.append((ident["year"], ident["season"]))
                if ident.get("pub_year") and not ident.get("pub_is_date"):
                    cands.append((ident["pub_year"], ident["pub_season"]))
                if cands:
                    ms_ok = any(session_eq(y, se, paper["year"], paper["season"]) for y, se in cands)
                rec["ms_doc"] = str(ms_doc.relative_to(ROOT))
                rec["ms_sitting"] = ident.get("evidence") or ident.get("pubcode")
            if qp_ok is False:
                verdict = "QP_SITTING"
            elif ms_ok is False:
                verdict = "MS_SITTING"
            elif qp_ok is None:
                verdict = "QP_UNPROVEN"
            elif ms_ok is None:
                verdict = "MS_UNPROVEN"
            else:
                verdict = "OK"
            rec["verdict"] = verdict
            counts[verdict] += 1
            report["rows"].append(rec)
        print(f"{code:6} {len(live):5}  {dict(counts)}")
        PARTIAL.write_text(json.dumps(report["rows"], default=str), encoding="utf-8")
    OUT.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    PARTIAL.unlink(missing_ok=True)
    total = Counter(r["verdict"] for r in report["rows"])
    print(f"\nALL {sum(total.values())}  {dict(total)}\nreport -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
