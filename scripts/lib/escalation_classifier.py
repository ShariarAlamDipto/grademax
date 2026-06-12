#!/usr/bin/env python3
"""Escalation-ladder topic classifier: keyword → strong text LLM → vision.

Replaces the single-weak-model approach (llama-3.1-8b on a 500-char excerpt)
with three rungs, each only invoked when the cheaper one below it is not
confident enough:

  Rung 1  KEYWORD   free, instant. Keyword/formula/synonym scorer built from
                    the subject topics YAML. Accepts when score-derived
                    confidence >= keyword_accept (default 0.75).
  Rung 2  TEXT LLM  Groq llama-3.3-70b-versatile on the FULL question text
                    (not a 500-char excerpt). Accepts when the model's own
                    confidence >= llm_accept (default 0.55).
  Rung 3  VISION    Groq llama-4-scout on a rendered page image. Used when
                    rung 2 is unconfident, the text is too short to mean
                    anything (< min_text_chars), or has_diagram is set.

Per-subject scripts stay separate (one dedicated script per subject — see
project convention); they import this module and supply their own YAML config:

    import yaml
    from lib.escalation_classifier import EscalationClassifier

    config = yaml.safe_load(open("config/chemistry_topics.yaml", encoding="utf-8"))
    clf = EscalationClassifier(config, groq_api_key=os.environ["GROQ_API_KEY"])
    result = clf.classify(full_text, pdf_path=Path("data/.../q3.pdf"))
    # result.topic_ids -> ranked list, e.g. ["3", "1"]
    # result.tier      -> "keyword" | "text_llm" | "vision" | "none"

Expected YAML shape (same as reclassify_chem_bio.py):
    topics:
      - id: "1"
        name: Atomic Structure
        description: ...
        keywords: [...]
        formulas: [...]      # optional
        synonyms: [...]      # optional
    negatives: [...]         # optional
"""

from __future__ import annotations

import base64
import json
import re
import time
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Optional

TEXT_MODEL = "llama-3.3-70b-versatile"
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
MAX_TEXT_CHARS = 6000
DIFFICULTIES = ("easy", "medium", "hard")


@dataclass(frozen=True)
class ClassificationResult:
    """Outcome of one classify() call."""

    topic_ids: tuple[str, ...] = field(default_factory=tuple)  # ranked, primary first
    difficulty: Optional[str] = None
    confidence: float = 0.0
    tier: str = "none"  # which rung produced the result


def difficulty_from_marks(total_marks: Optional[int]) -> Optional[str]:
    """Cheap difficulty heuristic from the question's total marks."""
    if total_marks is None:
        return None
    if total_marks <= 3:
        return "easy"
    if total_marks <= 6:
        return "medium"
    return "hard"


class _KeywordRung:
    """Keyword/formula/synonym scorer built from the subject YAML config."""

    def __init__(self, config: dict):
        self.valid_ids = {str(t["id"]) for t in config["topics"]}
        self.keyword_index: dict[str, list[tuple[str, float]]] = {}
        for topic in config["topics"]:
            tid = str(topic["id"])
            for kw in topic.get("keywords", []):
                self.keyword_index.setdefault(kw.lower(), []).append((tid, 3.0))
            for f in topic.get("formulas", []):
                self.keyword_index.setdefault(f.lower(), []).append((tid, 5.0))
            for s in topic.get("synonyms", []):
                self.keyword_index.setdefault(s.lower(), []).append((tid, 2.0))
            for word in topic.get("description", "").lower().split():
                word = re.sub(r"[^a-z0-9]", "", word)
                if len(word) > 4:
                    self.keyword_index.setdefault(word, []).append((tid, 0.5))

    def classify(self, text: str) -> tuple[tuple[str, ...], float]:
        """Returns (ranked topic ids, confidence in [0,1])."""
        text_lower = text.lower()
        scores: dict[str, float] = {}
        for term, hits in self.keyword_index.items():
            if term in text_lower:
                for tid, weight in hits:
                    scores[tid] = scores.get(tid, 0.0) + weight
        if not scores:
            return (), 0.0

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        top_score = ranked[0][1]
        runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
        # Confidence = how decisively the top topic beats the runner-up,
        # damped when the absolute evidence is thin.
        margin = (top_score - runner_up) / top_score if top_score > 0 else 0.0
        evidence = min(top_score / 10.0, 1.0)
        confidence = round(margin * 0.6 + evidence * 0.4, 3)
        topics = tuple(tid for tid, s in ranked[:3] if s >= top_score * 0.4)
        return topics, confidence


class EscalationClassifier:
    """Three-rung classifier. Construct once per subject, reuse across pages."""

    def __init__(
        self,
        topics_config: dict,
        groq_api_key: str,
        *,
        keyword_accept: float = 0.75,
        llm_accept: float = 0.55,
        min_text_chars: int = 120,
        max_retries: int = 4,
    ):
        self.config = topics_config
        self.valid_ids = {str(t["id"]) for t in topics_config["topics"]}
        self.keyword_rung = _KeywordRung(topics_config)
        self.keyword_accept = keyword_accept
        self.llm_accept = llm_accept
        self.min_text_chars = min_text_chars
        self.max_retries = max_retries
        self._groq_api_key = groq_api_key
        self._groq_client = None  # lazy — keyword rung needs no SDK
        self._topic_listing = "\n".join(
            f"  {t['id']}: {t['name']} — {t.get('description', '')[:140]}"
            for t in topics_config["topics"]
        )

    # ── public API ────────────────────────────────────────────────────────────

    def classify(
        self,
        text: str,
        *,
        pdf_path: Optional[Path] = None,
        has_diagram: bool = False,
        total_marks: Optional[int] = None,
    ) -> ClassificationResult:
        """Classify one question. Escalates only as far as needed."""
        text = (text or "").strip()
        fallback_difficulty = difficulty_from_marks(total_marks)

        # Rung 1 — keyword (skip when there is barely any text to score)
        if len(text) >= self.min_text_chars:
            topics, confidence = self.keyword_rung.classify(text)
            if topics and confidence >= self.keyword_accept:
                return ClassificationResult(
                    topic_ids=topics,
                    difficulty=fallback_difficulty,
                    confidence=confidence,
                    tier="keyword",
                )

        # Rung 2 — strong text LLM on the full text
        text_result: Optional[ClassificationResult] = None
        if len(text) >= self.min_text_chars:
            text_result = self._classify_text_llm(text, fallback_difficulty)
            if text_result and text_result.confidence >= self.llm_accept and not has_diagram:
                return text_result

        # Rung 3 — vision, when we have a PDF and a reason to look at it
        needs_vision = pdf_path is not None and (
            has_diagram
            or len(text) < self.min_text_chars
            or text_result is None
            or text_result.confidence < self.llm_accept
        )
        if needs_vision:
            vision_result = self._classify_vision(pdf_path, fallback_difficulty)
            if vision_result and vision_result.confidence >= (
                text_result.confidence if text_result else 0.0
            ):
                return vision_result

        if text_result and text_result.topic_ids:
            return text_result
        return ClassificationResult(difficulty=fallback_difficulty)

    # ── rung 2: text LLM ──────────────────────────────────────────────────────

    def _classify_text_llm(
        self, text: str, fallback_difficulty: Optional[str]
    ) -> Optional[ClassificationResult]:
        prompt = (
            "You are classifying one Edexcel exam question into syllabus topics.\n"
            f"Topics:\n{self._topic_listing}\n\n"
            f"Question text:\n---\n{text[:MAX_TEXT_CHARS]}\n---\n\n"
            "Reply with JSON only:\n"
            '{"topics": ["<primary topic id>", "<secondary id if clearly relevant>"],'
            ' "difficulty": "easy"|"medium"|"hard", "confidence": 0.0-1.0}\n'
            "Use ids from the list verbatim. List at most 3 topics, most relevant first."
        )
        raw = self._groq_chat(
            model=TEXT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
        )
        return self._parse_llm_json(raw, "text_llm", fallback_difficulty)

    # ── rung 3: vision ────────────────────────────────────────────────────────

    def _classify_vision(
        self, pdf_path: Path, fallback_difficulty: Optional[str]
    ) -> Optional[ClassificationResult]:
        b64 = self._render_first_page_b64(pdf_path)
        if not b64:
            return None
        prompt = (
            "This is one Edexcel exam question (may include diagrams).\n"
            f"Classify it into these syllabus topics:\n{self._topic_listing}\n\n"
            "Reply with JSON only:\n"
            '{"topics": ["<primary topic id>"], "difficulty": "easy"|"medium"|"hard",'
            ' "confidence": 0.0-1.0}'
        )
        raw = self._groq_chat(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        },
                    ],
                }
            ],
            max_tokens=150,
        )
        return self._parse_llm_json(raw, "vision", fallback_difficulty)

    # ── shared plumbing ───────────────────────────────────────────────────────

    def _client(self):
        if self._groq_client is None:
            from groq import Groq  # lazy: keyword-only use needs no SDK

            self._groq_client = Groq(api_key=self._groq_api_key)
        return self._groq_client

    def _groq_chat(self, *, model: str, messages: list, max_tokens: int) -> Optional[str]:
        for attempt in range(self.max_retries):
            try:
                resp = self._client().chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )
                return resp.choices[0].message.content
            except Exception as exc:  # noqa: BLE001 — backoff on 429/5xx, then give up
                wait = 2.0 ** (attempt + 1)
                if "429" in str(exc) or "rate" in str(exc).lower():
                    time.sleep(wait)
                    continue
                if attempt + 1 < self.max_retries:
                    time.sleep(wait)
                    continue
                return None
        return None

    def _parse_llm_json(
        self, raw: Optional[str], tier: str, fallback_difficulty: Optional[str]
    ) -> Optional[ClassificationResult]:
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None

        raw_topics = data.get("topics") or []
        if isinstance(raw_topics, str):
            raw_topics = [raw_topics]
        topics = tuple(
            str(t).strip() for t in raw_topics if str(t).strip() in self.valid_ids
        )[:3]

        difficulty = data.get("difficulty")
        if difficulty not in DIFFICULTIES:
            difficulty = fallback_difficulty

        try:
            confidence = max(0.0, min(1.0, float(data.get("confidence", 0.0))))
        except (TypeError, ValueError):
            confidence = 0.0

        if not topics:
            return None
        return ClassificationResult(
            topic_ids=topics, difficulty=difficulty, confidence=confidence, tier=tier
        )

    @staticmethod
    def _render_first_page_b64(pdf_path: Path, dpi: int = 140) -> Optional[str]:
        try:
            import fitz  # lazy: only the vision rung renders pages
        except ImportError:
            return None
        try:
            doc = fitz.open(str(pdf_path))
            try:
                if len(doc) == 0:
                    return None
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                pix = doc[0].get_pixmap(matrix=mat)
                buf = BytesIO(pix.tobytes("png"))
                return base64.b64encode(buf.getvalue()).decode()
            finally:
                doc.close()
        except Exception:  # noqa: BLE001 — unreadable PDF is a skip, not a crash
            return None
