"""Regression checks for finishing a Maths A review without external writes."""

import hashlib
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import classify_mathsa_tool_topics as subject


class ReviewRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.stage = Path(self.temp.name)
        self.keys = [f"2026_may-jun_1H|{n}" for n in range(1, 4)]
        rows = []
        for n in range(1, 4):
            qp = self.stage / f"q{n}.pdf"
            with fitz.open() as doc:
                doc.new_page().insert_text((50, 50),
                    f"{n} Work out the requested value. Show all working clearly. "
                    f"(Total for Question {n} is 3 marks)")
                doc.save(qp)
            rows.append({"paper": "2026_may-jun_1H", "question": n,
                         "marks": 3, "qp": str(qp)})
        self.write("verdicts.json", {"rows": rows})
        self.write("topics_new.json", {self.keys[0]: ["1.2"]})
        self.write("topic_sources.json", {self.keys[0]: "workbook"})
        self.write("topic_reads.json", {self.keys[1]: ["4.10"]})
        self.write("topic_model_cache.json", {
            f"2026_may-jun_1H:{n}": {
                "a": {"primary": "4.9", "secondary": []},
                "b": {"primary": "4.9", "secondary": []}}
            for n in (2, 3)})
        self.write("topic_read_notes.json", {self.keys[1]: {
            "tags": ["4.10"], "qp_sha256": hashlib.sha256(
                (self.stage / "q2.pdf").read_bytes()).hexdigest()}})

    def write(self, name, value):
        (self.stage / name).write_text(json.dumps(value), encoding="utf-8")

    def run_review(self):
        with ExitStack() as stack:
            for name, filename in {
                "CACHE": "topic_model_cache.json", "READS": "topic_reads.json",
                "READ_NOTES": "topic_read_notes.json", "OUT": "topics_new.json",
                "RECORD": "topic_sources.json"}.items():
                stack.enter_context(patch.object(subject, name, self.stage / filename))
            stack.enter_context(patch.object(subject, "STAGE", self.stage))
            stack.enter_context(patch.object(sys, "argv", ["classify", "--review-only"]))
            for name in ("model_pass", "supabase_client", "workbook_index"):
                stack.enter_context(patch.object(subject, name,
                    side_effect=AssertionError(f"External call: {name}")))
            stack.enter_context(redirect_stdout(StringIO()))
            return subject.main()

    def test_offline_review_overrides_models_and_preserves_workbook_match(self):
        self.assertEqual(self.run_review(), 0)
        topics = json.loads((self.stage / "topics_new.json").read_text())
        self.assertEqual(topics, dict(zip(self.keys, [["1.2"], ["4.10"], ["4.9"]])))
        self.assertEqual(json.loads((self.stage / "topic_sources.json").read_text()),
                         dict(zip(self.keys, ["workbook", "reviewed", "agreed"])))
        self.assertEqual(self.run_review(), 0)  # repeat without losing workbook tags

    def test_changed_question_invalidates_read_without_replacing_outputs(self):
        original = (self.stage / "topics_new.json").read_bytes()
        self.write("topic_read_notes.json", {self.keys[1]: {
            "tags": ["4.10"], "qp_sha256": "old-artifact"}})
        with self.assertRaisesRegex(ValueError, "changed since topic review"):
            self.run_review()
        self.assertEqual((self.stage / "topics_new.json").read_bytes(), original)

    def test_invalid_decisions_cannot_replace_completed_output(self):
        original = (self.stage / "topics_new.json").read_bytes()
        for value in (["4.99"], [], ["4.4"], ["4.9", "4.9"], "4.9"):
            with self.subTest(value=value):
                self.write("topic_reads.json", {self.keys[1]: value})
                with self.assertRaises(ValueError):
                    self.run_review()
                self.assertEqual((self.stage / "topics_new.json").read_bytes(), original)
        self.write("topic_reads.json", {"absent_paper|1": ["4.9"]})
        with self.assertRaisesRegex(ValueError, "Unknown question"):
            self.run_review()

    def test_unresolved_model_disagreement_returns_failure_and_no_guess(self):
        cache = json.loads((self.stage / "topic_model_cache.json").read_text())
        cache["2026_may-jun_1H:3"]["b"]["primary"] = "4.10"
        self.write("topic_model_cache.json", cache)
        self.assertEqual(self.run_review(), 1)
        self.assertNotIn(self.keys[2], json.loads((self.stage / "topics_new.json").read_text()))


if __name__ == "__main__":
    unittest.main()
