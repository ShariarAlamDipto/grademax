"""
Re-segment Further Pure Maths (4PM1) papers for the chapterwise workbook.

WHY THIS EXISTS
---------------
The existing segments in `data/processed/Further Pure Maths Processed/` are 84%
correct: of 435 segments covering 2016-2022, 44 staple 2-3 questions into one
PDF and 17 sit under the wrong question number.

Root cause: the old segmenter detected question *starts* with a left-margin
regex and assigned everything between two detected starts to the earlier
question. A missed start silently merges questions; a misread start mislabels
them. Both failure modes are invisible without an independent check.

This script inverts the approach. Every Edexcel FPM question ends with the
fence `Total for Question N is X marks`, which states its own question number
and its own mark tally. Reading boundaries from the fence means the label comes
from the paper rather than from our inference, and no fence can be "missed"
without the validation below failing loudly.

Three independent signals must agree before anything is written:

  1. Fences          -- question numbers and marks, read from the QP.
  2. Left-margin     -- the printed question number at the top of each start
     start markers      page, cross-checked against fence-derived starts.
  3. Mark scheme     -- per-question MS blocks whose own mark totals must
     mark totals        equal the QP fence marks for the same question.

Plus two paper-level invariants: question numbers form a contiguous run from 1,
and the marks sum to 100.

A paper failing any check is REPORTED AND SKIPPED, never written. Partial
output is worse than no output here, because a wrong segment in the workbook is
a wrong page in a book a student is holding.

OUTPUT
------
Writes to `data/workbook/fpm/` -- a NEW tree. The live
`data/processed/Further Pure Maths Processed/` corpus feeds the test builder and
worksheet generator and is left untouched, so this is fully reversible.

USAGE
-----
    python scripts/build_fpm_workbook_segments.py                 # dry run
    python scripts/build_fpm_workbook_segments.py --execute       # write PDFs
    python scripts/build_fpm_workbook_segments.py --paper 2016_may-jun_1
    python scripts/build_fpm_workbook_segments.py --audit         # verify output
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF

from lib import ms_bands

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT / "data" / "Ultimate Final IGCSE" / "Further_Pure_Maths"
OUTPUT_DIR = REPO_ROOT / "data" / "workbook" / "fpm"
REPORT_PATH = REPO_ROOT / "data" / "workbook" / "fpm_segmentation_report.json"

YEAR_START = 2016
YEAR_END = 2022

TOTAL_PAPER_MARKS = 100

# Papers deliberately excluded, with the reason recorded so the exclusion is
# auditable rather than folklore.
EXCLUDED_PAPERS: dict[str, str] = {
    "2017_oct-nov_1": "Extracted text is byte-identical to 2016 Specimen Paper 1 "
                      "-- these are the specimen papers refiled under a session "
                      "that was never sat. Including them duplicates ~10 questions.",
    "2017_oct-nov_2": "Extracted text is byte-identical to 2016 Specimen Paper 2 "
                      "-- see 2017_oct-nov_1.",
}

# Papers whose QP is an image-only scan carrying no extractable text, so no
# fence exists to read. Each entry maps question number -> (first_page,
# last_page, marks) with 0-indexed inclusive pages.
#
# Pages are established by visual inspection of the rendered page tops (every
# question opens with its number, and every following page is headed "Question N
# continued", so the boundaries are unambiguous). Marks are read from the mark
# scheme, which does carry text.
#
# These entries are subject to exactly the same validation as parsed papers:
# contiguous numbering from 1 and marks summing to 100. A typo here fails the
# paper rather than corrupting the workbook.
MANUAL_QP_RANGES: dict[str, dict[int, tuple[int, int, int]]] = {
    # 2019 May-Jun Paper 1 is a scan: 36 pages, ~3.7k chars of text, all of it
    # our own watermark. Pages verified against a rendered contact sheet;
    # marks read from the mark scheme's per-question totals (sum = 100).
    "2019_may-jun_1": {
        1: (2, 2, 4),
        2: (3, 4, 3),
        3: (5, 6, 6),
        4: (7, 8, 6),
        5: (9, 10, 5),
        6: (11, 14, 11),
        7: (15, 18, 12),
        8: (19, 22, 10),
        9: (23, 26, 12),
        10: (27, 30, 14),
        11: (31, 35, 17),
    },
}

SEASON_FROM_FOLDER = {
    "Jan": "jan",
    "May-Jun": "may-jun",
    "Oct-Nov": "oct-nov",
    "Specimen": "specimen",
}

# ─────────────────────────────────────────────────────────────────────────────
# Text patterns
# ─────────────────────────────────────────────────────────────────────────────

# Fence: "(Total for Question 7 is 11 marks)". Whitespace is normalised before
# matching because PyMuPDF injects newlines mid-phrase.
#
# The connector varies across the series: most papers print "is", but the 2016
# specimen uses "=" ("Total for Question 10 = 15 marks"). Accepting only "is"
# silently loses that question and 15 marks off the paper total.
FENCE_RE = re.compile(
    r"Total\s+for\s+Question\s+(\d{1,2})\s*(?:is|=|:)\s*(\d{1,3})\s+marks?", re.I
)

# A bare fence with no mark tally -- used only to detect that we under-matched.
FENCE_LOOSE_RE = re.compile(r"Total\s+for\s+Question\s+(\d{1,2})", re.I)

# Finding a mark scheme block -- its header row and the question number under
# it -- lives in lib/ms_bands.py, which reads both WITH COORDINATES so a block
# becomes a band rather than a range of whole pages. The flat-text regexes that
# used to do it here are gone with the code that used them. The point they
# recorded still holds and is kept in find_block_headers: detecting the header
# row and reading its number are separate steps, because several papers print a
# plainly visible header whose number cannot be read, and requiring both at once
# loses the block entirely.

# Mark scheme per-question tally: "Total 9 marks".
MS_TOTAL_RE = re.compile(r"Total\s+(\d{1,3})\s+marks?", re.I)

# Older mark schemes print no "Total N marks" line and instead close each part
# with a bracketed tally, the last of which is the question total: "(3) (4) (7)".
MS_BRACKET_RE = re.compile(r"[\[(]\s*(\d{1,3})\s*[\])]")

# The printed question number at the top-left of a question's first page.
START_MARKER_MAX_X = 80.0
START_MARKER_MAX_Y = 260.0
# Page-number footers sit at the same x but near the bottom; excluded by max_y.


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PaperSource:
    """One question paper plus its mark scheme, located on disk."""

    key: str  # "2016_may-jun_1"
    year: int
    season: str  # "may-jun"
    paper_number: str  # "1" | "1R"
    qp_path: Path
    ms_path: Path | None


@dataclass(frozen=True)
class Region:
    """
    One page of a mark scheme segment, with an optional band across it.

    The question paper side still works in whole page ranges, because an FPM
    question owns its pages outright. The mark scheme side does not: Edexcel
    packs two short questions onto one mark scheme page, and a page range then
    hands both of them to each question. See `locate_ms_bands`.
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
    qp_pages: tuple[int, int]  # inclusive [start, end], 0-indexed
    ms_regions: tuple[Region, ...] | None


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
    """`..._Paper_1R_QP.pdf` -> `1R`."""
    match = re.search(r"_Paper_(\d+R?)_QP\.pdf$", filename, re.I)
    return match.group(1).upper() if match else None


def discover_papers() -> list[PaperSource]:
    """Find every QP in the year range, pairing each with its mark scheme."""
    if not SOURCE_DIR.is_dir():
        raise FileNotFoundError(f"Source archive not found: {SOURCE_DIR}")

    papers: list[PaperSource] = []

    for year in range(YEAR_START, YEAR_END + 1):
        year_dir = SOURCE_DIR / str(year)
        if not year_dir.is_dir():
            continue

        for session_dir in sorted(p for p in year_dir.iterdir() if p.is_dir()):
            season = SEASON_FROM_FOLDER.get(session_dir.name)
            if season is None:
                print(f"  ! unknown session folder, skipped: {session_dir}")
                continue

            for qp_path in sorted(session_dir.glob("*_QP.pdf")):
                paper_number = parse_paper_number(qp_path.name)
                if paper_number is None:
                    print(f"  ! unparseable paper number, skipped: {qp_path.name}")
                    continue

                ms_path = qp_path.with_name(qp_path.name.replace("_QP.pdf", "_MS.pdf"))
                papers.append(
                    PaperSource(
                        key=f"{year}_{season}_{paper_number}",
                        year=year,
                        season=season,
                        paper_number=paper_number,
                        qp_path=qp_path,
                        ms_path=ms_path if ms_path.is_file() else None,
                    )
                )

    return papers


# ─────────────────────────────────────────────────────────────────────────────
# Extraction
# ─────────────────────────────────────────────────────────────────────────────


def page_texts(pdf_path: Path) -> list[str]:
    """Raw per-page text. Never raises -- an unreadable page yields ''."""
    with fitz.open(pdf_path) as doc:
        out = []
        for page in doc:
            try:
                out.append(page.get_text())
            except Exception:  # noqa: BLE001 - a bad page must not kill the paper
                out.append("")
        return out


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def find_fences(pages: list[str]) -> tuple[dict[int, tuple[int, int]], list[str]]:
    """
    Map question number -> (end_page_index, marks), read from the QP's own
    end-of-question fences.

    Returns the map plus any structural complaints (duplicate fences, fences
    that matched loosely but not with a mark tally).
    """
    fences: dict[int, tuple[int, int]] = {}
    problems: list[str] = []

    for index, raw in enumerate(pages):
        flat = normalise(raw)

        for question_str, marks_str in FENCE_RE.findall(flat):
            question = int(question_str)
            marks = int(marks_str)
            if question in fences:
                problems.append(
                    f"question {question} fenced twice "
                    f"(pages {fences[question][0]} and {index})"
                )
                continue
            fences[question] = (index, marks)

        loose = {int(q) for q in FENCE_LOOSE_RE.findall(flat)}
        unmatched = loose - {int(q) for q, _ in FENCE_RE.findall(flat)}
        for question in sorted(unmatched):
            if question not in fences:
                problems.append(
                    f"page {index}: found 'Total for Question {question}' but "
                    f"could not read its mark tally"
                )

    return fences, problems


def find_start_markers(pdf_path: Path) -> dict[int, list[int]]:
    """
    Map question number -> page indices carrying that number as a printed
    left-margin marker near the top of the page.

    This is the independent second signal. It is never used to define a
    boundary -- only to confirm the fence-derived one.
    """
    markers: dict[int, list[int]] = {}

    with fitz.open(pdf_path) as doc:
        for index, page in enumerate(doc):
            try:
                blocks = page.get_text("dict")["blocks"]
            except Exception:  # noqa: BLE001
                continue

            for block in blocks:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span["text"].strip().rstrip(".")
                        if not re.fullmatch(r"\d{1,2}", text):
                            continue
                        x0, y0 = span["bbox"][0], span["bbox"][1]
                        if x0 < START_MARKER_MAX_X and y0 < START_MARKER_MAX_Y:
                            markers.setdefault(int(text), []).append(index)

    return markers


def derive_ranges(
    fences: dict[int, tuple[int, int]],
    start_markers: dict[int, list[int]],
) -> tuple[dict[int, tuple[int, int]], list[str]]:
    """
    Turn fences into inclusive page ranges.

    Question N ends on its fence page. It starts on the page after question
    N-1's fence. Question 1 starts at its printed marker, since nothing fences
    the cover pages off for us.
    """
    problems: list[str] = []
    numbers = sorted(fences)
    if not numbers:
        return {}, ["no fences found at all"]

    ranges: dict[int, tuple[int, int]] = {}
    previous_end: int | None = None

    for question in numbers:
        end_page = fences[question][0]

        if previous_end is None:
            candidates = [p for p in start_markers.get(question, []) if p <= end_page]
            if not candidates:
                problems.append(
                    f"question {question} is the first question but has no printed "
                    f"start marker at or before its fence on page {end_page}"
                )
                start_page = max(0, end_page - 1)
            else:
                start_page = min(candidates)
        else:
            start_page = previous_end + 1

        if start_page > end_page:
            problems.append(
                f"question {question}: derived start page {start_page} is after "
                f"its fence page {end_page}"
            )
            continue

        ranges[question] = (start_page, end_page)
        previous_end = end_page

    return ranges, problems


def cross_check_starts(
    ranges: dict[int, tuple[int, int]],
    start_markers: dict[int, list[int]],
) -> list[str]:
    """
    Confirm each fence-derived start page carries that question's printed
    number. Disagreement is a warning, not a hard failure: a handful of
    questions begin mid-page after a short predecessor, and some papers render
    the marker as a glyph the text layer misses.
    """
    warnings: list[str] = []

    for question, (start_page, _) in sorted(ranges.items()):
        observed = start_markers.get(question, [])
        if start_page not in observed:
            warnings.append(
                f"question {question}: derived start page {start_page} carries no "
                f"printed '{question}' marker (markers seen on {observed or 'no pages'})"
            )

    return warnings


def align_sequences(expected: list[int], observed: list[int]) -> dict[int, int]:
    """
    Longest common subsequence between the paper's per-question marks and the
    mark scheme's tallies, as {index_in_expected: index_in_observed}.

    Same routine the Maths B segmenter uses, for the same reason: several papers
    print one tally more or fewer than they have questions, and a strict
    comparison threw away a whole mark scheme over a single discrepancy.
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


def locate_ms_bands(
    ms_path: Path, fences: dict[int, tuple[int, int]]
) -> tuple[dict[int, ms_bands.Band], set[int], list[str]]:
    """
    Map question number -> the slice of the mark scheme that holds it, plus the
    set of questions whose block number was inferred rather than read.

    WHY THIS REPLACED A PAGE RANGE
    ------------------------------
    A block used to be a range of whole pages, running from the page carrying
    its header to the page before the next header. That is exact whenever a
    question owns its pages, which is usually true of Further Pure -- 11 long
    questions over ~16 mark scheme pages. It is wrong whenever two questions
    share a page, and then it is wrong in both directions at once: each of the
    two gets a PDF containing both schemes.

    Measured over the archive that was 5 segments, among them 2020 Jan 2R q1 and
    q2, which both resolved to mark scheme page 6 and so both opened on
    question 1's scheme followed by question 2's.

    So a block is now a band. Two delimiters are available and the more precise
    one is preferred:

      the tally      Papers from 2018 on close each block with "Total N marks".
                     The band runs from the previous block's tally to its own,
                     and can then be verified by reading it back -- exactly one
                     tally inside, stating exactly the fence's marks.

      the header row The older papers print no tally, so the band runs from its
                     own "Question number / Scheme / Marks" row to the next
                     one. Where the header does not restate the question number
                     -- which Edexcel omits whenever a question runs on past a
                     page break -- the block is assigned the next question in
                     sequence and returned as provisional, for check_ms_marks to
                     confirm or drop. That is the same rule the page-range
                     version used; only the boundary has changed.
    """
    warnings: list[str] = []
    numbers = sorted(fences)
    if not numbers:
        return {}, set(), ["no fences, so no mark scheme blocks"]

    with fitz.open(ms_path) as doc:
        last_page = doc.page_count - 1

    # ── Preferred: the per-question tally ────────────────────────────────────
    tallies = ms_bands.find_tallies(ms_path)
    if tallies:
        expected = [fences[q][1] for q in numbers]
        alignment = align_sequences(expected, [t.marks for t in tallies])
        if len(alignment) >= 0.6 * len(numbers):
            assignment = {numbers[pos]: index for pos, index in alignment.items()}
            # Headers let a band skip the previous question's Guidance table,
            # which sits AFTER that question's tally in several papers.
            bands = ms_bands.bands_from_tallies(
                tallies, assignment, ms_bands.find_block_headers(ms_path)
            )

            kept: dict[int, ms_bands.Band] = {}
            rejected: list[str] = []
            for question, band in bands.items():
                inside = ms_bands.verify_band(tallies, band)
                if len(inside) == 1 and inside[0] == fences[question][1]:
                    kept[question] = band
                else:
                    rejected.append(f"q{question}")

            if kept:
                warnings.append(
                    f"mark scheme banded on per-question tallies: "
                    f"{len(kept)}/{len(numbers)} questions"
                )
                if rejected:
                    warnings.append(
                        "tally band did not verify for " + ", ".join(sorted(rejected))
                    )
                filled = fill_tally_gaps(ms_path, numbers, kept, last_page, warnings)
                return filled, set(), warnings

    # ── Fallback: the block header rows ──────────────────────────────────────
    headers = ms_bands.find_block_headers(ms_path)
    if not headers:
        return {}, set(), ["no mark scheme question headers found"]

    # A header that does not restate the question number CONTINUES the block
    # above it rather than opening a new one. Edexcel prints such a header at
    # the top of every notes page and at every page break inside a long
    # question, so reading one as "the next question in sequence" walks the
    # whole mark scheme out of step: in 2018 Jan Paper 2 that made question 8's
    # scheme out of question 7's notes page, question 10's out of question 9's,
    # and so on down the paper.
    #
    # Leaving those headers unassigned is what keeps the notes attached to their
    # own question -- bands_from_headers ends a block at the next ASSIGNED
    # header, so an unassigned one falls inside the block it belongs to.
    assignment: dict[int, int] = {}
    provisional: set[int] = set()
    last_assigned = 0

    for index, header in enumerate(headers):
        explicit = header.question
        if explicit is None:
            continue
        if explicit <= last_assigned or explicit > numbers[-1]:
            continue  # a repeat of the current block's own header, or noise
        if explicit in assignment:
            continue

        assignment[explicit] = index
        last_assigned = explicit

    headers, assignment = anchor_unheaded_questions(
        ms_path, numbers, headers, assignment, warnings
    )

    bands = ms_bands.bands_from_headers(
        headers, assignment, last_page=last_page, runs_to_end=numbers[-1]
    )
    warnings.append(
        f"mark scheme banded on header rows: {len(bands)}/{len(numbers)} questions, "
        f"{len(provisional)} inferred from sequence"
    )
    return bands, provisional, warnings


def _first_anchor(
    candidates: list[ms_bands.BlockHeader],
    question: int,
    after: tuple[int, float] | None,
    before: tuple[int, float] | None,
) -> ms_bands.BlockHeader | None:
    """The earliest anchor naming `question` strictly between two positions."""
    inside = [
        c
        for c in candidates
        if c.question == question and ms_bands.position_between(c, after, before)
    ]
    return min(inside, key=lambda c: (c.page, c.lo)) if inside else None


def anchor_unheaded_questions(
    ms_path: Path,
    numbers: list[int],
    headers: list[ms_bands.BlockHeader],
    assignment: dict[int, int],
    warnings: list[str],
) -> tuple[list[ms_bands.BlockHeader], dict[int, int]]:
    """
    Give a header-banded question with no readable header an anchor at its own
    printed label, so it gets a band AND stops leaking into the one above.

    Without this, bands_from_headers runs the previous question's block on to
    the next assigned header, so the unheaded question's scheme is printed as
    part of its neighbour's and it gets none of its own. That was 5 of the 9
    printed-workbook questions with no mark scheme (2018 May-Jun P2 q2, 2019
    Jan P2 q5, 2019 May-Jun P2 q4, 2020 Oct-Nov P1 q4 and P2 q8).

    The label is only searched for strictly between the two neighbouring
    assigned headers, so a stray digit elsewhere cannot be taken for it.
    """
    missing = [q for q in numbers if q not in assignment]
    if not missing:
        return headers, assignment

    labels = ms_bands.find_question_labels(ms_path)
    added: dict[int, ms_bands.BlockHeader] = {}
    for question in missing:
        lower = [q for q in assignment if q < question]
        upper = [q for q in assignment if q > question]
        after = None
        if lower:
            h = headers[assignment[max(lower)]]
            after = (h.page, h.lo)
        before = None
        if upper:
            h = headers[assignment[min(upper)]]
            before = (h.page, h.lo)
        label = _first_anchor(labels, question, after, before)
        if label is not None:
            added[question] = label

    if not added:
        return headers, assignment

    by_question = {q: headers[i] for q, i in assignment.items()} | added
    merged = sorted(set(headers) | set(added.values()), key=lambda h: (h.page, h.lo))
    position = {h: i for i, h in enumerate(merged)}
    warnings.append(
        "mark scheme header unreadable, banded from the printed question label "
        f"for questions {sorted(added)}"
    )
    return merged, {q: position[h] for q, h in by_question.items()}


def fill_tally_gaps(
    ms_path: Path,
    numbers: list[int],
    kept: dict[int, ms_bands.Band],
    last_page: int,
    warnings: list[str],
) -> dict[int, ms_bands.Band]:
    """
    Band a question the tally method could not, from its own header (or label)
    to where the next banded question begins.

    A tally goes unmatched when the paper words it differently ("Total is 16
    marks", 2021 May-Jun P2 q4) or prints none for that question (2022 May-Jun
    P1R q4, 2019 May-Jun P2R q11). The whole block then belonged to nobody --
    4 of the 9 printed-workbook questions with no mark scheme.

    The anchor is only searched for after the previous banded question ENDS
    and before the next one starts, so it can never overlap either neighbour.
    """
    missing = [q for q in numbers if q not in kept]
    if not missing:
        return kept

    candidates = ms_bands.find_block_headers(ms_path) + ms_bands.find_question_labels(
        ms_path
    )
    filled = dict(kept)
    for question in missing:
        lower = [q for q in filled if q < question]
        upper = [q for q in filled if q > question]
        after = None
        if lower:
            prev = filled[max(lower)]
            after = (prev.end_page, prev.end_at if prev.end_at is not None else float("inf"))
        following = filled[min(upper)] if upper else None
        before = None
        if following is not None:
            before = (following.start_page, following.start_at or -1.0)
        anchor = _first_anchor(candidates, question, after, before)
        if anchor is None:
            continue
        filled[question] = ms_bands.band_until(anchor, following, last_page=last_page)

    added = sorted(set(filled) - set(kept))
    if added:
        warnings.append(
            f"tally unmatched, banded from the question's own header for {added}"
        )
    return filled


def check_ms_marks(
    ms_path: Path,
    bands: dict[int, ms_bands.Band],
    provisional: set[int],
    fences: dict[int, tuple[int, int]],
) -> tuple[dict[int, ms_bands.Band], list[str]]:
    """
    Third signal: the mark total inside each MS band must equal the QP fence
    marks for the same question. Agreement proves the QP and MS segments
    describe the same question.

    Blocks whose question number was inferred from sequence rather than read
    from the page are DROPPED unless their marks verify. Blocks with an
    explicitly read number are kept and merely warned about, since the number on
    the page outranks a mark tally that Edexcel sometimes misprints.

    This now reads the BAND rather than its pages. On a shared page the page's
    text carries the neighbour's tally too, so the old check could pass for the
    wrong reason -- finding the expected figure in a block that did not state
    it.
    """
    warnings: list[str] = []
    kept: dict[int, ms_bands.Band] = {}

    for question, band in sorted(bands.items()):
        if question not in fences:
            warnings.append(f"mark scheme has question {question} but the QP does not")
            continue

        expected = fences[question][1]
        text = ms_bands.band_text(ms_path, band)

        totals = [int(m) for m in MS_TOTAL_RE.findall(text)]
        source = "total line"
        if not totals:
            # Older mark schemes tally each part in brackets and close with the
            # question total, so presence of the expected figure is the signal.
            totals = [int(m) for m in MS_BRACKET_RE.findall(text)]
            source = "bracketed part tallies"

        verified = expected in totals

        if question in provisional and not verified:
            warnings.append(
                f"question {question}: mark scheme block inferred from sequence and "
                f"its marks do not confirm it ({source} give {totals or 'nothing'}, "
                f"expected {expected}) -- block dropped"
            )
            continue

        if not verified:
            detail = f"{source} give {totals}" if totals else "block states no marks"
            warnings.append(
                f"question {question}: QP fence says {expected} marks but the mark "
                f"scheme {detail}"
            )

        kept[question] = band

    missing_from_ms = sorted(set(fences) - set(kept))
    if missing_from_ms:
        warnings.append(f"no mark scheme block found for questions {missing_from_ms}")

    return kept, warnings


# Validation
# ─────────────────────────────────────────────────────────────────────────────


def validate_paper(
    fences: dict[int, tuple[int, int]],
    ranges: dict[int, tuple[int, int]],
) -> list[str]:
    """Paper-level invariants. Anything here failing blocks the whole paper."""
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

    total_marks = sum(marks for _, marks in fences.values())
    if total_marks != TOTAL_PAPER_MARKS:
        issues.append(
            f"marks sum to {total_marks}, expected {TOTAL_PAPER_MARKS} "
            f"(per question: {{{', '.join(f'{q}:{m}' for q, (_, m) in sorted(fences.items()))}}})"
        )

    ordered = sorted(ranges.items())
    for (q_a, (_, end_a)), (q_b, (start_b, _)) in zip(ordered, ordered[1:]):
        if start_b != end_a + 1:
            issues.append(
                f"page gap or overlap between question {q_a} (ends {end_a}) and "
                f"question {q_b} (starts {start_b})"
            )

    if len(ranges) != len(fences):
        issues.append(
            f"{len(fences)} questions fenced but only {len(ranges)} produced page ranges"
        )

    return issues


# ─────────────────────────────────────────────────────────────────────────────
# Processing
# ─────────────────────────────────────────────────────────────────────────────


def process_paper(source: PaperSource) -> PaperResult:
    result = PaperResult(source=source)

    if source.key in EXCLUDED_PAPERS:
        result.skipped_reason = EXCLUDED_PAPERS[source.key]
        return result

    qp_pages = page_texts(source.qp_path)
    fences, fence_problems = find_fences(qp_pages)
    result.warnings.extend(fence_problems)

    manual = MANUAL_QP_RANGES.get(source.key)

    if not fences and manual is None:
        text_volume = sum(len(p.strip()) for p in qp_pages)
        result.issues.append(
            f"no question fences found in {len(qp_pages)} pages "
            f"({text_volume} chars of text -- likely an image-only scan; "
            f"add an entry to MANUAL_QP_RANGES)"
        )
        return result

    start_markers = find_start_markers(source.qp_path)

    if manual is not None:
        ranges = {q: (start, end) for q, (start, end, _) in manual.items()}
        fences = {q: (end, marks) for q, (_, end, marks) in manual.items()}
        result.warnings.append(
            f"image-only scan: using hand-verified page ranges and mark-scheme "
            f"marks for {len(ranges)} questions"
        )
    else:
        ranges, range_problems = derive_ranges(fences, start_markers)
        result.issues.extend(range_problems)
        result.warnings.extend(cross_check_starts(ranges, start_markers))

    result.issues.extend(validate_paper(fences, ranges))

    ms_regions: dict[int, tuple[Region, ...]] = {}
    if source.ms_path is None:
        result.warnings.append("no mark scheme file found")
    else:
        bands, provisional, ms_problems = locate_ms_bands(source.ms_path, fences)
        result.warnings.extend(ms_problems)
        bands, mark_warnings = check_ms_marks(
            source.ms_path, bands, provisional, fences
        )
        result.warnings.extend(mark_warnings)

        for question, band in bands.items():
            extents = ms_bands.page_extents_of(source.ms_path, band.axis)
            ms_regions[question] = ms_bands.band_to_regions(band, Region, extents)

    result.segments = [
        QuestionSegment(
            number=question,
            marks=fences[question][1] if question in fences else 0,
            qp_pages=page_range,
            ms_regions=ms_regions.get(question),
        )
        for question, page_range in sorted(ranges.items())
    ]

    return result


def extract_range(source_pdf: Path, page_range: tuple[int, int], target: Path) -> None:
    """Write pages [start, end] of `source_pdf` to `target` as a new PDF."""
    start, end = page_range
    target.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(source_pdf) as src:
        out = fitz.open()
        try:
            out.insert_pdf(src, from_page=start, to_page=end)
            out.save(target)
        finally:
            out.close()


def extract_regions(
    source_pdf: Path, regions: tuple[Region, ...], target: Path
) -> None:
    """
    Write `regions` of `source_pdf` to `target` as a new PDF.

    A region with no band is copied whole, which preserves the page exactly. A
    banded region is drawn onto a fresh page of the band's size with
    show_pdf_page, whose `clip` is in the source page's own coordinate space --
    the same space get_text reports, so no conversion is involved. Narrowing the
    crop box instead would be wrong on the papers whose MediaBox and CropBox
    disagree, and wrong in a way that looks fine until the audit reads it back.
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
                top = (
                    page_rect.y0 if region.top is None else max(page_rect.y0, region.top)
                )
                bottom = (
                    page_rect.y1
                    if region.bottom is None
                    else min(page_rect.y1, region.bottom)
                )
                left = (
                    page_rect.x0
                    if region.left is None
                    else max(page_rect.x0, region.left)
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

    Files this run did not produce are DELETED first, so a segment the current
    logic declines to emit cannot silently keep whatever an earlier run left at
    that path. Rebuilding Maths B after its mark schemes were banded turned up
    103 such orphans, holding the very contamination the rebuild existed to
    remove, and its audit read them back as if they were current output.
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
        extract_range(
            result.source.qp_path,
            segment.qp_pages,
            paper_dir / "questions" / f"q{segment.number}.pdf",
        )
        written += 1

        if segment.ms_regions is not None and result.source.ms_path is not None:
            extract_regions(
                result.source.ms_path,
                segment.ms_regions,
                paper_dir / "markschemes" / f"q{segment.number}.pdf",
            )
            written += 1

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
                "qp_pages": list(s.qp_pages),
                "ms_regions": (
                    [
                        {
                            "page": r.page,
                            "top": r.top,
                            "bottom": r.bottom,
                            "left": r.left,
                            "right": r.right,
                            "cropped": r.cropped,
                        }
                        for r in s.ms_regions
                    ]
                    if s.ms_regions
                    else None
                ),
                "has_markscheme": s.ms_regions is not None,
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
    Re-open every written segment and confirm it holds exactly one question,
    and that it is the question named on the file.

    This is deliberately independent of everything above: it reads only the
    written PDFs, so it would catch a bug in the range logic rather than
    inheriting one. Returns the number of defects.
    """
    if not OUTPUT_DIR.is_dir():
        print(f"No output to audit at {OUTPUT_DIR}")
        return 0

    checked = bundled = mislabelled = unverifiable = hand_verified = 0
    ms_checked = ms_bundled = ms_no_header = 0
    defects: list[str] = []
    ms_defects: list[str] = []

    for paper_dir in sorted(OUTPUT_DIR.iterdir()):
        questions_dir = paper_dir / "questions"
        if not questions_dir.is_dir():
            continue

        # A scanned paper carries no text to check against, so its segments were
        # established and confirmed by eye. Counting them as defects would be
        # false; counting them as passes would be dishonest. They are reported
        # in their own line.
        is_manual = paper_dir.name in MANUAL_QP_RANGES

        # ── The mark scheme side ────────────────────────────────────────────
        #
        # A mark scheme block opens with a header row that names its question.
        # A segment holding a header for some OTHER question is holding another
        # question's scheme, which is the defect banding exists to remove. Read
        # from the written PDF only, so a bug in the band logic shows up here
        # rather than being inherited.
        for ms_path in sorted((paper_dir / "markschemes").glob("q*.pdf")):
            ms_match = re.fullmatch(r"q(\d+)\.pdf", ms_path.name)
            if not ms_match:
                continue
            ms_expected = int(ms_match.group(1))
            ms_checked += 1

            flat = normalise(" ".join(page_texts(ms_path)))
            numbered = {
                int(n)
                for n in re.findall(
                    r"Question\s+(?:number\s+)?Scheme\s+Marks?\s+(\d{1,2})", flat, re.I
                )
            }
            # The flat text cannot tell a header's question number from the
            # first exponent of the working under a CONTINUATION header
            # ("4q² = 9p²" reads as "... Marks 2"), which flagged three clean
            # 2017 May-Jun P2 schemes. So a number only counts if it is also
            # printed as a label in the number column of the written PDF.
            if numbered - {ms_expected}:
                labelled = {h.question for h in ms_bands.find_question_labels(ms_path)}
                numbered &= labelled | {ms_expected}
            others = sorted(numbered - {ms_expected})

            if others:
                ms_bundled += 1
                ms_defects.append(
                    f"MS BUNDLED   {paper_dir.name}/{ms_path.name}: also holds {others}"
                )
            elif not numbered:
                ms_no_header += 1

        for pdf_path in sorted(questions_dir.glob("q*.pdf")):
            match = re.fullmatch(r"q(\d+)\.pdf", pdf_path.name)
            if not match:
                continue
            expected = int(match.group(1))
            checked += 1

            flat = normalise(" ".join(page_texts(pdf_path)))
            found = sorted({int(q) for q, _ in FENCE_RE.findall(flat)})

            if not found:
                if is_manual:
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

    print(f"\n{'=' * 74}\nAUDIT\n{'=' * 74}")
    print(f"  segments checked      : {checked}")
    print(f"  text-verified         : {checked - hand_verified - bundled - mislabelled - unverifiable}")
    print(f"  hand-verified (scans) : {hand_verified}")
    print(f"  bundled               : {bundled}")
    print(f"  mislabelled           : {mislabelled}")
    print(f"  unverifiable          : {unverifiable}")

    print(f"\n  mark schemes checked  : {ms_checked}")
    print(f"  single-question       : {ms_checked - ms_bundled - ms_no_header}")
    print(f"  no readable header    : {ms_no_header}")
    print(f"  bundled               : {ms_bundled}")

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

    total_defects = bundled + mislabelled + unverifiable + ms_bundled
    verdict = "PASS" if total_defects == 0 else "FAIL"
    print(
        f"\n  GATE: {verdict} (question defects "
        f"{bundled + mislabelled + unverifiable}, mark scheme defects {ms_bundled})"
    )
    return total_defects


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="write PDFs (default: dry run)")
    parser.add_argument("--paper", help="process only this paper key, e.g. 2016_may-jun_1")
    parser.add_argument("--audit", action="store_true", help="audit existing output and exit")
    parser.add_argument("--verbose", action="store_true", help="show per-paper warnings")
    args = parser.parse_args()

    if args.audit:
        return 1 if audit_output() else 0

    papers = discover_papers()
    if args.paper:
        papers = [p for p in papers if p.key == args.paper]
        if not papers:
            print(f"No paper matching key '{args.paper}'")
            return 1

    mode = "EXECUTE" if args.execute else "DRY RUN"
    print(f"{'=' * 74}")
    print(f"FPM WORKBOOK SEGMENTATION  [{mode}]  {YEAR_START}-{YEAR_END}")
    print(f"  source: {SOURCE_DIR.relative_to(REPO_ROOT)}")
    print(f"  output: {OUTPUT_DIR.relative_to(REPO_ROOT)}")
    print(f"{'=' * 74}\n")

    results = [process_paper(p) for p in papers]

    written_files = 0
    for result in results:
        key = result.source.key

        if result.skipped_reason:
            print(f"  SKIP  {key:<22} {result.skipped_reason[:70]}")
            continue

        if result.issues:
            print(f"  FAIL  {key:<22} {len(result.segments)} segments held back")
            for issue in result.issues:
                print(f"          - {issue}")
            continue

        marks = sum(s.marks for s in result.segments)
        with_ms = sum(1 for s in result.segments if s.ms_regions)
        flag = f"  ({len(result.warnings)} warnings)" if result.warnings else ""
        print(
            f"  OK    {key:<22} {len(result.segments):>2} questions, "
            f"{marks} marks, {with_ms} mark schemes{flag}"
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
