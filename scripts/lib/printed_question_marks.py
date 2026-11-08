"""
Read each question's marks from the totals Pearson prints on the question paper.

Every live question segment is read in this order, and the first source that
answers wins:

1. The PDF text: "(Total for Question 7 is 6 marks)" (IGCSE and newer IAL)
   or "Q7 (Total 10 marks)" (IAL). The number must be this question's own.
2. OCR of the pages, for scans and PDFs whose fonts decode to garbage, with
   the same two patterns plus the old "(Total Question 6 = 6 marks)".
3. OCR of the right-hand margin, adding up the part marks "(3)". Old IAL
   papers (about 2014-2017) print no question totals, only part marks.

Source 3 is a sum of OCR'd numbers, so it is accepted only when the whole
paper is read and its questions add up exactly to a valid total for the paper
(`paper_total_ok`). Sources 1 and 2 are also checked against the paper total
whenever the whole paper is live.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

# "(Total for Question 7 is 6 marks)", "Total for Question 3 = 4 marks"
_LABELLED_IGCSE = re.compile(
    r"Total\s+for\s+Question\s+(\d+)\s*(?:is|=|:)?\s*(\d+)\s*marks?", re.I)
# "Q7 (Total 10 marks)"
_LABELLED_IAL = re.compile(
    r"\bQ\s?(\d+)\s*\(\s*Total\s*(?:is\s*)?(\d+)\s*marks?\s*\)", re.I)
# "(Total Question 6 = 6 marks)" -- old Human Biology
_LABELLED_OLD = re.compile(
    r"Total\s+Question\s+(\d+)\s*=\s*(\d+)\s*marks?", re.I)
# "(Total 6 marks)" with no question number
_UNLABELLED = re.compile(r"\(\s*Total\s*(?:is\s*)?(\d+)\s*marks?\s*\)", re.I)
# A part mark as printed in the margin: "(3)"
_PART_MARK = re.compile(r"\((\d{1,2})\)")

# Valid whole-paper totals per subject, from the specifications (old and new
# specification where both are live). Used to accept OCR part-mark sums.
PAPER_TOTALS: Mapping[str, frozenset[int]] = {
    "4PH1": frozenset({110, 70, 120, 60}),
    "4CH1": frozenset({110, 70, 120, 60}),
    "4BI1": frozenset({110, 70, 120, 60}),
    "4HB1": frozenset({90, 120, 60}),
    "4MA1": frozenset({100}),
    "4MB1": frozenset({100}),
    "4PM1": frozenset({100}),
    "4AC1": frozenset({100}),
    "4BS1": frozenset({80}),
    "4EC1": frozenset({80}),
    "4CP1": frozenset({80}),
    "WMA11": frozenset({75}),
    "WMA12": frozenset({75}),
    "WMA13": frozenset({75}),
    "WMA14": frozenset({75}),
    "WME01": frozenset({75}),
    "WST01": frozenset({75}),
}

MAX_QUESTION_MARKS = 40


def question_digits(question_number: str | None) -> str:
    """'Q07' -> '7'; '12' -> '12'."""
    digits = re.sub(r"\D", "", str(question_number or ""))
    return digits.lstrip("0") or digits


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def labelled_marks(text: str, question_number: str) -> int | None:
    """This question's printed total, or None when absent or contradictory."""
    want = question_digits(question_number)
    found = {
        int(marks)
        for pattern in (_LABELLED_IGCSE, _LABELLED_IAL, _LABELLED_OLD)
        for number, marks in pattern.findall(text)
        if number.lstrip("0") == want
    }
    return found.pop() if len(found) == 1 else None


def unlabelled_marks(text: str) -> int | None:
    """A lone "(Total N marks)", only when no numbered total is on the pages."""
    if any(p.search(text) for p in (_LABELLED_IGCSE, _LABELLED_IAL, _LABELLED_OLD)):
        return None
    found = {int(m) for m in _UNLABELLED.findall(text)}
    return found.pop() if len(found) == 1 else None


def part_marks_sum(text: str) -> int | None:
    parts = [int(m) for m in _PART_MARK.findall(text)]
    return sum(parts) if parts else None


def plausible(marks: int | None) -> bool:
    return marks is not None and 0 < marks <= MAX_QUESTION_MARKS


def is_whole_paper(question_numbers: Iterable[str]) -> bool:
    """True when the live questions are exactly Q1..Qn."""
    nums = sorted(int(question_digits(q) or 0) for q in question_numbers)
    return nums == list(range(1, len(nums) + 1))


def paper_total_ok(code: str, marks: Iterable[int],
                   printed_total: int | None = None) -> bool:
    total = sum(marks)
    if printed_total is not None:
        return total == printed_total
    return total in PAPER_TOTALS.get(code, frozenset())


_PAPER_TOTAL = re.compile(r"TOTAL\s+FOR\s+PAPER\s*(?:IS|=|:)?\s*(\d+)\s*MARKS", re.I)


def printed_paper_total(text: str) -> int | None:
    found = {int(m) for m in _PAPER_TOTAL.findall(text)}
    return found.pop() if len(found) == 1 else None
