"""
Re-segment Edexcel IGCSE Mathematics A (4MA1) HIGHER TIER papers 1H and 2H into
one PDF per question, for the chapterwise workbook.

This is the Maths A counterpart of build_mathsb_workbook_segments.py, and it is
a close port of it: Maths A is an IGCSE, so it uses the IGCSE method -- read
boundaries from the paper's own end-of-question fences, and require independent
signals to agree before writing anything. It is NOT the IAL page-header method
built for S1/P4; Edexcel IGCSE does not print "Question N continued" headers.

Full working notes: docs/workbook-mathsa-plan.md

SCOPE: THE FILENAMES LIE, SO THE COVER DECIDES
----------------------------------------------
The archive files 123 papers as "1H"/"2H"/"1HR"/"2HR", but 38 of them disagree
with their own cover: everything before June 2018 is really 4MA0 Paper 3H/4H,
duplicated under a 4MA1-style name. The old 4MA0 specification had no papers 1H
or 2H at all -- its Higher tier WAS 3H and 4H -- so a "2016 Paper 1H" cannot
exist, and every such file duplicates the correctly-named 3H/4H beside it.

4MA1's first assessment was June 2018, so the window opens at 2018 May-Jun. The
window is enforced by date AND each paper is checked against its own cover, the
same way is_in_scope() gates the P4 build. A paper whose cover cannot be read is
accepted on the date rule alone but flagged, because several genuine 2019 Jan
covers carry no extractable paper code.

Beware: some covers extract only a PhysicsAndMathsTutor watermark
("4MA1 | 2015 | May/June | Paper 1H |"), which is PMT's own -- sometimes wrong --
label rather than the Pearson cover. It is stripped before any cover is read.

WHY PAGE RANGES ARE NOT ENOUGH HERE
-----------------------------------
Measured over the 43 in-scope papers, 13% of fence pages also start a later
question. A page range would staple those questions together -- the exact defect
this rebuild exists to remove. So a segment is a list of REGIONS: each region is
a page plus an optional vertical band, and a band is applied only where a page is
genuinely shared. A question that owns its pages still gets whole pages.

Unlike Maths B, 1H and 2H are the SAME shape -- ~24 short questions each, mean
4.1 marks, nothing above 9 -- so one set of rules covers both papers.

DO NOT CROP WITH set_cropbox
----------------------------
34 of the 43 papers have CropBox != MediaBox. get_text reports coordinates
against the CropBox (page.rect) but set_cropbox takes MediaBox coordinates, so
every band would land ~28pt off and each question's PDF would silently capture
its PREDECESSOR's fence. That cost the Maths B build 137 audit defects. Cropping
here goes through show_pdf_page(..., clip=...), whose clip is in the source
page's own coordinate space.

SIGNALS
-------
1. Fences      "(Total for Question 7 is 2 marks)" -- defines the boundary and
               states the marks. The label is READ, never inferred.
2. Start marks The printed question number in the left margin. Confirms the
               derived start; also supplies the crop top on shared pages.
3. MS marks    The mark scheme's own tally must equal the fence marks.

Plus two paper-level invariants: numbering contiguous from 1, and marks summing
to 100. A paper failing either is held back WHOLE -- never written partially,
because a partially written paper is indistinguishable from a complete one later.

OUTPUT
------
    data/workbook/mathsa/<paper_key>/questions/qN.pdf
    data/workbook/mathsa/<paper_key>/markschemes/qN.pdf
    data/workbook/mathsa/<paper_key>/manifest.json

Nothing here touches data/processed/, which still feeds the test builder.

USAGE
-----
    python scripts/build_mathsa_workbook_segments.py                 # dry run
    python scripts/build_mathsa_workbook_segments.py --execute
    python scripts/build_mathsa_workbook_segments.py --audit
    python scripts/build_mathsa_workbook_segments.py --paper 2022_jan_1H --verbose
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import fitz

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT / "data" / "Ultimate Final IGCSE" / "Mathematics_A"
OUTPUT_DIR = REPO_ROOT / "data" / "workbook" / "mathsa"
REPORT_PATH = REPO_ROOT / "data" / "workbook" / "mathsa_segmentation_report.json"

# Higher tier only -- 1H and 2H, plus the R variants, which are genuinely
# different papers sat in the same session (the same call Maths B made for its
# 1R/2R). Foundation papers are a different content table and are out of scope.
HIGHER_PAPERS = {"1H", "2H", "1HR", "2HR"}

# 4MA1's first assessment was June 2018. Everything filed as 1H/2H before that
# is really 4MA0 3H/4H under a misleading name -- see the module docstring.
# Widening is not possible backwards; the earlier papers are a different
# specification, not merely an earlier year.
WINDOW_START = (2018, "may-jun")

# Cover evidence. `4MA1/1H` is what a genuine paper prints; the tier line is a
# secondary confirmation for the covers that carry no code.
COVER_CODE_RE = re.compile(r"\b(4MA[01])\s*/\s*([0-9][A-Z]{0,2})\b")
COVER_TIER_RE = re.compile(r"\b(Higher|Foundation)\s+Tier\b", re.I)

# PhysicsAndMathsTutor stamps its own label on every page
# ("4MA1 | 2015 | May/June | Paper 1H |"), and it is sometimes WRONG -- reading
# it as cover evidence is how this archive's labels got corrupted in the first
# place. Stripped before any cover is read. Mirrors the rule already recorded in
# scripts/audit_igcse_edexcel_labels.py.
WATERMARK_RE = re.compile(
    r"(?<![0-9A-Za-z])4[A-Z]{2}[01]\s*\|\s*20\d{2}\s*\|\s*[A-Za-z/]+\s*\|\s*"
    r"Paper\s*[0-9A-Za-z]+\s*\|?"
    r"|(?<![0-9A-Za-z])(?:GradeMax\s*)?[A-Za-z_][A-Za-z_ ]{0,28}·\s*20\d{2}\s*·"
    r"[^·]{2,12}·\s*Paper\s*[0-9A-Za-z]+\s*·\s*(?:QP|MS)"
    r"|(?<![0-9A-Za-z])GradeMax",
    re.I,
)

TOTAL_PAPER_MARKS = 100

SEASON_FROM_FOLDER = {
    "Jan": "jan",
    "May-Jun": "may-jun",
    "Oct-Nov": "oct-nov",
    "Specimen": "specimen",
}

# Papers deliberately excluded, with the reason recorded so the exclusion is
# auditable rather than folklore.
EXCLUDED_PAPERS: dict[str, str] = {}

# Papers whose QP carries no usable text layer, so no fence can be read. Each
# entry maps question number -> (first_page, last_page, marks), 0-indexed
# inclusive, established by eye from a rendered contact sheet.
#
# Entries here are subject to exactly the same validation as parsed papers:
# contiguous numbering from 1 and marks summing to 100. A typo fails the paper
# rather than corrupting the workbook.
MANUAL_QP_RANGES: dict[str, dict[int, tuple[int, int, int]]] = {}

# Marks for questions whose end fence exists on the page but cannot be read out
# of the text layer. Supplying the marks lets recover_missing_fence rebuild the
# boundary from the next question's printed start marker.
#
# These are READ OFF THE RENDERED PAGE, not inferred. Each entry must still
# satisfy the paper's 100-mark total or the paper fails, so a misread here is
# caught rather than propagated.
MANUAL_QUESTION_MARKS: dict[str, dict[int, int]] = {
    # All four 2019 Jan papers contain a handful of IMAGE-ONLY pages (95-97
    # characters of watermark, one image, no body text), and every missing fence
    # falls on one of them. This is not the +29 CMap breakage seen elsewhere --
    # there is simply no text layer to read.
    #
    # 2H and 2HR each lose a single fence, so the 100-mark total pins the value
    # with no ambiguity and recover_missing_fence handles them unaided.
    #
    # 1H and 1HR each lose two, so the shortfall could split several ways. These
    # four values were READ OFF THE RENDERED PAGES at 130 dpi, not inferred:
    #   1H  page 5  "(Total for Question 2 is 6 marks)"
    #   1H  page 6  "(Total for Question 3 is 4 marks)"     6 + 4 = 10 shortfall
    #   1HR page 9  "(Total for Question 7 is 3 marks)"
    #   1HR page 12 "(Total for Question 10 is 3 marks)"    3 + 3 =  6 shortfall
    "2019_jan_1H": {2: 6, 3: 4},
    "2019_jan_1HR": {7: 3, 10: 3},
}

# Start page (0-indexed) for a question whose printed left-margin marker cannot
# be read, because the page it opens on is image-only.
#
# recover_missing_fence places a recovered boundary using the NEXT question's
# start marker. That fails when the next question ALSO opens on an image page,
# which is 2019 Jan 1H exactly: Q2's fence and Q3's opening both fall on scanned
# pages, so neither signal survives. Supplying Q3's start page restores the
# second signal without inventing one -- and, like the marks above, it is READ
# OFF THE RENDERED PAGE, not inferred:
#
#   1H page 6 (index 5) opens "3  Here is a biased 5-sided spinner." at the top
#   of the page and closes with "(Total for Question 3 is 4 marks)", so Q3 owns
#   that page alone and Q2 ends with page index 4.
#
# A wrong value here cannot pass silently: the resulting segment still has to
# satisfy contiguous numbering and the 100-mark total, and the audit re-reads
# every written PDF to confirm it opens with its own question number.
MANUAL_START_PAGES: dict[str, dict[int, int]] = {
    "2019_jan_1H": {3: 5},
}

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

# Mark scheme table head. Maths A prints "Question / Working / Answer / Mark /
# Notes"; the FPM and Maths B variants are kept because the wording drifts
# across the series.
MS_HEADER_ROW_RE = re.compile(
    r"Question(?:\s+Working)?\s*\n\s*(?:Number\s*\n\s*)?(?:Scheme|Answer|Working)", re.I
)

# Read immediately after a header row: "1", "2 (a)(i)", "4(a)".
MS_NUMBER_RE = re.compile(
    r"^[^\S\n]*\n?(?:[^\S\n]*(?:Marks?|AO|Notes|Scheme|Answer|Working)[^\S\n]*\n)*"
    r"\s*(\d{1,2})\s*\.?\s*(?:\(\s*[a-z]\s*\)\s*)*",
)

# Mark scheme per-question tally: "Total 2 marks".
MS_TOTAL_RE = re.compile(r"Total\s+(\d{1,3})\s+marks?", re.I)

# Older mark schemes close each part with a bracketed tally instead.
MS_BRACKET_RE = re.compile(r"[\[(]\s*(\d{1,3})\s*[\])]")

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

    key: str  # "2016_jan_1R"
    year: int
    season: str  # "jan"
    paper_number: str  # "1" | "1R" | "2" | "2R"
    qp_path: Path
    ms_path: Path | None


@dataclass(frozen=True)
class Region:
    """
    One page of a segment. `top`/`bottom` are None where the segment owns the
    full page and a float where the page is shared and must be cropped.
    """

    page: int
    top: float | None = None
    bottom: float | None = None

    @property
    def cropped(self) -> bool:
        return self.top is not None or self.bottom is not None


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
    """`..._Paper_1HR_QP.pdf` -> `1HR`."""
    match = re.search(r"_Paper_(\d+[A-Z]{0,2})_QP\.pdf$", filename, re.I)
    return match.group(1).upper() if match else None


SEASON_ORDER = {"jan": 0, "may-jun": 1, "oct-nov": 2, "specimen": 3}


def within_window(year: int, season: str) -> bool:
    """True from WINDOW_START (2018 May-Jun) onwards."""
    start_year, start_season = WINDOW_START
    if year != start_year:
        return year > start_year
    return SEASON_ORDER.get(season, 99) >= SEASON_ORDER[start_season]


def read_cover_code(qp_path: Path) -> tuple[str | None, str | None]:
    """
    The paper code and tier printed on the paper's OWN cover, or (None, None).

    The watermark is stripped first: PMT stamps its own label on every page and
    it is sometimes wrong -- believing it is how this archive's labels became
    unreliable. Several genuine 2019 Jan covers carry no extractable code at
    all, so a None here is not evidence against a paper.
    """
    try:
        with fitz.open(qp_path) as doc:
            text = WATERMARK_RE.sub(" ", doc[0].get_text())
    except Exception:  # noqa: BLE001 - an unreadable cover is not fatal
        return None, None

    code_match = COVER_CODE_RE.search(text)
    tier_match = COVER_TIER_RE.search(text)
    code = f"{code_match.group(1)}/{code_match.group(2)}" if code_match else None
    return code, (tier_match.group(1).title() if tier_match else None)


def discover_papers(verbose: bool = False) -> list[PaperSource]:
    """
    Find every in-scope Higher-tier QP, pairing each with its mark scheme.

    Scope is Higher tier (1H/2H and the R variants) from 2018 May-Jun onwards.
    THE FILENAME IS NOT TRUSTED: 38 of the archive's 123 Higher-tier files are
    really 4MA0 3H/4H duplicated under a 4MA1-style name, so each candidate is
    also checked against its own cover. A cover that reads 4MA0, or a different
    paper, is rejected outright; a cover that reads nothing is accepted on the
    date rule but reported, because that is the benign 2019 Jan case.
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
            if season is None:
                print(f"  ! unknown session folder, skipped: {session_dir}")
                continue
            if not within_window(year, season):
                continue

            for qp_path in sorted(session_dir.glob("*_QP.pdf")):
                paper_number = parse_paper_number(qp_path.name)
                if paper_number is None:
                    print(f"  ! unparseable paper number, skipped: {qp_path.name}")
                    continue
                if paper_number not in HIGHER_PAPERS:
                    continue

                key = f"{year}_{season}_{paper_number}"
                code, tier = read_cover_code(qp_path)
                if code is not None and code != f"4MA1/{paper_number}":
                    rejected.append(f"{key}: cover says {code}")
                    continue
                if tier == "Foundation":
                    rejected.append(f"{key}: cover says Foundation tier")
                    continue
                if code is None and verbose:
                    print(f"  . {key}: no cover code extractable, accepted on date")

                ms_path = qp_path.with_name(qp_path.name.replace("_QP.pdf", "_MS.pdf"))
                papers.append(
                    PaperSource(
                        key=key,
                        year=year,
                        season=season,
                        paper_number=paper_number,
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

    shortfall = TOTAL_PAPER_MARKS - sum(marks for _, marks, _ in fences.values())
    if shortfall <= 0:
        return fences, notes

    if len(missing) == 1 and missing[0] not in manual_marks:
        marks_for = {missing[0]: shortfall}
        source = "the 100-mark paper total"
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
                start = (previous_page + 1, None)  # type: ignore[assignment]

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


def ms_totals_in_order(ms_path: Path) -> list[tuple[int, int]]:
    """
    Format A delimiter: every "Total N marks" line as (page_index, marks), in
    document order.

    Used by the 2016, 2017 and 2020-2022 mark schemes, which box each question
    separately and close each box with its own tally.
    """
    found: list[tuple[int, int]] = []
    with fitz.open(ms_path) as doc:
        for index, page in enumerate(doc):
            for match in MS_TOTAL_RE.finditer(normalise(page.get_text())):
                found.append((index, int(match.group(1))))
    return found


def ms_question_rows(ms_path: Path) -> list[tuple[int, int, int | None]]:
    """
    Format B delimiter: the question-number rows of a continuous mark scheme
    table, as (page_index, question, marks_or_None).

    The 2018 and 2019 mark schemes print no per-question total at all. Instead
    one table runs the length of the document with the question number in the
    leftmost column and the question's mark in the rightmost numeric column:

        x=77.6  "3"   ...working...   x=536.6  "2"

    So a row is a standalone integer hard against the left edge, and its mark is
    the standalone integer on the far side of the page at the same height. Both
    columns are located per page rather than hardcoded, since the layout shifts
    between portrait and landscape pages.
    """
    rows: list[tuple[int, int, int | None]] = []

    with fitz.open(ms_path) as doc:
        for index, page in enumerate(doc):
            width = page.rect.width
            left_limit = page.rect.x0 + width * 0.14
            right_floor = page.rect.x0 + width * 0.55

            left: list[tuple[float, int]] = []
            right: list[tuple[float, int]] = []

            try:
                blocks = page.get_text("dict")["blocks"]
            except Exception:  # noqa: BLE001
                continue

            for block in blocks:
                for line in block.get("lines", []):
                    text = "".join(s["text"] for s in line.get("spans", [])).strip()
                    if not re.fullmatch(r"\d{1,2}", text):
                        continue
                    x0, y0 = line["bbox"][0], line["bbox"][1]
                    if x0 < left_limit:
                        left.append((y0, int(text)))
                    elif x0 > right_floor:
                        right.append((y0, int(text)))

            for y0, question in sorted(left):
                mark = next(
                    (value for my, value in sorted(right) if abs(my - y0) <= 6), None
                )
                rows.append((index, question, mark))

    return rows


def align_sequences(expected: list[int], observed: list[int]) -> dict[int, int]:
    """
    Longest common subsequence between the paper's per-question marks and the
    mark scheme's tallies, as {index_in_expected: index_in_observed}.

    Demanding an exact whole-sequence match was too brittle: several papers
    print one tally more or fewer than they have questions -- an extra "Total
    ... marks" in the general guidance, or one question whose tally is missing.
    A strict comparison threw away the entire mark scheme over a single
    discrepancy. Aligning instead keeps every question whose marks agree in
    order and drops only the ones that genuinely do not line up.
    """
    n, k = len(expected), len(observed)
    table = [[0] * (k + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(k - 1, -1, -1):
            table[i][j] = (
                table[i + 1][j + 1] + 1
                if expected[i] == observed[j]
                else max(table[i + 1][j], table[i][j + 1])
            )

    pairs: dict[int, int] = {}
    i = j = 0
    while i < n and j < k:
        if expected[i] == observed[j]:
            pairs[i] = j
            i += 1
            j += 1
        elif table[i + 1][j] >= table[i][j + 1]:
            i += 1
        else:
            j += 1
    return pairs


def locate_ms_blocks(
    ms_path: Path, fences: dict[int, tuple[int, int, float]]
) -> tuple[dict[int, tuple[Region, ...]], list[str]]:
    """
    Map question number -> the mark scheme pages that hold it.

    Maths A mark schemes come in the same two layouts as Maths B's, and
    neither can be read
    geometrically with any confidence: pages mix portrait and landscape, and
    several print their table cells as rotated text, so "the line below this one"
    is not a well-defined idea. Blocks are therefore delimited by CONTENT -- the
    tally that closes each question, or the numbered row that opens it -- and
    emitted as whole pages.

    That means a Paper 1 mark scheme page shared by three questions is attached
    to all three. This is deliberate. Cropping it would mean trusting
    coordinates that have already proved unreliable, and the cost of the
    imprecision is small: adjacent questions land in different chapters of the
    workbook, so a neighbour's scheme is not the answer to anything nearby. The
    QP side, which is what a student actually attempts, is cropped exactly.

    A block is attached only when the mapping from questions to blocks is
    FORCED, not merely consistent -- see the note on skipped tallies below,
    which is the real safeguard. A wrong mark scheme is worse than a missing
    one.
    """
    warnings: list[str] = []
    numbers = sorted(fences)
    expected_marks = [fences[q][1] for q in numbers]

    anchors: dict[int, int] = {}  # question -> page where its block starts
    note = ""

    # ── Format A: align the tally sequence against the paper's marks ─────────
    #
    # NOTE ON WHAT THIS DOES AND DOES NOT PROVE. Aligning on marks and then
    # "checking" the marks agree is circular -- LCS guarantees agreement by
    # construction. The real safeguard is how much had to be skipped to reach
    # that agreement:
    #
    #   skipped questions = 0  every question found a tally, so any extra
    #                          tallies are noise (a stray "Total ... marks" in
    #                          the guidance) and the mapping is forced.
    #   skipped tallies   = 0  every tally was consumed, so unmatched questions
    #                          simply have no mark scheme. Also forced.
    #
    # Only when BOTH sides skip is the mapping genuinely ambiguous, because a
    # question could then have been paired with a different tally of equal
    # value. Measured across the archive: 32 papers match exactly and never
    # reach this path, 5 skip on one side only, and 2 skip on both -- of which
    # one (2016 May-Jun 2R, 3 skipped each way) is rejected outright rather
    # than risk attaching another question's mark scheme.
    totals = ms_totals_in_order(ms_path)
    if totals:
        alignment = align_sequences(expected_marks, [m for _, m in totals])
        skipped_questions = len(numbers) - len(alignment)
        skipped_tallies = len(totals) - len(alignment)
        unambiguous = (
            min(skipped_questions, skipped_tallies) == 0
            or skipped_questions + skipped_tallies <= 2
        )

        if len(alignment) >= 0.6 * len(numbers) and unambiguous:
            for position, total_index in alignment.items():
                anchors[numbers[position]] = totals[total_index][0]
            note = (
                f"mark scheme read as per-question tallies: "
                f"{len(alignment)}/{len(numbers)} aligned "
                f"(skipped {skipped_questions} question(s), "
                f"{skipped_tallies} tally/tallies)"
            )
        elif len(alignment) >= 0.6 * len(numbers):
            warnings.append(
                f"mark scheme tallies align only ambiguously "
                f"({skipped_questions} question(s) and {skipped_tallies} "
                f"tally/tallies unmatched, so a question could pair with the "
                f"wrong tally of equal value) -- no mark schemes attached"
            )
            return {}, warnings

    # ── Format B: the continuous table's own numbered rows ───────────────────
    if not anchors:
        rows = ms_question_rows(ms_path)
        confirmed = 0
        seen_page = -1
        for page, question, mark in rows:
            if question not in fences or question in anchors:
                continue
            # Blocks run in question order, so a row that jumps backwards is a
            # stray integer from the working column, not a question row.
            if page < seen_page:
                continue
            anchors[question] = page
            seen_page = page
            if mark is not None and mark == fences[question][1]:
                confirmed += 1

        if len(anchors) < 0.6 * len(numbers):
            anchors = {}
        else:
            note = (
                f"mark scheme read as a continuous table: {len(anchors)} numbered "
                f"rows, {confirmed} also confirmed by their printed mark"
            )

    if not anchors:
        warnings.append(
            f"mark scheme could not be aligned to the paper "
            f"({len(totals)} tallies for {len(numbers)} questions, and no readable "
            f"numbered table) -- no mark schemes attached"
        )
        return {}, warnings

    if len(anchors) < len(numbers):
        note += f" -- {len(numbers) - len(anchors)} question(s) unmatched"
    warnings.append(note)

    # A block runs from its own anchor page to the page before the next one.
    ordered = sorted(anchors.items())
    blocks: dict[int, tuple[int, int]] = {}
    for position, (question, page) in enumerate(ordered):
        end = ordered[position + 1][1] if position + 1 < len(ordered) else page
        blocks[question] = (page, max(page, end))

    kept: dict[int, tuple[Region, ...]] = {}
    with fitz.open(ms_path) as doc:
        last_page = doc.page_count - 1

    for question, (start, end) in sorted(blocks.items()):
        if question not in fences:
            warnings.append(f"mark scheme has question {question} but the QP does not")
            continue
        start = max(0, min(start, last_page))
        end = max(start, min(end, last_page))
        kept[question] = tuple(Region(page=p) for p in range(start, end + 1))

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
    if total != TOTAL_PAPER_MARKS:
        per_question = ", ".join(f"{q}:{m}" for q, (_, m, _) in sorted(fences.items()))
        issues.append(
            f"marks sum to {total}, expected {TOTAL_PAPER_MARKS} ({{{per_question}}})"
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
        if first_page not in (last_page, last_page + 1):
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
        )
        recovered_numbers = set(fences) - before
        result.warnings.extend(recovery_notes)

        bounds, problems = derive_bounds(fences, start_markers)
        result.issues.extend(problems)
        regions = build_regions(bounds)

    result.issues.extend(validate_paper(fences, regions))

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

    with fitz.open(source_pdf) as src:
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
                if bottom - top < 20:  # a band this thin means a bad coordinate
                    out.insert_pdf(src, from_page=region.page, to_page=region.page)
                    continue

                clip = fitz.Rect(page_rect.x0, top, page_rect.x1, bottom)
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
    """Write every segment of a validated paper. Returns files written."""
    paper_dir = OUTPUT_DIR / result.source.key
    written = 0

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
            {"page": r.page, "top": r.top, "bottom": r.bottom, "cropped": r.cropped}
            for r in regions
        ]

    manifest = {
        "key": result.source.key,
        "year": result.source.year,
        "season": result.source.season,
        "paper_number": result.source.paper_number,
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
    defects: list[str] = []

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

    if defects:
        print(f"\n  {len(defects)} defect(s):")
        for defect in defects[:60]:
            print(f"    {defect}")
        if len(defects) > 60:
            print(f"    ... and {len(defects) - 60} more")

    total = bundled + mislabelled + unverifiable
    print(f"\n  GATE: {'PASS' if total == 0 else 'FAIL'} "
          f"(bundled + mislabelled + unverifiable = {total})")
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
        f"MATHS A (4MA1) HIGHER WORKBOOK SEGMENTATION  [{mode}]  "
        f"{WINDOW_START[0]} {WINDOW_START[1]} onwards"
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
