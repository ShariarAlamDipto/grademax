"""
Build the Further Pure Mathematics (4PM1) Teacher's Notes PDF.

The notes are written chapter by chapter as HTML fragments (maths in $...$ for
KaTeX) in data/workbook/fpm/teachers_notes/chNN.html. This script wraps them with
a cover, a contents page, a "how Edexcel marks" primer and a ranking of every section
by its share of the marks. Every chapter gets an exam-weight table, the graded
exercises from chNN_practice.html (Levels 1-5, Beginner -> Expert; their answers are
moved to the back of the book) and, as Level 6, a practice map generated from the
2016-2022 complete index: every past-paper question in that chapter, with its source,
marks and number in the Worked Solutions (Complete) book.

Output: data/workbook/fpm/print/final/Further_Pure_Mathematics_Teachers_Notes.pdf

USAGE
  python scripts/build_fpm_teachers_notes.py             # build the PDF
  python scripts/build_fpm_teachers_notes.py --html-only # just emit HTML
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
from lib.teachers_notes_render import (  # noqa: E402
    CSS, KATEX, LADDER_CSS, build_pdf, ladder_table_html, split_ladder, stars, weight_table,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTES_DIR = REPO_ROOT / "data" / "workbook" / "fpm" / "teachers_notes"
OUT_DIR = REPO_ROOT / "data" / "workbook" / "fpm" / "print" / "final"
COMPLETE_INDEX_PATH = REPO_ROOT / "data" / "workbook" / "fpm_complete_index.json"
STEM = "Further_Pure_Mathematics_Teachers_Notes"

CHAPTER_TITLES = OrderedDict([
    (1, "Logarithmic functions and indices"),
    (2, "The quadratic function"),
    (3, "Identities and inequalities"),
    (4, "Graphs"),
    (5, "Series"),
    (6, "The binomial series"),
    (7, "Scalar and vector quantities"),
    (8, "Rectangular Cartesian coordinates"),
    (9, "Calculus"),
    (10, "Trigonometry"),
])

FRONT = r"""
<div class="front">
<h1 class="ct">How to use these notes</h1>
<p>These notes cover every topic in the Pearson Edexcel International GCSE Further Pure
Mathematics specification (4PM1) and, within each topic, every distinct <em>type</em> of
question that appeared on the 2016&ndash;2022 papers (431 questions, both papers, every
series including the specimen). Each type is taught from the basics upward and ends with
what the mark scheme actually rewards.</p>
<p>Every question type has the same five parts:</p>
<ul>
<li><b>What it looks like</b> &ndash; how Edexcel phrases it and how many marks it usually carries.</li>
<li><b>Method</b> &ndash; the steps to teach, in order.</li>
<li><b>Worked example</b> &ndash; taken from (or modelled closely on) a real paper, with the source.</li>
<li><b>Mark scheme</b> &ndash; where the M, A and B marks sit, so students write the lines that score.</li>
<li><b>Traps</b> &ndash; the errors that cost marks most often.</li>
</ul>
<p>Each chapter opens with a table of <b>how much it is worth</b>: the questions and marks each
section carried on the 2016&ndash;2022 papers, with a priority rating.</p>

<h2>Graded practice: beginner to expert</h2>
<p>Every chapter ends with student exercises in six levels. A student who can do Level 3 but is
stuck on Level 5 usually lacks a Level 4 skill: go back one level, not forward. Answers to
Levels 1&ndash;5 are at the back of the book, so the exercise pages can be copied without them.</p>
%%LADDER%%
<table><tr><td><b>6 &ndash; Past papers</b></td><td>Every real question on the chapter, with its
question number in the <em>Worked Solutions (Complete edition)</em>.</td></tr></table>

<h2>The exam</h2>
<table>
<tr><th>Paper</th><th>Length</th><th>Marks</th><th>Calculator</th><th>Notes</th></tr>
<tr><td>Paper 1</td><td>2 hours</td><td>100</td><td>Allowed</td><td rowspan="2">Both papers can test any topic. About 11 questions each, rising from 3&ndash;5 marks to 13&ndash;18 marks. A formula sheet is printed at the front.</td></tr>
<tr><td>Paper 2</td><td>2 hours</td><td>100</td><td>Allowed</td></tr>
</table>
<p>A calculator is allowed, but "show that", "exact value" and "use algebra" questions score
nothing for an answer typed straight out of a calculator. Teach students to write every
line that carries a mark.</p>

<h2>How Edexcel marks</h2>
<table>
<tr><th>Code</th><th>Meaning</th><th>What students must do</th></tr>
<tr><td><b>M1</b></td><td>Method mark</td><td>Show a correct method applied to the right thing, even if the arithmetic then slips. A method that is not written down cannot earn it.</td></tr>
<tr><td><b>dM1</b></td><td>Dependent method</td><td>Only available if the previous M mark was earned. One wrong method early can wipe out a whole chain.</td></tr>
<tr><td><b>A1</b></td><td>Accuracy mark</td><td>A correct answer or statement that follows from a correct method. Never awarded without the M mark it depends on.</td></tr>
<tr><td><b>B1</b></td><td>Independent mark</td><td>A correct fact, value or statement on its own (for example a correct sum of roots).</td></tr>
<tr><td><b>ft</b></td><td>Follow through</td><td>Credit for correct work using an earlier wrong value. Worth continuing after a mistake.</td></tr>
<tr><td><b>cso</b></td><td>Correct solution only</td><td>Every line must be correct. Used on "show that" answers.</td></tr>
<tr><td><b>cao</b></td><td>Correct answer only</td><td>No follow-through: the final value itself must be right.</td></tr>
<tr><td><b>oe / awrt</b></td><td>Or equivalent / answers which round to</td><td>Equivalent forms are fine; decimals must round to the printed value.</td></tr>
<tr><td><b>*</b></td><td>Given answer</td><td>The answer is printed in the question, so the working is what earns the marks. Never write the given result without the line that produces it.</td></tr>
</table>

<div class="box trap"><span class="lbl">Five habits that save the most marks</span>
<ol>
<li>Write the formula or rule before substituting into it. That line is usually the M1.</li>
<li>In "show that" questions, work from one side to the other and end with the exact printed result.</li>
<li>Give answers to the accuracy asked for (3 s.f., 1 d.p., exact). Keep full accuracy in the working.</li>
<li>Use radians whenever calculus or $\pi$ appears; set the calculator mode before starting.</li>
<li>Check the range of the answer (for $\theta$, for $x$ inside a region, for $n$ as a positive integer) and reject values that fall outside it, saying why.</li>
</ol></div>
</div>
"""


def load_index() -> dict:
    idx = json.loads(COMPLETE_INDEX_PATH.read_text(encoding="utf-8"))
    by_ch: dict[int, list] = {}
    for q in idx["questions"]:
        by_ch.setdefault(q["chapter"], []).append(q)
    return by_ch


def practice_map(ch: int, qs: list) -> str:
    rows = []
    cur = None
    for q in qs:
        if q["section"] != cur:
            cur = q["section"]
            rows.append(f'<tr><th colspan="4">{html.escape(cur)} &nbsp;{html.escape(q["section_title"])}</th></tr>')
        rows.append(
            f'<tr><td class="n">Q{q["printed_number"]}</td><td>{html.escape(q["source"])}</td>'
            f'<td class="n">{q["marks"]} marks</td></tr>')
    total = sum(q["marks"] for q in qs)
    return (f'<div class="practice"><h2>Level 6 &mdash; past-paper questions</h2>'
            f'<p class="src">{len(qs)} past-paper questions, {total} marks. "Q" numbers are the '
            f'question numbers in the Worked Solutions (Complete edition), Chapter {ch}.</p>'
            f'<table>{"".join(rows)}</table></div>')


def _sections(qs: list) -> list[tuple[str, str, int, int]]:
    agg: dict[str, list] = {}
    for q in qs:
        a = agg.setdefault(q["section"], [q["section_title"], 0, 0])
        a[1] += 1
        a[2] += q["marks"]
    return [(s, *agg[s]) for s in sorted(agg, key=lambda k: tuple(int(p) for p in k.split(".")))]


def chapter_weight(qs: list, grand: int) -> str:
    return weight_table(_sections(qs), grand, "2016&ndash;2022")


def priority_ranking(by_ch: dict, grand: int) -> str:
    rows = [r for qs in by_ch.values() for r in _sections(qs)]
    body = []
    for i, (sec, title, n, marks) in enumerate(sorted(rows, key=lambda r: -r[3]), 1):
        share = marks / grand
        body.append(f'<tr><td class="n">{i}</td><td class="n">{sec}</td><td>{html.escape(title)}</td>'
                    f'<td class="n">{n}</td><td class="n">{marks}</td>'
                    f'<td class="n">{100 * share:.1f}%</td><td class="stars">{stars(share)}</td></tr>')
    n_q = sum(len(qs) for qs in by_ch.values())
    return ('<h2>What matters most: every section ranked by marks</h2>'
            f'<p>All {n_q} questions on the 2016&ndash;2022 papers ({grand} marks), ranked by section. '
            'Three stars means at least 3% of all marks; one star means under 1.2%.</p>'
            '<table class="weight"><tr><th class="n">#</th><th class="n">Section</th><th>Topic</th>'
            '<th class="n">Questions</th><th class="n">Marks</th><th class="n">Share</th><th>Priority</th></tr>'
            f'{"".join(body)}</table>')


def build_html(by_ch: dict) -> str:
    toc, chapters, answer_parts = [], [], []
    grand = sum(q["marks"] for qs in by_ch.values() for q in qs)
    for ch, title in CHAPTER_TITLES.items():
        frag_path = NOTES_DIR / f"ch{ch:02d}.html"
        if not frag_path.exists():
            print(f"WARNING: missing {frag_path.name}; chapter {ch} skipped")
            continue
        frag = frag_path.read_text(encoding="utf-8")
        types = re.findall(r'<div class="type"><h3>(.*?)<', frag)
        toc.append(f'<tr><td><b>Chapter {ch}</b></td><td><b>{html.escape(title)}</b></td></tr>')
        for t in types:
            toc.append(f'<tr><td></td><td>{t}</td></tr>')
        qs = sorted(by_ch.get(ch, []), key=lambda q: (q["section"], q["printed_number"]))
        ladder, answers = split_ladder(NOTES_DIR / f"ch{ch:02d}_practice.html")
        chapters.append(f'<div class="chapter"><h1 class="ct">Chapter {ch} &mdash; {html.escape(title)}</h1>'
                        f'{chapter_weight(by_ch.get(ch, []), grand)}{frag}'
                        f'<div class="practice"><h2>Graded practice &mdash; Chapter {ch}</h2>{ladder}</div>'
                        f'{practice_map(ch, qs)}</div>')
        if answers:
            answer_parts.append(f'<h2>Chapter {ch} &mdash; {html.escape(title)}</h2>{answers}')
    cover = """
    <div class="cover">
      <h1>Teacher's Notes</h1>
      <h2>Edexcel International GCSE Further Pure Mathematics (4PM1)</h2>
      <h2>Every topic and every question type, 2016&ndash;2022</h2>
      <div class="brand">GRADEMAX</div>
      <div class="note">From the basics to exam standard, with worked examples from past papers,
      the mark-scheme points each type earns, the mistakes that cost marks, and graded
      student exercises from beginner to expert.</div>
    </div>"""
    toc.append('<tr><td><b>Answers</b></td><td><b>Answers to Levels 1&ndash;5</b></td></tr>')
    front = FRONT.replace("%%LADDER%%", ladder_table_html())
    front = front[:front.rstrip().rfind("</div>")] + priority_ranking(by_ch, grand) + "</div>"
    back = (f'<div class="chapter answers-back"><h1 class="ct">Answers to the graded practice</h1>'
            f'{"".join(answer_parts)}</div>')
    contents = f'<div class="front"><h1 class="ct">Contents</h1><table class="toc">{"".join(toc)}</table></div>'
    return (f'<!doctype html><html><head><meta charset="utf-8">{KATEX}<style>{CSS}{LADDER_CSS}</style></head>'
            f'<body>{cover}{contents}{front}{"".join(chapters)}{back}</body></html>')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html-only", action="store_true")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    html_path = OUT_DIR / f"{STEM}.html"
    html_path.write_text(build_html(load_index()), encoding="utf-8")
    print(f"HTML -> {html_path.relative_to(REPO_ROOT)}")
    if not args.html_only:
        build_pdf(html_path, OUT_DIR / f"{STEM}.pdf")


if __name__ == "__main__":
    main()
