#!/usr/bin/env python3
"""Offline unit tests for scripts/lib/escalation_classifier.py.

Covers the keyword rung and LLM-response parsing — no network calls.

Run either way:
    python -m pytest tests/test_escalation_classifier.py
    python tests/test_escalation_classifier.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib.escalation_classifier import (  # noqa: E402
    EscalationClassifier,
    difficulty_from_marks,
)

CONFIG = {
    "topics": [
        {
            "id": "1",
            "name": "Forces and Motion",
            "description": "Speed velocity acceleration forces momentum",
            "keywords": ["acceleration", "velocity", "momentum", "resultant force"],
            "formulas": ["f = ma", "v = u + at"],
        },
        {
            "id": "2",
            "name": "Electricity",
            "description": "Current voltage resistance circuits",
            "keywords": ["current", "voltage", "resistor", "circuit"],
            "formulas": ["v = ir"],
        },
    ]
}


def make_classifier() -> EscalationClassifier:
    return EscalationClassifier(CONFIG, groq_api_key="test-key-never-used")


def test_keyword_rung_clear_match():
    clf = make_classifier()
    topics, confidence = clf.keyword_rung.classify(
        "A car accelerates from rest. Using F = ma, calculate the resultant force "
        "given the acceleration is 3 m/s^2 and the velocity after 5 s."
    )
    assert topics[0] == "1"
    assert confidence > 0.5


def test_keyword_rung_no_match():
    clf = make_classifier()
    topics, confidence = clf.keyword_rung.classify("Completely unrelated prose.")
    assert topics == ()
    assert confidence == 0.0


def test_keyword_rung_ambiguous_text_low_confidence():
    clf = make_classifier()
    # One weak hit for each topic — decisiveness should be low.
    _, confidence = clf.keyword_rung.classify(
        "The velocity of electrons gives rise to a current."
    )
    assert confidence < 0.75  # must NOT be accepted by the keyword rung


def test_parse_llm_json_valid():
    clf = make_classifier()
    result = clf._parse_llm_json(
        '{"topics": ["2", "1"], "difficulty": "hard", "confidence": 0.9}',
        "text_llm",
        None,
    )
    assert result is not None
    assert result.topic_ids == ("2", "1")
    assert result.difficulty == "hard"
    assert result.confidence == 0.9
    assert result.tier == "text_llm"


def test_parse_llm_json_rejects_unknown_topic_ids():
    clf = make_classifier()
    result = clf._parse_llm_json(
        '{"topics": ["99"], "difficulty": "easy", "confidence": 0.8}', "text_llm", None
    )
    assert result is None  # no valid topics survive filtering


def test_parse_llm_json_bad_payloads():
    clf = make_classifier()
    assert clf._parse_llm_json(None, "text_llm", None) is None
    assert clf._parse_llm_json("not json at all", "text_llm", None) is None
    assert clf._parse_llm_json("{}", "text_llm", None) is None


def test_parse_llm_json_clamps_confidence_and_difficulty():
    clf = make_classifier()
    result = clf._parse_llm_json(
        '{"topics": ["1"], "difficulty": "extreme", "confidence": 7}',
        "vision",
        "medium",
    )
    assert result is not None
    assert result.confidence == 1.0
    assert result.difficulty == "medium"  # fallback used for invalid value


def test_difficulty_from_marks():
    assert difficulty_from_marks(None) is None
    assert difficulty_from_marks(2) == "easy"
    assert difficulty_from_marks(5) == "medium"
    assert difficulty_from_marks(9) == "hard"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"  FAIL {name}: {exc}")
    print(f"\n{'OK' if failures == 0 else f'{failures} FAILURE(S)'}")
    sys.exit(1 if failures else 0)
