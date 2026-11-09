"""Checks for IGCSE ICT (4IT1) in the worksheet generator and test builder.

    .venv/Scripts/python -X utf8 -m unittest tests/test_igcse_ict.py
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from lib import commerce_chapters as cc  # noqa: E402
from lib.igcse_ict_topics import CHAPTERS, SUBJECT  # noqa: E402
from lib.igcse_science_rebuild import PUBLISHABLE  # noqa: E402
from onboard_igcse_ict import LABEL_RE, QP_PART_RE  # noqa: E402

STAGE = SUBJECT.stage
ROOT = Path(__file__).resolve().parents[1]


def verdicts() -> dict:
    return json.loads((STAGE / 'verdicts.json').read_text(encoding='utf-8'))


class StagedBank(unittest.TestCase):
    def test_every_publishable_question_is_read_and_current(self) -> None:
        rows = cc.published_rows(SUBJECT)
        self.assertEqual(cc.validate(SUBJECT, cc.load_reads(SUBJECT), rows), [])
        self.assertEqual(len(rows), 80)

    def test_each_paper_is_five_questions_totalling_100(self) -> None:
        papers: dict[str, list[dict]] = {}
        for row in cc.published_rows(SUBJECT):
            papers.setdefault(row['paper'], []).append(row)
        for key, rows in papers.items():
            self.assertEqual(sorted(r['question'] for r in rows), [1, 2, 3, 4, 5], key)
            self.assertEqual(sum(r['marks'] for r in rows), 100, key)

    def test_paper_2_practicals_are_held(self) -> None:
        for key, note in verdicts()['papers'].items():
            if key.endswith('_P2'):
                self.assertTrue(note.startswith('HELD'), key)
        self.assertFalse(any(r['paper'].endswith('_P2') for r in verdicts()['rows']))

    def test_review_decisions_are_applied(self) -> None:
        decisions = json.loads((STAGE / 'manual_review.json').read_text(encoding='utf-8'))
        rows = {cc.key_of(r): r for r in verdicts()['rows']}
        for key in decisions:
            self.assertEqual(rows[key]['verdict'], 'REVIEWED_PROVEN', key)

    def test_reads_use_only_paper_1_sections(self) -> None:
        for key, read in cc.load_reads(SUBJECT).items():
            self.assertTrue(set(read['topics']) <= set(CHAPTERS), key)
            self.assertEqual(len(read['topics']), len(set(read['topics'])), key)

    def test_marks_file_matches_staged_rows(self) -> None:
        marks = json.loads((ROOT / 'src' / 'lib' / 'ictQuestionMarks.json').read_text(encoding='utf-8'))
        for row in cc.published_rows(SUBJECT):
            self.assertEqual(marks[f"{row['paper_id']}|{row['question']}"], row['marks'], cc.key_of(row))

    def test_every_published_verdict_is_publishable(self) -> None:
        self.assertTrue(all(r['verdict'] in PUBLISHABLE for r in cc.published_rows(SUBJECT)))


def label(text: str) -> tuple[int, str] | None:
    m = LABEL_RE.match(text)
    return (int(m[1]), m[2] or m[3]) if m else None


class SchemeLabels(unittest.TestCase):
    def test_compact_and_bracketed_forms(self) -> None:
        for text, want in [('1ai Award one mark', (1, 'a')), ('2biii any two', (2, 'b')),
                           ('3g Indicative content', (3, 'g')), ('4(a)(i) one mark', (4, 'a')),
                           ('5(c) Answers', (5, 'c')), ('1e(ii)', (1, 'e'))]:
            self.assertEqual(label(text), want, text)

    def test_non_labels(self) -> None:
        for text in ('6a outside the paper', '12 marks', '1 mark per point', 'a) loose', '2 bits'):
            self.assertIsNone(label(text), text)

    def test_qp_part_letters(self) -> None:
        self.assertEqual(QP_PART_RE.findall('(a) State (b) Explain x(c)'), ['a', 'b'])


if __name__ == '__main__':
    unittest.main()
