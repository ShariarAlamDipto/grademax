"""
Shared rendering for the teacher's-notes PDFs (FPM 4PM1, IAL P4 WMA14, ...).

Each subject has its own builder script that supplies the chapter fragments and the
practice maps; this module owns only the look (CSS), KaTeX and the PDF print.
"""

from __future__ import annotations

from pathlib import Path

CSS = """
:root { --ink:#1a1a1a; --muted:#5f6368; --accent:#7a1f2b; --line:#e2e2e2;
        --key:#eef4fb; --keyb:#2c5d8f; --ex:#f7f7f2; --exb:#8a7a2c;
        --ms:#f1f8f1; --msb:#2e8b57; --trap:#fdf1f0; --trapb:#c0392b; --teach:#f4f0fa; --teachb:#6a4c93; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", Arial, sans-serif; color: var(--ink); margin: 0;
       font-size: 10.5pt; line-height: 1.55; }
.cover { height: 100vh; display: flex; flex-direction: column; justify-content: center;
         align-items: center; text-align: center; page-break-after: always; }
.cover h1 { font-size: 30pt; margin: 0 0 8pt; color: var(--accent); }
.cover h2 { font-size: 15pt; font-weight: 500; margin: 0 0 14pt; color: var(--muted); }
.cover .brand { font-size: 13pt; letter-spacing: 2px; margin-top: 40pt; }
.cover .note { font-size: 10pt; color: var(--muted); max-width: 62%; margin-top: 16pt; }
.front, .chapter { page-break-before: always; }
h1.ct { font-size: 20pt; color: var(--accent); border-bottom: 3px solid var(--accent);
        padding-bottom: 6pt; margin: 0 0 10pt; }
h2 { font-size: 14pt; color: var(--accent); margin: 18pt 0 6pt; }
h3 { font-size: 12pt; margin: 14pt 0 4pt; }
h4 { font-size: 10.5pt; margin: 10pt 0 2pt; }
p { margin: 5pt 0; }
ul, ol { margin: 4pt 0 6pt; padding-left: 20pt; }
li { margin: 2pt 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0; font-size: 9.5pt; }
th, td { border: 1px solid var(--line); padding: 3pt 6pt; text-align: left; vertical-align: top; }
th { background: #f5f5f5; }
.box { border-left: 4px solid; border-radius: 4px; padding: 7pt 10pt; margin: 8pt 0;
       page-break-inside: avoid; }
.box > .lbl { display: block; font-size: 8pt; font-weight: 700; letter-spacing: 1px;
              text-transform: uppercase; margin-bottom: 3pt; }
.key { background: var(--key); border-color: var(--keyb); } .key > .lbl { color: var(--keyb); }
.example { background: var(--ex); border-color: var(--exb); } .example > .lbl { color: var(--exb); }
.ms { background: var(--ms); border-color: var(--msb); } .ms > .lbl { color: var(--msb); }
.trap { background: var(--trap); border-color: var(--trapb); } .trap > .lbl { color: var(--trapb); }
.teach { background: var(--teach); border-color: var(--teachb); } .teach > .lbl { color: var(--teachb); }
.type { border-top: 1px solid var(--line); margin-top: 14pt; padding-top: 4pt; }
.type > h3 { color: var(--ink); }
.type > h3 .tag { font-size: 8pt; font-weight: 600; color: var(--muted); margin-left: 6pt; }
.src { font-size: 8.5pt; color: var(--muted); }
.mk { display: inline-block; background: #f6eef0; color: var(--accent); border: 1px solid #e6cdd2;
      border-radius: 3px; font-size: 7.5pt; font-weight: 700; padding: 0 4px; margin-left: 4px; }
.practice { page-break-before: always; }
.practice td.n { white-space: nowrap; width: 1%; }
.toc td { border: none; padding: 1pt 4pt; }
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

def build_pdf(html_path: Path, pdf_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome")
        except Exception:
            browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle", timeout=120000)
        page.wait_for_function("window.__katexDone === true", timeout=120000)
        errors = page.evaluate("document.querySelectorAll('.katex-error').length")
        if errors:
            print(f"WARNING: {errors} KaTeX errors in the rendered notes")
        page.pdf(path=str(pdf_path), format="A4", print_background=True,
                 margin={"top": "16mm", "bottom": "16mm", "left": "15mm", "right": "15mm"})
        browser.close()
    print(f"PDF -> {pdf_path}  ({pdf_path.stat().st_size // 1024} KB)")




# ---------------------------------------------------------------------------
# Shared building blocks for the graded-ladder editions (Maths B, FPM).
# ---------------------------------------------------------------------------

import html as _html
import re as _re

LADDER_CSS = """
.weight td.n, .weight th.n { text-align: right; white-space: nowrap; width: 1%; }
.stars { color: var(--accent); letter-spacing: 1px; white-space: nowrap; }
.lvl { border-top: 2px solid var(--line); margin-top: 12pt; }
.lvl > h3 .tag { font-size: 8pt; font-weight: 600; color: var(--muted); margin-left: 6pt; }
.answers-back ol { font-size: 9.5pt; }
"""

LADDER_LEVELS = [
    ("1", "Beginner", "The prerequisite skill on its own, with small friendly numbers.",
     "Starter, or before the topic is taught."),
    ("2", "Developing", "One-step drills of the single technique just taught.",
     "In the lesson, straight after the method."),
    ("3", "Secure", "Short textbook questions using the full method once.",
     "Homework after the first lesson."),
    ("4", "Exam style", "Written in Edexcel's style (not from a paper): two steps combined, "
     "a \"show that\", a context or an unknown constant.", "Once Level 3 is secure."),
    ("5", "Expert", "Harder than a typical exam question: several topics combined, an "
     "unfamiliar setting, or a proof. For students aiming at the top grade.",
     "Stretch work, after the past papers are going well."),
]

ANSWERS_RE = _re.compile(r'<div class="answers">(.*?)</div><!--/answers-->', _re.S)


def ladder_table_html() -> str:
    rows = "".join(f"<tr><td><b>{n} &ndash; {name}</b></td><td>{what}</td><td>{when}</td></tr>"
                   for n, name, what, when in LADDER_LEVELS)
    return ("<table><tr><th>Level</th><th>What it is</th><th>When to set it</th></tr>"
            f"{rows}</table>")


def split_ladder(path: Path) -> tuple[str, str]:
    """Return (exercises, answers) from a chNN_practice.html file; answers go to the back."""
    if not path.exists():
        print(f"WARNING: missing {path.name}; no graded practice for this chapter")
        return "", ""
    text = path.read_text(encoding="utf-8")
    m = ANSWERS_RE.search(text)
    return ANSWERS_RE.sub("", text), (m.group(1) if m else "")


def stars(share: float) -> str:
    """Priority from a section's share of all exam marks."""
    n = 3 if share >= 0.03 else 2 if share >= 0.012 else 1
    return "&#9733;" * n + "&#9734;" * (3 - n)


def weight_table(rows: list[tuple[str, str, int, int]], grand_marks: int, years: str) -> str:
    """rows: (section, title, questions, marks), in section order."""
    body = []
    for sec, title, n, marks in rows:
        share = marks / grand_marks if grand_marks else 0
        body.append(f'<tr><td class="n">{sec}</td><td>{_html.escape(title)}</td>'
                    f'<td class="n">{n}</td><td class="n">{marks}</td>'
                    f'<td class="n">{100 * share:.1f}%</td><td class="stars">{stars(share)}</td></tr>')
    return (f'<div class="box key weight"><span class="lbl">How much this chapter is worth ({years})</span>'
            '<table><tr><th class="n">Section</th><th>Topic</th><th class="n">Questions</th>'
            '<th class="n">Marks</th><th class="n">Share of all marks</th><th>Priority</th></tr>'
            f'{"".join(body)}</table></div>')
