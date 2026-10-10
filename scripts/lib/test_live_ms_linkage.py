"""Verdict rules of lib.live_ms_linkage.judge.  Run: python -m pytest scripts/lib/test_live_ms_linkage.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.live_ms_linkage import Evidence, judge  # noqa: E402

TEXT = 500


def qp(*totals):
    return Evidence(TEXT, tuple(totals), (), ())


def ms(totals=(), tallies=(), labels=()):
    return Evidence(TEXT, tuple(totals), tuple(tallies), tuple(labels))


def test_physics_numbered_match_is_proven():
    assert judge(4, qp((4, 6)), ms(totals=[(4, 6)]))[0] == "PROVEN"


def test_physics_scheme_for_neighbour_is_wrong():
    assert judge(4, qp((4, 6)), ms(totals=[(5, 6)]))[0] == "MS_WRONG"


def test_physics_scheme_with_two_questions_is_bundled():
    assert judge(4, qp((4, 6)), ms(totals=[(4, 6), (5, 3)]))[0] == "MS_BUNDLED"


def test_marks_disagree_is_wrong():
    assert judge(3, qp((3, 4)), ms(tallies=[5]))[0] == "MS_WRONG"


def test_maths_label_and_marks_is_proven():
    assert judge(3, qp((3, 4)), ms(tallies=[4], labels=[3]))[0] == "PROVEN"


def test_maths_marks_without_number_is_not_proof():
    assert judge(3, qp((3, 4)), ms(tallies=[4]))[0] == "MARKS_ONLY"


def test_maths_label_for_other_question_is_wrong():
    assert judge(3, qp((3, 4)), ms(tallies=[4], labels=[7]))[0] == "MS_WRONG"


def test_maths_two_different_tallies_is_bundled():
    assert judge(3, qp((3, 4)), ms(tallies=[4, 2]))[0] == "MS_BUNDLED"


def test_equal_tallies_alt_method_is_not_bundled():
    assert judge(3, qp((3, 4)), ms(tallies=[4, 4], labels=[3]))[0] == "PROVEN"


def test_question_file_with_two_questions():
    assert judge(3, qp((3, 4), (4, 2)), ms(tallies=[4]))[0] == "QP_BUNDLED"


def test_question_file_holds_other_number():
    assert judge(2, qp((5, 4)), ms(tallies=[4]))[0] == "QP_WRONG"


def test_no_ms():
    assert judge(2, qp((2, 4)), None)[0] == "NO_MS"


def test_image_only_is_unreadable_not_ok():
    assert judge(2, qp((2, 4)), Evidence(0, (), (), ()))[0] == "UNREADABLE"


def test_tally_less_scheme_with_own_label():
    assert judge(3, qp((3, 4)), ms(labels=[3]))[0] == "LABEL_ONLY"


def test_tally_less_scheme_with_other_label_is_wrong():
    assert judge(3, qp((3, 4)), ms(labels=[5]))[0] == "MS_WRONG"


def test_tally_less_scheme_label_and_column_sum_is_proven():
    ev = Evidence(TEXT, (), (), (3,), 4)
    assert judge(3, qp((3, 4)), ev)[0] == "PROVEN"


def test_tally_less_scheme_column_sum_disagrees_stays_label_only():
    ev = Evidence(TEXT, (), (), (3,), 6)
    assert judge(3, qp((3, 4)), ev)[0] == "LABEL_ONLY"


def test_misprinted_total_with_matching_cells_is_proven():
    ev = Evidence(TEXT, ((1, 8),), (), (), 9)
    assert judge(1, qp((1, 9)), ev)[0] == "PROVEN"


def test_wrong_total_and_cells_stays_wrong():
    ev = Evidence(TEXT, ((1, 8),), (), (), 8)
    assert judge(1, qp((1, 9)), ev)[0] == "MS_WRONG"


def test_scheme_missing_opening_parts_is_partial():
    q = Evidence(TEXT, ((5, 13),), (), (), None, ("a", "b", "c", "d", "e", "f"))
    m = Evidence(TEXT, ((5, 13),), (), (), None, ("f",))
    assert judge(5, q, m)[0] == "MS_PARTIAL"


def test_scheme_with_all_parts_is_proven():
    q = Evidence(TEXT, ((5, 13),), (), (), None, ("a", "b"))
    m = Evidence(TEXT, ((5, 13),), (), (), None, ("a", "b"))
    assert judge(5, q, m)[0] == "PROVEN"


def test_tally_less_scheme_with_uniform_question_totals_is_proven():
    ev = Evidence(TEXT, (), (), (11,), 6, (), 3)
    assert judge(11, qp((11, 3)), ev)[0] == "PROVEN"


def test_tally_less_scheme_with_matching_mark_codes_is_proven():
    ev = Evidence(TEXT, (), (), (3,), None, (), None, 7)
    assert judge(3, qp((3, 7)), ev)[0] == "PROVEN"


def test_mark_code_regex():
    from lib.live_ms_linkage import CODE_DIGIT_RE, MARK_CODE_RE
    assert MARK_CODE_RE.match("M1A1A1") and MARK_CODE_RE.match("dM1") and MARK_CODE_RE.match("A1ft")
    assert not MARK_CODE_RE.match("MAB") and not MARK_CODE_RE.match("A")
    assert sum(int(d) for d in CODE_DIGIT_RE.findall("M1A1A1")) == 3
