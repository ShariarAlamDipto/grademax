"""Verify complete question cuts and the references needed to answer them."""

from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from onboard_igcse_commerce import add_business_formulae, is_current_specification, paper_topic
from lib.igcse_science_rebuild import question_segments, write_cut


class CommerceQuestionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.pdf"
        with fitz.open() as doc:
            page = doc.new_page()
            page.insert_text((45, 80), "4BS1/01")
            page = doc.new_page()
            page.insert_text((45, 80), "FORMULAE FOR INTERNATIONAL GCSE BUSINESS")
            page.insert_text((45, 130), "Gross profit = revenue - cost of sales")
            page = doc.new_page()
            page.insert_text((45, 80), "1 Amber Gym employs 14 people in two branches.")
            page.insert_text((60, 180), "(a) Define limited liability. (2)")
            page.insert_text((60, 300), "(b) Explain one benefit to Amber Gym. (3)")
            page.insert_text((60, 500), "(Total for Question 1 = 5 marks)")
            page = doc.new_page()
            page.insert_text((45, 80), "2 Amber Gym plans a new branch.")
            page.insert_text((60, 180), "(a) Explain the effect on costs. (5)")
            page.insert_text((60, 500), "(Total for Question 2 = 5 marks)")
            page.insert_text((60, 550), "TOTAL FOR PAPER = 10 MARKS")
            doc.save(self.source)

    def test_question_cuts_keep_subparts_and_exclude_neighbours(self):
        with fitz.open(self.source) as doc:
            segments, why = question_segments(doc)
            self.assertEqual(why, "")
            self.assertEqual([s.marks for s in segments], [5, 5])
            target = self.root / "q1.pdf"
            write_cut(doc, segments[0].regions, target)
        with fitz.open(target) as doc:
            text = " ".join(p.get_text() for p in doc)
        self.assertIn("(a) Define limited liability", text)
        self.assertIn("(b) Explain one benefit", text)
        self.assertNotIn("plans a new branch", text)

    def test_business_question_keeps_formulae_and_shared_case(self):
        with fitz.open(self.source) as doc:
            segments, _ = question_segments(doc)
            staged = []
            for segment in segments:
                target = self.root / "questions" / f"q{segment.number}.pdf"
                write_cut(doc, segment.regions, target)
                staged.append({"number": segment.number, "qp": target,
                               "pages": [r[0] + 1 for r in segment.regions]})
        add_business_formulae(SimpleNamespace(qp_path=self.source), staged)
        with fitz.open(staged[1]["qp"]) as doc:
            text = " ".join(p.get_text() for p in doc)
            self.assertEqual(len(doc), len(staged[1]["pages"]))
        self.assertIn("Gross profit = revenue", text)
        self.assertIn("employs 14 people", text)
        self.assertIn("Explain the effect on costs", text)
        self.assertNotIn("Define limited liability", text)

    def test_incomplete_question_coverage_is_held(self):
        with fitz.open() as doc:
            page = doc.new_page()
            page.insert_text((45, 80), "1 Explain your answer.")
            page.insert_text((45, 300), "(Total for Question 1 = 5 marks)")
            page.insert_text((45, 350), "TOTAL FOR PAPER = 10 MARKS")
            segments, why = question_segments(doc)
        self.assertEqual(segments, [])
        self.assertIn("paper prints TOTAL 10", why)

    def test_regional_papers_share_scope_and_legacy_papers_are_excluded(self):
        self.assertEqual(paper_topic("01R"), "1")
        self.assertEqual(paper_topic("2"), "2")
        with self.assertRaises(ValueError):
            paper_topic("3")
        paper = SimpleNamespace(qp_path=self.source, ms_path=self.source)
        self.assertTrue(is_current_specification("4BS1", paper))
        self.assertFalse(is_current_specification("4EC1", paper))


if __name__ == "__main__":
    unittest.main()
