"""
Worked-solution solver for the Maths B (4MB1) chapterwise workbook -- PART 1
(chapters 1-5, 401 questions).

For every question in `print_index_paged_part1.json` this:

  1. Resolves the source question paper (QP) and its attached mark scheme (MS)
     back to the per-question PDFs under `data/workbook/mathsb/<paper>/`.
  2. Renders both to page images and asks a vision model to
       a. read the printed question number,
       b. list which question numbers actually appear in the MS image(s),
       c. decide whether the MS attached to this question really contains the
          marking for THIS question (the shared-MS-page defect, see
          [[project_mathsb_chapterwise_workbook]]),
       d. check the mark scheme's arithmetic,
       e. produce a clean, correct, step-by-step worked solution in LaTeX with
          the M1/A1/B1 mark annotations, and the final answer.
  3. AUTO-CORRECTS mark-scheme placement where confident: if the attached MS
     does not contain this question, it searches sibling MS PDFs in the same
     paper for the page that does, and relinks it (recorded in the report).

Results are cached per slug so the run is resumable and re-runs are free.

Why a SEPARATE script (not folded into build_mathsb_workbook_segments): per the
project rule, every subject/stage gets its own dedicated script.

USAGE
  python scripts/solve_mathsb_workbook_part1.py --limit 5      # smoke test
  python scripts/solve_mathsb_workbook_part1.py --execute      # full run (resumes)
  python scripts/solve_mathsb_workbook_part1.py --report       # audit only, no calls
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
from pathlib import Path

import fitz  # PyMuPDF
import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
MATHSB_ROOT = REPO_ROOT / "data" / "workbook" / "mathsb"


def index_path(part: int) -> Path:
    return MATHSB_ROOT / "print" / f"print_index_paged_part{part}.json"


def cache_path(part: int) -> Path:
    return REPO_ROOT / "data" / "workbook" / f"mathsb_worked_solutions_part{part}.json"


def report_path(part: int) -> Path:
    return REPO_ROOT / "data" / "workbook" / f"mathsb_worked_solutions_part{part}_report.json"


RENDER_DPI = 110  # 140 blew the per-minute token budget on the lite models; 110 reads fine
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# Each free-tier model carries its OWN daily quota, so rotating across several
# pools their capacity -- the single-model chain exhausted after ~17 solves.
# These three were the ones still returning 200 after that exhaustion; the older
# gemini-3-flash-preview / gemini-flash-latest / gemini-2.5-flash entries are
# either daily-capped or now 404. Ordered best-maths-first.
# Lite models first: their higher daily quota outlasts gemini-3.5-flash, which
# caps after ~17 heavy calls. gemini-3.5-flash stays last as a quality option
# for whenever its quota frees.
MODEL_CHAIN = ["gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-3.5-flash"]
# Per-model cooldown after a 429, so an exhausted model is skipped rather than
# retried in a tight loop. Shared across calls within one process run.
_COOLDOWN: dict[str, float] = {}
COOLDOWN_SECS = 75
PACE_SECS = 4.0          # gap between successful calls -- stays under the per-minute token cap
MAX_STALL_SECS = 600     # give up on a question only after every model is cold this long

SEASON = {
    "January": "jan",
    "May/June": "may-jun",
    "Oct/Nov": "oct-nov",
    "October/November": "oct-nov",
}

SOURCE_RE = re.compile(
    r"(\d{4}) (January|May/June|Oct/Nov|October/November) Paper (\w+) Q(\d+)"
)

PROMPT = (
    "You are a senior Edexcel International GCSE Mathematics B (4MB1) examiner.\n"
    "The FIRST image(s) are a QUESTION PAPER extract containing ONE question. "
    "The image(s) AFTER the '--- MARK SCHEME ---' marker are the official mark "
    "scheme extract that has been attached to that question.\n\n"
    "Do all of the following, carefully:\n"
    "1. Read the question number as printed on the question paper.\n"
    "2. List every question number whose marking is visible in the mark-scheme "
    "image(s) (mark schemes for several questions can share one page).\n"
    "3. Decide whether the mark scheme actually contains the marking for THIS "
    "question (ms_matches_question).\n"
    "4. Check the mark scheme's mathematics. If it contains an arithmetic or "
    "method error, or the final answer is wrong, set ms_math_correct=false and "
    "describe it in ms_error; otherwise ms_math_correct=true and ms_error=null.\n"
    "5. Solve the question yourself, correctly, showing every stage. Present it "
    "as ordered steps. Use LaTeX for ALL mathematics, inline as $...$ (never "
    "unicode math symbols). Attach the mark-scheme mark code (e.g. 'M1', 'A1', "
    "'B1', 'M1 A1') to the step it is earned on, or null if none.\n"
    "6. Give the final answer in final_answer (LaTeX).\n"
    "7. Set answer_agrees_with_ms=true only if your final answer matches the "
    "mark scheme's stated answer.\n\n"
    "Return ONLY minified JSON with EXACTLY these keys: "
    '{"question_number":int,"ms_questions_visible":[int],'
    '"ms_matches_question":bool,"ms_math_correct":bool,"ms_error":string|null,'
    '"steps":[{"step":string,"marks":string|null}],"final_answer":string,'
    '"answer_agrees_with_ms":bool,"confidence":number}'
)


def load_env() -> str:
    load_dotenv(REPO_ROOT / ".env.local")
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY is not set in .env.local")
    return key


def parse_source(source: str) -> tuple[str, int] | None:
    m = SOURCE_RE.match(source)
    if not m:
        return None
    year, season, paper, qn = m.groups()
    return f"{year}_{SEASON[season]}_{paper}", int(qn)


def render_pages(pdf_path: Path, dpi: int = RENDER_DPI) -> list[str]:
    out: list[str] = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            out.append(base64.b64encode(pix.tobytes("png")).decode())
    return out


def ms_question_numbers(pdf_path: Path) -> list[int]:
    """Best-effort list of question numbers whose rows appear in an MS PDF.

    Used only to relink a misplaced MS; the vision model is the arbiter of
    correctness. Reads the leftmost 'Question' column integers.
    """
    found: list[int] = []
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                for block in page.get_text("dict").get("blocks", []):
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            if span["bbox"][0] < 95:
                                t = span["text"].strip()
                                if re.fullmatch(r"\d{1,2}", t):
                                    found.append(int(t))
    except Exception:
        pass
    return sorted(set(found))


def loads_latex_json(txt: str) -> dict:
    """json.loads a Gemini response that contains raw LaTeX.

    Gemini returns application/json, so every backslash lives INSIDE a string
    value. But it routinely emits single-backslash LaTeX (\\frac, \\times, \\sqrt)
    which json.loads either rejects (\\s, \\c -> JSONDecodeError) or silently
    mis-decodes (\\f -> formfeed, \\t -> tab), corrupting the maths. So escape
    every backslash that is not a genuine JSON escape and reparse.

    The tricky case is \\b \\f \\n \\r \\t: those are valid JSON escapes, but here
    they almost always begin a LaTeX command (\\frac, \\times, \\right, \\binom).
    We treat them as LaTeX -- and escape the backslash -- only when a lowercase
    letter follows (\\frac, \\neq); a real newline/tab is followed by '$', a
    digit, a capital or punctuation, so it is preserved."""
    out: list[str] = []
    i, n = 0, len(txt)
    hexd = "0123456789abcdefABCDEF"
    while i < n:
        ch = txt[i]
        if ch == "\\" and i + 1 < n:
            nxt = txt[i + 1]
            if nxt == "\\":                       # keep an escaped backslash pair
                out.append("\\\\"); i += 2; continue
            if nxt in '"/':                        # keep escaped quote / slash
                out.append("\\" + nxt); i += 2; continue
            if nxt == "u" and i + 6 <= n and all(c in hexd for c in txt[i + 2:i + 6]):
                out.append(txt[i:i + 6]); i += 6; continue
            if nxt in "bfnrt":                     # valid JSON escape OR LaTeX command
                after = txt[i + 2] if i + 2 < n else ""
                if not ("a" <= after <= "z"):      # real control char -> keep it
                    out.append("\\" + nxt); i += 2; continue
            out.append("\\\\"); i += 1; continue    # LaTeX / bad escape -> escape it
        out.append(ch); i += 1
    return json.loads("".join(out))


def call_gemini(key: str, parts: list[dict]) -> tuple[dict | None, str | None]:
    """Try the model chain, rotating past any model in 429 cooldown.

    A model that 429s (quota/rate) is parked in _COOLDOWN and skipped; when every
    model is cold we sleep until the soonest one frees, up to MAX_STALL_SECS,
    then give up (the question stays unsolved and is retried on the next run)."""
    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
        },
    }
    dead: set[str] = set()
    stalled = 0.0
    while True:
        now = time.time()
        available = [m for m in MODEL_CHAIN if m not in dead and _COOLDOWN.get(m, 0) <= now]
        if not available:
            live = [m for m in MODEL_CHAIN if m not in dead]
            if not live:
                return None, None
            wait = min(max(0.0, min(_COOLDOWN[m] for m in live) - now), COOLDOWN_SECS)
            stalled += wait
            if stalled > MAX_STALL_SECS:
                return None, None
            time.sleep(max(wait, 1))
            continue
        model = available[0]
        try:
            r = requests.post(
                GEMINI_URL.format(model=model),
                params={"key": key},
                json=body,
                timeout=180,
            )
        except requests.RequestException as exc:
            print(f"    network error ({model}): {exc}; cooling 10s")
            _COOLDOWN[model] = time.time() + 10
            continue
        if r.status_code == 200:
            time.sleep(PACE_SECS)
            try:
                txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                return loads_latex_json(txt), model
            except (KeyError, IndexError, json.JSONDecodeError) as exc:
                print(f"    parse error ({model}): {exc}")
                return None, model
        if r.status_code in (429, 503):
            _COOLDOWN[model] = time.time() + COOLDOWN_SECS
            print(f"    {r.status_code} on {model}; cooling {COOLDOWN_SECS}s")
            continue
        print(f"    HTTP {r.status_code} on {model}: {r.text[:120]}")
        dead.add(model)  # 404 / bad request: don't try this model again for this call


def build_parts(qp_imgs: list[str], ms_imgs: list[str]) -> list[dict]:
    parts: list[dict] = [{"text": PROMPT}, {"text": "--- QUESTION PAPER ---"}]
    for b in qp_imgs:
        parts.append({"inline_data": {"mime_type": "image/png", "data": b}})
    parts.append({"text": "--- MARK SCHEME ---"})
    for b in ms_imgs:
        parts.append({"inline_data": {"mime_type": "image/png", "data": b}})
    return parts


def relink_markscheme(paper_key: str, want_qn: int) -> str | None:
    """Find a sibling MS PDF in the same paper that contains want_qn."""
    ms_dir = MATHSB_ROOT / paper_key / "markschemes"
    if not ms_dir.exists():
        return None
    for pdf in sorted(ms_dir.glob("q*.pdf")):
        if want_qn in ms_question_numbers(pdf):
            return str(pdf.relative_to(REPO_ROOT)).replace("\\", "/")
    return None


def load_cache(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict, path: Path) -> None:
    path.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def write_report(cache: dict, index_by_slug: dict, report_path_: Path) -> None:
    flags = {"ms_misplaced": [], "ms_math_wrong": [], "answer_disagrees": [], "low_confidence": [], "failed": []}
    for slug, rec in cache.items():
        src = index_by_slug.get(slug, {}).get("source", "?")
        sol = rec.get("solution")
        if not sol:
            flags["failed"].append({"slug": slug, "source": src})
            continue
        tag = {"slug": slug, "source": src}
        if not sol.get("ms_matches_question", True):
            flags["ms_misplaced"].append({**tag, "relinked_to": rec.get("relinked_ms")})
        if not sol.get("ms_math_correct", True):
            flags["ms_math_wrong"].append({**tag, "error": sol.get("ms_error")})
        if not sol.get("answer_agrees_with_ms", True):
            flags["answer_disagrees"].append({**tag, "answer": sol.get("final_answer")})
        if (sol.get("confidence") or 0) < 0.6:
            flags["low_confidence"].append({**tag, "confidence": sol.get("confidence")})
    summary = {k: len(v) for k, v in flags.items()}
    summary["total_solved"] = sum(1 for r in cache.values() if r.get("solution"))
    report_path_.write_text(
        json.dumps({"summary": summary, "flags": flags}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("\n=== REPORT ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"  written -> {report_path_.relative_to(REPO_ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", type=int, choices=(1, 2), default=1, help="booklet part")
    ap.add_argument("--execute", action="store_true", help="run the solver")
    ap.add_argument("--limit", type=int, default=0, help="only process N (smoke test)")
    ap.add_argument("--report", action="store_true", help="rebuild report from cache only")
    ap.add_argument("--force", action="store_true", help="re-solve cached items")
    args = ap.parse_args()

    idx_path = index_path(args.part)
    cch_path = cache_path(args.part)
    rpt_path = report_path(args.part)

    index = json.loads(idx_path.read_text(encoding="utf-8"))
    questions = index["questions"]
    index_by_slug = {q["slug"]: q for q in questions}
    cache = load_cache(cch_path)

    if args.report and not args.execute:
        write_report(cache, index_by_slug, rpt_path)
        return

    key = load_env()
    todo = [q for q in questions if args.force or q["slug"] not in cache or not cache[q["slug"]].get("solution")]
    if args.limit:
        todo = todo[: args.limit]
    print(f"Part {args.part}: {len(questions)} questions, {len(cache)} cached, {len(todo)} to solve\n")

    for i, q in enumerate(todo, 1):
        slug = q["slug"]
        parsed = parse_source(q["source"])
        if not parsed:
            print(f"[{i}/{len(todo)}] {slug}: UNPARSEABLE source {q['source']!r}")
            continue
        paper_key, qn = parsed
        qp_pdf = MATHSB_ROOT / paper_key / "questions" / f"q{qn}.pdf"
        ms_pdf = MATHSB_ROOT / paper_key / "markschemes" / f"q{qn}.pdf"
        print(f"[{i}/{len(todo)}] {slug}  {q['source']}  (ch{q['chapter']} {q['section']}, {q['marks']}m)")
        if not qp_pdf.exists():
            print(f"    MISSING QP {qp_pdf}")
            continue

        qp_imgs = render_pages(qp_pdf)
        ms_imgs = render_pages(ms_pdf) if ms_pdf.exists() else []
        sol, model = call_gemini(key, build_parts(qp_imgs, ms_imgs))

        relinked = None
        if sol and not sol.get("ms_matches_question", True):
            alt = relink_markscheme(paper_key, qn)
            if alt and Path(REPO_ROOT / alt) != ms_pdf:
                print(f"    MS misplaced -> relinking to {alt} and re-solving")
                relinked = alt
                ms_imgs = render_pages(REPO_ROOT / alt)
                sol2, model2 = call_gemini(key, build_parts(qp_imgs, ms_imgs))
                if sol2 and sol2.get("ms_matches_question"):
                    sol, model = sol2, model2

        cache[slug] = {
            "slug": slug,
            "source": q["source"],
            "paper_key": paper_key,
            "question_number": qn,
            "chapter": q["chapter"],
            "chapter_title": q["chapter_title"],
            "section": q["section"],
            "section_title": q["section_title"],
            "printed_number": q["printed_number"],
            "marks": q["marks"],
            "qp_pdf": str(qp_pdf.relative_to(REPO_ROOT)).replace("\\", "/"),
            "ms_pdf": (relinked or str(ms_pdf.relative_to(REPO_ROOT)).replace("\\", "/")) if (ms_pdf.exists() or relinked) else None,
            "relinked_ms": relinked,
            "model": model,
            "solution": sol,
        }
        if sol:
            fa = (sol.get("final_answer") or "")[:60]
            print(f"    ok conf={sol.get('confidence')} ans={fa!r}")
        else:
            print("    FAILED to solve")
        if i % 10 == 0:
            save_cache(cache, cch_path)

    save_cache(cache, cch_path)
    write_report(cache, index_by_slug, rpt_path)


if __name__ == "__main__":
    main()
