"""Checks for the IGCSE Business (4BS1) bank extension: legacy 4BS0 Paper 1
(2011-2018) and the November 2025 papers.

    .venv/Scripts/python -X utf8 -m unittest tests/test_igcse_business_bank.py
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from extend_igcse_business_bank import TARGETS  # noqa: E402
from lib import commerce_chapters as cc  # noqa: E402
from lib.business_topics import SUBJECT  # noqa: E402

STAGE = SUBJECT.stage


class ExtendedBank(unittest.TestCase):
    def setUp(self) -> None:
        self.v = json.loads((STAGE / 'verdicts.json').read_text(encoding='utf-8'))

    def test_every_publishable_question_is_read_and_current(self) -> None:
        rows = cc.published_rows(SUBJECT)
        self.assertEqual(cc.validate(SUBJECT, cc.load_reads(SUBJECT), rows), [])
        self.assertEqual(len(rows), 178)

    def test_questions_are_twenty_marks(self) -> None:
        self.assertEqual({r['marks'] for r in cc.published_rows(SUBJECT)}, {20})

    def test_unprovable_targets_are_held(self) -> None:
        self.assertTrue(self.v['papers']['2012_may-jun_P1'].startswith('HELD'))
        self.assertTrue(self.v['papers']['2015_may-jun_P1'].startswith('HELD'))

    def test_targets_are_staged(self) -> None:
        staged = {r['paper'] for r in cc.published_rows(SUBJECT)}
        held = {k for k, n in self.v['papers'].items() if n.startswith('HELD')}
        for key in TARGETS:
            self.assertTrue(key in staged or key in held, key)

    def test_review_decisions_are_applied(self) -> None:
        decisions = json.loads((STAGE / 'manual_review.json').read_text(encoding='utf-8'))
        rows = {cc.key_of(r): r for r in self.v['rows']}
        for key, d in decisions.items():
            if d.get('verdict') == 'REVIEWED_PROVEN' and key in rows:
                self.assertEqual(rows[key]['verdict'], 'REVIEWED_PROVEN', key)


if __name__ == '__main__':
    unittest.main()
