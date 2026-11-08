"""
Write the printed marks of every live tool question of one subject to
src/lib/printedMarks/<CODE>.json  ({"<paper_id>|<question_number>": marks}).

The Test Builder and Worksheet Generator add these up for "Total Marks" on the
cover page. Questions with no entry are counted as 4 marks, so rerun this
after publishing new questions for a subject.

Read-only against Supabase and R2. See scripts/lib/printed_question_marks.py
for the reading order and the checks.

    .venv/Scripts/python -X utf8 scripts/extract_printed_question_marks.py --subject 4PH1
    .venv/Scripts/python -X utf8 scripts/extract_printed_question_marks.py --subject 4PH1 --check

--check writes nothing and fails if the file differs from what would be written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import printed_question_marks as pqm  # noqa: E402
from lib.live_paper_sources import fetch_rows, r2_reader, subject_id, supabase_client  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "src" / "lib" / "printedMarks"
CACHE_DIR = ROOT / "tmp" / "printed_marks"
TESSERACT = Path(os.environ.get("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe"))


@dataclass(frozen=True)
class Question:
    page_id: str
    paper_id: str
    question_number: str
    qp_url: str
    label: str  # "2019 may-jun P1 Q7", for reports

    @property
    def key(self) -> str:
        return f"{self.paper_id}|{self.question_number}"


@dataclass(frozen=True)
class Reading:
    marks: int | None
    source: str  # text | ocr | part_sum | unread
    paper_total: int | None


def load_questions(code: str) -> list[Question]:
    sb = supabase_client()
    sid = subject_id(sb, code)
    papers = fetch_rows(lambda o: sb.table("papers").select("id,year,season,paper_number")
                        .eq("subject_id", sid).order("id").range(o, o + 999))
    by_id = {p["id"]: p for p in papers}
    ids = list(by_id)
    rows: list[dict] = []
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        rows += fetch_rows(lambda o, c=chunk: sb.table("pages")
                           .select("id,paper_id,question_number,qp_page_url")
                           .eq("is_question", True).not_.is_("qp_page_url", "null")
                           .in_("paper_id", c).order("id").range(o, o + 999))
    out = []
    for r in rows:
        p = by_id[r["paper_id"]]
        label = f"{p['year']} {p['season']} P{p['paper_number']} Q{r['question_number']}"
        out.append(Question(r["id"], r["paper_id"], str(r["question_number"]), r["qp_page_url"], label))
    return out


def fetch_pdf(q: Question, get_bytes) -> bytes:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / (hashlib.sha256(q.qp_url.encode()).hexdigest() + ".pdf")
    if path.is_file() and path.stat().st_size:
        return path.read_bytes()
    data = get_bytes(q.qp_url)
    if not data:
        raise RuntimeError(f"could not read {q.qp_url}")
    path.write_bytes(data)
    return data


def ocr(doc: fitz.Document, *, margin_only: bool) -> str:
    out: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        for i, page in enumerate(doc):
            img = Path(td) / f"{i}.png"
            if margin_only:
                r = page.rect
                clip = fitz.Rect(r.width * 0.70, r.height * 0.04, r.width * 0.90, r.height * 0.95)
                page.get_pixmap(dpi=400, clip=clip).save(img)
                args = ["--psm", "11", "-c", "tessedit_char_whitelist=()0123456789"]
            else:
                page.get_pixmap(dpi=300).save(img)
                args = ["--psm", "6"]
            result = subprocess.run([str(TESSERACT), str(img), "stdout", *args],
                                    capture_output=True, text=True, encoding="utf-8",
                                    errors="replace", check=False)
            out.append(result.stdout)
    return pqm.normalise(" ".join(out))


def read_question(q: Question, get_bytes) -> Reading:
    doc = fitz.open(stream=fetch_pdf(q, get_bytes), filetype="pdf")
    text = pqm.normalise(" ".join(page.get_text() for page in doc))
    marks = pqm.labelled_marks(text, q.question_number) or pqm.unlabelled_marks(text)
    if pqm.plausible(marks):
        return Reading(marks, "text", pqm.printed_paper_total(text))
    if not TESSERACT.is_file():
        return Reading(None, "unread", None)
    scanned = ocr(doc, margin_only=False)
    marks = pqm.labelled_marks(scanned, q.question_number) or pqm.unlabelled_marks(scanned)
    total = pqm.printed_paper_total(text) or pqm.printed_paper_total(scanned)
    if pqm.plausible(marks):
        return Reading(marks, "ocr", total)
    marks = pqm.part_marks_sum(ocr(doc, margin_only=True))
    return Reading(marks if pqm.plausible(marks) else None, "part_sum" if pqm.plausible(marks) else "unread", total)


def resolve(code: str, questions: list[Question], readings: dict[str, Reading]) -> tuple[dict[str, int], list[str]]:
    """Accepted marks per key, plus problems to report."""
    by_paper: dict[str, list[Question]] = defaultdict(list)
    for q in questions:
        by_paper[q.paper_id].append(q)
    accepted: dict[str, int] = {}
    problems: list[str] = []
    for qs in by_paper.values():
        reads = [readings[q.page_id] for q in qs]
        printed = next((r.paper_total for r in reads if r.paper_total), None)
        complete = all(r.marks is not None for r in reads)
        whole = complete and pqm.is_whole_paper(q.question_number for q in qs)
        totals_ok = whole and pqm.paper_total_ok(code, [r.marks for r in reads], printed)
        for q, r in zip(qs, reads):
            if r.marks is None:
                problems.append(f"UNREAD   {q.label}")
            elif r.source == "part_sum" and not totals_ok:
                problems.append(f"HELD     {q.label}: part marks add to {r.marks}, but the paper "
                                f"does not add up to a valid total")
            else:
                accepted[q.key] = r.marks
        if whole and not totals_ok and all(r.source != "part_sum" for r in reads):
            total = sum(r.marks for r in reads)
            problems.append(f"WARNING  {qs[0].label.rsplit(' Q', 1)[0]}: printed question totals "
                            f"add to {total} (live questions may not cover the whole paper)")
    return dict(sorted(accepted.items())), problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subject", required=True, help="subjects.code, e.g. 4PH1")
    ap.add_argument("--check", action="store_true", help="compare with the existing file, write nothing")
    args = ap.parse_args()
    code = args.subject

    questions = load_questions(code)
    get_bytes, _ = r2_reader()
    with ThreadPoolExecutor(8) as pool:
        readings = dict(zip((q.page_id for q in questions),
                            pool.map(lambda q: read_question(q, get_bytes), questions)))
    accepted, problems = resolve(code, questions, readings)

    sources = defaultdict(int)
    for r in readings.values():
        sources[r.source] += 1
    print(f"{code}: {len(questions)} live questions, {len(accepted)} with printed marks; "
          f"read from {dict(sources)}")
    for line in problems:
        print("  " + line)

    out = OUT_DIR / f"{code}.json"
    body = json.dumps(accepted, indent=0, sort_keys=True) + "\n"
    if args.check:
        same = out.is_file() and json.loads(out.read_text()) == accepted
        print("check:", "file is current" if same else f"{out} differs")
        return 0 if same else 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}")
    return 1 if any(p.startswith(("UNREAD", "HELD")) for p in problems) else 0


if __name__ == "__main__":
    raise SystemExit(main())
