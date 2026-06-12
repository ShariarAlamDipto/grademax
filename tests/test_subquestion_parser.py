#!/usr/bin/env python3
"""Unit tests for scripts/lib/subquestion_parser.py.

Run either way:
    python -m pytest tests/test_subquestion_parser.py
    python tests/test_subquestion_parser.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib.subquestion_parser import (  # noqa: E402
    parse_question_structure,
    structure_to_dict,
)

# Fixtures shaped like real PyMuPDF extraction of Edexcel papers: part labels
# at line starts, marks markers standalone on their own line.

SIMPLE_NO_PARTS = """\
3 Solve the equation 5x - 7 = 2x + 8
(3)
(Total for Question 3 is 3 marks)
"""

TWO_PARTS = """\
5 The line L has equation y = 2x + 3
(a) Find the gradient of L
(2)
(b) Find the coordinates of the point where L crosses the x-axis
(2)
(Total for Question 5 is 4 marks)
"""

PARTS_WITH_SUBPARTS = """\
7 f(x) = x^2 - 4x + 1
(a) Express f(x) in the form (x + a)^2 + b
(2)
(b) Hence, or otherwise, find
(i) the minimum value of f(x)
(2)
(ii) the value of x at which the minimum occurs
(1)
(Total for Question 7 is 5 marks)
"""

INLINE_PAREN_NOISE = """\
4 The probability that a counter is red is 2/(5)x and P(A) = 0.3
(a) Work out the value of (i) given the table below where (b) is unknown
(3)
(Total for Question 4 is 3 marks)
"""

INCONSISTENT_MARKS = """\
6 (a) Differentiate y = 3x^2
(2)
(b) Find the turning point
(3)
(Total for Question 6 is 9 marks)
"""

NO_FENCE = """\
2 (a) State Hooke's law
(1)
(b) Calculate the extension
(3)
"""


def test_simple_question_no_parts():
    s = parse_question_structure(SIMPLE_NO_PARTS)
    assert s.parts == ()
    assert s.total_marks == 3
    assert s.detected_marks_sum == 3
    assert s.is_consistent is True


def test_two_parts_with_marks():
    s = parse_question_structure(TWO_PARTS)
    assert [p.label for p in s.parts] == ["a", "b"]
    assert [p.marks for p in s.parts] == [2, 2]
    assert s.total_marks == 4
    assert s.is_consistent is True


def test_nested_subparts():
    s = parse_question_structure(PARTS_WITH_SUBPARTS)
    assert [p.label for p in s.parts] == ["a", "b"]
    part_b = s.parts[1]
    assert [sub.label for sub in part_b.subparts] == ["i", "ii"]
    assert [sub.marks for sub in part_b.subparts] == [2, 1]
    assert part_b.marks == 3
    assert s.total_marks == 5
    assert s.is_consistent is True


def test_inline_parens_are_not_parts():
    # "(5)", "(A)", "(i)", "(b)" appearing mid-line must not create parts;
    # the only line-start part marker is (a).
    s = parse_question_structure(INLINE_PAREN_NOISE)
    assert [p.label for p in s.parts] == ["a"]
    assert s.parts[0].marks == 3
    assert s.is_consistent is True


def test_inconsistent_marks_flagged():
    s = parse_question_structure(INCONSISTENT_MARKS)
    assert s.detected_marks_sum == 5
    assert s.total_marks == 9
    assert s.is_consistent is False


def test_missing_fence_gives_none_consistency():
    s = parse_question_structure(NO_FENCE)
    assert s.total_marks is None
    assert s.detected_marks_sum == 4
    assert s.is_consistent is None


def test_empty_text():
    s = parse_question_structure("")
    assert s.parts == ()
    assert s.total_marks is None
    assert s.is_consistent is None


def test_out_of_sequence_letter_rejected():
    # A "(d)" with no prior (a)-(c) is formula noise, not a part.
    text = "1 Given that (d) = 4\n(2)\n(Total for Question 1 is 2 marks)\n"
    s = parse_question_structure(text)
    assert s.parts == ()
    assert s.detected_marks_sum == 2


def test_structure_to_dict_roundtrip():
    d = structure_to_dict(parse_question_structure(PARTS_WITH_SUBPARTS))
    assert d["total_marks"] == 5
    assert d["parts"][1]["subparts"][0] == {"label": "i", "marks": 2}
    assert d["is_consistent"] is True


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"  FAIL {name}: {exc}")
    print(f"\n{'OK' if failures == 0 else f'{failures} FAILURE(S)'}")
    sys.exit(1 if failures else 0)
