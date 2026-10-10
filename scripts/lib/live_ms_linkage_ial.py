"""
IAL (P1-P4, S1, M1) evidence for the live mark-scheme linkage gate.

lib.live_ms_linkage reads what IGCSE files print about themselves. IAL files
print the same two facts in other words, so its reader saw neither and the
first IAL audit (2026-10-07) called most pairs LABEL_ONLY:

  question paper  "3." in the left margin opens the question and, before 2022,
                  "(Total 5 marks)" closes it with no number (2022+ prints
                  "(Total for Question 3 is 5 marks)", already read).
  mark scheme     the number in the Question Number column ("3.(a)", already
                  read as a label) and "(5 marks)" closing the block.

This module adds both readings to the Evidence the shared judge consumes, so
an IAL pair is PROVEN by the same rule as every other subject: the number AND
the marks agree on both sides. `install()` swaps the reader in for the audit
and the rebuild gate; nothing else changes.
"""

from __future__ import annotations

import dataclasses
import re
import sys
from pathlib import Path

import fitz

import lib.live_ms_linkage as linkage
from lib.ial_qp_parse import read_paper

# A scheme block's own closing total, alone on its line: "(5 marks)".
MS_BLOCK_TOTAL_RE = re.compile(r"^\(\s*(\d{1,3})\s*marks?\s*\)$", re.I)

_shared_read_evidence = linkage.read_evidence


def _qp_totals(path: Path) -> tuple[tuple[int, int], ...]:
    """
    (question, marks) for a pre-2022 question file: the numbers the file's
    pages open or continue, paired with its bare "(Total M marks)" fences.
    A file holding two questions yields two entries, which the judge reads as
    QP_BUNDLED; a file whose question prints no fence yields nothing.
    """
    facts = read_paper(path)
    if any(f.numbered_fences for f in facts):
        return ()
    numbers: list[int] = []
    for f in facts:
        for n in (f.starts, f.continues):
            if n is not None and n not in numbers:
                numbers.append(n)
    fences = [m for f in facts for m in f.bare_fences]
    if len(numbers) == 1 and len(fences) == 1:
        return ((numbers[0], fences[0]),)
    if len(numbers) > 1:
        # Marks are unknown per question; 0 never matches a scheme, and the
        # judge stops at the bundle before comparing marks anyway.
        return tuple((n, 0) for n in numbers)
    return ()


def _ms_block_totals(path: Path) -> tuple[int, ...]:
    found: list[int] = []
    with fitz.open(path) as doc:
        for page in doc:
            for line in page.get_text().splitlines():
                match = MS_BLOCK_TOTAL_RE.match(line.strip())
                if match:
                    found.append(int(match.group(1)))
    return tuple(found)


def read_evidence_ial(path: Path, *, is_ms: bool) -> linkage.Evidence:
    evidence = _shared_read_evidence(path, is_ms=is_ms)
    if not is_ms:
        if evidence.totals:
            return evidence
        return dataclasses.replace(evidence, totals=_qp_totals(path))
    if evidence.totals or evidence.tallies:
        return evidence
    return dataclasses.replace(evidence, tallies=_ms_block_totals(path))


def install() -> None:
    """Use the IAL reader in the audit and (if loaded) the rebuild gate."""
    linkage.read_evidence = read_evidence_ial
    # The gate imported the reader by name; patch it only where already loaded
    # (importing it here would install its fitz/ms_bands hooks in the audit).
    common = sys.modules.get("lib.live_rebuild_common")
    if common is not None:
        common.read_evidence = read_evidence_ial
