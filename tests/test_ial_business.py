"""Checks for IAL Business (WBS) in the worksheet generator and test builder.

    .venv/Scripts/python -X utf8 -m unittest tests/test_ial_business.py
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from lib import commerce_chapters as cc  # noqa: E402
from lib.ial_business_stage import PAGE_FURNITURE_RE, SOURCE_RE, TOTAL_RE, _is_rule  # noqa: E402
from lib.ial_business_topics import CHAPTERS, SUBJECT  # noqa: E402

STAGE = SUBJECT.stage
ROOT = Path(__file__).resolve().parents[1]


def verdicts() -> dict:
    return json.loads((STAGE / 'verdicts.json').read_text(encoding='utf-8'))


class StagedBank(unittest.TestCase):
    def test_every_publishable_question_is_read_and_current(self) -> None:
        rows = cc.published_rows(SUBJECT)
        self.assertEqual(cc.validate(SUBJECT, cc.load_reads(SUBJECT), rows), [])
        self.assertEqual(len(rows), 39)

    def test_each_paper_is_three_sections_totalling_80(self) -> None:
        papers: dict[str, list[dict]] = {}
        for row in cc.published_rows(SUBJECT):
            papers.setdefault(row['paper'], []).append(row)
        for key, rows in papers.items():
            self.assertEqual(sorted(r['question'] for r in rows), [1, 2, 3], key)
            self.assertEqual(sum(r['marks'] for r in rows), 80, key)

    def test_wrong_unit_qp_is_held(self) -> None:
        # The live June 2025 Unit 1 row holds the WBS12 (Unit 2) question paper.
        self.assertIn('WBS12', verdicts()['papers']['2025_may-jun_PUnit_1'])

    def test_reads_use_spec_topics(self) -> None:
        for key, read in cc.load_reads(SUBJECT).items():
            self.assertTrue(set(read['topics']) <= set(CHAPTERS), key)

    def test_marks_file_matches_staged_rows(self) -> None:
        marks = json.loads((ROOT / 'src' / 'lib' / 'ialBusinessQuestionMarks.json').read_text(encoding='utf-8'))
        for row in cc.published_rows(SUBJECT):
            self.assertEqual(marks[f"{row['paper_id']}|{row['question']}"], row['marks'], cc.key_of(row))


class PageText(unittest.TestCase):
    def test_answer_lines_and_margin_words_are_rules(self) -> None:
        for text in ('........................', '....... ....... .......', 'DO ........ NOT', '…………'):
            self.assertTrue(_is_rule(text), text)
        self.assertFalse(_is_rule('(a) Define the term ........'))

    def test_furniture(self) -> None:
        for text in ('DO NOT WRITE IN THIS AREA', 'AREA', '*P72876A0124*', 'WBS11 · QP'):
            self.assertTrue(PAGE_FURNITURE_RE.search(text), text)
        self.assertIsNone(PAGE_FURNITURE_RE.search('Analyse the impact on Product sales'))

    def test_markers(self) -> None:
        self.assertEqual(TOTAL_RE.search('(Total for Question 2 = 30 marks)').groups(), ('2', '30'))
        self.assertEqual(SOURCE_RE.match('Sources for use with Section B')[1], 'B')


if __name__ == '__main__':
    unittest.main()
