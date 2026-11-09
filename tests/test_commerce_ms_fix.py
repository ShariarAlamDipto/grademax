"""Tests for the Economics/Business page-range mark-scheme cut (scripts/lib/commerce_ms_fix.py)."""
import sys
import tempfile
import unittest
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib import commerce_ms_fix as fix  # noqa: E402


def doc(*pages: str) -> fitz.Document:
    out = fitz.open()
    for text in pages:
        out.new_page().insert_textbox(fitz.Rect(40, 40, 560, 800), text, fontsize=9)
    return out


COVER = "Mark Scheme (Results) Summer 2024 Pearson Edexcel International GCSE"
BACK = "Pearson Education Limited. Registered company number 872828 with its registered office at 80 Strand"
LEVELS = "Level Mark Descriptor 0 No rewardable material. Level 1 1-4 basic knowledge"


class QuestionPagesTest(unittest.TestCase):
    def test_each_question_runs_to_the_next_start_and_back_cover_is_dropped(self):
        src = doc(COVER, "1(a) answer 1(b) answer", LEVELS, "2(a) answer", "2(b) analyse", LEVELS, BACK)
        self.assertEqual(fix.question_pages(src), {1: [1, 2], 2: [3, 4, 5]})

    def test_a_question_starting_mid_page_is_refused(self):
        src = doc(COVER, "1(a) answer", "1(b) answer 2(a) answer", "2(b) answer")
        with self.assertRaises(ValueError):
            fix.question_pages(src)

    def test_footer_on_a_content_page_is_not_a_back_cover(self):
        src = doc("1(a) answer", LEVELS + " evaluate analyse assess discuss explain judge weigh " * 3 + BACK)
        self.assertEqual(fix.question_pages(src), {1: [0, 1]})


class CheckTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.qp = Path(tmp.name) / "qp.pdf"
        doc("3 (a) Define. (1) (b) Explain. (3) (c) Evaluate. (12) (Total for Question 3 = 16 marks)").save(self.qp)

    def test_complete_cut_passes(self):
        self.assertIsNone(fix._check(3, doc("3(a) x 3(b) y", "3(c) z", LEVELS), self.qp))

    def test_bare_part_label_before_assessment_objective_counts(self):
        self.assertIsNone(fix._check(3, doc("3(a) x 3(b) y", "Indicative content\n(c)\nAO2 (4 marks)"), self.qp))

    def test_missing_part_is_refused(self):
        self.assertIn("lacks part(s) ['c']", fix._check(3, doc("3(a) x 3(b) y", LEVELS), self.qp))

    def test_another_questions_label_is_refused(self):
        self.assertIn("question(s) [4]", fix._check(3, doc("3(a) x 3(b) y 3(c) z", "4(a) w"), self.qp))


if __name__ == "__main__":
    unittest.main()
