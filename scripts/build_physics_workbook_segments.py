"""
Re-segment Edexcel International GCSE Physics papers (4PH1, and the legacy 4PH0
papers sat up to January 2019) into one PDF per question, for the chapterwise
Physics workbook.

This is the Physics counterpart of build_mathsa_workbook_segments.py and a close
port of it: Physics is an Edexcel IGCSE, so it uses the IGCSE method -- read
boundaries from the paper's own end-of-question fences, require independent
signals to agree, and hold back any paper that fails a paper-level invariant.

WINDOW AND SCOPE
----------------
2018 Jan to 2023 Oct-Nov, Papers 1P/2P and the R variants (1PR/2PR, a separate
paper sat in the same session). Measured 2026-10-03 over that window: 45
papers, 44 with a full text layer whose fences are contiguous from 1 and sum
to the paper's total, no two papers sharing a barcode.

The archive names files "Paper_1"/"Paper_1R"; the cover prints "4PH1/1P" or
"4PH1/1PR". Keys here use the cover's form (2022_jan_1PR), and every paper is
checked against its own cover -- a cover naming a different paper is rejected.

TWO SPECIFICATIONS, TWO SETS OF TOTALS
--------------------------------------
2018 Jan, 2018 May-Jun and 2019 Jan are the legacy 4PH0 papers (4PH1's first
assessment was June 2019). The content is the same eight topics, so they belong
in the book, but the paper totals differ and the 100-mark invariant every maths
segmenter used does not hold for either:

    4PH0  Paper 1 = 120   Paper 2 = 60
    4PH1  Paper 1 = 110   Paper 2 = 70

The total is chosen from the cover's code. A cover that yields no code (the one
image-only scan) falls back on the date: from 2019 May-Jun it is 4PH1.

PHYSICS-SPECIFIC DIFFERENCES FROM THE MATHS SEGMENTERS
------------------------------------------------------
1. The mark scheme states the question number in its own tally:
   "Total for question 7 = 11 marks". So a scheme block is attached by the
   NUMBER IT PRINTS, with the marks as an independent confirmation -- not by
   aligning mark sequences, which is all the maths schemes allowed. One tally in
   2018 Jan Paper 1 omits the number ("Total for question = 3 marks"); such a
   tally is placed by its neighbours and accepted only if its marks agree.
2. Physics papers print "BLANK PAGE" sheets between questions. A question that
   starts "on the page after the previous fence" would otherwise open on a blank
   sheet, so blank pages are skipped when locating a start.
3. From 2022 the separate Equation Booklet is bound in after the last question.
   The last question ends at its own fence, so the booklet is never included --
   which is the defect the live test-builder segments still carry
   (see scripts/fix_physics_front_pages.py).

DO NOT CROP WITH set_cropbox -- see extract_regions(). Same trap as Maths A/B.

OUTPUT
------
    data/workbook/physics/<paper_key>/questions/qN.pdf
    data/workbook/physics/<paper_key>/markschemes/qN.pdf
    data/workbook/physics/<paper_key>/manifest.json

Nothing here touches data/processed/, which still feeds the test builder.

USAGE
-----
    python scripts/build_physics_workbook_segments.py                 # dry run
    python scripts/build_physics_workbook_segments.py --execute
    python scripts/build_physics_workbook_segments.py --audit
    python scripts/build_physics_workbook_segments.py --paper 2022_jan_1P --verbose
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import fitz

from lib import ms_bands

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT / "data" / "Ultimate Final IGCSE" / "Physics"
OUTPUT_DIR = REPO_ROOT / "data" / "workbook" / "physics"
REPORT_PATH = REPO_ROOT / "data" / "workbook" / "physics_segmentation_report.json"

# Filename paper number -> the paper code the cover prints.
PAPER_CODES = {"1": "1P", "2": "2P", "1R": "1PR", "2R": "2PR"}

WINDOW_START = (2018, "jan")
WINDOW_END = (2023, "oct-nov")

# 4PH1 was first sat in June 2019; everything before is 4PH0.
FIRST_4PH1 = (2019, "may-jun")

PAPER_TOTALS = {
    ("4PH0", "1"): 120,
    ("4PH0", "2"): 60,
    ("4PH1", "1"): 110,
    ("4PH1", "2"): 70,
}

COVER_CODE_RE = re.compile(r"\b(4PH[01])\s*/\s*([12]PR?)\b")

# PhysicsAndMathsTutor and our own stamp both print a label on every page; it is
# not cover evidence and is stripped before the cover is read.
WATERMARK_RE = re.compile(
    r"(?<![0-9A-Za-z])4[A-Z]{2}[01]\s*\|\s*20\d{2}\s*\|\s*[A-Za-z/]+\s*\|\s*"
    r"Paper\s*[0-9A-Za-z]+\s*\|?"
    r"|(?<![0-9A-Za-z])GradeMax",
    re.I,
)

SEASON_FROM_FOLDER = {
    "Jan": "jan",
    "May-Jun": "may-jun",
    "Oct-Nov": "oct-nov",
}

# Papers deliberately excluded, with the reason recorded so the exclusion is
# auditable rather than folklore.
EXCLUDED_PAPERS: dict[str, str] = {}

# Papers whose QP carries no usable text layer, so no fence can be read. Each
# entry maps question number -> (first_page, last_page, marks), 0-indexed
# inclusive, established by eye from a rendered contact sheet. Marks come from
# the mark scheme's own numbered tallies. Entries are validated exactly like a
# parsed paper: contiguous numbering and the paper total.
MANUAL_QP_RANGES: dict[str, dict[int, tuple[int, int, int]]] = {
    # 2019 May-Jun Paper 1 is an image-only scan (2,944 characters over 32
    # pages, all of it our own stamp). Starts READ OFF A RENDERED CONTACT SHEET
    # 2026-10-03; pages 2, 12, 15, 23 and 31 were rendered whole and are all
    # "BLANK PAGE" sheets, so no range includes them. Marks are the mark
    # scheme's own numbered tallies ("Total for question N = M marks"), which
    # sum to 110 -- the 4PH1 Paper 1 total.
    "2019_may-jun_1P": {
        1: (3, 4, 5),
        2: (5, 6, 6),
        3: (7, 8, 4),
        4: (9, 10, 12),
        5: (11, 11, 5),
        6: (13, 14, 12),
        7: (16, 18, 14),
        8: (19, 20, 12),
        9: (21, 22, 12),
        10: (24, 26, 11),
        11: (27, 28, 10),
        12: (29, 30, 7),
    },
}

# BLANK PAGE sheets that find_blank_pages cannot see because the page is an
# image. Rendered whole and read by eye, 2026-10-03.
MANUAL_BLANK_PAGES: dict[str, set[int]] = {
    "2019_may-jun_1P": {2, 12, 15, 23, 31},
}

# Marks for questions whose end fence exists but cannot be read; see
# recover_missing_fence. None needed in this window (measured).
MANUAL_QUESTION_MARKS: dict[str, dict[int, int]] = {}

# Start page for a question whose printed marker cannot be read. None needed.
MANUAL_START_PAGES: dict[str, dict[int, int]] = {}

# A page with less real text than this, once furniture is removed, and saying
# "BLANK PAGE", is a separator sheet rather than part of a question.
BLANK_PAGE_RE = re.compile(r"BLANK\s+PAGE", re.I)
BLANK_PAGE_MAX_CHARS = 160

# ─────────────────────────────────────────────────────────────────────────────
# Text patterns
# ─────────────────────────────────────────────────────────────────────────────

# "(Total for Question 7 is 2 marks)". The connector varies across the series,
# so "is", "=" and ":" are all accepted -- and it is allowed to be absent, which
# some papers in this series do.
FENCE_RE = re.compile(
    r"Total\s+for\s+Question\s+(\d{1,2})\s*(?:is|=|:)?\s*(\d{1,3})\s+marks?", re.I
)

# A bare fence with no mark tally -- used only to detect that we under-matched.
FENCE_LOOSE_RE = re.compile(r"Total\s+for\s+Question\s+(\d{1,2})", re.I)

# Everything the mark scheme side needs to read -- the per-question tally, the
# table head, the question number under it -- now lives in lib/ms_bands.py,
# which reads them with coordinates so a block can be cut to its own band
# instead of taking whole pages. The regexes that used to sit here read the
# same things out of flat page text and are gone with the code that used them.

# The printed question number sits hard against the left margin. Page-number
# footers sit at a similar x, so the bottom strip of the page is excluded --
# unlike FPM this cannot be done with a fixed y ceiling, because a legitimate
# Paper 1 marker can appear anywhere down the page.
START_MARKER_MAX_X = 80.0
FOOTER_BAND = 60.0  # points above the page bottom to ignore

# The marker is not always a span of its own. Where a question opens directly
# on an algebraic expression the typesetter runs the two together, so the span
# reads "5 a" rather than "5" and an exact match silently loses that question:
#
#     x0=42.4  '4'            <- Q4, matches either way
#     x0=42.4  '5 a'          <- Q5, lost by an exact match
#     x0=42.4  '6 '           <- Q6, matches either way
#
# Requiring whitespace or end-of-span after the digits keeps "832 in the form"
# out (its "83" is followed by "2", so the match backtracks and fails), and the
# left-margin x limit already excludes anything from the body column.
START_MARKER_RE = re.compile(r"^(\d{1,2})(?:[\s.]|$)")

# Breathing room around a cropped band so the question number and the fence
# line are never clipped by a rounding error.
CROP_PAD_TOP = 8.0
CROP_PAD_BOTTOM = 10.0


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PaperSource:
    """One question paper plus its mark scheme, located on disk."""

    key: str  # "2022_jan_1PR"
    year: int
    season: str  # "jan"
    paper_number: str  # the cover's code: "1P" | "1PR" | "2P" | "2PR"
    spec: str  # "4PH0" | "4PH1"
    total_marks: int
    qp_path: Path
    ms_path: Path | None


@dataclass(frozen=True)
class Region:
    """
    One page of a segment. `top`/`bottom` are None where the segment owns the
    full page and a float where the page is shared and must be cropped.

    `left`/`right` are the same idea across the page instead of down it, and are
    used only by mark scheme pages that set /Rotate 90 and write their text
    bottom-to-top. On those the table's rows advance along x, so a question's
    block is a vertical stripe rather than a horizontal band. See
    scripts/lib/ms_bands.py for why that layout has to be cut on its own axis.
    """

    page: int
    top: float | None = None
    bottom: float | None = None
    left: float | None = None
    right: float | None = None

    @property
    def cropped(self) -> bool:
        return any(
            edge is not None for edge in (self.top, self.bottom, self.left, self.right)
        )


@dataclass(frozen=True)
class QuestionSegment:
    number: int
    marks: int
    qp_regions: tuple[Region, ...]
    ms_regions: tuple[Region, ...] | None
    # True when this question's end fence was unreadable and its boundary came
    # from the next question's start marker. Such a segment carries no fence, so
    # the audit reports it separately rather than counting it a defect.
    fence_recovered: bool = False


@dataclass
class PaperResult:
    source: PaperSource
    segments: list[QuestionSegment] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped_reason: str | None = None

    @property
    def ok(self) -> bool:
        return not self.issues and self.skipped_reason is None


# ─────────────────────────────────────────────────────────────────────────────
# Discovery
# ─────────────────────────────────────────────────────────────────────────────


def parse_paper_number(filename: str) -> str | None:
    """`..._Paper_1R_QP.pdf` -> `1R` (the archive's own spelling)."""
    match = re.search(r"_Paper_(\d+R?)_QP\.pdf$", filename, re.I)
    return match.group(1).upper() if match else None


SEASON_ORDER = {"jan": 0, "may-jun": 1, "oct-nov": 2}


def session_rank(year: int, season: str) -> tuple[int, int]:
    return (year, SEASON_ORDER.get(season, 99))


def within_window(year: int, season: str) -> bool:
    """True from WINDOW_START to WINDOW_END inclusive."""
    rank = session_rank(year, season)
    return session_rank(*WINDOW_START) <= rank <= session_rank(*WINDOW_END)


def read_cover_code(qp_path: Path) -> str | None:
    """
    The paper code printed on the paper's OWN cover ("4PH1/1PR"), or None.

    The watermark is stripped first -- it is a label someone else applied, not
    the cover. The one image-only scan in the window yields None, which is not
    evidence against it.
    """
    try:
        with fitz.open(qp_path) as doc:
            text = WATERMARK_RE.sub(" ", doc[0].get_text())
    except Exception:  # noqa: BLE001 - an unreadable cover is not fatal
        return None

    match = COVER_CODE_RE.search(text)
    return f"{match.group(1)}/{match.group(2)}" if match else None


def discover_papers(verbose: bool = False) -> list[PaperSource]:
    """
    Find every in-window QP, pairing each with its mark scheme.

    The filename's paper number is checked against the cover's. A cover that
    names a different paper is rejected outright; a cover that reads nothing is
    accepted on the filename and the date, and reported.
    """
    if not SOURCE_DIR.is_dir():
        raise FileNotFoundError(f"Source archive not found: {SOURCE_DIR}")

    papers: list[PaperSource] = []
    rejected: list[str] = []

    for year_dir in sorted(p for p in SOURCE_DIR.iterdir() if p.is_dir()):
        if not year_dir.name.isdigit():
            continue
        year = int(year_dir.name)

        for session_dir in sorted(p for p in year_dir.iterdir() if p.is_dir()):
            season = SEASON_FROM_FOLDER.get(session_dir.name)
            if season is None or not within_window(year, season):
                continue

            for qp_path in sorted(session_dir.glob("*_QP.pdf")):
                file_number = parse_paper_number(qp_path.name)
                paper_code = PAPER_CODES.get(file_number or "")
                if paper_code is None:
                    print(f"  ! unparseable paper number, skipped: {qp_path.name}")
                    continue

                key = f"{year}_{season}_{paper_code}"
                code = read_cover_code(qp_path)
                if code is not None and code.split("/")[1] != paper_code:
                    rejected.append(f"{key}: cover says {code}")
                    continue

                if code is not None:
                    spec = code.split("/")[0]
                else:
                    spec = (
                        "4PH1"
                        if session_rank(year, season) >= session_rank(*FIRST_4PH1)
                        else "4PH0"
                    )
                    if verbose:
                        print(f"  . {key}: no cover code extractable, {spec} by date")

                ms_path = qp_path.with_name(qp_path.name.replace("_QP.pdf", "_MS.pdf"))
                papers.append(
                    PaperSource(
                        key=key,
                        year=year,
                        season=season,
                        paper_number=paper_code,
                        spec=spec,
                        total_marks=PAPER_TOTALS[(spec, paper_code[0])],
                        qp_path=qp_path,
                        ms_path=ms_path if ms_path.is_file() else None,
                    )
                )

    if rejected:
        print(f"  {len(rejected)} file(s) rejected on cover evidence:")
        for line in rejected:
            print(f"    - {line}")

    return papers


# ─────────────────────────────────────────────────────────────────────────────
# Extraction primitives
# ─────────────────────────────────────────────────────────────────────────────


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def page_lines(page: fitz.Page) -> list[tuple[str, float, float]]:
    """Every text line as (text, y_top, y_bottom), in reading order."""
    lines: list[tuple[str, float, float]] = []
    try:
        blocks = page.get_text("dict")["blocks"]
    except Exception:  # noqa: BLE001 - a bad page must not kill the paper
        return lines

    for block in blocks:
        for line in block.get("lines", []):
            text = "".join(span["text"] for span in line.get("spans", []))
            if text.strip():
                lines.append((text, line["bbox"][1], line["bbox"][3]))

    lines.sort(key=lambda row: row[1])
    return lines


def page_texts(pdf_path: Path) -> list[str]:
    """Raw per-page text. Never raises -- an unreadable page yields ''."""
    with fitz.open(pdf_path) as doc:
        out = []
        for page in doc:
            try:
                out.append(page.get_text())
            except Exception:  # noqa: BLE001
                out.append("")
        return out


def find_blank_pages(pdf_path: Path) -> set[int]:
    """
    Indexes of "BLANK PAGE" separator sheets.

    A page qualifies only if it says so AND carries almost no other text once
    the watermark and stamp are removed -- a real question page that happens to
    mention a blank page would carry far more.
    """
    blank: set[int] = set()
    with fitz.open(pdf_path) as doc:
        for index, page in enumerate(doc):
            try:
                text = WATERMARK_RE.sub(" ", page.get_text())
            except Exception:  # noqa: BLE001
                continue
            if not BLANK_PAGE_RE.search(text):
                continue
            residue = re.sub(r"\s+", "", BLANK_PAGE_RE.sub("", text))
            # Footer furniture: page number and the item barcode.
            residue = re.sub(r"\*?P\d{5}R?A\d*\*?|\d{1,2}", "", residue)
            if len(residue) <= BLANK_PAGE_MAX_CHARS:
                blank.add(index)
    return blank


def find_fences(
    pdf_path: Path,
) -> tuple[dict[int, tuple[int, int, float]], list[str]]:
    """
    Map question number -> (end_page_index, marks, fence_bottom_y).

    The y coordinate is what makes shared pages separable, so it is captured
    here rather than recovered later. A fence that wraps across two lines is
    joined before matching, otherwise the mark tally is lost.
    """
    fences: dict[int, tuple[int, int, float]] = {}
    problems: list[str] = []

    with fitz.open(pdf_path) as doc:
        for index, page in enumerate(doc):
            lines = page_lines(page)
            seen_here: set[int] = set()

            for position, (text, _, bottom) in enumerate(lines):
                joined, end_y = text, bottom
                match = FENCE_RE.search(normalise(joined))

                if not match and position + 1 < len(lines):
                    following = lines[position + 1]
                    joined = f"{text} {following[0]}"
                    match = FENCE_RE.search(normalise(joined))
                    if match:
                        end_y = following[2]

                if not match:
                    continue

                question, marks = int(match.group(1)), int(match.group(2))
                if question in seen_here:
                    continue  # the wrap-join can see the same fence twice
                seen_here.add(question)

                if question in fences:
                    problems.append(
                        f"question {question} fenced twice "
                        f"(pages {fences[question][0]} and {index})"
                    )
                    continue

                fences[question] = (index, marks, end_y)

            flat = normalise(page.get_text())
            loose = {int(q) for q in FENCE_LOOSE_RE.findall(flat)}
            for question in sorted(loose - seen_here):
                if question not in fences:
                    problems.append(
                        f"page {index}: found 'Total for Question {question}' but "
                        f"could not read its mark tally"
                    )

    return fences, problems


def recover_missing_fence(
    fences: dict[int, tuple[int, int, float]],
    start_markers: dict[int, list[tuple[int, float]]],
    page_heights: list[float],
    manual_marks: dict[int, int] | None = None,
    manual_starts: dict[int, int] | None = None,
    total_marks: int = 110,
) -> tuple[dict[int, tuple[int, int, float]], list[str]]:
    """
    Reconstruct unreadable fences from the paper's own invariants.

    A few papers print a question's end fence in glyphs the text layer cannot
    map, so the fence is absent while every other question reads cleanly. The
    whole paper was being held back over one line.

    A fence can be put back only when BOTH unknowns are pinned down
    independently:

      marks     the paper must total 100, so a SINGLE gap in an otherwise
                complete sequence has exactly one possible value. Where two or
                more are missing the shortfall could be split several ways, and
                the marks must instead be supplied by MANUAL_QUESTION_MARKS,
                read off the rendered page. Their sum still has to equal the
                shortfall, so a misread is caught here rather than propagated.
      boundary  the NEXT question's printed start marker says where this one
                stops -- the same second signal used to confirm every other
                boundary, here used to supply one. This works even for
                consecutive gaps, because markers are read independently of
                fences.

    Refuses outright rather than guessing when the marks cannot be established.
    """
    notes: list[str] = []
    if not fences:
        return fences, notes

    manual_marks = manual_marks or {}
    manual_starts = manual_starts or {}
    highest = max(fences)
    missing = [q for q in range(1, highest + 1) if q not in fences]
    if not missing:
        return fences, notes

    shortfall = total_marks - sum(marks for _, marks, _ in fences.values())
    if shortfall <= 0:
        return fences, notes

    if len(missing) == 1 and missing[0] not in manual_marks:
        marks_for = {missing[0]: shortfall}
        source = "the paper total"
    else:
        if not all(q in manual_marks for q in missing):
            notes.append(
                f"{len(missing)} fences unreadable ({missing}) and the "
                f"{shortfall}-mark shortfall cannot be split between them -- add "
                f"them to MANUAL_QUESTION_MARKS after reading the rendered pages"
            )
            return fences, notes
        marks_for = {q: manual_marks[q] for q in missing}
        if sum(marks_for.values()) != shortfall:
            notes.append(
                f"MANUAL_QUESTION_MARKS for {missing} sum to "
                f"{sum(marks_for.values())} but the paper is short by {shortfall}"
            )
            return fences, notes
        source = "MANUAL_QUESTION_MARKS (read off the rendered page)"

    recovered = dict(fences)

    for question in missing:
        candidates = start_markers.get(question + 1, [])
        if not candidates and question + 1 in manual_starts:
            # The next question opens on an image-only page, so its marker is
            # unreadable. y=0.0 marks the top of that page, which is what the
            # rendered page shows and what the whole-page branch below expects.
            candidates = [(manual_starts[question + 1], 0.0)]
            notes.append(
                f"question {question + 1}: start marker unreadable (image-only "
                f"page) -- start page {manual_starts[question + 1]} supplied from "
                f"MANUAL_START_PAGES (read off the rendered page)"
            )
        if not candidates:
            notes.append(
                f"question {question}: fence unreadable and question "
                f"{question + 1} has no printed start marker -- cannot place the "
                f"boundary"
            )
            return fences, notes

        previous_page = recovered[question - 1][0] if question - 1 in recovered else 0
        usable = [(page, y) for page, y in candidates if page >= previous_page]
        if not usable:
            notes.append(
                f"question {question}: no start marker for question "
                f"{question + 1} at or after page {previous_page}"
            )
            return fences, notes

        next_page, next_y = usable[0]

        if next_y < 100 and next_page - 1 >= previous_page:
            # The next question opens at the top of its page, so this one ends
            # with the page before it -- no crop needed.
            end_page = next_page - 1
            end_y = page_heights[end_page] if end_page < len(page_heights) else 800.0
        else:
            end_page, end_y = next_page, max(0.0, next_y - CROP_PAD_TOP)

        recovered[question] = (end_page, marks_for[question], end_y)
        notes.append(
            f"question {question}: fence unreadable -- marks "
            f"({marks_for[question]}) from {source}, boundary from question "
            f"{question + 1}'s printed start marker on page {next_page}"
        )

    return recovered, notes


def find_start_markers(pdf_path: Path) -> dict[int, list[tuple[int, float]]]:
    """
    Map question number -> [(page_index, y_top)] for the printed left-margin
    question number.

    This is the independent second signal. It never defines a boundary on its
    own -- it confirms the fence-derived one, and supplies the crop top where a
    page is shared.
    """
    markers: dict[int, list[tuple[int, float]]] = {}

    with fitz.open(pdf_path) as doc:
        for index, page in enumerate(doc):
            floor = page.rect.height - FOOTER_BAND
            try:
                blocks = page.get_text("dict")["blocks"]
            except Exception:  # noqa: BLE001
                continue

            for block in blocks:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        match = START_MARKER_RE.match(span["text"].strip())
                        if not match:
                            continue
                        x0, y0 = span["bbox"][0], span["bbox"][1]
                        if x0 < START_MARKER_MAX_X and y0 < floor:
                            markers.setdefault(int(match.group(1)), []).append((index, y0))

    for entries in markers.values():
        entries.sort()

    return markers


# ─────────────────────────────────────────────────────────────────────────────
# Boundary derivation
# ─────────────────────────────────────────────────────────────────────────────


def derive_bounds(
    fences: dict[int, tuple[int, int, float]],
    start_markers: dict[int, list[tuple[int, float]]],
    blank_pages: set[int] | None = None,
) -> tuple[dict[int, tuple[tuple[int, float | None], tuple[int, float]]], list[str]]:
    """
    Turn fences into (start, end) positions, each a (page, y) pair.

    Question N ends at its fence. It starts either at its own printed marker on
    the page where the previous question ended -- the shared-page case -- or at
    the top of the page after it.
    """
    problems: list[str] = []
    numbers = sorted(fences)
    if not numbers:
        return {}, ["no fences found at all"]

    bounds: dict[int, tuple[tuple[int, float | None], tuple[int, float]]] = {}
    previous: tuple[int, float] | None = None

    for question in numbers:
        end_page, _, end_y = fences[question]
        candidates = start_markers.get(question, [])

        if previous is None:
            # Nothing fences the cover pages off, so question 1 must be located
            # by its own printed marker.
            usable = [(p, y) for p, y in candidates if p <= end_page]
            if not usable:
                problems.append(
                    f"question {question} is the first question but has no printed "
                    f"start marker at or before its fence on page {end_page}"
                )
                continue
            start = usable[0]
        else:
            previous_page, previous_y = previous
            on_shared_page = [
                (p, y) for p, y in candidates if p == previous_page and y > previous_y
            ]
            if on_shared_page:
                # Continues below the previous question on the same page.
                start = on_shared_page[0]
            else:
                # Physics prints BLANK PAGE separators between questions; a
                # question never opens on one.
                fresh = previous_page + 1
                while blank_pages and fresh in blank_pages and fresh < end_page:
                    fresh += 1
                start = (fresh, None)  # type: ignore[assignment]

        start_page = start[0]
        if start_page > end_page:
            problems.append(
                f"question {question}: derived start page {start_page} is after "
                f"its fence page {end_page}"
            )
            continue

        bounds[question] = (start, (end_page, end_y))
        previous = (end_page, end_y)

    return bounds, problems


def build_regions(
    bounds: dict[int, tuple[tuple[int, float | None], tuple[int, float]]],
    blank_pages: set[int] | None = None,
) -> dict[int, tuple[Region, ...]]:
    """
    Turn (start, end) positions into per-page regions, cropping only where a
    page is actually shared with another question.

    A page owned outright is taken whole, so diagrams and rubric that sit above
    the question number or below the fence are never clipped.
    """
    # How many questions touch each page.
    occupancy: dict[int, set[int]] = {}
    for question, (start, end) in bounds.items():
        for page in range(start[0], end[0] + 1):
            occupancy.setdefault(page, set()).add(question)

    # ONE boundary per adjacent pair, not two independent pads.
    #
    # Padding each side separately (fence + 10 below, marker - 8 above) let the
    # two bands overlap wherever the real gap was under 18pt -- 70 of 208
    # adjacent pairs, each by 0.65pt. Harmless at 10pt type, but it meant the
    # boundary between two questions had two different answers depending on
    # which one you asked. The midpoint of the gap is a single answer, always
    # below the fence it must keep and above the question number it must
    # exclude.
    bottom_at: dict[int, float] = {}
    top_at: dict[int, float] = {}

    ordered = sorted(bounds)
    for above, below in zip(ordered, ordered[1:]):
        _, (above_page, above_y) = bounds[above]
        (below_page, below_y), _ = bounds[below]
        if below_page != above_page or below_y is None:
            continue  # the next question starts on a fresh page
        boundary = (
            (above_y + below_y) / 2.0
            if below_y > above_y
            else above_y + CROP_PAD_BOTTOM
        )
        bottom_at[above] = boundary
        top_at[below] = boundary

    regions: dict[int, tuple[Region, ...]] = {}

    for question, ((start_page, _), (end_page, _)) in sorted(bounds.items()):
        pages: list[Region] = []

        for page in range(start_page, end_page + 1):
            if blank_pages and page in blank_pages:
                continue
            shared = len(occupancy.get(page, set())) > 1

            # A question that opens a shared page keeps everything above it
            # (rubric, a diagram sitting over the number); one that closes a
            # shared page keeps everything below. Only the seam is cut.
            top = top_at.get(question) if shared and page == start_page else None
            bottom = bottom_at.get(question) if shared and page == end_page else None

            pages.append(Region(page=page, top=top, bottom=bottom))

        regions[question] = tuple(pages)

    return regions


# ─────────────────────────────────────────────────────────────────────────────
# Mark schemes
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PhysicsTally:
    """One "Total for question N = M marks" line. `question` is None where the
    mark scheme omits the number (2018 Jan Paper 1 question 3 does)."""

    tally: ms_bands.Tally
    question: int | None


# Read on the word stream (see ms_bands.find_tallies for why). Edexcel writes
# the number and the "=" as one word or two ("1=" / "1 ="), and the marks and
# "marks" likewise, so the window is joined and matched as text.
PHYSICS_TALLY_RE = re.compile(
    r"^\(?Total\s+for\s+question\s*(\d{1,2})?\s*(?:is|=|:)?\s*(\d{1,3})\s*marks?",
    re.I,
)
TALLY_WINDOW = 8


def find_physics_tallies(ms_path: Path) -> list[PhysicsTally]:
    """Every per-question tally in document order, with its band coordinates."""
    found: list[PhysicsTally] = []

    with fitz.open(ms_path) as doc:
        for index, page in enumerate(doc):
            axis = ms_bands.page_axis(page)
            if axis is None:
                continue
            words = page.get_text("words")
            for position, word in enumerate(words):
                if word[4].lower().lstrip("(").rstrip(":.") != "total":
                    continue
                window = words[position : position + TALLY_WINDOW]
                joined = " ".join(item[4] for item in window)
                match = PHYSICS_TALLY_RE.match(joined)
                if match is None:
                    continue
                # Only the words the match actually consumed set the extent.
                consumed, length = [], 0
                for item in window:
                    if length >= match.end():
                        break
                    consumed.append(item)
                    length += len(item[4]) + 1
                edges = [ms_bands._extent(item[:4], axis) for item in consumed]
                found.append(
                    PhysicsTally(
                        tally=ms_bands.Tally(
                            page=index,
                            marks=int(match.group(2)),
                            lo=min(edge[0] for edge in edges),
                            hi=max(edge[1] for edge in edges),
                            axis=axis,
                        ),
                        question=int(match.group(1)) if match.group(1) else None,
                    )
                )

    found.sort(key=lambda item: (item.tally.page, item.tally.lo))
    return found


def assign_tallies(
    tallies: list[PhysicsTally], fences: dict[int, tuple[int, int, float]]
) -> tuple[dict[int, int], list[str]]:
    """
    question number -> index into `tallies`.

    A tally that prints its number is attached by that number -- the label is
    READ, not inferred. A numberless tally is attached to the question after the
    previous attached one, and only if its marks agree with that question's
    fence; otherwise it is left unattached.
    """
    notes: list[str] = []
    assignment: dict[int, int] = {}
    previous_question = 0

    for index, item in enumerate(tallies):
        question = item.question
        if question is None:
            candidate = previous_question + 1
            if (
                candidate in fences
                and candidate not in assignment
                and fences[candidate][1] == item.tally.marks
            ):
                notes.append(
                    f"q{candidate}: tally prints no number -- placed by sequence, "
                    f"confirmed by its {item.tally.marks} marks"
                )
                question = candidate
            else:
                notes.append(
                    f"numberless tally ({item.tally.marks} marks, page "
                    f"{item.tally.page}) could not be placed -- left unattached"
                )
                continue

        if question not in fences:
            notes.append(f"mark scheme tally for q{question} but the QP has no such question")
            continue
        if question in assignment:
            notes.append(f"q{question}: mark scheme prints two tallies -- kept the first")
            continue
        if fences[question][1] != item.tally.marks:
            # The question paper's fence is authoritative (Edexcel MS typos
            # exist). The number still identifies the block, so it is kept;
            # the audit lists it.
            notes.append(
                f"q{question}: mark scheme tally says {item.tally.marks} marks, "
                f"QP fence says {fences[question][1]} -- block kept on its number"
            )
        assignment[question] = index
        previous_question = question

    return assignment, notes


def extend_first_band(
    band: ms_bands.Band,
    question: int,
    headers: list[ms_bands.BlockHeader],
) -> ms_bands.Band:
    """
    The first block in a mark scheme has no previous tally to start after, so
    ms_bands starts it at the top of its tally's page. A long first question
    begins a page or more earlier; reach back to the first header that names
    it, but never past it into the general marking guidance.
    """
    for header in headers:
        if header.question != question or header.axis != band.axis:
            continue
        if header.page < band.start_page:
            return ms_bands.Band(
                start_page=header.page,
                start_at=max(0.0, header.lo - ms_bands.PAD_BEFORE),
                end_page=band.end_page,
                end_at=band.end_at,
                axis=band.axis,
            )
        break
    return band


def skip_empty_opening(ms_path: Path, band: ms_bands.Band) -> ms_bands.Band:
    """
    Move a band's start to the top of the next page when the slice it opens
    with holds no text.

    A band opens just past the previous question's tally. In Physics schemes
    that tally usually sits partway down a page and the next question's table
    starts on a FRESH page, so the opening slice is the white space below the
    tally -- measured on 51 of 457 blocks before this fix, each printing as a
    blank strip at the head of its answer. Only the board's running furniture
    (our stamp, the page footer) may sit in that slice and still count as empty.
    """
    if band.start_at is None or band.end_page <= band.start_page:
        return band

    with fitz.open(ms_path) as doc:
        page = doc[band.start_page]
        floor = page.rect.height - 45.0  # footer strip
        for word in page.get_text("words"):
            low, _ = ms_bands._extent(word[:4], band.axis)
            if low < band.start_at or (band.axis == ms_bands.AXIS_Y and low > floor):
                continue
            if WATERMARK_RE.fullmatch(word[4]) or not word[4].strip():
                continue
            return band

    return ms_bands.Band(
        start_page=band.start_page + 1,
        start_at=None,
        end_page=band.end_page,
        end_at=band.end_at,
        axis=band.axis,
    )


def locate_ms_blocks(
    ms_path: Path, fences: dict[int, tuple[int, int, float]]
) -> tuple[dict[int, tuple[Region, ...]], list[str]]:
    """
    Map question number -> the slice of the mark scheme that holds it.

    Primary: the numbered tallies (see the module docstring). Fallback, for a
    scheme that prints no tallies at all (2019 May-Jun Paper 2): the table's own
    numbered rows, as the Maths B "Format B" reader does.

    Every band is then read back: it must hold exactly one tally, naming this
    question where it names any. A band that fails is DROPPED, not widened to
    whole pages -- a missing mark scheme is honest, a neighbour's is not.
    """
    warnings: list[str] = []

    with fitz.open(ms_path) as doc:
        last_page = doc.page_count - 1

    tallies = find_physics_tallies(ms_path)
    headers = ms_bands.find_block_headers(ms_path)
    bands: dict[int, ms_bands.Band] = {}

    if tallies:
        assignment, notes = assign_tallies(tallies, fences)
        warnings.extend(notes)
        bands = ms_bands.bands_from_tallies(
            [t.tally for t in tallies], assignment, headers
        )
        first = min(assignment, key=assignment.get, default=None)
        if first is not None and first in bands and assignment[first] == 0:
            bands[first] = extend_first_band(bands[first], first, headers)
        warnings.append(
            f"mark scheme read as numbered tallies: {len(assignment)}/{len(fences)}"
        )
    else:
        rows = ms_bands.find_numbered_rows(ms_path)
        row_assignment: dict[int, int] = {}
        seen_page = -1
        for index, row in enumerate(rows):
            if row.question not in fences or row.question in row_assignment:
                continue
            if row.page < seen_page:
                continue
            # Rows run in question order; a number that skips ahead of the next
            # expected question is a stray integer from the working column.
            expected = max(row_assignment, default=0) + 1
            if row.question != expected:
                continue
            row_assignment[row.question] = index
            seen_page = row.page
        if len(row_assignment) == len(fences):
            bands = ms_bands.bands_from_rows(rows, row_assignment, last_page=last_page)
            warnings.append(
                f"mark scheme has no tallies -- read as a numbered table, "
                f"{len(row_assignment)}/{len(fences)} rows in sequence"
            )
        else:
            warnings.append(
                f"mark scheme has no tallies and only {len(row_assignment)}/"
                f"{len(fences)} numbered rows run in sequence -- none attached"
            )
            return {}, warnings

    bands = {q: skip_empty_opening(ms_path, band) for q, band in bands.items()}

    kept: dict[int, tuple[Region, ...]] = {}
    rejected: list[str] = []
    for question, band in sorted(bands.items()):
        if band.start_page > last_page:
            continue
        if tallies:
            inside = [
                t for t in tallies
                if ms_bands.verify_band([t.tally], band)
            ]
            if len(inside) != 1:
                rejected.append(f"q{question} ({len(inside)} tallies in its band)")
                continue
            named = inside[0].question
            if named is not None and named != question:
                rejected.append(f"q{question} (its band closes on q{named}'s tally)")
                continue
        extents = ms_bands.page_extents_of(ms_path, band.axis)
        kept[question] = ms_bands.band_to_regions(band, Region, extents)

    if rejected:
        warnings.append("mark scheme band rejected for " + ", ".join(rejected))

    missing = sorted(set(fences) - set(kept))
    if missing:
        warnings.append(f"no mark scheme block found for questions {missing}")

    return kept, warnings


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────


def validate_paper(
    fences: dict[int, tuple[int, int, float]],
    regions: dict[int, tuple[Region, ...]],
    total_marks: int,
    blank_pages: set[int] | None = None,
) -> list[str]:
    """Paper-level invariants. Anything failing here blocks the whole paper."""
    issues: list[str] = []
    numbers = sorted(fences)

    if not numbers:
        return ["no questions detected"]

    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        missing = sorted(set(expected) - set(numbers))
        extra = sorted(set(numbers) - set(expected))
        detail = []
        if missing:
            detail.append(f"missing {missing}")
        if extra:
            detail.append(f"unexpected {extra}")
        issues.append(f"question numbers are not contiguous from 1: {', '.join(detail)}")

    total = sum(marks for _, marks, _ in fences.values())
    if total != total_marks:
        per_question = ", ".join(f"{q}:{m}" for q, (_, m, _) in sorted(fences.items()))
        issues.append(
            f"marks sum to {total}, expected {total_marks} ({{{per_question}}})"
        )

    if len(regions) != len(fences):
        issues.append(
            f"{len(fences)} questions fenced but only {len(regions)} produced regions"
        )

    # Consecutive questions must be contiguous: either the next starts on the
    # same page below this one, or on the page immediately after.
    ordered = sorted(regions.items())
    for (q_a, regions_a), (q_b, regions_b) in zip(ordered, ordered[1:]):
        last_page = regions_a[-1].page
        first_page = regions_b[0].page
        gap = set(range(last_page + 1, first_page))
        if first_page < last_page or not gap <= (blank_pages or set()):
            issues.append(
                f"page gap between question {q_a} (ends on page {last_page}) and "
                f"question {q_b} (starts on page {first_page})"
            )

    return issues


# ─────────────────────────────────────────────────────────────────────────────
# Processing
# ─────────────────────────────────────────────────────────────────────────────


def process_paper(source: PaperSource) -> PaperResult:
    result = PaperResult(source=source)
    recovered_numbers: set[int] = set()

    if source.key in EXCLUDED_PAPERS:
        result.skipped_reason = EXCLUDED_PAPERS[source.key]
        return result

    fences, fence_problems = find_fences(source.qp_path)
    blank_pages = find_blank_pages(source.qp_path) | MANUAL_BLANK_PAGES.get(
        source.key, set()
    )
    result.warnings.extend(fence_problems)

    manual = MANUAL_QP_RANGES.get(source.key)

    if not fences and manual is None:
        pages = page_texts(source.qp_path)
        volume = sum(len(p.strip()) for p in pages)
        result.issues.append(
            f"no question fences found in {len(pages)} pages ({volume} chars of "
            f"text -- an image-only scan or a broken text layer; add an entry to "
            f"MANUAL_QP_RANGES)"
        )
        return result

    if manual is not None:
        regions = {
            q: tuple(Region(page=p) for p in range(start, end + 1))
            for q, (start, end, _) in manual.items()
        }
        fences = {q: (end, marks, 0.0) for q, (_, end, marks) in manual.items()}
        result.warnings.append(
            f"no usable text layer: using hand-verified page ranges and "
            f"mark-scheme marks for {len(regions)} questions"
        )
    else:
        start_markers = find_start_markers(source.qp_path)

        with fitz.open(source.qp_path) as doc:
            page_heights = [page.rect.height for page in doc]
        before = set(fences)
        fences, recovery_notes = recover_missing_fence(
            fences,
            start_markers,
            page_heights,
            MANUAL_QUESTION_MARKS.get(source.key),
            MANUAL_START_PAGES.get(source.key),
            source.total_marks,
        )
        recovered_numbers = set(fences) - before
        result.warnings.extend(recovery_notes)

        bounds, problems = derive_bounds(fences, start_markers, blank_pages)
        result.issues.extend(problems)
        regions = build_regions(bounds, blank_pages)

    result.issues.extend(
        validate_paper(fences, regions, source.total_marks, blank_pages)
    )

    ms_regions: dict[int, tuple[Region, ...]] = {}
    if source.ms_path is None:
        result.warnings.append("no mark scheme file found")
    else:
        ms_regions, ms_warnings = locate_ms_blocks(source.ms_path, fences)
        result.warnings.extend(ms_warnings)

    result.segments = [
        QuestionSegment(
            number=question,
            marks=fences[question][1] if question in fences else 0,
            qp_regions=question_regions,
            ms_regions=ms_regions.get(question),
            fence_recovered=question in recovered_numbers,
        )
        for question, question_regions in sorted(regions.items())
    ]

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Writing
# ─────────────────────────────────────────────────────────────────────────────


def has_hidden_layers(doc: fitz.Document) -> bool:
    try:
        return any(not ocg["on"] for ocg in doc.get_ocgs().values())
    except Exception:  # noqa: BLE001 - "No default Layer config" on some files
        return False


def open_source(source_pdf: Path) -> fitz.Document:
    """
    Open a source PDF with any HIDDEN optional-content layers applied.

    The board's InDesign exports can carry layers switched off in the
    document's own layer config -- 2018 Jan Paper 1 has "Exemplar", "DRAFT",
    "OMR grids" and "Guides and Grids". insert_pdf and show_pdf_page copy the
    page content but not that config, so every hidden layer reappears: the
    segment printed a diagonal EXEMPLAR stamp over a red OMR grid. Found by
    rendering, invisible to every text check.

    Such a document is re-emitted through MuPDF's PDF writer, which runs each
    page with the layer config applied: hidden content is dropped, vectors and
    text survive at identical coordinates (verified word-for-word on 2018 Jan
    Paper 1). Documents without hidden layers are opened untouched.
    """
    import io

    from pymupdf import mupdf

    doc = fitz.open(source_pdf)
    if not has_hidden_layers(doc):
        return doc

    buffer = io.BytesIO()
    writer = fitz.DocumentWriter(buffer, "pdf")
    for page in doc:
        device = writer.begin_page(page.rect)
        # PyMuPDF 1.26's Page.run cannot drive a DocumentWriter device
        # ("'DeviceWrapper' object has no attribute 'device'"), so call MuPDF.
        mupdf.fz_run_page(page.this, device.this, mupdf.FzMatrix(), mupdf.FzCookie())
        writer.end_page()
    writer.close()
    doc.close()
    return fitz.open("pdf", buffer.getvalue())


def extract_regions(source_pdf: Path, regions: tuple[Region, ...], target: Path) -> None:
    """
    Write `regions` of `source_pdf` to `target` as a new PDF.

    A region with no band is copied whole, which preserves the page exactly. A
    banded region is drawn onto a fresh page of the band's size.

    WHY NOT set_cropbox
    -------------------
    The obvious implementation -- copy the page, then narrow its crop box -- is
    wrong on this archive, and wrong in a way that looks fine until the audit
    reads it back. From 2020 these papers carry a MediaBox of 652x899 with a
    CropBox inset 28.3pt inside it:

        page.rect     (0, 0, 595.3, 841.9)      <- what get_text measures against
        page.cropbox  (28.3, 28.3, 623.6, 870.2)
        page.mediabox (0, 0, 652.0, 898.6)

    Text coordinates are relative to the CropBox, but set_cropbox takes MediaBox
    coordinates, so every band landed 28.3pt off. The visible symptom was a
    question's PDF holding its predecessor's end fence and not its own -- 137
    audit defects, all of them a one-question shift.

    show_pdf_page's `clip` is in the source page's own coordinate space, the
    same space get_text reports, so no conversion is involved and there is
    nothing to get backwards. Text stays extractable, so the audit can still
    read the result back and confirm what it holds.
    """
    target.parent.mkdir(parents=True, exist_ok=True)

    with open_source(source_pdf) as src:
        out = fitz.open()
        try:
            for region in regions:
                if not region.cropped:
                    out.insert_pdf(src, from_page=region.page, to_page=region.page)
                    continue

                page_rect = src[region.page].rect
                top = page_rect.y0 if region.top is None else max(page_rect.y0, region.top)
                bottom = (
                    page_rect.y1
                    if region.bottom is None
                    else min(page_rect.y1, region.bottom)
                )
                left = (
                    page_rect.x0 if region.left is None else max(page_rect.x0, region.left)
                )
                right = (
                    page_rect.x1
                    if region.right is None
                    else min(page_rect.x1, region.right)
                )
                # A band this thin on either axis means a bad coordinate.
                if bottom - top < 20 or right - left < 20:
                    out.insert_pdf(src, from_page=region.page, to_page=region.page)
                    continue

                clip = fitz.Rect(left, top, right, bottom)
                band = out.new_page(width=clip.width, height=clip.height)
                band.show_pdf_page(
                    fitz.Rect(0, 0, clip.width, clip.height),
                    src,
                    region.page,
                    clip=clip,
                )
            out.save(target)
        finally:
            out.close()


def write_paper(result: PaperResult) -> int:
    """
    Write every segment of a validated paper. Returns files written.

    Files this run did not produce are DELETED first. Without that, a segment
    the current logic declines to emit -- because its mark scheme band could not
    be verified, say -- silently keeps whatever an earlier run left at that
    path. Rebuilding Maths B after its mark schemes were banded turned up 103
    such orphans, holding the very contamination the rebuild existed to remove,
    and the audit read them back as if they were current output.
    """
    paper_dir = OUTPUT_DIR / result.source.key
    written = 0

    wanted = {
        "questions": {f"q{s.number}.pdf" for s in result.segments},
        "markschemes": {f"q{s.number}.pdf" for s in result.segments if s.ms_regions},
    }
    for subdir, keep in wanted.items():
        directory = paper_dir / subdir
        if not directory.is_dir():
            continue
        for stale in directory.glob("q*.pdf"):
            if stale.name not in keep:
                stale.unlink()

    for segment in result.segments:
        extract_regions(
            result.source.qp_path,
            segment.qp_regions,
            paper_dir / "questions" / f"q{segment.number}.pdf",
        )
        written += 1

        if segment.ms_regions and result.source.ms_path is not None:
            extract_regions(
                result.source.ms_path,
                segment.ms_regions,
                paper_dir / "markschemes" / f"q{segment.number}.pdf",
            )
            written += 1

    def describe(regions: tuple[Region, ...] | None) -> list[dict] | None:
        if regions is None:
            return None
        return [
            {
                "page": r.page,
                "top": r.top,
                "bottom": r.bottom,
                "left": r.left,
                "right": r.right,
                "cropped": r.cropped,
            }
            for r in regions
        ]

    manifest = {
        "key": result.source.key,
        "year": result.source.year,
        "season": result.source.season,
        "paper_number": result.source.paper_number,
        "spec": result.source.spec,
        "paper_total": result.source.total_marks,
        "source_qp": str(result.source.qp_path.relative_to(REPO_ROOT)),
        "source_ms": (
            str(result.source.ms_path.relative_to(REPO_ROOT))
            if result.source.ms_path
            else None
        ),
        "total_questions": len(result.segments),
        "total_marks": sum(s.marks for s in result.segments),
        "warnings": result.warnings,
        "questions": [
            {
                "question_number": s.number,
                "marks": s.marks,
                "qp_regions": describe(s.qp_regions),
                "ms_regions": describe(s.ms_regions),
                "has_markscheme": s.ms_regions is not None,
                "cropped": any(r.cropped for r in s.qp_regions),
                "fence_recovered": s.fence_recovered,
            }
            for s in result.segments
        ],
    }
    (paper_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    return written


# ─────────────────────────────────────────────────────────────────────────────
# Audit -- the Phase 1 gate
# ─────────────────────────────────────────────────────────────────────────────


def audit_output() -> int:
    """
    Re-open every written segment and confirm it holds exactly one question, and
    that it is the question named on the file.

    Deliberately independent of everything above: it reads only the written
    PDFs, so it catches a bug in the region logic rather than inheriting one.
    Cropping is what makes this possible -- a cropped page reports
    only the text inside its crop box, so a segment that still holds its
    neighbour shows up here as BUNDLED.

    Returns the number of defects.
    """
    if not OUTPUT_DIR.is_dir():
        print(f"No output to audit at {OUTPUT_DIR}")
        return 0

    checked = bundled = mislabelled = unverifiable = hand_verified = 0
    ms_checked = ms_bundled = ms_wrong_marks = ms_empty = 0
    defects: list[str] = []
    ms_defects: list[str] = []
    ms_typos: list[str] = []

    for paper_dir in sorted(OUTPUT_DIR.iterdir()):
        questions_dir = paper_dir / "questions"
        if not questions_dir.is_dir():
            continue

        is_manual = paper_dir.name in MANUAL_QP_RANGES

        # Questions whose fence was unreadable carry no fence to check against,
        # so they are reported in their own line. Counting them as defects would
        # be false; counting them as passes would be dishonest.
        manifest_path = paper_dir / "manifest.json"
        recovered: set[int] = set()
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            recovered = {
                entry["question_number"]
                for entry in manifest.get("questions", [])
                if entry.get("fence_recovered")
            }
            marks_of = {
                entry["question_number"]: entry["marks"]
                for entry in manifest.get("questions", [])
            }
        else:
            marks_of = {}

        # ── The mark scheme side ────────────────────────────────────────────
        #
        # The point of banding is that a segment now closes with exactly one
        # question's tally. So read each written file back and count them. Two
        # tallies is the original defect -- a neighbour's scheme stapled on --
        # and a tally stating marks the question paper's fence did not is the
        # worse one, a scheme belonging to a different question altogether.
        for ms_path in sorted((paper_dir / "markschemes").glob("q*.pdf")):
            ms_match = re.fullmatch(r"q(\d+)\.pdf", ms_path.name)
            if not ms_match:
                continue
            ms_expected = int(ms_match.group(1))
            ms_checked += 1

            # Counted with the same word-level reader the bands were cut with.
            found = find_physics_tallies(ms_path)
            label = f"{paper_dir.name}/{ms_path.name}"
            named = {t.question for t in found if t.question is not None}

            if not found:
                # The one tally-less scheme (2019 May-Jun Paper 2) is banded on
                # its numbered rows instead; it is counted, not failed.
                ms_empty += 1
            elif len(found) > 1:
                ms_bundled += 1
                ms_defects.append(
                    f"MS BUNDLED   {label}: holds {len(found)} tallies "
                    f"{[(t.question, t.tally.marks) for t in found]}"
                )
            elif named and named != {ms_expected}:
                ms_wrong_marks += 1
                ms_defects.append(
                    f"MS WRONG Q   {label}: closes on question {sorted(named)}'s tally"
                )
            elif ms_expected in marks_of and found[0].tally.marks != marks_of[ms_expected]:
                if named:
                    # Right question by its printed number; the board's own
                    # tally disagrees with its question paper. Reported, not
                    # failed -- the QP fence is authoritative.
                    ms_typos.append(
                        f"MS TALLY TYPO {label}: scheme says {found[0].tally.marks}, "
                        f"QP says {marks_of[ms_expected]}"
                    )
                else:
                    ms_wrong_marks += 1
                    ms_defects.append(
                        f"MS MISMATCH  {label}: tally says {found[0].tally.marks} marks, "
                        f"question is {marks_of[ms_expected]}"
                    )

        for pdf_path in sorted(questions_dir.glob("q*.pdf")):
            match = re.fullmatch(r"q(\d+)\.pdf", pdf_path.name)
            if not match:
                continue
            expected = int(match.group(1))
            checked += 1

            flat = normalise(" ".join(page_texts(pdf_path)))
            found = sorted({int(q) for q, _ in FENCE_RE.findall(flat)})

            if not found:
                if is_manual or expected in recovered:
                    hand_verified += 1
                else:
                    unverifiable += 1
                    defects.append(
                        f"UNVERIFIABLE {paper_dir.name}/{pdf_path.name}: no fence"
                    )
            elif len(found) > 1:
                bundled += 1
                defects.append(
                    f"BUNDLED      {paper_dir.name}/{pdf_path.name}: holds {found}"
                )
            elif found[0] != expected:
                mislabelled += 1
                defects.append(
                    f"MISLABELLED  {paper_dir.name}/{pdf_path.name}: holds Q{found[0]}"
                )

    verified = checked - hand_verified - bundled - mislabelled - unverifiable
    print(f"\n{'=' * 74}\nAUDIT\n{'=' * 74}")
    print(f"  segments checked      : {checked}")
    print(f"  text-verified         : {verified}")
    print(f"  boundary-inferred     : {hand_verified}")
    print(f"  bundled               : {bundled}")
    print(f"  mislabelled           : {mislabelled}")
    print(f"  unverifiable          : {unverifiable}")

    print(f"\n  mark schemes checked  : {ms_checked}")
    print(
        f"  single-tally          : "
        f"{ms_checked - ms_bundled - ms_wrong_marks - ms_empty}"
    )
    print(f"  no tally (format B)   : {ms_empty}")
    print(f"  bundled               : {ms_bundled}")
    print(f"  wrong question/marks  : {ms_wrong_marks}")
    print(f"  board tally typos     : {len(ms_typos)} (reported, not failed)")
    for typo in ms_typos:
        print(f"    {typo}")

    if defects:
        print(f"\n  {len(defects)} question defect(s):")
        for defect in defects[:60]:
            print(f"    {defect}")
        if len(defects) > 60:
            print(f"    ... and {len(defects) - 60} more")

    if ms_defects:
        print(f"\n  {len(ms_defects)} mark scheme defect(s):")
        for defect in ms_defects[:60]:
            print(f"    {defect}")
        if len(ms_defects) > 60:
            print(f"    ... and {len(ms_defects) - 60} more")

    total = bundled + mislabelled + unverifiable + ms_bundled + ms_wrong_marks
    print(
        f"\n  GATE: {'PASS' if total == 0 else 'FAIL'} (question defects "
        f"{bundled + mislabelled + unverifiable}, mark scheme defects "
        f"{ms_bundled + ms_wrong_marks})"
    )
    return total


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="write PDFs (default: dry run)")
    parser.add_argument("--paper", help="process only this paper key, e.g. 2016_jan_1")
    parser.add_argument("--audit", action="store_true", help="audit existing output and exit")
    parser.add_argument("--verbose", action="store_true", help="show per-paper warnings")
    args = parser.parse_args()

    if args.audit:
        return 1 if audit_output() else 0

    papers = discover_papers(verbose=args.verbose)
    if args.paper:
        papers = [p for p in papers if p.key == args.paper]
        if not papers:
            print(f"No paper matching key '{args.paper}'")
            return 1

    mode = "EXECUTE" if args.execute else "DRY RUN"
    print(f"{'=' * 74}")
    print(
        f"PHYSICS (4PH0/4PH1) WORKBOOK SEGMENTATION  [{mode}]  "
        f"{WINDOW_START[0]} {WINDOW_START[1]} to {WINDOW_END[0]} {WINDOW_END[1]}"
    )
    print(f"  source: {SOURCE_DIR.relative_to(REPO_ROOT)}")
    print(f"  output: {OUTPUT_DIR.relative_to(REPO_ROOT)}")
    print(f"{'=' * 74}\n")

    results = [process_paper(p) for p in papers]

    written_files = 0
    for result in results:
        key = result.source.key

        if result.skipped_reason:
            print(f"  SKIP  {key:<20} {result.skipped_reason[:70]}")
            continue

        if result.issues:
            print(f"  FAIL  {key:<20} {len(result.segments)} segments held back")
            for issue in result.issues:
                print(f"          - {issue[:150]}")
            continue

        marks = sum(s.marks for s in result.segments)
        with_ms = sum(1 for s in result.segments if s.ms_regions)
        cropped = sum(1 for s in result.segments if any(r.cropped for r in s.qp_regions))
        flag = f"  ({len(result.warnings)} warnings)" if result.warnings else ""
        print(
            f"  OK    {key:<20} {len(result.segments):>2} questions, {marks} marks, "
            f"{with_ms:>2} mark schemes, {cropped:>2} cropped{flag}"
        )

        if args.verbose:
            for warning in result.warnings:
                print(f"          ~ {warning}")

        if args.execute:
            written_files += write_paper(result)

    ok = [r for r in results if r.ok]
    failed = [r for r in results if r.issues]
    skipped = [r for r in results if r.skipped_reason]

    print(f"\n{'=' * 74}\nSUMMARY\n{'=' * 74}")
    print(f"  papers found      : {len(results)}")
    print(f"  passed validation : {len(ok)}")
    print(f"  failed validation : {len(failed)}")
    print(f"  excluded          : {len(skipped)}")
    print(f"  questions         : {sum(len(r.segments) for r in ok)}")
    print(f"  with mark scheme  : {sum(1 for r in ok for s in r.segments if s.ms_regions)}")
    print(f"  cropped segments  : {sum(1 for r in ok for s in r.segments if any(x.cropped for x in s.qp_regions))}")
    print(f"  warnings          : {sum(len(r.warnings) for r in ok)}")

    if args.execute:
        print(f"  files written     : {written_files}")
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(
            json.dumps(
                {
                    "papers": [
                        {
                            "key": r.source.key,
                            "status": (
                                "excluded" if r.skipped_reason
                                else "failed" if r.issues
                                else "ok"
                            ),
                            "skipped_reason": r.skipped_reason,
                            "issues": r.issues,
                            "warnings": r.warnings,
                            "questions": len(r.segments),
                            "marks": sum(s.marks for s in r.segments),
                        }
                        for r in results
                    ]
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"  report            : {REPORT_PATH.relative_to(REPO_ROOT)}")
    else:
        print("\n  Dry run -- nothing written. Re-run with --execute.")

    if failed:
        print(f"\n  {len(failed)} paper(s) need attention before the gate can pass.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
