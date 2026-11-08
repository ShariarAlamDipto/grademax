import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from lib import printed_question_marks as pqm  # noqa: E402


class LabelledMarks(unittest.TestCase):
    def test_igcse_wording(self):
        text = "... (2) (Total for Question 7 is 6 marks)"
        self.assertEqual(pqm.labelled_marks(text, "7"), 6)

    def test_ial_wording(self):
        self.assertEqual(pqm.labelled_marks("____ Q10 (Total 7 marks) Mathematics", "10"), 7)

    def test_old_human_biology_wording(self):
        self.assertEqual(pqm.labelled_marks("(4) (Total Question 6 = 6 marks)", "6"), 6)

    def test_ignores_a_neighbouring_question(self):
        text = "(Total for Question 3 is 5 marks) ... question 4 starts"
        self.assertIsNone(pqm.labelled_marks(text, "4"))

    def test_question_number_with_prefix_or_zero(self):
        self.assertEqual(pqm.labelled_marks("(Total for Question 7 is 6 marks)", "Q07"), 6)

    def test_contradictory_totals_are_rejected(self):
        text = "(Total for Question 2 is 4 marks) (Total for Question 2 is 5 marks)"
        self.assertIsNone(pqm.labelled_marks(text, "2"))

    def test_repeated_identical_total_is_fine(self):
        text = "Q1 (Total 6 marks) footer Q1 (Total 6 marks)"
        self.assertEqual(pqm.labelled_marks(text, "1"), 6)


class UnlabelledMarks(unittest.TestCase):
    def test_single_lone_total(self):
        self.assertEqual(pqm.unlabelled_marks("(3) (Total 9 marks)"), 9)

    def test_not_used_when_a_numbered_total_exists(self):
        self.assertIsNone(pqm.unlabelled_marks("(Total for Question 3 is 5 marks) (Total 9 marks)"))

    def test_two_different_lone_totals(self):
        self.assertIsNone(pqm.unlabelled_marks("(Total 9 marks) (Total 4 marks)"))


class PartMarks(unittest.TestCase):
    def test_sum(self):
        self.assertEqual(pqm.part_marks_sum("(2) (4) (1)"), 7)

    def test_none_found(self):
        self.assertIsNone(pqm.part_marks_sum("no marks here"))


class PaperChecks(unittest.TestCase):
    def test_whole_paper(self):
        self.assertTrue(pqm.is_whole_paper(["2", "1", "3"]))
        self.assertFalse(pqm.is_whole_paper(["1", "3"]))

    def test_paper_total_from_spec(self):
        self.assertTrue(pqm.paper_total_ok("WST01", [10, 15, 50]))
        self.assertFalse(pqm.paper_total_ok("WST01", [10, 15, 54]))
        self.assertFalse(pqm.paper_total_ok("UNKNOWN", [75]))

    def test_printed_total_wins_over_spec(self):
        self.assertTrue(pqm.paper_total_ok("4PH1", [50, 50], printed_total=100))
        self.assertFalse(pqm.paper_total_ok("4PH1", [55, 55], printed_total=100))

    def test_printed_paper_total(self):
        self.assertEqual(pqm.printed_paper_total("TOTAL FOR PAPER IS 75 MARKS END"), 75)
        self.assertEqual(pqm.printed_paper_total("TOTAL FOR PAPER = 110 MARKS"), 110)

    def test_plausible(self):
        self.assertTrue(pqm.plausible(12))
        self.assertFalse(pqm.plausible(0))
        self.assertFalse(pqm.plausible(None))
        self.assertFalse(pqm.plausible(75))


if __name__ == "__main__":
    unittest.main()
