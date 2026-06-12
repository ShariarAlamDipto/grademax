#!/usr/bin/env python3
"""Sub-question structure parser for Edexcel exam question text.

Given the plain text of one segmented question (PyMuPDF ``page.get_text()``
output, all pages of the question joined), extracts:

  * parts        — (a), (b), (c) … with per-part marks
  * subparts     — (i), (ii) … nested inside a part, with marks
  * total_marks  — from the "(Total for Question N is X marks)" fence
  * consistency  — whether detected part marks sum to the fence total

Edexcel layout facts this relies on (true across IGCSE/IAL papers):
  * Part labels are printed at the start of a line: "(a) Find …"
  * Per-part marks are printed right-aligned on their OWN line as "(2)" —
    PyMuPDF extracts them as a standalone line, which is what separates a
    marks marker from a "(2)" inside an equation.
  * The question fence is "(Total for Question N is X marks)".

Pure text → data; no I/O. Safe to use from any per-subject segment script.

Usage:
    from lib.subquestion_parser import parse_question_structure, structure_to_dict

    structure = parse_question_structure(question_text)
    manifest_entry["parts"] = structure_to_dict(structure)["parts"]
    manifest_entry["total_marks"] = structure.total_marks
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# Part labels (a)–(h). Stops before (i) which is a roman-numeral subpart.
_PART_RE = re.compile(r"^\s*\(([a-h])\)\s", re.MULTILINE)
# Roman-numeral subparts (i)–(x).
_SUBPART_RE = re.compile(r"^\s*\((i|ii|iii|iv|v|vi|vii|viii|ix|x)\)\s", re.MULTILINE)
# A marks marker: "(2)" alone on its line (Edexcel right-aligns these).
_MARKS_RE = re.compile(r"^\s*\((\d{1,2})\)\s*$")
# Question fence: "(Total for Question 5 is 9 marks)".
_TOTAL_RE = re.compile(
    r"\(\s*Total\s+for\s+Question\s+\d+\s+is\s+(\d+)\s+marks?\s*\)", re.IGNORECASE
)

_ROMAN_ORDER = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"]


@dataclass(frozen=True)
class SubPart:
    """A roman-numeral subpart, e.g. (ii) worth 3 marks."""

    label: str
    marks: Optional[int] = None


@dataclass(frozen=True)
class QuestionPart:
    """A lettered part, e.g. (b), with optional nested subparts."""

    label: str
    marks: Optional[int] = None
    subparts: tuple[SubPart, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class QuestionStructure:
    """Parsed structure of one exam question."""

    parts: tuple[QuestionPart, ...] = field(default_factory=tuple)
    total_marks: Optional[int] = None
    detected_marks_sum: Optional[int] = None
    # True/False when both totals known, None when either side is missing.
    is_consistent: Optional[bool] = None


def _is_plausible_next_part(label: str, seen_labels: list[str]) -> bool:
    """Reject out-of-sequence part letters (catches '(c)' inside formulas).

    Parts must appear in order: first part is (a); each later part is at most
    one letter past the highest seen so far. Repeats are allowed ("(b)
    continued" reprints happen on page joins) but skips are not.
    """
    if not seen_labels:
        return label == "a"
    highest = max(ord(l) for l in seen_labels)
    return ord(label) <= highest + 1


def _is_plausible_next_subpart(label: str, seen_labels: list[str]) -> bool:
    if not seen_labels:
        return label == "i"
    highest = max(_ROMAN_ORDER.index(l) for l in seen_labels)
    return _ROMAN_ORDER.index(label) <= highest + 1


def parse_question_structure(text: str) -> QuestionStructure:
    """Parse part/subpart/marks structure from one question's plain text."""
    if not text or not text.strip():
        return QuestionStructure()

    total_marks: Optional[int] = None
    total_match = _TOTAL_RE.search(text)
    if total_match:
        total_marks = int(total_match.group(1))

    # Mutable builders; frozen dataclasses are produced at the end.
    part_builders: list[dict] = []
    question_level_marks: list[int] = []
    seen_part_labels: list[str] = []

    for line in text.splitlines():
        marks_match = _MARKS_RE.match(line)
        if marks_match:
            marks = int(marks_match.group(1))
            if part_builders:
                current = part_builders[-1]
                if current["subparts"]:
                    sub = current["subparts"][-1]
                    if sub["marks"] is None:
                        sub["marks"] = marks
                    else:
                        current["direct_marks"].append(marks)
                else:
                    current["direct_marks"].append(marks)
            else:
                question_level_marks.append(marks)
            continue

        part_match = _PART_RE.match(line)
        if part_match:
            label = part_match.group(1)
            if _is_plausible_next_part(label, seen_part_labels):
                if label not in seen_part_labels:
                    seen_part_labels.append(label)
                    part_builders.append(
                        {"label": label, "direct_marks": [], "subparts": []}
                    )
                # A repeated label ("(b) continued") keeps the current builder.
                continue

        sub_match = _SUBPART_RE.match(line)
        if sub_match and part_builders:
            label = sub_match.group(1)
            current = part_builders[-1]
            seen_subs = [s["label"] for s in current["subparts"]]
            if _is_plausible_next_subpart(label, seen_subs) and label not in seen_subs:
                current["subparts"].append({"label": label, "marks": None})

    parts: list[QuestionPart] = []
    for builder in part_builders:
        subparts = tuple(
            SubPart(label=s["label"], marks=s["marks"]) for s in builder["subparts"]
        )
        sub_marks = [s.marks for s in subparts if s.marks is not None]
        direct = sum(builder["direct_marks"]) if builder["direct_marks"] else None
        if direct is not None and sub_marks:
            marks: Optional[int] = direct + sum(sub_marks)
        elif direct is not None:
            marks = direct
        elif sub_marks:
            marks = sum(sub_marks)
        else:
            marks = None
        parts.append(QuestionPart(label=builder["label"], marks=marks, subparts=subparts))

    known_part_marks = [p.marks for p in parts if p.marks is not None]
    if parts:
        detected_sum = sum(known_part_marks) if known_part_marks else None
        # Only trust the sum when every part has known marks.
        if len(known_part_marks) != len(parts):
            detected_sum = None
    else:
        detected_sum = sum(question_level_marks) if question_level_marks else None

    is_consistent: Optional[bool] = None
    if total_marks is not None and detected_sum is not None:
        is_consistent = total_marks == detected_sum

    return QuestionStructure(
        parts=tuple(parts),
        total_marks=total_marks,
        detected_marks_sum=detected_sum,
        is_consistent=is_consistent,
    )


def structure_to_dict(structure: QuestionStructure) -> dict:
    """JSON-serializable form for manifest.json / the pages.parts column."""
    return {
        "parts": [
            {
                "label": part.label,
                "marks": part.marks,
                "subparts": [
                    {"label": sub.label, "marks": sub.marks} for sub in part.subparts
                ],
            }
            for part in structure.parts
        ],
        "total_marks": structure.total_marks,
        "detected_marks_sum": structure.detected_marks_sum,
        "is_consistent": structure.is_consistent,
    }
