#!/usr/bin/env python3
"""Read-only audit: does every LIVE Edexcel IGCSE mark scheme belong to the
question paper it is served next to?

Why this exists
---------------
`audit_igcse_edexcel_labels.py` reads the LOCAL archive and checks each file
against its own filename. That leaves two gaps:

  1. The site does not serve the archive. It serves whatever URL the `papers`
     row holds on R2, and fixes applied to the archive have failed to reach R2
     before (see the 166 live PMT Model Answers). Only the live file counts.
  2. A file can match its label and still be the wrong partner: if the QP and
     the MS were each checked in isolation, nobody compared them to each other.

So this downloads the two files every `papers` row actually serves, reads each
one's OWN front page, and compares QP <-> MS directly, then both against the row.

What each document says about itself
------------------------------------
  QP  cover: paper reference `4PH1/1P`, exam date `Monday 20 May 2019`,
      and the barcode at the foot of every page (`*P61234A0120*`).
  MS  cover: `Mark Scheme (Results) Summer 2019 ... (4PH1) Paper 1P`, and the
      publications code `4PH1_1P_1906_MS` -- subject, paper and YYMM in one
      token, which is the strongest identity signal a mark scheme carries.

PMT / GradeMax stamp text is stripped before anything is read (it is the very
thing that mislabelled the archive; see WATERMARK_RE in the label audit).

Verdicts, per row
-----------------
  OK          QP and MS agree with each other and with the row
  MISPAIRED   QP and MS contradict each other (code, paper or session) -- the
              student is shown another paper's answers
  QP_WRONG    MS matches the row, QP does not
  MS_WRONG    QP matches the row, MS does not
  LABEL_WRONG QP and MS agree with each other but not with the row
  UNVERIFIED  a cover could not be read (image-only / mojibake); unproven, not bad
  MISSING     the row lacks a QP or an MS URL, or the URL does not return a PDF

Nothing is written except the report files and a download cache.

Usage:
    python -X utf8 scripts/audit_live_igcse_qp_ms_pairing.py
    python -X utf8 scripts/audit_live_igcse_qp_ms_pairing.py --subject 4PH1
    python -X utf8 scripts/audit_live_igcse_qp_ms_pairing.py --workers 12
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import fitz  # PyMuPDF
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_igcse_edexcel_labels import (  # noqa: E402
    ANY_CODE_RE, BARCODE_RE, EXAM_DATE_RE, MONTH_SEASON, MS_RE, PAPER_LINE_RE,
    QP_COVER_RE, REISSUE_RE, SESSION_RE, WATERMARK_RE, parse_variant,
)

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = REPO_ROOT / "data" / "analysis" / "live_igcse_qp_ms_pairing.json"
OUT_CSV = REPO_ROOT / "data" / "analysis" / "live_igcse_qp_ms_pairing.csv"
CACHE_DIR = Path(os.environ.get("PAIRING_CACHE_DIR",
                                REPO_ROOT / "data" / "analysis" / ".pairing_cache"))
PAGE_SIZE = 1000
COVER_PAGES = 3
OCR_DPI = 150

# Subject stems that legitimately appear on a subject's own documents.
ALT_STEMS = {
    "4BN": ("4BN", "4BE", "4BA"),   # Bangla ran as Bengali 4BE0, then 4BA0
    "4PM": ("4PM", "4MP"),          # Pearson typo on the June 2011 P01 MS
}
# Mathematics A: the archive's 1H/2H are Edexcel's 3H/4H, and plain 1/2 are 1F/2F.
MATHS_A_EQUIV = {"1": "1F", "2": "2F", "1R": "1FR", "2R": "2FR",
                 "1H": "3H", "2H": "4H", "1HR": "3HR", "2HR": "4HR"}
# Nov 2020 re-sat the cancelled summer papers, so May-Jun covers under Oct-Nov.
COVID_REUSE_YEAR = 2020

# `4PH1_1P_1906_MS`; older ones print `UG031234` style codes, which carry no
# identity and are ignored.
PUB_CODE_RE = re.compile(
    r"\b(4[A-Z]{2}[01])_([0-9]{1,2}[A-Z]{0,3})_(\d{2})(\d{2})_(?:MS|ms)\b")
MS_PAPER_RE = re.compile(r"\bPaper\s*:?\s*0?([0-9]{1,2}[A-Z]{0,3})(?![A-Za-z0-9])")
MONTH_NUM_SEASON = {1: "jan", 2: "jan", 3: "jan", 4: "may-jun", 5: "may-jun",
                    6: "may-jun", 7: "may-jun", 8: "oct-nov", 9: "oct-nov",
                    10: "oct-nov", 11: "oct-nov", 12: "oct-nov"}


# ── fetching ─────────────────────────────────────────────────────────────────

def fetch(url: str) -> bytes | None:
    """Download `url` (cached on disk). None unless the body is really a PDF."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / (hashlib.sha1(url.encode()).hexdigest() + ".pdf")
    if path.is_file() and path.stat().st_size > 0:
        return path.read_bytes()
    for _attempt in range(3):
        try:
            resp = requests.get(url, timeout=60)
        except requests.RequestException:
            continue
        if resp.status_code != 200:
            return None
        body = resp.content
        if not body.startswith(b"%PDF"):
            return None
        tmp = path.with_suffix(".part")
        tmp.write_bytes(body)
        tmp.replace(path)
        return body
    return None


# ── reading a front page ─────────────────────────────────────────────────────

# Pearson sometimes types the spec digit as a letter O ("Physics (4PHO)").
LETTER_O_CODE_RE = re.compile(r"\b(4[A-Z]{2})O\b")


def clean(text: str) -> str:
    text = REISSUE_RE.sub(" ", WATERMARK_RE.sub(" ", " ".join(text.split())))
    return LETTER_O_CODE_RE.sub(r"\g<1>0", text)


_OCR_ENGINE = None
OCR_STAMP_RE = re.compile(r"GradeMax|PhysicsAndMaths|[·|]", re.I)


def ocr_page(doc: "fitz.Document", index: int) -> str:
    """OCR one rendered page. Covers that are scanned images, or whose fonts
    have no usable ToUnicode map, carry no readable text layer at all."""
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        from rapidocr_onnxruntime import RapidOCR
        _OCR_ENGINE = RapidOCR()
    pix = doc[index].get_pixmap(dpi=OCR_DPI)
    result, _elapse = _OCR_ENGINE(pix.tobytes("png"))
    # Drop our own stamps. OCR renders "Paper 1 · MS" as "Paper1MS", which
    # WATERMARK_RE no longer recognises, and it would be read as the cover.
    return " ".join(item[1] for item in (result or [])
                    if not OCR_STAMP_RE.search(item[1]))


def read_identity(body: bytes, stem_ok: tuple[str, ...]) -> dict:
    """What the document says it is, from its own first pages only; falls back
    to OCR of the cover when the text layer says nothing legible."""
    try:
        doc = fitz.open(stream=body, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        return {"error": f"unreadable ({type(exc).__name__})"}
    try:
        n_pages = doc.page_count
        pages = [doc[i].get_text() for i in range(min(COVER_PAGES, n_pages))]
        ident = identify(pages, stem_ok, n_pages)
        # 2021+ QP covers draw the exam date and paper reference as outlines,
        # so the text layer has the barcode but no session. OCR fills the gaps
        # and never overrides what the text layer already stated.
        incomplete = not legible(ident) or (ident["kind"] != "MS" and not ident["year"])
        if incomplete and n_pages:
            ocr_pages = [ocr_page(doc, i) for i in range(min(2, n_pages))]
            from_ocr = identify(ocr_pages, stem_ok, n_pages)
            filled = {k: v for k, v in from_ocr.items() if v and not ident.get(k)}
            if filled:
                ident = {**ident, **filled, "ocr": sorted(filled)}
    finally:
        doc.close()
    return ident


def identify(pages: list[str], stem_ok: tuple[str, ...], n_pages: int) -> dict:
    head = clean(" ".join(pages))
    page1 = clean(pages[0]) if pages else ""

    kind = "MS" if MS_RE.search(head) else ("QP" if QP_COVER_RE.search(head) else None)

    ident = {"kind": kind, "code": None, "paper": None, "year": None,
             "season": None, "evidence": "", "barcode": None, "pages": n_pages,
             "source": None}

    # 1. the mark scheme's own cover title ("Summer 2021 ... (4GE1) Paper 1").
    #    It outranks the publications code: Pearson copy-pastes that code from
    #    the sibling paper often enough (4GE1 2021 P1 prints `4GE1_02_2106_MS`,
    #    4AC1 Summer 2025 prints `..._2406_MS`) -- each checked against the
    #    answers, and the title was right every time.
    if kind == "MS":
        m = MS_PAPER_RE.search(page1)
        if m:
            ident.update(paper=m.group(1).upper(), source="ms-title")
        m = SESSION_RE.search(page1)
        if m:
            ident.update(year=int(m.group(2)),
                         season=MONTH_SEASON[m.group(1).lower()].lower(),
                         evidence=m.group(0))

    # 2. publications code `4PH1_1P_1906_MS` -- fills only what the title lacks
    pub = [m for m in PUB_CODE_RE.finditer(head) if m.group(1).startswith(stem_ok)]
    if pub:
        m = pub[0]
        yy, mm = int(m.group(3)), int(m.group(4))
        ident["pubcode"] = m.group(0)
        ident["code"] = m.group(1)
        pub_paper = m.group(2).upper()
        pub_session = (2000 + yy, MONTH_NUM_SEASON[mm]) if 1 <= mm <= 12 else (None, None)
        if ident["paper"] is None:
            ident.update(paper=pub_paper, source="pubcode")
        if ident["year"] is None and pub_session[0]:
            ident.update(year=pub_session[0], season=pub_session[1], evidence=m.group(0))
        # ...but the title is not infallible either: 4PH0 January 2017 P1's
        # title reads "Chemistry (4PH0) Paper 1C" over a Physics scheme whose
        # code says 1P. Keep the code's reading as an alternative identity.
        ident["alt"] = {"paper": pub_paper, "year": pub_session[0], "season": pub_session[1]}

    # 2. paper reference `4PH1/1P` (QP cover; some MS covers too)
    if ident["paper"] is None:
        refs = Counter()
        for m in ANY_CODE_RE.finditer(head):
            refs[(m.group(1) + m.group(2), m.group(3).upper())] += 1
        own = [(k, n) for k, n in refs.most_common() if k[0].startswith(stem_ok)]
        if own:
            (code, paper), _n = own[0]
            ident.update(code=code, paper=paper, source="ref")
        else:
            others = [k for k, _n in refs.most_common() if not k[0].startswith("4SC")]
            if others:
                ident.update(code=others[0][0], paper=others[0][1], source="ref-foreign")

    # 3. a bare "Paper 1P" line (MS covers that print no reference)
    if ident["paper"] is None:
        m = (PAPER_LINE_RE.search(page1) if kind == "QP" else MS_PAPER_RE.search(page1))
        if m:
            ident.update(paper=m.group(1).upper(), source=ident["source"] or "paper-line")
    if ident["code"] is None:
        # a joint mark scheme names several codes; prefer this subject's own
        bare = re.findall(r"\b(4[A-Z]{2}[01])\b", page1)
        own = [c for c in bare if c.startswith(stem_ok)]
        others = [c for c in bare if not c.startswith("4SC")]
        if own or others:
            ident["code"] = (own or others)[0]

    # session: exam date on a QP cover; "Summer 2019" on an MS cover
    if ident["year"] is None:
        m = EXAM_DATE_RE.search(page1)
        if m:
            ident.update(year=int(m.group(3)),
                         season=MONTH_SEASON[m.group(2).lower()].lower(),
                         evidence=m.group(0))
        elif kind == "MS":
            m = SESSION_RE.search(page1)
            if m:
                ident.update(year=int(m.group(2)),
                             season=MONTH_SEASON[m.group(1).lower()].lower(),
                             evidence=m.group(0))

    bc = BARCODE_RE.search(head)
    ident["barcode"] = bc.group(1) if bc else None
    return ident


# ── comparing ────────────────────────────────────────────────────────────────

def norm_paper(token: str | None, stem: str) -> str | None:
    if not token:
        return None
    token = token.upper().lstrip("0") or token
    if stem == "4MA":
        token = MATHS_A_EQUIV.get(token, token)
    return token


def papers_agree(a: str | None, b: str | None, stem: str, b_is_ms: bool) -> bool | None:
    """None = cannot tell. Paper number and R-flag must agree; tier letters too
    for Maths A; subject letters (P/C/B) may be omitted by one side."""
    pa, pb = parse_variant(a or ""), parse_variant(b or "")
    if not pa or not pb:
        return None
    if pa[0] != pb[0]:
        return False
    if pa[2] != pb[2]:
        # MS covers often print the plain number for the R series ("Paper 02")
        if b_is_ms and not pb[2] and not pb[1]:
            return None
        if not pa[2] and not pa[1] and not pb[1]:
            return None
        return False
    if stem == "4MA":
        ta, tb = {c for c in pa[1] if c in "FH"}, {c for c in pb[1] if c in "FH"}
        if ta and tb and ta != tb:
            return False
    if pa[1] and pb[1] and pa[1] != pb[1]:
        return False
    return True


def sessions_agree(y1, s1, y2, s2) -> bool | None:
    if not (y1 and s1 and y2 and s2):
        return None
    if (y1, s1) == (y2, s2):
        return True
    if y1 == y2 == COVID_REUSE_YEAR and {s1, s2} == {"may-jun", "oct-nov"}:
        return True
    return False


def codes_agree(c1, c2) -> bool | None:
    if not c1 or not c2:
        return None
    s1, s2 = c1[:3], c2[:3]
    return s1 == s2 or any(s1 in group and s2 in group for group in ALT_STEMS.values())


def compare(a: dict, b: dict, stem: str, b_is_ms: bool) -> list[str]:
    """Contradictions between two identities (either may be the row)."""
    issues = []
    if codes_agree(a.get("code"), b.get("code")) is False:
        issues.append(f"subject {a['code']}!={b['code']}")
    pa, pb = norm_paper(a.get("paper"), stem), norm_paper(b.get("paper"), stem)
    if papers_agree(pa, pb, stem, b_is_ms) is False:
        issues.append(f"paper {pa}!={pb}")
    if (a.get("season") != "specimen" and b.get("season") != "specimen"
            and sessions_agree(a.get("year"), a.get("season"),
                               b.get("year"), b.get("season")) is False):
        issues.append(f"session {a['year']}/{a['season']}!={b['year']}/{b['season']}")
    return issues


def compare_any(a: dict, b: dict, stem: str, b_is_ms: bool) -> list[str]:
    """`compare`, accepting `b`'s alternative identity (its publications code)
    when that is what agrees. A title/code disagreement inside one mark scheme
    is Pearson's typo, not evidence the scheme belongs to another paper."""
    issues = compare(a, b, stem, b_is_ms)
    alt = b.get("alt")
    if issues and alt:
        alt_issues = compare(a, {**b, **{k: v for k, v in alt.items() if v}}, stem, b_is_ms)
        if len(alt_issues) < len(issues):
            return alt_issues
    return issues


def legible(ident: dict) -> bool:
    return bool(ident.get("paper") or ident.get("year"))


def audit_row(job: dict) -> dict:
    stem = job["code"][:3]
    stem_ok = ALT_STEMS.get(stem, (stem,))
    row_ident = {"code": job["code"], "paper": job["paper_number"],
                 "year": job["year"], "season": job["season"]}
    out = {**{k: job[k] for k in ("id", "code", "subject", "year", "season",
                                   "paper_number", "pdf_url", "markscheme_pdf_url")},
           "verdict": "OK", "issues": [], "qp": None, "ms": None}

    idents = {}
    for side, url in (("qp", job["pdf_url"]), ("ms", job["markscheme_pdf_url"])):
        if not url:
            out["verdict"] = "MISSING"
            out["issues"].append(f"no {side} url")
            continue
        body = fetch(url)
        if body is None:
            out["verdict"] = "MISSING"
            out["issues"].append(f"{side} not a pdf / not 200")
            continue
        ident = read_identity(body, stem_ok)
        out[side] = ident
        idents[side] = ident
    if out["verdict"] == "MISSING":
        return out

    qp, ms = idents["qp"], idents["ms"]
    if qp.get("kind") == "MS":
        out["issues"].append("qp url serves a MARK SCHEME")
    if ms.get("kind") == "QP":
        out["issues"].append("ms url serves a QUESTION PAPER")

    if not legible(qp) or not legible(ms):
        out["verdict"] = "UNVERIFIED" if not out["issues"] else "MISPAIRED"
        return out

    pair = compare_any(qp, ms, stem, b_is_ms=True)
    qp_vs_row = compare(row_ident, qp, stem, b_is_ms=False)
    ms_vs_row = compare_any(row_ident, ms, stem, b_is_ms=True)

    if pair or out["issues"]:
        out["issues"] += [f"QP<>MS {i}" for i in pair]
        if not qp_vs_row and ms_vs_row:
            out["verdict"] = "MS_WRONG"
            out["issues"] += [f"MS<>row {i}" for i in ms_vs_row]
        elif qp_vs_row and not ms_vs_row:
            out["verdict"] = "QP_WRONG"
            out["issues"] += [f"QP<>row {i}" for i in qp_vs_row]
        else:
            out["verdict"] = "MISPAIRED"
            out["issues"] += [f"QP<>row {i}" for i in qp_vs_row]
            out["issues"] += [f"MS<>row {i}" for i in ms_vs_row]
    elif qp_vs_row:
        out["verdict"] = "LABEL_WRONG"
        out["issues"] += [f"row<>docs {i}" for i in qp_vs_row]
    return out


# ── driver ───────────────────────────────────────────────────────────────────

def load_rows(subject_code: str | None) -> list[dict]:
    from supabase import create_client

    load_dotenv(REPO_ROOT / ".env.local")
    sb = create_client(os.environ["NEXT_PUBLIC_SUPABASE_URL"],
                       os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    query = sb.table("subjects").select("id,code,name").eq("board", "Edexcel").eq("level", "IGCSE")
    subjects = {s["id"]: s for s in query.execute().data}
    if subject_code:
        subjects = {k: v for k, v in subjects.items() if v["code"] == subject_code}
    rows, offset = [], 0
    while True:
        chunk = (sb.table("papers")
                 .select("id,subject_id,year,season,paper_number,pdf_url,markscheme_pdf_url")
                 .in_("subject_id", list(subjects))
                 .order("id")
                 .range(offset, offset + PAGE_SIZE - 1)
                 .execute().data)
        rows.extend(chunk)
        if len(chunk) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return [{**r, "code": subjects[r["subject_id"]]["code"],
             "subject": subjects[r["subject_id"]]["name"],
             "season": (r["season"] or "").lower()} for r in rows]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", help="one subject code, e.g. 4PH1")
    ap.add_argument("--workers", type=int, default=10)
    args = ap.parse_args()

    rows = load_rows(args.subject)
    print(f"auditing {len(rows)} live papers rows ...\n")
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for i, res in enumerate(ex.map(audit_row, rows, chunksize=4), 1):
            results.append(res)
            if i % 100 == 0:
                print(f"  ... {i}/{len(rows)}", flush=True)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["code", "subject", "year", "season", "paper", "verdict", "issues",
                    "qp_found", "ms_found", "pdf_url", "markscheme_pdf_url"])
        for r in sorted(results, key=lambda r: (r["code"], r["year"], r["season"], r["paper_number"])):
            def found(side):
                i = r.get(side) or {}
                return f"{i.get('code')}/{i.get('paper')} {i.get('year')} {i.get('season')} [{i.get('evidence', '')}]"
            w.writerow([r["code"], r["subject"], r["year"], r["season"], r["paper_number"],
                        r["verdict"], "; ".join(r["issues"]), found("qp"), found("ms"),
                        r["pdf_url"], r["markscheme_pdf_url"]])

    by_subject = defaultdict(Counter)
    for r in results:
        by_subject[f"{r['code']} {r['subject']}"][r["verdict"]] += 1
    cols = ["OK", "MISPAIRED", "QP_WRONG", "MS_WRONG", "LABEL_WRONG", "UNVERIFIED", "MISSING"]
    print(f"\n{'SUBJECT':<32}{'ROWS':>6}" + "".join(f"{c:>12}" for c in cols))
    total = Counter()
    for subject in sorted(by_subject):
        c = by_subject[subject]
        total.update(c)
        print(f"{subject[:31]:<32}{sum(c.values()):>6}" + "".join(f"{c[k]:>12}" for k in cols))
    print(f"{'TOTAL':<32}{sum(total.values()):>6}" + "".join(f"{total[k]:>12}" for k in cols))

    print("\nPROBLEMS")
    for r in sorted(results, key=lambda r: (r["code"], r["year"], r["season"], r["paper_number"])):
        if r["verdict"] in ("OK", "UNVERIFIED"):
            continue
        print(f"  {r['code']} {r['year']} {r['season']:<8} P{r['paper_number']:<4} "
              f"{r['verdict']:<11} {'; '.join(r['issues'])}")
    print(f"\nreports -> {OUT_JSON.relative_to(REPO_ROOT)} , {OUT_CSV.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
