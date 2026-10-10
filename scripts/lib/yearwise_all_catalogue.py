"""
The units the 2018-2026 yearwise books are built from, and where each unit's
papers can be found.

A `Unit` is one exam paper that gets its own run of sittings: IGCSE Maths B
Paper 1, IAL Physics Unit 4, IAL Pure Mathematics P2. A book is one subject's
units over a year range (decided 2026-10-04: split by year range, a sitting's
Paper 1 and Paper 2 kept together), so the catalogue groups units by `book`.

WHERE A UNIT'S PAPERS LIVE -- three places, none of them complete:

  db          the live `papers` rows (R2 copies). IGCSE sciences are filed under
              TWO paper numbers for the same paper -- "1" and "1P"/"1C"/"1B" --
              because the cover prints `4PH1/1P`. June 2026 exists ONLY under
              the lettered slot, so both slots are candidates.
  local       data/Ultimate Final {IGCSE,IAL}/<subject>/<year>/<season>/...
  paperlords  the October 2019 - January 2022 IAL science run the DB never
              had, harvested 2026-10-04 (data/yearwise_all/paperlords_index.json).

None of the three is trusted for identity. Every file is identified from its
own text by `lib/yearwise_linkage.py`; the slot a file was found in only says
which sitting it is a CANDIDATE for.

The 1R/2R time-zone variants are excluded (user decision 2026-10-04). The
paper-code patterns below therefore refuse a trailing R.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "data" / "yearwise_all"
FIRST_YEAR, LAST_YEAR = 2018, 2026


@dataclass(frozen=True)
class Unit:
    key: str                     # file-safe id, e.g. "4PH1_P1", "WPH14"
    book: str                    # which book family it is printed in
    level: str                   # IGCSE | IAL
    label: str                   # "Physics Paper 1"
    db_code: str                 # subjects.code
    db_papers: tuple[str, ...]   # papers.paper_number slots that may hold it
    # What a genuine cover says. Group 1 = specification code (4PH1 vs the
    # legacy 4PH0), so the audit can report the spec rather than guess it.
    qp_code: re.Pattern
    # Publication-code unit + paper, e.g. ("4PH1", "1P") or ("WPH14", "01").
    pub_units: tuple[str, ...]
    pub_paper: tuple[str, ...]
    local_dir: str               # "Ultimate Final IGCSE/Physics"
    local_names: tuple[str, ...] # formatted with year, season, kind
    paperlords: tuple[str, str] | None = None   # (subject, unit label "U4")


def _igcse(book, subj_code, label, local_dir, stem, paper, letter):
    """One IGCSE paper: `4PH1/1P` on the cover, `4PH1_1P_2306_MS` on the scheme."""
    spec = subj_code[:3]
    suffix = letter or ""
    return Unit(
        key=f"{subj_code}_P{paper}", book=book, level="IGCSE",
        label=f"{label} Paper {paper}", db_code=subj_code,
        db_papers=tuple(dict.fromkeys((str(paper), f"{paper}{suffix}"))),
        qp_code=re.compile(
            rf"\b({spec}[01])\s*/\s*0?{paper}{suffix}(?![A-Z0-9])"),
        pub_units=(f"{spec}1", f"{spec}0"),
        pub_paper=tuple(dict.fromkeys((f"0{paper}", f"{paper}{suffix}"))),
        local_dir=f"Ultimate Final IGCSE/{local_dir}",
        local_names=tuple(dict.fromkeys((
            f"{stem}_{{year}}_{{season}}_Paper_{paper}_{{kind}}.pdf",
            f"{stem}_{{year}}_{{season}}_Paper_{paper}{suffix}_{{kind}}.pdf"))),
    )


def _ial_science(book, code, subject, n):
    unit = f"{code}1{n}"
    return Unit(
        key=unit, book=book, level="IAL", label=f"{subject} Unit {n}",
        db_code=code, db_papers=(f"Unit_{n}",),
        # Legacy (pre-2018 spec) units are WPH0n; capture so it is reported.
        qp_code=re.compile(rf"\b({code}[01]){n}\s*/\s*0?1(?![A-Z0-9])"),
        pub_units=(unit, f"{code}0{n}"), pub_paper=("01",),
        local_dir=f"Ultimate Final IAL/{subject}",
        local_names=(f"{subject}_Unit_{n}_{{year}}_{{season}}_{{kind}}.pdf",),
        paperlords=(subject, f"U{n}"),
    )


def _ial_pure(n):
    unit = f"WMA1{n}"
    return Unit(
        key=unit, book="ial_pure", level="IAL", label=f"Pure Mathematics P{n}",
        db_code=unit, db_papers=("1",),
        # Before each unit's cutover the slot holds the legacy C12/C34 paper
        # (WMA01/WMA02); capturing the code lets the audit say so.
        qp_code=re.compile(r"\b(WMA\d)\d\s*/\s*0?1(?![A-Z0-9])"),
        pub_units=(unit,), pub_paper=("01",),
        local_dir="Ultimate Final IAL/Mathematics",
        local_names=(f"Mathematics_P{n}_{{year}}_{{season}}_{{kind}}.pdf",),
    )


UNITS: tuple[Unit, ...] = (
    _igcse("igcse_mathsb", "4MB1", "Mathematics B", "Mathematics_B", "Mathematics_B", 1, None),
    _igcse("igcse_mathsb", "4MB1", "Mathematics B", "Mathematics_B", "Mathematics_B", 2, None),
    _igcse("igcse_fpm", "4PM1", "Further Pure Mathematics", "Further_Pure_Maths", "Further_Pure_Maths", 1, None),
    _igcse("igcse_fpm", "4PM1", "Further Pure Mathematics", "Further_Pure_Maths", "Further_Pure_Maths", 2, None),
    _igcse("igcse_physics", "4PH1", "Physics", "Physics", "Physics", 1, "P"),
    _igcse("igcse_physics", "4PH1", "Physics", "Physics", "Physics", 2, "P"),
    _igcse("igcse_chemistry", "4CH1", "Chemistry", "Chemistry", "Chemistry", 1, "C"),
    _igcse("igcse_chemistry", "4CH1", "Chemistry", "Chemistry", "Chemistry", 2, "C"),
    _igcse("igcse_biology", "4BI1", "Biology", "Biology", "Biology", 1, "B"),
    _igcse("igcse_biology", "4BI1", "Biology", "Biology", "Biology", 2, "B"),
    *(_ial_science("ial_physics", "WPH", "Physics", n) for n in range(1, 7)),
    *(_ial_science("ial_chemistry", "WCH", "Chemistry", n) for n in range(1, 7)),
    *(_ial_science("ial_biology", "WBI", "Biology", n) for n in range(1, 7)),
    *(_ial_pure(n) for n in range(1, 5)),
)

BOOKS = tuple(dict.fromkeys(u.book for u in UNITS))


def units_of(book: str) -> tuple[Unit, ...]:
    found = tuple(u for u in UNITS if u.book == book)
    if not found:
        raise SystemExit(f"unknown book {book!r}; known: {', '.join(BOOKS)}")
    return found


# Our season spellings: DB lower-case, archive folders title-case.
SEASONS = ("Jan", "May-Jun", "Oct-Nov")
DB_SEASON = {"jan": "Jan", "may-jun": "May-Jun", "oct-nov": "Oct-Nov"}
PAPERLORDS_SEASON = {"Jan": "Jan", "June": "May-Jun", "May": "May-Jun",
                     "May/June": "May-Jun", "Oct": "Oct-Nov", "Nov": "Oct-Nov"}


def sitting_of(year: int, season: str) -> tuple[int, str]:
    """
    The sitting a slot's paper was actually sat in.

    Summer 2020 was cancelled. Its paper, printed for June, was sat in the
    October 2020 series, so files filed under 2020 May-Jun (ours) or "June 2020"
    (Paperlords) are candidates for 2020 Oct-Nov. Pairing and the item-code
    de-duplication then decide whether the two slots hold one paper or two.
    """
    if (year, season) == (2020, "May-Jun"):
        return 2020, "Oct-Nov"
    return year, season
