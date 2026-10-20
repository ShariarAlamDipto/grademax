#!/usr/bin/env python3
"""
Reading sheets for the question <-> mark-scheme ANSWER check: one text block
per live tool question with the question's text, its linked scheme's text,
the marks, and an automatic content-overlap signal, so every pair can be read
by Claude and judged "does this scheme answer this question?".

    python -X utf8 scripts/build_answer_check_sheets.py [--subject 4PH1]

Text comes from the staged cuts (byte-identical to the live files, see
audit_tool_question_identity.py); cuts without a usable text layer
(scans, scrambled fonts) are OCR'd (RapidOCR, cached on disk).

Writes data/analysis/answer_check/<CODE>/<paper>.txt and
data/analysis/answer_check/<CODE>/pairs.json. Read-only otherwise.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.live_paper_sources import ROOT  # noqa: E402

CODES = ["4PH1", "4MB1", "4PM1", "4CH1", "4BI1", "4HB1",
         "WME01", "WMA11", "WMA12", "WMA13", "WMA14", "WST01"]
PUBLISHABLE = {"PROVEN", "SEQUENCE_PROVEN", "LABEL_PROVEN", "MANUAL_PROVEN", "REVIEWED_PROVEN"}
OUT = ROOT / "data" / "analysis" / "answer_check"
OCR_CACHE = OUT / "_ocr_cache"
NOISE = re.compile(
    r"DO NOT WRITE IN THIS AREA|GradeMax|\*P\d{5}[A-Z]*\d*\*|Turn over|\.{3,}|_{3,}|"
    r"[A-Za-z_ ]+ · \d{4} · [^\n]*|\d?[A-Z0-9]{4} \| \d{4} \|[^\n]*|Leave\s+blank", re.I)
NUM = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w])")
WORD = re.compile(r"[a-z]{5,}")
QP_CHARS, MS_CHARS = 380, 460
_ocr = None


def ocr_pdf(pdf: Path) -> str:
    global _ocr
    key = hashlib.md5(pdf.read_bytes()).hexdigest()
    cache = OCR_CACHE / f"{key}.txt"
    if cache.is_file():
        return cache.read_text(encoding="utf-8")
    if _ocr is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr = RapidOCR()
    parts = []
    with fitz.open(pdf) as doc:
        for page in doc:
            result, _ = _ocr(page.get_pixmap(dpi=150).tobytes("png"))
            parts.append(" ".join(item[1] for item in (result or [])))
    text = "\n".join(parts)
    OCR_CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(text, encoding="utf-8")
    return text


def readable(text: str) -> bool:
    words = re.findall(r"[A-Za-z]{3,}", text)
    if len(words) < 8:
        return False
    common = sum(w.lower() in {"the", "and", "for", "find", "show", "mark", "with", "that",
                               "this", "which", "total", "question", "answer", "award"} for w in words)
    return common >= 2


def text_of(pdf: Path) -> tuple[str, str]:
    with fitz.open(pdf) as doc:
        text = "\n".join(page.get_text() for page in doc)
    if readable(text):
        return text, "text"
    return ocr_pdf(pdf), "ocr"


def tidy(text: str, limit: int) -> str:
    text = NOISE.sub(" ", text)
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\s*\n\s*", " / ", text).strip(" /")
    return text[:limit]


FRONT_RE = re.compile(r"Mark Scheme \(Results\)|General Marking Guidance|Edexcel and BTEC Qualifications", re.I)
QP_START_RE = re.compile(r"Answer ALL questions\.?|Write your answers in the spaces provided\.?|"
                         r"You must write down all the stages in your working\.?", re.I)


def from_answers(ms_text: str, question: int) -> str:
    """Skip any scheme front matter: start at this question's own label."""
    m = re.search(rf"(?:^|\n)\s*{question}\s*(?:\.|\(|\n|[a-z]\b)", ms_text)
    return ms_text[m.start():] if m else ms_text


def overlap(qp: str, ms: str) -> dict:
    qn = {n for n in NUM.findall(qp) if not (n.isdigit() and int(n) <= 20)}
    mn = {n for n in NUM.findall(ms) if not (n.isdigit() and int(n) <= 20)}
    qw, mw = set(WORD.findall(qp.lower())), set(WORD.findall(ms.lower()))
    return {"shared_numbers": sorted(qn & mn)[:12], "shared_words": len(qw & mw),
            "qp_numbers": len(qn)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject")
    args = ap.parse_args()
    for code in ([args.subject] if args.subject else CODES):
        rows = json.loads((ROOT / "data/analysis/live_rebuild" / code / "verdicts.json").read_text(encoding="utf-8"))["rows"]
        rows = [r for r in rows if r["verdict"] in PUBLISHABLE and r.get("ms")]
        rows.sort(key=lambda r: (r["live_key"], int(r["question"])))
        out_dir = OUT / code
        out_dir.mkdir(parents=True, exist_ok=True)
        pairs, sheets = [], {}
        for r in rows:
            qp_text, qp_mode = text_of(ROOT / r["qp"])
            ms_text, ms_mode = text_of(ROOT / r["ms"])
            front = bool(FRONT_RE.search(ms_text))
            qp = tidy(QP_START_RE.sub(" ", qp_text), QP_CHARS)
            ms = tidy(from_answers(ms_text, int(r["question"])), MS_CHARS)
            ov = overlap(qp_text, ms_text)
            pair = {"paper": r["live_key"], "question": r["question"], "marks": r["marks"], "ms_front_matter": front,
                    "proof": r["verdict"], "qp_mode": qp_mode, "ms_mode": ms_mode, **ov}
            pairs.append(pair)
            sheets.setdefault(r["live_key"], []).append(
                f"### {r['live_key']} Q{r['question']}  [{r['marks']} marks]  proof={r['verdict']}  "
                f"text={qp_mode}/{ms_mode}  shared#={ov['shared_numbers']}  sharedwords={ov['shared_words']}"
                f"{'  MS_FRONT_MATTER' if front else ''}\n"
                f"QP: {qp}\nMS: {ms}\n")
        for paper, blocks in sheets.items():
            (out_dir / f"{paper}.txt").write_text("\n".join(blocks), encoding="utf-8")
        (out_dir / "pairs.json").write_text(json.dumps(pairs, indent=1), encoding="utf-8")
        print(f"{code}: {len(pairs)} pairs, {len(sheets)} papers, "
              f"ocr qp {sum(p['qp_mode'] == 'ocr' for p in pairs)} / ms {sum(p['ms_mode'] == 'ocr' for p in pairs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
