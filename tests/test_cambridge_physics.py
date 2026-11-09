"""Cambridge IGCSE Physics (0625) P42/P62 segmenter and proof gate.

    .venv/Scripts/python -X utf8 -m unittest tests/test_cambridge_physics.py
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fitz  # noqa: E402

from lib.cambridge_physics_segments import (  # noqa: E402
    LABEL_RE, PAPER_MARKS, PART_RE, _label_of, judge, question_cuts,
)
from lib.igcse_science_rebuild import PUBLISHABLE  # noqa: E402

BASE = ROOT / "data" / "analysis" / "live_rebuild" / "0625"


class LabelTests(unittest.TestCase):
    def test_scheme_labels(self):
        self.assertEqual(_label_of("1(a)(i) 4.7 B1"), (1, "a"))
        self.assertEqual(_label_of("10(c)(ii)"), (10, "c"))
        self.assertEqual(_label_of("5(c)(i),(ii) labelled wavelength"), (5, "c"))
        self.assertEqual(_label_of("4"), (4, None))

    def test_answer_values_are_not_labels(self):
        self.assertIsNone(_label_of("4.7"))
        self.assertIsNone(_label_of("(A = 44 × 20 =)"))
        self.assertIsNone(LABEL_RE.match("880"))

    def test_part_tokens(self):
        self.assertEqual(PART_RE.match("(a)").group(1), "a")
        self.assertEqual(PART_RE.match("(a)(i)(ii)").group(1), "a")
        self.assertIsNone(PART_RE.match("(ii)"))
        self.assertIsNone(PART_RE.match("(A"))


class JudgeTests(unittest.TestCase):
    def evidence(self, numbers, parts, marks):
        return {"numbers": numbers, "parts": tuple(parts), "marks": marks}

    def test_proven_needs_number_parts_and_marks(self):
        verdict, _ = judge(3, 8, ("a", "b"), self.evidence([3], "ab", 8))
        self.assertEqual(verdict, "PROVEN")

    def test_marks_unreadable_is_label_proven(self):
        verdict, _ = judge(3, 8, ("a", "b"), self.evidence([3], "ab", None))
        self.assertEqual(verdict, "LABEL_PROVEN")

    def test_neighbour_in_block_is_held(self):
        verdict, _ = judge(3, 8, ("a", "b"), self.evidence([3, 4], "ab", 8))
        self.assertEqual(verdict, "MS_WRONG")
        self.assertNotIn(verdict, PUBLISHABLE)

    def test_missing_part_is_held(self):
        verdict, _ = judge(3, 8, ("a", "b", "c"), self.evidence([3], "ab", 8))
        self.assertEqual(verdict, "MS_PARTIAL")
        self.assertNotIn(verdict, PUBLISHABLE)

    def test_scheme_without_parts_is_held(self):
        verdict, _ = judge(3, 8, ("a", "b"), self.evidence([3], "", 8))
        self.assertNotIn(verdict, PUBLISHABLE)


@unittest.skipUnless((BASE / "sources").is_dir(), "0625 sources not cached")
class CachedPaperTests(unittest.TestCase):
    def test_cuts_add_up_to_paper_total(self):
        for stem, component in (("2019_may-jun_P42", "4"), ("2021_may-jun_P62", "6")):
            with fitz.open(BASE / "sources" / f"{stem}_qp.pdf") as doc:
                cuts, why = question_cuts(doc, component)
            self.assertEqual(why, "")
            self.assertEqual([c.number for c in cuts], list(range(1, len(cuts) + 1)))
            self.assertEqual(sum(c.marks for c in cuts), PAPER_MARKS[component])

    def test_staged_rows_are_complete_papers(self):
        verdicts = json.loads((BASE / "verdicts.json").read_text(encoding="utf-8"))
        papers: dict[str, list[dict]] = {}
        for row in verdicts["rows"]:
            papers.setdefault(row["paper"], []).append(row)
        for paper, rows in papers.items():
            self.assertTrue(all(r["verdict"] in PUBLISHABLE for r in rows), paper)
            self.assertEqual(sum(r["marks"] for r in rows), PAPER_MARKS[paper.split("_P")[1][0]], paper)


if __name__ == "__main__":
    unittest.main()
