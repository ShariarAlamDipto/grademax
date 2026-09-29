"""
Build the Pearson Edexcel IAL Pure Mathematics 4 (WMA14) Teacher's Notes PDF.

The notes are written chapter by chapter as HTML fragments (maths in $...$ for
KaTeX) in data/workbook/p4/teachers_notes/chNN.html, following the seven content
headings of the WMA14 specification. This script adds a cover, contents, a
"how Edexcel marks" primer and, after every chapter, a practice map built from the
chapterwise workbook: every WMA14 question from the 2018 specimen to January 2025,
with its paper, question number and marks, grouped by section.

Sections come from data/workbook/p4_classifications.json (the classifier's primary
section, the same one the chapterwise workbook uses).

Output: data/workbook/p4/print/final/Pure_Mathematics_4_Teachers_Notes.pdf

USAGE
  python scripts/build_p4_teachers_notes.py             # build the PDF
  python scripts/build_p4_teachers_notes.py --html-only # just emit HTML
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.teachers_notes_render import CSS, KATEX, build_pdf  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTES_DIR = REPO_ROOT / "data" / "workbook" / "p4" / "teachers_notes"
OUT_DIR = REPO_ROOT / "data" / "workbook" / "p4" / "print" / "final"
QUESTIONS_PATH = REPO_ROOT / "data" / "workbook" / "p4_questions.json"
CLASSIFICATIONS_PATH = REPO_ROOT / "data" / "workbook" / "p4_classifications.json"
STEM = "Pure_Mathematics_4_Teachers_Notes"

# WMA14 specification (Issue 3), P4.3 content headings, as in migration 19.
CHAPTER_TITLES = OrderedDict([
    (1, "Proof"),
    (2, "Algebra and functions"),
    (3, "Coordinate geometry in the (x, y) plane"),
    (4, "Binomial expansion"),
    (5, "Differentiation"),
    (6, "Integration"),
    (7, "Vectors"),
])
SECTION_TITLES = {
    "1.1": "Proof by contradiction",
    "2.1": "Partial fractions",
    "3.1": "Parametric equations and conversion to cartesian form",
    "4.1": "Binomial series for any rational n and its range of validity",
    "5.1": "Implicit differentiation, tangents and normals",
    "5.2": "Parametric differentiation, tangents and normals",
    "5.3": "Connected rates of change and forming differential equations",
    "6.1": "Integration by substitution and by parts",
    "6.2": "Integration using partial fractions",
    "6.3": "First order differential equations with separable variables",
    "6.4": "Volumes of revolution",
    "6.5": "Area under a curve given parametrically",
    "7.1": "Vector algebra, magnitude, unit vectors and position vectors",
    "7.2": "Vector equations of lines: parallel, intersecting and skew",
    "7.3": "The scalar product and the angle between two lines",
}
SEASONS = {"jan": "January", "may-jun": "May/June", "oct-nov": "October/November",
           "specimen": "Specimen"}

FRONT = r"""
<div class="front">
<h1 class="ct">How to use these notes</h1>
<p>These notes cover every statement in the Pure Mathematics 4 (WMA14) specification and,
within each topic, every distinct <em>type</em> of question that has appeared from the
2018 specimen to January 2025. That is 130 questions across the first 14 unique WMA14 papers.
(Papers filed as "P4" before October 2020 are the old C34/C4 units and are not used.)
Each type goes from the prerequisite skill up to exam standard.</p>
<p>Every question type has the same parts: <b>what it looks like</b>, the <b>method</b> to
teach, a <b>worked example</b> modelled on a real paper, where the <b>mark scheme</b> puts its
M, A and B marks, and the <b>traps</b> that cost marks. Each chapter ends with a <b>practice map</b>
of every past-paper question on it.</p>

<h2>The exam</h2>
<table>
<tr><th>Unit</th><th>Length</th><th>Marks</th><th>Calculator</th><th>Notes</th></tr>
<tr><td>WMA14 Pure Mathematics 4</td><td>1 hour 30 minutes</td><td>75</td><td>Allowed</td>
<td>8&ndash;11 questions, 3&ndash;15 marks each (median 8). Assumes all of P1, P2 and P3.
The formula booklet gives the binomial series, the standard derivatives and integrals, and
the volume formulae; it does not give the scalar product in component form.</td></tr>
</table>
<p>Many questions say <em>"Solutions relying entirely on calculator technology are not
acceptable"</em> or "use algebraic integration". A correct number from the calculator's
integration function then scores nothing. Every substitution, limit change and
antiderivative must be written.</p>

<h2>How Edexcel marks</h2>
<table>
<tr><th>Code</th><th>Meaning</th><th>What students must do</th></tr>
<tr><td><b>M1</b></td><td>Method</td><td>A correct method applied to the right thing, written down. Slips after it still keep the M.</td></tr>
<tr><td><b>dM1</b></td><td>Dependent method</td><td>Only if the previous M was earned.</td></tr>
<tr><td><b>A1</b></td><td>Accuracy</td><td>Correct answer or statement following a correct method.</td></tr>
<tr><td><b>B1</b></td><td>Independent</td><td>A correct fact or value on its own.</td></tr>
<tr><td><b>ft / cso / cao / oe / awrt</b></td><td>&nbsp;</td><td>Follow through, correct solution only, correct answer only, or equivalent, answers which round to.</td></tr>
<tr><td><b>*</b></td><td>Given answer</td><td>The result is printed, so every line leading to it must be shown and correct.</td></tr>
</table>
<div class="box trap"><span class="lbl">Habits that save the most marks in P4</span>
<ol>
<li>Write the rule before using it: the chain rule for rates, $\frac{\mathrm{d}y}{\mathrm{d}x} = \frac{\mathrm{d}y/\mathrm{d}t}{\mathrm{d}x/\mathrm{d}t}$, the parts formula.</li>
<li>In substitutions, change <b>every</b> part: the integrand, the $\mathrm{d}x$ and the limits.</li>
<li>Differential equations: separate, integrate <b>both</b> sides, put the $+c$ in immediately, find it before rearranging.</li>
<li>Proof by contradiction: state the assumption, reach a contradiction, and <b>conclude in words</b>.</li>
<li>Vectors: keep column vectors in columns, and write the equations you are solving component by component.</li>
</ol></div>
</div>
"""


def paper_label(key: str) -> str:
    year, _, rest = key.partition("_")
    return f"{year} {SEASONS.get(rest, rest)}"


def load_questions() -> dict[int, list]:
    qs = {q["slug"]: q for q in json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))}
    cls = {c["slug"]: c for c in json.loads(CLASSIFICATIONS_PATH.read_text(encoding="utf-8"))}
    by_ch: dict[int, list] = {}
    for slug, q in qs.items():
        sec = cls[slug]["section"]
        by_ch.setdefault(int(sec.split(".")[0]), []).append({
            "section": sec,
            "source": f'{paper_label(q["source_paper_key"])} Q{q["source_question_number"]}',
            "sort": (sec, q["year"], q["source_paper_key"], q["source_question_number"]),
            "marks": q["marks"],
            "also": cls[slug].get("secondary_sections") or [],
        })
    return by_ch


def practice_map(ch: int, qs: list) -> str:
    rows = []
    cur = None
    for q in sorted(qs, key=lambda r: r["sort"]):
        if q["section"] != cur:
            cur = q["section"]
            rows.append(f'<tr><th colspan="3">{cur} &nbsp;{html.escape(SECTION_TITLES[cur])}</th></tr>')
        also = f' <span class="src">(also {", ".join(q["also"])})</span>' if q["also"] else ""
        rows.append(f'<tr><td>{html.escape(q["source"])}{also}</td><td class="n">{q["marks"]} marks</td></tr>')
    total = sum(q["marks"] for q in qs)
    return (f'<div class="practice"><h2>Chapter {ch} practice map</h2>'
            f'<p class="src">{len(qs)} past-paper questions, {total} marks, grouped by the section of '
            f'their main topic ("also" lists other sections the question uses).</p>'
            f'<table>{"".join(rows)}</table></div>')


def build_html(by_ch: dict) -> str:
    toc, chapters = [], []
    for ch, title in CHAPTER_TITLES.items():
        frag_path = NOTES_DIR / f"ch{ch:02d}.html"
        if not frag_path.exists():
            print(f"WARNING: missing {frag_path.name}; chapter {ch} skipped")
            continue
        frag = frag_path.read_text(encoding="utf-8")
        toc.append(f'<tr><td><b>Chapter {ch}</b></td><td><b>{html.escape(title)}</b></td></tr>')
        for t in re.findall(r'<div class="type"><h3>(.*?)<', frag):
            toc.append(f'<tr><td></td><td>{t}</td></tr>')
        chapters.append(f'<div class="chapter"><h1 class="ct">Chapter {ch} &mdash; {html.escape(title)}</h1>'
                        f'{frag}{practice_map(ch, by_ch.get(ch, []))}</div>')
    cover = """
    <div class="cover">
      <h1>Teacher's Notes</h1>
      <h2>Pearson Edexcel International A Level Mathematics</h2>
      <h2>Pure Mathematics 4 (WMA14)</h2>
      <h2>Every topic and every question type, 2018 specimen &ndash; January 2025</h2>
      <div class="brand">GRADEMAX</div>
      <div class="note">From the prerequisites to exam standard, with worked examples modelled on
      past papers, the mark-scheme points each type earns, and the mistakes that cost marks.</div>
    </div>"""
    contents = f'<div class="front"><h1 class="ct">Contents</h1><table class="toc">{"".join(toc)}</table></div>'
    return (f'<!doctype html><html><head><meta charset="utf-8">{KATEX}<style>{CSS}</style></head>'
            f'<body>{cover}{contents}{FRONT}{"".join(chapters)}</body></html>')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html-only", action="store_true")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    html_path = OUT_DIR / f"{STEM}.html"
    html_path.write_text(build_html(load_questions()), encoding="utf-8")
    print(f"HTML -> {html_path.relative_to(REPO_ROOT)}")
    if not args.html_only:
        build_pdf(html_path, OUT_DIR / f"{STEM}.pdf")


if __name__ == "__main__":
    main()
