"""Question fingerprinting for near-duplicate / template detection."""
from __future__ import annotations
import re

_STOP = {"the", "a", "an", "of", "to", "and", "in", "is", "for", "on", "with",
         "that", "this", "find", "given", "show", "calculate", "work", "out"}


def _tokens(s: str) -> set[str]:
    words = re.findall(r"[a-z]+", (s or "").lower())
    return {w for w in words if len(w) > 2 and w not in _STOP}


def token_set(record: dict) -> set[str]:
    """Skill/concept token set used for similarity. Built from structured fields,
    not raw prose, so it captures *what is tested* rather than surface wording."""
    toks: set[str] = set()
    toks |= {f"topic:{t}" for t in record.get("topics", [])}
    toks |= {f"cmd:{c.lower()}" for c in record.get("command_words", [])}
    for s in record.get("skills", []) or []:
        toks |= {f"skill:{w}" for w in _tokens(s)}
    for s in record.get("formulae", []) or []:
        toks |= {f"f:{w}" for w in _tokens(s)}
    if record.get("context_tag"):
        toks |= {f"ctx:{w}" for w in _tokens(record["context_tag"])}
    return toks


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def signature(record: dict) -> str:
    """Compact human-readable signature: primary topic + sorted command words + marks band."""
    topic = record.get("primary_topic") or "?"
    cmds = ",".join(sorted({c.lower() for c in record.get("command_words", [])}))
    marks = record.get("marks_total") or 0
    band = "lo" if marks <= 4 else ("mid" if marks <= 8 else "hi")
    return f"{topic}|{cmds}|{band}"
