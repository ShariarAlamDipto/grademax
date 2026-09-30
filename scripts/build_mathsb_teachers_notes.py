"""
Build the Pearson Edexcel International GCSE Mathematics B (4MB1) Teacher's Notes PDF.

The notes are written chapter by chapter as HTML fragments (maths in $...$ for
KaTeX) in data/workbook/mathsb/teachers_notes/:
  chNN.html           foundations, teaching sequence, one block per question type
  chNN_practice.html  graded exercises, Levels 1-5 (Beginner -> Expert), with answers
                      in a <div class="answers">...</div><!--/answers--> block that this
                      script moves to the back of the book

This script adds a cover, contents, a front section (the exam, how Edexcel marks, and
a ranking of every section by its share of the marks), and for every chapter:
  - an exam-weight table from data/workbook/mathsb_classifications.json
    (all 1046 questions, 2016-2022, both papers, classifier's primary section);
  - Level 6, a past-paper map from the printed chapterwise workbook
    (data/workbook/mathsb/print/print_index.json, 742 questions) with each question's
    workbook number and page, easiest (fewest marks) first within each section.

Output: data/workbook/mathsb/print/final/Mathematics_B_Teachers_Notes.pdf

USAGE
  python scripts/build_mathsb_teachers_notes.py             # build the PDF
  python scripts/build_mathsb_teachers_notes.py --html-only # just emit HTML
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.teachers_notes_render import (  # noqa: E402
    CSS, KATEX, LADDER_CSS, build_pdf, ladder_table_html, split_ladder, stars, weight_table,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTES_DIR = REPO_ROOT / "data" / "workbook" / "mathsb" / "teachers_notes"
OUT_DIR = REPO_ROOT / "data" / "workbook" / "mathsb" / "print" / "final"
CLASSIFICATIONS_PATH = REPO_ROOT / "data" / "workbook" / "mathsb_classifications.json"
PRINT_INDEX_PATH = REPO_ROOT / "data" / "workbook" / "mathsb" / "print" / "print_index.json"
STEM = "Mathematics_B_Teachers_Notes"
YEARS = "2016&ndash;2022"

# Migrations 15 and 16 (4MB1 chapterwise taxonomy).
CHAPTER_TITLES = OrderedDict([
    (1, "Number"),
    (2, "Sets"),
    (3, "Algebra"),
    (4, "Functions"),
    (5, "Matrices"),
    (6, "Geometry"),
    (7, "Mensuration"),
    (8, "Vectors and transformation geometry"),
    (9, "Trigonometry"),
    (10, "Statistics and probability"),
    (11, "Calculus"),
])
SECTION_TITLES = {
    "1.1": "Fractions, decimals and percentages",
    "1.2": "Ratio, proportion and rates of change",
    "1.3": "Indices, surds and standard form",
    "1.4": "Accuracy, bounds and estimation",
    "2.1": "Set notation and Venn diagrams",
    "2.2": "Two-set problems",
    "2.3": "Three-set problems",
    "3.1": "Expanding, factorising and simplifying",
    "3.2": "Linear equations and inequalities",
    "3.3": "Simultaneous equations",
    "3.4": "Quadratic equations",
    "3.5": "Algebraic fractions",
    "3.6": "Rearranging formulae and changing the subject",
    "3.7": "Sequences and the nth term",
    "3.8": "Factor and remainder theorem",
    "4.1": "Function notation, domain and range",
    "4.2": "Composite functions",
    "4.3": "Inverse functions",
    "4.4": "Graphs of functions and graphical solutions",
    "5.1": "Matrix arithmetic",
    "5.2": "Determinants and inverse matrices",
    "5.3": "Solving simultaneous equations with matrices",
    "5.4": "Matrix transformations",
    "6.1": "Angles, parallel lines and polygons",
    "6.2": "Triangles, congruence and similarity",
    "6.3": "Circle theorems",
    "6.4": "Pythagoras' theorem",
    "6.5": "Constructions and loci",
    "6.6": "Coordinate geometry: gradient, length and midpoint",
    "6.7": "Equations of straight lines, parallel and perpendicular",
    "7.1": "Perimeter and area of plane shapes",
    "7.2": "Circles, arcs and sectors",
    "7.3": "Volume and surface area of solids",
    "7.4": "Similar shapes: length, area and volume",
    "8.1": "Vector arithmetic and magnitude",
    "8.2": "Position vectors and geometric proof",
    "8.3": "Single transformations",
    "8.4": "Combined and inverse transformations",
    "9.1": "Right-angled triangle trigonometry",
    "9.2": "The sine rule",
    "9.3": "The cosine rule and the area of a triangle",
    "9.4": "Bearings and three-dimensional problems",
    "9.5": "Trigonometric graphs and equations",
    "10.1": "Presenting and interpreting data",
    "10.2": "Averages and measures of spread",
    "10.3": "Cumulative frequency and box plots",
    "10.4": "Histograms and frequency density",
    "10.5": "Probability of single and combined events",
    "10.6": "Tree diagrams and conditional probability",
    "11.1": "Differentiating polynomials",
    "11.2": "Gradients, tangents and normals",
    "11.3": "Turning points and their nature",
    "11.4": "Kinematics: displacement, velocity and acceleration",
}


def sec_key(sec: str) -> tuple[int, int]:
    a, b = sec.split(".")
    return int(a), int(b)


def load_weights() -> tuple[dict[str, list[int]], int]:
    """Questions and marks per section across every 2016-2022 paper."""
    cls = json.loads(CLASSIFICATIONS_PATH.read_text(encoding="utf-8"))
    w: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for q in cls:
        sec = q["classification"]["primary"]
        w[sec][0] += 1
        w[sec][1] += q["marks"]
    return dict(w), sum(q["marks"] for q in cls)


def load_print_index() -> dict[int, list]:
    idx = json.loads(PRINT_INDEX_PATH.read_text(encoding="utf-8"))
    by_ch: dict[int, list] = {}
    for q in idx["questions"]:
        by_ch.setdefault(q["chapter"], []).append(q)
    return by_ch


def chapter_weight(ch: int, weights: dict, grand: int) -> str:
    secs = sorted((s for s in SECTION_TITLES if sec_key(s)[0] == ch), key=sec_key)
    rows = [(s, SECTION_TITLES[s], *weights.get(s, [0, 0])) for s in secs]
    rows = [r for r in rows if r[2]]
    return weight_table(rows, grand, YEARS)


def priority_ranking(weights: dict, grand: int) -> str:
    ranked = sorted(weights.items(), key=lambda kv: -kv[1][1])
    rows = []
    for i, (sec, (n, marks)) in enumerate(ranked, 1):
        share = marks / grand
        rows.append(f'<tr><td class="n">{i}</td><td class="n">{sec}</td>'
                    f'<td>{html.escape(SECTION_TITLES.get(sec, sec))}</td>'
                    f'<td class="n">{n}</td><td class="n">{marks}</td>'
                    f'<td class="n">{100 * share:.1f}%</td><td class="stars">{stars(share)}</td></tr>')
    return ('<h2>What matters most: every section ranked by marks</h2>'
            f'<p>Every question on all 53 Maths B papers from {YEARS} (1046 questions, 5300 marks) was '
            'classified into the workbook sections. This table ranks the sections by the marks they '
            'carried. Three stars means at least 3% of all marks (about 6 marks a series); one star '
            'means under 1.2%. Teach every section, but spend the time where the marks are.</p>'
            '<table class="weight"><tr><th class="n">#</th><th class="n">Section</th><th>Topic</th>'
            '<th class="n">Questions</th><th class="n">Marks</th><th class="n">Share</th><th>Priority</th></tr>'
            f'{"".join(rows)}</table>')


def practice_map(ch: int, qs: list) -> str:
    """Level 6: every workbook question in the chapter, fewest marks first within each section."""
    rows, cur = [], None
    for q in sorted(qs, key=lambda r: (sec_key(r["section"]), r["marks"], r["printed_number"])):
        if q["section"] != cur:
            cur = q["section"]
            rows.append(f'<tr><th colspan="4">{cur} &nbsp;{html.escape(q["section_title"])}</th></tr>')
        rows.append(f'<tr><td class="n">Q{q["printed_number"]}</td><td class="n">p.&nbsp;{q["workbook_page"]}</td>'
                    f'<td>{html.escape(q["source"])}</td><td class="n">{q["marks"]} marks</td></tr>')
    total = sum(q["marks"] for q in qs)
    return (f'<div class="practice"><h2>Level 6 &mdash; past-paper questions in the workbook</h2>'
            f'<p class="src">{len(qs)} questions, {total} marks. "Q" and "p." are the question number and '
            f'page in the GradeMax Mathematics B chapterwise workbook, Chapter {ch}. Within each section '
            f'they are ordered by marks, so the shortest come first. Set them after Levels 1&ndash;4.</p>'
            f'<table>{"".join(rows)}</table></div>')


FRONT_TOP = r"""
<div class="front">
<h1 class="ct">How to use these notes</h1>
<p>These notes cover every section of the Pearson Edexcel International GCSE Mathematics B
specification (4MB1) as the GradeMax chapterwise workbook arranges it: 11 chapters and 53
sections. Within each section they teach every distinct <em>type</em> of question that appeared
on the 2016&ndash;2022 papers, from the prerequisite skill up to exam standard.</p>
<p>Every chapter has the same parts:</p>
<ul>
<li><b>How much it is worth</b> &ndash; the questions and marks each section carried, with a
priority rating, so you know where to spend lesson time.</li>
<li><b>Foundations</b> and a <b>teaching sequence</b>.</li>
<li>One block per <b>question type</b>: what it looks like, the method, a worked example
modelled on a real paper, where the mark scheme puts its marks, and the traps.</li>
<li><b>Graded practice</b> in six levels, from beginner to expert, ending with the real
past-paper questions in the workbook.</li>
</ul>

<h2>Graded practice: climb the ladder, do not jump</h2>
<p>A student who can do Level 3 but is stuck on Level 5 usually lacks a Level 4 skill: go back
one level, not forward. Answers to Levels 1&ndash;5 are at the back, so the exercise pages can be
copied for students without them.</p>
"""

FRONT_BOTTOM = r"""
<table><tr><td><b>6 &ndash; Past papers</b></td><td>Every real question on the chapter in the
chapterwise workbook, with its question number and page, shortest first in each section.
Worked solutions for all of them are in the GradeMax Worked Solutions books.</td></tr></table>

<h2>The exam</h2>
<table>
<tr><th>Paper</th><th>Length</th><th>Marks</th><th>Calculator</th><th>What it looks like</th></tr>
<tr><td>Paper 1</td><td>1 hour 30 minutes</td><td>100</td><td>Allowed</td>
<td>About 27&ndash;29 short questions of 1&ndash;6 marks each. Mostly Number, Algebra,
Geometry, Mensuration and short Statistics questions.</td></tr>
<tr><td>Paper 2</td><td>2 hours 30 minutes</td><td>100</td><td>Allowed</td>
<td>About 10&ndash;11 long, structured questions of 7&ndash;16 marks. This is where sets, matrices and
transformations, functions, vectors, calculus and the longer probability questions sit.</td></tr>
</table>
<p>There is <b>no formula sheet</b> in Maths B. Students must know the area and volume formulae
(except those printed in a question), the trigonometry rules, the quadratic formula and the
circle theorems by heart. Every paper says "You must write down all the stages in your
working": an answer with no working can lose every mark.</p>

<h2>How Edexcel marks</h2>
<table>
<tr><th>Code</th><th>Meaning</th><th>What students must do</th></tr>
<tr><td><b>M1</b></td><td>Method</td><td>A correct method applied to the right numbers, written down. Arithmetic slips afterwards still keep it.</td></tr>
<tr><td><b>A1</b></td><td>Accuracy</td><td>The correct answer following a correct method.</td></tr>
<tr><td><b>B1</b></td><td>Independent</td><td>A correct value or statement on its own (a reading from a graph, a reason in a geometry proof).</td></tr>
<tr><td><b>ft / cao / oe / awrt / isw</b></td><td>&nbsp;</td><td>Follow through, correct answer only, or equivalent, answers which round to, ignore subsequent working.</td></tr>
<tr><td><b>SC</b></td><td>Special case</td><td>Partial credit the scheme allows for a common alternative or incomplete answer.</td></tr>
</table>
<div class="box trap"><span class="lbl">Habits that save the most marks in Maths B</span>
<ol>
<li>Write the method line before the answer: the formula, the substitution, the equation.</li>
<li>Keep full calculator values in the working; round only the final answer, to 3 s.f. unless told otherwise (angles to 1 d.p.).</li>
<li>Geometry "give reasons" questions: every angle needs its reason in the proper words ("alternate angles are equal").</li>
<li>Read the units and the final demand: "give your answer in cm&sup2;", "in the form&hellip;", "as a fraction in its simplest form".</li>
<li>On Paper 2, a later part often follows from an earlier one ("hence"): use it, and if an earlier part went wrong, carry your answer forward for follow-through marks.</li>
</ol></div>
"""


def build_html(weights: dict, grand: int, by_ch: dict) -> str:
    toc, chapters, answer_parts = [], [], []
    for ch, title in CHAPTER_TITLES.items():
        frag_path = NOTES_DIR / f"ch{ch:02d}.html"
        if not frag_path.exists():
            print(f"WARNING: missing {frag_path.name}; chapter {ch} skipped")
            continue
        frag = frag_path.read_text(encoding="utf-8")
        toc.append(f'<tr><td><b>Chapter {ch}</b></td><td><b>{html.escape(title)}</b></td></tr>')
        for t in re.findall(r'<div class="type"><h3>(.*?)<', frag):
            toc.append(f'<tr><td></td><td>{t}</td></tr>')
        ladder, answers = split_ladder(NOTES_DIR / f"ch{ch:02d}_practice.html")
        chapters.append(
            f'<div class="chapter"><h1 class="ct">Chapter {ch} &mdash; {html.escape(title)}</h1>'
            f'{chapter_weight(ch, weights, grand)}{frag}'
            f'<div class="practice"><h2>Graded practice &mdash; Chapter {ch}</h2>{ladder}</div>'
            f'{practice_map(ch, by_ch.get(ch, []))}</div>')
        if answers:
            answer_parts.append(f'<h2>Chapter {ch} &mdash; {html.escape(title)}</h2>{answers}')
    cover = """
    <div class="cover">
      <h1>Teacher's Notes</h1>
      <h2>Pearson Edexcel International GCSE Mathematics B (4MB1)</h2>
      <h2>Every chapter and every question type, 2016&ndash;2022</h2>
      <div class="brand">GRADEMAX</div>
      <div class="note">From the basics to exam standard, with worked examples modelled on past
      papers, the mark-scheme points each type earns, the mistakes that cost marks, and graded
      student exercises from beginner to expert.</div>
    </div>"""
    toc.append('<tr><td><b>Answers</b></td><td><b>Answers to Levels 1&ndash;5</b></td></tr>')
    contents = f'<div class="front"><h1 class="ct">Contents</h1><table class="toc">{"".join(toc)}</table></div>'
    front = (f'{FRONT_TOP}{ladder_table_html()}{FRONT_BOTTOM}{priority_ranking(weights, grand)}</div>')
    back = (f'<div class="chapter answers-back"><h1 class="ct">Answers to the graded practice</h1>'
            f'{"".join(answer_parts)}</div>')
    return (f'<!doctype html><html><head><meta charset="utf-8">{KATEX}<style>{CSS}{LADDER_CSS}</style></head>'
            f'<body>{cover}{contents}{front}{"".join(chapters)}{back}</body></html>')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html-only", action="store_true")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    weights, grand = load_weights()
    html_path = OUT_DIR / f"{STEM}.html"
    html_path.write_text(build_html(weights, grand, load_print_index()), encoding="utf-8")
    print(f"HTML -> {html_path.relative_to(REPO_ROOT)}")
    if not args.html_only:
        build_pdf(html_path, OUT_DIR / f"{STEM}.pdf")


if __name__ == "__main__":
    main()
