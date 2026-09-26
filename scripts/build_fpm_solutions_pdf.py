"""
Assemble the Further Pure Mathematics (4PM1) chapterwise workbook worked
solutions into a printable companion PDF, matching the layout of the printed
FPM workbook (chapters 1-10, ordered by section and printed question number).

Input:  data/workbook/fpm_worked_solutions.json  (from solve_fpm_workbook.py)
Output: data/workbook/fpm/print/final/Further_Pure_Mathematics_Worked_Solutions.pdf

Maths is rendered with KaTeX (loaded from CDN) inside headless Chrome via
Playwright, then printed to PDF -- so the LaTeX in every step renders as proper
notation rather than raw source.

USAGE
  python scripts/build_fpm_solutions_pdf.py            # build the PDF
  python scripts/build_fpm_solutions_pdf.py --html-only  # just emit HTML
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "data" / "workbook" / "fpm" / "print" / "final"
CACHE_PATH = REPO_ROOT / "data" / "workbook" / "fpm_worked_solutions.json"
INDEX_PATH = REPO_ROOT / "data" / "workbook" / "fpm" / "print" / "print_index_paged.json"

CSS = """
:root { --ink:#1a1a1a; --muted:#666; --accent:#7a1f2b; --line:#e2e2e2; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", Arial, sans-serif; color: var(--ink); margin: 0;
       font-size: 11pt; line-height: 1.5; }
.cover { height: 100vh; display: flex; flex-direction: column; justify-content: center;
         align-items: center; text-align: center; page-break-after: always; }
.cover h1 { font-size: 30pt; margin: 0 0 8pt; color: var(--accent); }
.cover h2 { font-size: 16pt; font-weight: 500; margin: 0 0 24pt; color: var(--muted); }
.cover .brand { font-size: 13pt; letter-spacing: 2px; color: var(--ink); margin-top: 40pt; }
.cover .note { font-size: 10pt; color: var(--muted); max-width: 60%; margin-top: 16pt; }
.chapter { page-break-before: always; }
.chapter-title { font-size: 20pt; color: var(--accent); border-bottom: 3px solid var(--accent);
                 padding-bottom: 6pt; margin: 0 0 4pt; }
.section-title { font-size: 13pt; color: var(--ink); margin: 20pt 0 6pt; font-weight: 600; }
.q { border: 1px solid var(--line); border-radius: 6px; padding: 12pt 14pt; margin: 10pt 0;
     page-break-inside: avoid; }
.q-head { display: flex; justify-content: space-between; align-items: baseline;
          border-bottom: 1px solid var(--line); padding-bottom: 6pt; margin-bottom: 8pt; }
.q-num { font-weight: 700; font-size: 12.5pt; color: var(--accent); }
.q-src { font-size: 8.5pt; color: var(--muted); }
.q-marks { font-size: 9pt; color: var(--muted); font-weight: 600; }
ol.steps { margin: 4pt 0 0; padding-left: 20pt; }
ol.steps li { margin: 5pt 0; }
.badge { display: inline-block; background: #f6eef0; color: var(--accent); border: 1px solid #e6cdd2;
         border-radius: 4px; font-size: 8pt; font-weight: 700; padding: 0 5px; margin-right: 6px;
         vertical-align: middle; }
.final { margin-top: 10pt; padding: 8pt 10pt; background: #f6faf6; border-left: 4px solid #2e8b57;
         border-radius: 4px; }
.final .lbl { font-size: 8.5pt; font-weight: 700; color: #2e8b57; text-transform: uppercase;
              letter-spacing: 1px; }
.flag { margin-top: 8pt; padding: 6pt 8pt; background: #fdf3f3; border-left: 4px solid #c0392b;
        border-radius: 4px; font-size: 8.5pt; color: #7a2620; }
"""

KATEX = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<script>
document.addEventListener("DOMContentLoaded", function () {
  renderMathInElement(document.body, {
    delimiters: [
      {left: "$$", right: "$$", display: true},
      {left: "$",  right: "$",  display: false}
    ],
    throwOnError: false
  });
  window.__katexDone = true;
});
</script>
"""


def esc_with_math(text: str) -> str:
    """Escape HTML but leave $...$ math spans for KaTeX."""
    return html.escape(text or "", quote=False)


def wrap_math(answer: str) -> str:
    a = (answer or "").strip()
    if not a:
        return ""
    # Wrap in $...$ ONLY when there is no real (unescaped) $ delimiter. An escaped
    # \$ is literal currency, not a delimiter; a string that already carries its
    # own $...$ spans is passed through so inner LaTeX is not stranded as text.
    if "$" in a.replace("\\$", ""):
        return esc_with_math(a)
    return "$" + esc_with_math(a) + "$"


def render_question(rec: dict) -> str:
    sol = rec.get("solution") or {}
    steps = sol.get("steps") or []
    parts = ['<div class="q">']
    parts.append('<div class="q-head">')
    parts.append(f'<span class="q-num">Question {rec["printed_number"]}</span>')
    parts.append(f'<span class="q-src">{html.escape(rec["source"])}</span>')
    parts.append(f'<span class="q-marks">{rec["marks"]} mark{"s" if rec["marks"] != 1 else ""}</span>')
    parts.append("</div>")

    if steps:
        parts.append('<ol class="steps">')
        for st in steps:
            badge = f'<span class="badge">{html.escape(st["marks"])}</span>' if st.get("marks") else ""
            parts.append(f'<li>{badge}{esc_with_math(st.get("step", ""))}</li>')
        parts.append("</ol>")
    else:
        parts.append('<p><em>Solution unavailable.</em></p>')

    fa = wrap_math(sol.get("final_answer", ""))
    if fa:
        parts.append(f'<div class="final"><span class="lbl">Answer</span>&nbsp; {fa}</div>')

    flags = []
    if sol and not sol.get("ms_matches_question", True):
        flags.append("Mark scheme placement was corrected for this question.")
    if sol and not sol.get("ms_math_correct", True) and sol.get("ms_error"):
        flags.append("Note on the official mark scheme: " + sol["ms_error"])
    for f in flags:
        parts.append(f'<div class="flag">{esc_with_math(f)}</div>')

    parts.append("</div>")
    return "\n".join(parts)


def build_html(cache: dict, index: dict) -> str:
    order = {q["slug"]: i for i, q in enumerate(index["questions"])}
    recs = [r for r in cache.values() if r.get("slug") in order]
    recs.sort(key=lambda r: order[r["slug"]])

    body = []
    cur_ch = cur_sec = None
    for r in recs:
        if r["chapter"] != cur_ch:
            cur_ch = r["chapter"]
            cur_sec = None
            body.append('<div class="chapter">')
            body.append(f'<h1 class="chapter-title">Chapter {cur_ch} &mdash; {html.escape(r["chapter_title"])}</h1>')
        if r["section"] != cur_sec:
            cur_sec = r["section"]
            body.append(f'<h2 class="section-title">{html.escape(str(cur_sec))} &nbsp;{html.escape(r["section_title"])}</h2>')
        body.append(render_question(r))
    body.append("</div>")

    solved = sum(1 for r in recs if r.get("solution"))
    cover = f"""
    <div class="cover">
      <h1>Worked Solutions</h1>
      <h2>Edexcel International GCSE Further Pure Mathematics (4PM1)</h2>
      <h2>Chapterwise Workbook &mdash; Chapters 1&ndash;10</h2>
      <div class="brand">GRADEMAX</div>
      <div class="note">Full step-by-step solutions with examiner mark allocations
      (M1 / A1 / B1). Every solution has been checked against the official Edexcel
      mark scheme. {solved} questions.</div>
    </div>
    """

    return f"""<!doctype html>
<html><head><meta charset="utf-8">{KATEX}<style>{CSS}</style></head>
<body>{cover}{''.join(body)}</body></html>"""


def build_pdf(html_path: Path, pdf_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    url = html_path.resolve().as_uri()
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome")
        except Exception:
            browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=120000)
        page.wait_for_function("window.__katexDone === true", timeout=120000)
        page.pdf(
            path=str(pdf_path),
            format="A4",
            margin={"top": "16mm", "bottom": "16mm", "left": "14mm", "right": "14mm"},
            print_background=True,
        )
        browser.close()
    print(f"PDF -> {pdf_path.relative_to(REPO_ROOT)}  ({pdf_path.stat().st_size//1024} KB)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html-only", action="store_true")
    args = ap.parse_args()

    html_path = OUT_DIR / "Further_Pure_Mathematics_Worked_Solutions.html"
    pdf_path = OUT_DIR / "Further_Pure_Mathematics_Worked_Solutions.pdf"

    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    html_path.write_text(build_html(cache, index), encoding="utf-8")
    print(f"HTML -> {html_path.relative_to(REPO_ROOT)}  ({len(cache)} records)")
    if not args.html_only:
        build_pdf(html_path, pdf_path)


if __name__ == "__main__":
    main()
