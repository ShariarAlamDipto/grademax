"""Build the joined question + mark scheme corpus for Edexcel IGCSE Physics.

Reads the original whole-paper PDFs rather than the segmented per-question ones:
segmentation on this subject was done by vision and mislays whole questions,
whereas the source papers carry their own arithmetic ("Total for Question 4 = 9
marks") which lets every parse be checked before it is used.

A question is admitted to the corpus only when its parsed marks reconcile with
that printed total. Anything that does not reconcile is reported, not silently
included, because a mark scheme quoted to a student a fortnight before an exam
has to be right.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .physics_difficulty import Difficulty, score_part
from .physics_ms_parse import parse_ms
from .physics_qp_parse import index_stems, parse_qp

FILE_RE = re.compile(
    r"Physics_(\d{4})_([A-Za-z-]+)_Paper_(\d)(R?)_QP\.pdf$", re.I
)
SESSION_ORDER = {"Jan": 0, "May-Jun": 1, "Oct-Nov": 2, "Specimen": 3}

# 4PH1 was first sat in June 2019; everything before that is the legacy 4PH0
# paper. The content overlaps heavily but the paper structure does not, so the
# two are labelled and can be counted separately.
FIRST_4PH1 = (2019, "May-Jun")

# Splitting a mark scheme cell on ';' gives the individual creditable points --
# that is Edexcel's own convention, one semicolon per available mark.
_POINT_SPLIT = re.compile(r";+")
_EG_RE = re.compile(r"^\s*e\.?g\.?\s*[:.]?\s*", re.I)

# On a multiple-choice question the scheme prints the key, then a paragraph saying
# why each other option is wrong. That paragraph is worth reading but it is not a
# creditable point, and listing it as one tells a student to write it down.
_DISTRACTOR = re.compile(
    r"\b[A-D]\b.{0,40}?\b(?:is|are|cannot be|can not be)\s+"
    r"(?:incorrect|correct|the only|not)\b"
    r"|\b(?:is incorrect|are incorrect|cannot be correct|is the only|this is the)\b",
    re.I,
)
_RESIDUE = re.compile(
    r"^\W*(?:answer|notes|marks|total\b.*|question\b.*)\W*$|^\W*$|[·|]\s*(?:MS|QP)\b",
    re.I,
)
# "any two from:" heads a menu of alternatives, so several lines for one mark is
# correct there and must not be collapsed.
_MENU = re.compile(r"\bany\s+(?:one|two|three|four|five|\d+)\b", re.I)


@dataclass
class QPart:
    paper_id: str
    year: int
    session: str
    paper: str
    variant: str
    spec: str
    q: int
    part: str
    stem: str
    tariff: int | None
    points: list[str]
    notes: str
    menu: bool = False
    difficulty: Difficulty = field(default=None)  # type: ignore[assignment]

    @property
    def ref(self) -> str:
        return f"Q{self.q}{self.part}"

    @property
    def sitting(self) -> str:
        return f"{self.session} {self.year} Paper {self.paper}{self.variant}"


def _spec_of(year: int, session: str) -> str:
    if (year, session) >= FIRST_4PH1 or year > FIRST_4PH1[0]:
        return "4PH1"
    if year == FIRST_4PH1[0] and SESSION_ORDER.get(session, 9) >= SESSION_ORDER["May-Jun"]:
        return "4PH1"
    return "4PH0"


def _points(answer: str, tariff: int | None) -> tuple[list[str], str, bool]:
    """Split a mark scheme answer cell into (creditable points, commentary, is_menu).

    A one-mark answer cannot have two separate creditable points, so when the split
    leaves several the semicolon belonged to the answer rather than between answers
    -- a fraction set over two lines, or an either/or. Those are rejoined, unless
    the scheme heads them with "any one from", where the list really is a menu.
    """
    points: list[str] = []
    aside: list[str] = []
    for chunk in _POINT_SPLIT.split(answer):
        chunk = re.sub(r"\s+", " ", _EG_RE.sub("", chunk)).strip(" .,")
        if len(chunk) < 2 or _RESIDUE.match(chunk):
            continue
        (aside if _DISTRACTOR.search(chunk) else points).append(chunk)

    menu = bool(_MENU.search(answer))
    if tariff == 1 and len(points) > 1 and not menu:
        points = [" / ".join(points)]
    return points, " ".join(aside), menu


def _clean_stem(text: str) -> str:
    text = re.sub(r"\s+", " ", text.replace("\t", " ")).strip()
    return re.sub(r"\s+([,.;:?])", r"\1", text)


def build_corpus(
    archive: Path, from_year: int = 2018, to_year: int = 2025
) -> tuple[list[QPart], list[str], list[str]]:
    """Return (parts, report lines, per-question reconciliation failures)."""
    parts: list[QPart] = []
    failures: list[str] = []
    papers = 0
    questions_seen = questions_ok = 0
    unjoined = 0

    for qp_path in sorted(archive.glob("*/*/*_QP.pdf")):
        match = FILE_RE.search(qp_path.name)
        if not match:
            continue
        year, session, paper, variant = (
            int(match.group(1)), match.group(2), match.group(3), match.group(4)
        )
        if not from_year <= year <= to_year:
            continue
        ms_path = qp_path.with_name(qp_path.name.replace("_QP.pdf", "_MS.pdf"))
        if not ms_path.exists():
            failures.append(f"{qp_path.name}: no mark scheme in the archive")
            continue

        paper_id = f"{year}_{session}_P{paper}{variant}"
        stems = index_stems(parse_qp(qp_path, paper_id))
        scheme = parse_ms(ms_path, paper_id)
        papers += 1

        parsed = scheme.marks_by_question()
        reconciled = set()
        for q, total in scheme.totals.items():
            questions_seen += 1
            if parsed.get(q, 0) == total:
                reconciled.add(q)
                questions_ok += 1
            else:
                failures.append(
                    f"{paper_id} Q{q}: mark scheme parsed to {parsed.get(q, 0)} "
                    f"marks but the paper prints {total} -- excluded"
                )

        spec = _spec_of(year, session)
        for cell in scheme.parts:
            if cell.q not in reconciled or not cell.answer:
                continue
            stem = stems.get(f"{cell.q}{cell.part}")
            if stem is None:
                unjoined += 1
                continue
            tariff = cell.marks or stem.tariff
            points, aside, menu = _points(cell.answer, tariff)
            if not points:
                continue
            text = _clean_stem(stem.text)
            notes = re.sub(r"\s+", " ", f"{cell.notes} {aside}").strip()
            parts.append(
                QPart(
                    paper_id=paper_id, year=year, session=session, paper=paper,
                    variant=variant, spec=spec, q=cell.q, part=cell.part,
                    stem=text, tariff=tariff, points=points, notes=notes, menu=menu,
                    difficulty=score_part(text, cell.answer, cell.notes, tariff),
                )
            )

    report = [
        f"{papers} question papers read from {archive}",
        f"{questions_ok} of {questions_seen} questions reconcile with their printed "
        f"mark total ({100 * questions_ok / max(questions_seen, 1):.1f}%)",
        f"{len(parts)} question parts joined to a mark scheme cell "
        f"({unjoined} mark scheme cells had no matching stem and were dropped)",
        f"{sum(1 for p in parts if p.spec == '4PH1')} parts on the current 4PH1 "
        f"specification, {sum(1 for p in parts if p.spec == '4PH0')} on legacy 4PH0",
    ]
    return parts, report, failures
