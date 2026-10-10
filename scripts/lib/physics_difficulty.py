"""Score how hard an Edexcel IGCSE Physics question part is, from its mark scheme.

Edexcel does not publish per-question candidate statistics, so real difficulty --
the mean mark a cohort actually scored -- is not available anywhere in the
archive. What IS available is the mark scheme, and it leaks a great deal about
where marks get lost:

  * "substitution; rearrangement; evaluation;" is the examiner's own statement
    that the calculation takes three separate steps.
  * a "reject ..." note exists because enough candidates wrote that exact wrong
    thing to be worth telling examiners about.
  * "ECF" means the part depends on an earlier answer, so an early slip
    propagates.
  * "any two from:" followed by five options is generous, not hard.
  * the levels-of-response grid on a six-mark question is the top-grade
    discriminator on the paper.

So this scores those observable features rather than guessing. It is a model of
difficulty, not a measurement of it, and the tier names say what the score is
for: how much revision attention the question deserves.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Command words, grouped by what they actually demand of a candidate.
COMMANDS: dict[str, tuple[str, int]] = {
    "state": ("recall", 0),
    "give": ("recall", 0),
    "name": ("recall", 0),
    "write": ("recall", 0),
    "identify": ("recall", 0),
    "complete": ("recall", 0),
    "draw": ("apply", 1),
    "add": ("apply", 1),
    "use": ("apply", 1),
    "describe": ("describe", 1),
    "compare": ("describe", 2),
    "calculate": ("calculate", 1),
    "determine": ("calculate", 2),
    "estimate": ("calculate", 2),
    "show that": ("calculate", 2),
    "explain": ("explain", 2),
    "suggest": ("explain", 3),
    "evaluate": ("explain", 3),
    "deduce": ("explain", 3),
    "plan": ("explain", 3),
    "devise": ("explain", 3),
}

_STEP_RE = re.compile(r"\b(substitution|rearrangement|evaluation|conversion)\b", re.I)
_MENU_RE = re.compile(r"any\s+(one|two|three|four|\d+)\s+(from|of)", re.I)
_LEVELS_RE = re.compile(r"\b(level\s*[123]|indicative content|six marks as distributed)\b", re.I)
_REJECT_RE = re.compile(r"\b(reject|do not (accept|credit))\b", re.I)
_ECF_RE = re.compile(r"\bECF\b", re.I)
_POT_RE = re.compile(r"\b(POT|power of ten|standard form)\b", re.I)
_CONVERT_RE = re.compile(
    r"(× *10|x *10|convert|÷ *1000|/ *1000|\bcm\b.*\bm\b|\bkm\b|\bminutes?\b.*\bs\b|kW ?h)", re.I
)

# Cut points chosen against the measured score distribution over the 2018-2025
# corpus, so each tier holds a share that matches what it claims to be:
#   0-1 -> 37% of parts, 2-4 -> 45%, 5-6 -> 14%, 7+ -> 4%.
# An earlier, looser set put half the paper in "banker", which would have told a
# student the exam is easier than it is.
TIERS = (
    (0, 1, "banker", "Guaranteed marks — learn these to a reflex"),
    (2, 4, "routine", "Standard marks — the bulk of every paper"),
    (5, 6, "discriminator", "Where grades separate — practise deliberately"),
    (7, 99, "top-grade", "The hardest marks on the paper — attempt last"),
)


@dataclass(frozen=True)
class Difficulty:
    score: int
    tier: str
    label: str
    command: str
    steps: int
    reasons: tuple[str, ...]


def command_of(stem: str) -> tuple[str, int]:
    """Classify the stem by its command word, taking the first one that appears."""
    low = stem.lower()
    best: tuple[int, str, int] | None = None
    for word, (family, weight) in COMMANDS.items():
        at = low.find(word)
        if at >= 0 and (best is None or at < best[0]):
            best = (at, family, weight)
    return (best[1], best[2]) if best else ("other", 1)


def _tier(score: int) -> tuple[str, str]:
    for lo, hi, tier, label in TIERS:
        if lo <= score <= hi:
            return tier, label
    return TIERS[-1][2], TIERS[-1][3]


def score_part(stem: str, answer: str, notes: str, tariff: int | None) -> Difficulty:
    """Rate one question part from its stem and its mark scheme cell."""
    family, cmd_weight = command_of(stem)
    text = f"{answer} {notes}"
    reasons: list[str] = []

    marks = tariff or 1
    score = max(0, marks - 1)
    if marks >= 4:
        reasons.append(f"{marks}-mark answer")

    score += cmd_weight
    if cmd_weight >= 2:
        reasons.append(f"'{family}' command word")

    steps = len({m.lower() for m in _STEP_RE.findall(answer)})
    if steps >= 3:
        score += 2
        reasons.append("multi-step calculation (substitute, rearrange, evaluate)")
    elif steps == 2:
        score += 1

    if _CONVERT_RE.search(text) or _POT_RE.search(text):
        score += 1
        reasons.append("unit conversion or power-of-ten trap")
    if _ECF_RE.search(notes):
        score += 1
        reasons.append("carries forward from an earlier answer")
    if _REJECT_RE.search(notes):
        score += 1
        reasons.append("mark scheme names a common wrong answer")
    if _LEVELS_RE.search(text):
        score += 4
        reasons.append("levels-of-response extended answer")
    if _MENU_RE.search(answer):
        score -= 1
        reasons.append("credit from a menu of acceptable points")

    score = max(0, score)
    tier, label = _tier(score)
    return Difficulty(score, tier, label, family, steps, tuple(reasons))
