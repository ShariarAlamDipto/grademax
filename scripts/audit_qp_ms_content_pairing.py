#!/usr/bin/env python3
"""Read-only audit: is every LIVE Edexcel (IGCSE + IAL) mark scheme the one for
the question paper it is served next to -- judged by CONTENT, not by labels?

Why the earlier audits missed it
--------------------------------
* The 2026-08-27 pairing audit compared URL stems: `..._Paper_1_QP.pdf` next to
  `..._Paper_1_MS.pdf` passes whatever is inside the files.
* `audit_live_igcse_qp_ms_pairing.py` compares covers, but treats "cannot tell"
  as agreement: 262 of its 1410 "OK" rows have a 2021+ QP whose cover date is
  drawn as outlines, so the QP session was never read. It never covered IAL.
* No cover check can see a file whose cover is honest but whose row is wrong
  (the M1 2023 "summer" QP that was really January's paper).

The method
----------
For each subject, every live QP is scored against every live MS by the
rarity-weighted overlap of their body numbers and words
(`lib/paper_fingerprint.RarityScorer`). A row whose own MS is clearly beaten by
another row's MS is a CONTENT mismatch, and the winner names the paper the QP
really answers to. Independently, each document's own identity (MS publication
code / cover session, QP exam date / barcode, OCR when the cover is outlines)
is compared with the row. Both signals are reported; neither is taken on trust.

Verdicts
--------
  OK            own MS is the best content match (or tied with an identical doc)
                and no identity contradicts the row
  MS_WRONG      content: another MS fits the QP clearly better, and the QP's
                identity agrees with the row (so the MS is the wrong file)
  QP_WRONG      content mismatch, and the MS identity agrees with the row but the
                QP identity does not (the QP is another session's paper)
  MISMATCH      content mismatch, side undetermined
  ID_CONFLICT   content does not object but an identity contradicts the row
  WEAK          content margin too small to call, identities agree / unknown
  NO_TEXT       a document has no usable text layer (content check impossible)
  MISSING       a URL is absent or does not return a PDF

Writes only data/analysis/qp_ms_content_pairing.{json,csv} and a cache.

Usage:
    python -X utf8 scripts/audit_qp_ms_content_pairing.py
    python -X utf8 scripts/audit_qp_ms_content_pairing.py --level IAL --subject WPH
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import pickle
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

import requests
from urllib.parse import unquote
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paper_fingerprint import (  # noqa: E402
    RarityScorer, identify, option_letters, read_pdf, unit_family,
)

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = REPO_ROOT / "data" / "analysis" / "qp_ms_content_pairing.json"
OUT_CSV = REPO_ROOT / "data" / "analysis" / "qp_ms_content_pairing.csv"
CACHE_DIR = Path(os.environ.get("PAIRING_CACHE_DIR",
                                REPO_ROOT / "data" / "analysis" / ".pairing_cache"))
PAGE_SIZE = 1000
MIN_TEXT_CHARS = 1500          # below this the body is scanned / mojibake
MIN_TOKENS = 60
# own/rival score ratio. Calibrated on M1 (hand-verified): right pairs 1.3-3.4
# with a few homogeneous-topic outliers down to ~0.4; wrong pairs 0.18-0.22.
STRONG_MISMATCH = 0.35   # at or below: content alone condemns the pair
REVIEW_BELOW = 0.8       # below: worth a look, not evidence on its own
MISMATCH_RATIO = 1.35    # own this far above the rival = a confident right pair
# Two MS files whose token sets overlap this much are the same document.
SAME_DOC_JACCARD = 0.9
COVID_YEAR = 2020


# ── fetching / parsing ───────────────────────────────────────────────────────

R2_PUBLIC_BASE = "https://pub-b96af5a8f7044337bcb17a51b3fd4a60.r2.dev/"
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "grademax-papers")
_R2_CLIENT = None


def _r2():
    global _R2_CLIENT
    if _R2_CLIENT is None:
        import boto3
        from botocore.config import Config
        _R2_CLIENT = boto3.client(
            "s3", endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
            aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
            region_name="auto", config=Config(retries={"max_attempts": 3},
                                              max_pool_connections=32))
    return _R2_CLIENT


def _cache_path(url: str, ext: str) -> Path:
    return CACHE_DIR / (hashlib.sha1(url.encode()).hexdigest() + ext)


def fetch(url: str) -> bool:
    """Download `url` into the cache. False unless the body is a real PDF."""
    path = _cache_path(url, ".pdf")
    if path.is_file() and path.stat().st_size > 0:
        return True
    # The public r2.dev endpoint is throttled (~100 files/min); read the bucket
    # directly when credentials are present. The key is the URL path.
    if url.startswith(R2_PUBLIC_BASE) and os.getenv("R2_ACCESS_KEY_ID"):
        try:
            body = _r2().get_object(Bucket=R2_BUCKET, Key=unquote(url[len(R2_PUBLIC_BASE):]))["Body"].read()
        except Exception:  # noqa: BLE001 -- missing key etc.: fall back to HTTP
            body = b""
        if body.startswith(b"%PDF"):
            tmp = path.with_suffix(".part")
            tmp.write_bytes(body)
            tmp.replace(path)
            return True
    for _attempt in range(3):
        try:
            resp = requests.get(url, timeout=90)
        except requests.RequestException:
            continue
        if resp.status_code != 200 or not resp.content.startswith(b"%PDF"):
            return False
        tmp = path.with_suffix(".part")
        tmp.write_bytes(resp.content)
        tmp.replace(path)
        return True
    return False


_OCR = None
OCR_STAMP_RE = re.compile(r"GradeMax|PhysicsAndMaths|·", re.I)


def _ocr_cover(body: bytes) -> str:
    """OCR page 1 -- 2021+ QP covers draw the date and reference as outlines."""
    global _OCR
    import fitz
    if _OCR is None:
        from rapidocr_onnxruntime import RapidOCR
        _OCR = RapidOCR()
    doc = fitz.open(stream=body, filetype="pdf")
    try:
        pix = doc[0].get_pixmap(dpi=150)
    finally:
        doc.close()
    result, _ = _OCR(pix.tobytes("png"))
    # our own stamp OCRs as "GradeMax Mathematics·2022·Jan-M1.QP" -- never evidence
    return " ".join(item[1] for item in (result or []) if not OCR_STAMP_RE.search(item[1]))


def parse(url: str) -> dict | None:
    """Parsed identity + content tokens for a cached PDF (memoised on disk)."""
    pkl = _cache_path(url, ".v5.pkl")
    if pkl.is_file():
        return pickle.loads(pkl.read_bytes())
    pdf = _cache_path(url, ".pdf")
    if not pdf.is_file():
        return None
    body = pdf.read_bytes()
    try:
        info = read_pdf(body)
    except Exception as exc:  # noqa: BLE001
        info = {"ident": {"kind": None}, "tokens": set(), "pages": 0, "chars": 0,
                "error": f"{type(exc).__name__}: {exc}"[:200]}
    ident = info["ident"]
    if not info.get("error") and (ident.get("year") is None or ident.get("kind") is None):
        try:
            ocr_text = _ocr_cover(body)
            from_ocr = identify([ocr_text])
            filled = {k: v for k, v in from_ocr.items() if v and not ident.get(k)}
            if filled:
                info["ident"] = {**ident, **filled, "ocr": sorted(filled)}
        except Exception as exc:  # noqa: BLE001
            info["ocr_error"] = f"{type(exc).__name__}"
    pkl.write_bytes(pickle.dumps(info))
    return info


# ── rows ─────────────────────────────────────────────────────────────────────

def load_rows(level: str | None, subject: str | None) -> list[dict]:
    from supabase import create_client

    load_dotenv(REPO_ROOT / ".env.local")
    sb = create_client(os.environ["NEXT_PUBLIC_SUPABASE_URL"],
                       os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    subs = sb.table("subjects").select("id,code,name,level").eq("board", "Edexcel").execute().data
    subs = {s["id"]: s for s in subs
            if (not level or s["level"] == level)
            and (not subject or s["code"].startswith(subject))}
    rows, offset = [], 0
    while True:
        chunk = (sb.table("papers")
                 .select("id,subject_id,year,season,paper_number,pdf_url,markscheme_pdf_url")
                 .in_("subject_id", list(subs)).order("id")
                 .range(offset, offset + PAGE_SIZE - 1).execute().data)
        rows.extend(chunk)
        if len(chunk) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return [{**r, "code": subs[r["subject_id"]]["code"], "subject": subs[r["subject_id"]]["name"],
             "level": subs[r["subject_id"]]["level"], "season": (r["season"] or "").lower()}
            for r in rows]


# ── judging ──────────────────────────────────────────────────────────────────

def session_eq(y1, s1, y2, s2) -> bool | None:
    if not (y1 and s1 and y2 and s2):
        return None
    if (y1, s1) == (y2, s2):
        return True
    # Nov 2020 re-sat the cancelled summer papers
    if y1 == y2 == COVID_YEAR and {s1, s2} == {"may-jun", "oct-nov"}:
        return True
    return False


def ident_vs_row(ident: dict, row: dict) -> bool | None:
    return session_eq(ident.get("year"), ident.get("season"), row["year"], row["season"])


def ms_session_candidates(ident: dict) -> list[tuple]:
    """A mark scheme's title and publication code can disagree (Pearson copies
    codes between siblings); either reading is a legitimate identity."""
    out = []
    if ident.get("year"):
        out.append((ident["year"], ident["season"]))
    if ident.get("pub_year") and not ident.get("pub_is_date"):
        out.append((ident["pub_year"], ident["pub_season"]))
    return out


def ms_vs_row(ident: dict, row: dict) -> bool | None:
    cands = ms_session_candidates(ident)
    if not cands:
        return None
    return any(session_eq(y, s, row["year"], row["season"]) for y, s in cands)


def units_agree(qi: dict, mi: dict) -> bool | None:
    """QP paper-reference unit vs the MS's own units (cover bracket AND
    publications code -- Pearson copies one between siblings, so either may be
    the right one). `WME01` vs legacy GCE `6677` is a different exam."""
    qu = unit_family(qi.get("unit"))
    mus = {unit_family(u) for u in (mi.get("cover_unit"), mi.get("unit"))} - {None}
    if not qu or not mus:
        return None
    return qu in mus


def options_agree(qi: dict, mi: dict) -> bool | None:
    """History-style options (WHI01/1B vs WHI01_1D) and tiers must match. Only
    decided when both sides print an option letter."""
    qo, mo = option_letters(qi.get("paper")), option_letters(mi.get("paper"))
    if not qo or not mo:
        return None
    return qo == mo


def score_row(r: dict, parsed: dict, scorer: RarityScorer, norm: dict,
              ms_urls: list[str]) -> dict:
    """Own-MS score, best distinct rival, and rank of the own MS."""
    qp, ms = parsed[r["pdf_url"]], parsed[r["markscheme_pdf_url"]]
    qt = qp["tokens"]
    scores = sorted(((scorer.score(qt, parsed[u]["tokens"], norm[r["pdf_url"]], norm[u]), u)
                     for u in ms_urls), reverse=True)
    own = next(sc for sc, u in scores if u == r["markscheme_pdf_url"])
    own_toks = ms["tokens"]
    rival_score, rival_url = 0.0, None
    for sc, u in scores:
        if u == r["markscheme_pdf_url"]:
            continue
        other = parsed[u]["tokens"]
        # a text twin of the own MS (duplicate row / re-upload) is not a rival
        if len(own_toks & other) / (len(own_toks | other) or 1) >= SAME_DOC_JACCARD:
            continue
        rival_score, rival_url = sc, u
        break
    return {"own": own, "rival": rival_score, "rival_url": rival_url,
            "rank": 1 + sum(1 for sc, _u in scores if sc > own)}


def judge_subject(rows: list[dict], parsed: dict[str, dict]) -> list[dict]:
    subject_urls = {r[k] for r in rows for k in ("pdf_url", "markscheme_pdf_url")
                    if r[k] and parsed.get(r[k])}
    scorer = RarityScorer([parsed[u]["tokens"] for u in subject_urls])
    norm = {u: scorer.vec_norm(parsed[u]["tokens"]) for u in subject_urls}
    ms_urls = sorted({r["markscheme_pdf_url"] for r in rows
                      if r["markscheme_pdf_url"] and parsed.get(r["markscheme_pdf_url"])
                      and not is_low_text(parsed[r["markscheme_pdf_url"]])})
    ms_owner = defaultdict(list)
    for r in rows:
        if r["markscheme_pdf_url"]:
            ms_owner[r["markscheme_pdf_url"]].append(r)

    staged = []
    for r in rows:
        res = {k: r[k] for k in ("id", "level", "code", "subject", "year", "season",
                                 "paper_number", "pdf_url", "markscheme_pdf_url")}
        res.update(verdict="OK", notes=[])
        qp, ms = parsed.get(r["pdf_url"] or ""), parsed.get(r["markscheme_pdf_url"] or "")
        if not r["pdf_url"] or not r["markscheme_pdf_url"] or qp is None or ms is None:
            res["verdict"] = "MISSING"
            staged.append((res, None))
            continue
        qi, mi = qp["ident"], ms["ident"]
        res["qp_ident"] = {k: qi.get(k) for k in ("kind", "unit", "paper", "year", "season",
                                                  "evidence", "barcode", "copy_year", "ocr")}
        res["ms_ident"] = {k: mi.get(k) for k in ("kind", "unit", "cover_unit", "paper", "year",
                                                  "season", "evidence", "pubcode", "pub_year",
                                                  "pub_season", "ocr")}
        res["qp_vs_row"], res["ms_vs_row"] = ident_vs_row(qi, r), ms_vs_row(mi, r)
        res["unit_agree"] = units_agree(qi, mi)
        res["option_agree"] = options_agree(qi, mi)
        if qi.get("kind") == "MS":
            res["notes"].append("QP url serves a mark scheme")
        if mi.get("kind") == "QP":
            res["notes"].append("MS url serves a question paper")
        low = [side for side, p in (("qp", qp), ("ms", ms)) if is_low_text(p)]
        if low:
            res["notes"].append("no text layer: " + ",".join(low))
            staged.append((res, None))
            continue
        sc = score_row(r, parsed, scorer, norm, ms_urls)
        res.update(own_score=round(sc["own"], 4), rival_score=round(sc["rival"], 4),
                   own_rank=sc["rank"])
        if sc["rival_url"]:
            res["rival"] = [f"{o['year']} {o['season']} P{o['paper_number']}"
                            for o in ms_owner[sc["rival_url"]]]
            res["rival_url"] = sc["rival_url"]
        staged.append((res, sc))

    # The same barcode under two different sessions is one paper filed twice.
    # The copy is whichever row its own mark scheme does not fit.
    by_barcode = defaultdict(list)
    for res, sc in staged:
        bc = (res.get("qp_ident") or {}).get("barcode")
        if bc and sc:
            by_barcode[bc].append((res, sc))
    for bc, group in by_barcode.items():
        if len({(g["year"], g["season"]) for g, _sc in group}) < 2:
            continue
        best = max(sc["own"] for _g, sc in group)
        for g, sc in group:
            if sc["own"] < best * STRONG_MISMATCH:
                g["qp_vs_row"] = False
                g["notes"].append(f"QP barcode {bc} is also filed under another session")

    out = []
    for res, sc in staged:
        if res["verdict"] == "MISSING":
            out.append(res)
            continue
        qp_row, ms_row, unit_ok = res["qp_vs_row"], res["ms_vs_row"], res["unit_agree"]
        cy = (res.get("qp_ident") or {}).get("copy_year")
        # a paper is copyrighted in its exam year or (January papers) the year before
        if qp_row is None and cy and not (res["year"] - 1 <= cy <= res["year"]):
            qp_row = res["qp_vs_row"] = False
            res["notes"].append(f"QP copyright {cy}")
        ms_bad = ms_row is False or unit_ok is False or res["option_agree"] is False
        if res["option_agree"] is False:
            res["notes"].append(f"QP option {res['qp_ident'].get('paper')} != MS option "
                                f"{res['ms_ident'].get('paper')}")
        if sc is None:
            res["verdict"] = ("QP_WRONG" if qp_row is False and ms_row is True
                              else "MS_WRONG" if ms_bad
                              else "NO_TEXT")
            out.append(res)
            continue
        ratio = sc["own"] / sc["rival"] if sc["rival"] else 99.0
        res["ratio"] = round(ratio, 3)
        if qp_row is False and ms_row is True:
            res["verdict"] = "QP_WRONG"
        elif ms_bad:
            res["verdict"] = "MS_WRONG"
        elif ratio <= STRONG_MISMATCH:
            # content condemns it; the side follows the identities if they speak
            res["verdict"] = ("QP_WRONG" if qp_row is False
                              else "MS_WRONG" if qp_row is True and ms_row is not True
                              else "MISMATCH")
        elif qp_row is False:
            res["verdict"] = "ID_CONFLICT"
        elif ratio < REVIEW_BELOW:
            res["verdict"] = "REVIEW"
        out.append(res)
    return out


def is_low_text(p: dict) -> bool:
    return p["chars"] < MIN_TEXT_CHARS or len(p["tokens"]) < MIN_TOKENS


# ── driver ───────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", choices=["IGCSE", "IAL"])
    ap.add_argument("--subject", help="subject code prefix, e.g. 4PH or WMA11")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_rows(args.level, args.subject)
    urls = sorted({r[k] for r in rows for k in ("pdf_url", "markscheme_pdf_url") if r[k]})
    print(f"{len(rows)} rows, {len(urls)} distinct PDFs")

    with ThreadPoolExecutor(max_workers=32) as ex:
        ok = dict(zip(urls, ex.map(fetch, urls)))
    print(f"fetched: {sum(ok.values())} ok, {sum(not v for v in ok.values())} failed")

    good = [u for u in urls if ok[u]]
    parsed: dict[str, dict] = {}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for i, (u, p) in enumerate(zip(good, ex.map(parse, good, chunksize=8)), 1):
            if p is not None:
                parsed[u] = p
            if i % 250 == 0:
                print(f"  parsed {i}/{len(good)}", flush=True)

    by_subject = defaultdict(list)
    for r in rows:
        by_subject[r["code"]].append(r)
    results = []
    for code in sorted(by_subject):
        results += judge_subject(by_subject[code], parsed)

    OUT_JSON.write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["level", "code", "subject", "year", "season", "paper", "verdict",
                    "own_score", "rival_score", "ratio", "rival", "qp_says", "ms_says", "notes",
                    "pdf_url", "markscheme_pdf_url"])
        for r in results:
            qi, mi = r.get("qp_ident") or {}, r.get("ms_ident") or {}
            w.writerow([r["level"], r["code"], r["subject"], r["year"], r["season"],
                        r["paper_number"], r["verdict"], r.get("own_score"),
                        r.get("rival_score"), r.get("ratio"), "; ".join(r.get("rival") or []),
                        f"{qi.get('year')} {qi.get('season')} [{qi.get('evidence')}] {qi.get('barcode')}",
                        f"{mi.get('year')} {mi.get('season')} [{mi.get('evidence')}] {mi.get('pubcode')}",
                        "; ".join(r["notes"]), r["pdf_url"], r["markscheme_pdf_url"]])

    table = defaultdict(Counter)
    for r in results:
        table[f"{r['level']} {r['code']} {r['subject']}"][r["verdict"]] += 1
    cols = ["OK", "MS_WRONG", "QP_WRONG", "MISMATCH", "ID_CONFLICT", "REVIEW", "NO_TEXT", "MISSING"]
    print(f"\n{'SUBJECT':<44}{'ROWS':>5}" + "".join(f"{c[:9]:>10}" for c in cols))
    total = Counter()
    for k in sorted(table):
        total.update(table[k])
        print(f"{k[:43]:<44}{sum(table[k].values()):>5}" + "".join(f"{table[k][c]:>10}" for c in cols))
    print(f"{'TOTAL':<44}{sum(total.values()):>5}" + "".join(f"{total[c]:>10}" for c in cols))
    print(f"\nreports -> {OUT_JSON.relative_to(REPO_ROOT)}, {OUT_CSV.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
