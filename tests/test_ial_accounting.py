"""Checks for IAL Accounting (WAC) in the worksheet generator and test builder.

    .venv/Scripts/python -X utf8 -m unittest tests/test_ial_accounting.py
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from lib import commerce_chapters as cc  # noqa: E402
from lib.ial_accounting_stage import (PLACEHOLDER_RE, SCHEME_START_RE, SCHEME_WEAK_RE,  # noqa: E402
                                      TOTAL_RE)
from lib.ial_accounting_topics import CHAPTERS, SUBJECT  # noqa: E402
from lib.igcse_science_rebuild import PUBLISHABLE  # noqa: E402

STAGE = SUBJECT.stage


def verdict_rows() -> dict[str, dict]:
    rows = json.loads((STAGE / 'verdicts.json').read_text(encoding='utf-8'))['rows']
    return {cc.key_of(r): r for r in rows}


class StagedBank(unittest.TestCase):
    def test_every_publishable_question_is_read_and_current(self) -> None:
        rows = cc.published_rows(SUBJECT)
        self.assertEqual(cc.validate(SUBJECT, cc.load_reads(SUBJECT), rows), [])
        self.assertEqual(len(rows), 119)

    def test_review_decisions_are_applied(self) -> None:
        decisions = json.loads((STAGE / 'manual_review.json').read_text(encoding='utf-8'))
        rows = verdict_rows()
        for key in decisions:
            self.assertEqual(rows[key]['verdict'], 'REVIEWED_PROVEN', key)

    def test_pearson_incomplete_scheme_is_held(self) -> None:
        row = verdict_rows()['2026_may-jun_PUnit_2|4']
        self.assertNotIn(row['verdict'], PUBLISHABLE)
        self.assertIn('incomplete', row['detail'])

    def test_wrong_papers_are_held(self) -> None:
        papers = json.loads((STAGE / 'verdicts.json').read_text(encoding='utf-8'))['papers']
        # Live Unit 2 June 2024 scheme is the Unit 1 scheme; live Jan 2023 Unit 2 QP is June 2023's.
        self.assertTrue(papers['2024_may-jun_PUnit_2'].startswith('HELD'))
        self.assertTrue(papers['2023_jan_PUnit_2'].startswith('HELD'))

    def test_marks_match_paper_structure(self) -> None:
        for row in cc.published_rows(SUBJECT):
            self.assertIn(row['marks'], (30, 55), cc.key_of(row))
            self.assertEqual(row['marks'] == 55, row['question'] in (1, 2), cc.key_of(row))

    def test_chapter_codes_sort_in_spec_order(self) -> None:
        self.assertEqual(list(CHAPTERS), sorted(CHAPTERS))


def strong(text: str) -> list[int]:
    return [int(next(g for g in m.groups() if g)) for m in SCHEME_START_RE.finditer(text)]


class SchemeMarkers(unittest.TestCase):
    def test_start_forms(self) -> None:
        for text, n in [('1(a) AO1:(2)', 1), ('4 (a) AO1:(4)', 4), ('Q1 (a) AO1 (14)', 1),
                        ('Q1(a)(i) Mark Scheme', 1), ('Q4 (i) AO1:(2)', 4), ('4 (i) AO1:(4) AO2(6)', 4),
                        ('Q4a to be integrated', 4), ('Q3. Mark scheme (a) (i)', 3)]:
            self.assertIn(n, strong(text), text)

    def test_money_and_references_are_not_starts(self) -> None:
        self.assertEqual(strong('£2 (a) total'), [])
        self.assertEqual([int(m[1]) for m in SCHEME_WEAK_RE.finditer('Question 3')], [3])

    def test_total_line_and_placeholder(self) -> None:
        self.assertEqual(TOTAL_RE.search('(Total for Question 2 = 55 marks)').groups(), ('2', '55'))
        self.assertTrue(PLACEHOLDER_RE.search('Q4a to be integrated from the Excel file.'))
        self.assertIsNone(PLACEHOLDER_RE.search('Ledger balances to be calculated'))


if __name__ == '__main__':
    unittest.main()
