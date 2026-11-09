"""Checks for the IGCSE Business (4BS1) and Economics (4EC1) chapter reads.

    .venv/Scripts/python -X utf8 -m unittest tests/test_igcse_commerce_chapters.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from lib import commerce_chapters as cc  # noqa: E402
from lib.business_topics import SUBJECT as BUSINESS  # noqa: E402
from lib.economics_topics import SUBJECT as ECONOMICS  # noqa: E402


class FakeQuery:
    """Records the topic rows an insert would create."""

    def __init__(self, sink: list) -> None:
        self.sink = sink

    def insert(self, rows: list) -> 'FakeQuery':
        self.sink.extend(rows)
        return self

    def execute(self) -> None:
        return None


class FakeClient:
    def __init__(self) -> None:
        self.inserted: list = []

    def table(self, _name: str) -> FakeQuery:
        return FakeQuery(self.inserted)


class CommittedReads(unittest.TestCase):
    """The reads on disk cover every published question and match the PDFs."""

    def check_subject(self, subject: cc.Subject) -> None:
        rows = cc.published_rows(subject)
        reads = cc.load_reads(subject)
        self.assertEqual(cc.validate(subject, reads, rows), [], 'unread questions')
        for key, read in reads.items():
            self.assertEqual(len(read['topics']), len(set(read['topics'])), key)

    def test_business(self) -> None:
        self.check_subject(BUSINESS)

    def test_economics(self) -> None:
        self.check_subject(ECONOMICS)

    def test_economics_paper_scope(self) -> None:
        """Paper 1 covers sections 1.x and Paper 2 covers 2.x; a primary chapter
        from the wrong paper's half would be a misread."""
        for key, read in cc.load_reads(ECONOMICS).items():
            paper = key.split('|')[0].rsplit('_P', 1)[1][0]
            primary = read['topics'][0]
            if paper == '1':
                self.assertTrue(primary.startswith('1.'), key)


class Validation(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = cc.published_rows(BUSINESS)
        self.key = cc.key_of(self.rows[0])
        self.good = cc.load_reads(BUSINESS)[self.key]

    def run_validate(self, read: dict) -> None:
        cc.validate(BUSINESS, {self.key: read}, self.rows)

    def test_good_read_passes(self) -> None:
        self.run_validate(self.good)

    def test_unknown_chapter_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, 'unknown chapter'):
            self.run_validate({**self.good, 'topics': ['9.9']})

    def test_stale_hash_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, 'read it again'):
            self.run_validate({**self.good, 'qp_sha256': '0' * 64})

    def test_missing_reason_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, 'no reason'):
            self.run_validate({**self.good, 'reason': ' '})

    def test_bad_difficulty_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, 'difficulty'):
            self.run_validate({**self.good, 'difficulty': 'tricky'})

    def test_unpublished_key_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, 'not published'):
            cc.validate(BUSINESS, {'1999_jan_P1|1': self.good}, self.rows)


class Result:
    def __init__(self, data: list) -> None:
        self.data = data


class GuardQuery:
    """A pages/questions/tags query that returns `rows` and records the filters used."""

    def __init__(self, rows: list, log: list) -> None:
        self.rows, self.log = rows, log

    def __getattr__(self, name: str):
        def call(*args, **_kwargs):
            self.log.append((name, args))
            return self
        return call

    def execute(self) -> Result:
        return Result(self.rows)


class GuardClient:
    def __init__(self, rows: list) -> None:
        self.rows, self.log = rows, []

    def table(self, _name: str) -> GuardQuery:
        return GuardQuery(self.rows, self.log)


class GuardedWrite(unittest.TestCase):
    PLAN = {('p1', '1'): {'topics': ['4.3'], 'difficulty': 'easy'}}

    def page(self, topics, difficulty=None) -> dict:
        return {('p1', '1'): {'id': 'q1', 'topics': topics, 'difficulty': difficulty}}

    def test_guard_miss_raises_with_resume_hint(self) -> None:
        client = GuardClient(rows=[])  # the guarded update matched nothing
        with self.assertRaisesRegex(SystemExit, 're-run apply to resume'):
            cc._write(client, BUSINESS, self.PLAN, self.page(['1']),
                      [{'id': 'q1', 'difficulty': None}], [])

    def test_null_topics_guarded_with_is_null(self) -> None:
        client = GuardClient(rows=[{'id': 'q1'}])
        cc._write(client, BUSINESS, self.PLAN, self.page(None), [{'id': 'q1', 'difficulty': 'easy'}], [])
        self.assertIn(('is_', ('topics', 'null')), client.log)
        self.assertIn(('is_', ('difficulty', 'null')), client.log)

    def test_array_topics_guarded_with_literal(self) -> None:
        client = GuardClient(rows=[{'id': 'q1'}])
        cc._write(client, BUSINESS, self.PLAN, self.page(['1']), [{'id': 'q1', 'difficulty': 'easy'}], [])
        self.assertIn(('filter', ('topics', 'eq', '{"1"}')), client.log)

    def test_retire_refuses_while_a_page_uses_paper_topics(self) -> None:
        with self.assertRaisesRegex(SystemExit, 'still use them'):
            cc._retire_paper_topics(GuardClient(rows=[]), BUSINESS, self.page(['2']))

    def test_retire_refuses_for_non_question_page(self) -> None:
        client = GuardClient(rows=[{'id': 'stray'}])  # papers lookup and overlaps both return it
        with self.assertRaisesRegex(SystemExit, 'page stray still uses them'):
            cc._retire_paper_topics(client, BUSINESS, self.page(['4.3']))

    def test_verify_catches_mirror_and_tags(self) -> None:
        pages = {('p1', '1'): {'id': 'q1', 'topics': ['4.3'], 'difficulty': 'easy'}}
        problems = cc._verify(self.PLAN, (pages, [{'id': 'q1', 'difficulty': None}],
                                          [{'question_id': 'q1', 'topic': '1'}], []))
        self.assertEqual(len(problems), 2)
        clean = cc._verify(self.PLAN, (pages, [{'id': 'q1', 'difficulty': 'easy'}],
                                       [{'question_id': 'q1', 'topic': '4.3'}], []))
        self.assertEqual(clean, [])


class TopicCreation(unittest.TestCase):
    def test_only_used_chapters_created(self) -> None:
        client = FakeClient()
        created = cc._create_topics(client, BUSINESS, [{'code': '1.1'}], {'1.1', '4.3', '2.4'})
        self.assertEqual(created, 2)
        self.assertEqual(sorted(r['code'] for r in client.inserted), ['2.4', '4.3'])

    def test_pg_array_literal(self) -> None:
        self.assertEqual(cc._pg_array(['1', '2']), '{"1","2"}')
        self.assertEqual(cc._pg_array(None), '{}')


if __name__ == '__main__':
    unittest.main()
