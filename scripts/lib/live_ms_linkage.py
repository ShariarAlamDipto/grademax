"""
Audit the question <-> mark-scheme links the test builder and worksheet
generator actually serve, by CONTENT.

Every live `pages` row carries `qp_page_url` (one question) and `ms_page_url`
(its mark scheme). Nothing so far has checked that the two files belong
together: earlier audits compared URL stems, or trusted a segmenter that had
already guessed. This reads both files and asks what each one PRINTS.

WHAT EACH FILE PRINTS ABOUT ITSELF

  question paper   "(Total for Question N is M marks)" -- the number and the
                   marks, at the foot of every Edexcel question.
  Physics MS       "Total for question N = M marks" -- number and marks again.
  Maths B / FPM MS "Total M marks" tallies (no number), plus the question
                   number in the table's margin column.

A link is PROVEN only when the question number agrees on both sides AND the
marks agree. Marks alone are not proof: neighbouring questions often carry the
same tariff (Maths B Paper 1 is mostly 2- and 3-mark questions), so a marks-only
match is reported as MARKS_ONLY and left for the content judge.

Read-only. It writes a cache of downloaded segments and a report, nothing else.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

import fitz

from lib.ms_bands import TALLY_RE, find_question_labels

# QP band; tolerant of "=10" with no space (2026-10-05 trap) and of a broken line.
QP_TOTAL_RE = re.compile(
    r"\(?\s*Total\s+for\s+Question\s+(\d{1,2})\s*(?:is|=|:)\s*(\d{1,3})\s*marks?", re.I
)
# Physics MS tally carries its own question number.
MS_NUMBERED_TOTAL_RE = re.compile(
    r"Total\s+for\s+question\s+(\d{1,2})\s*(?:is|=|:)?\s*(\d{1,3})\s*marks?", re.I
)
# 2017 Jan P2 / 2018 Jan P1 q3 print the tally without its number.
MS_NUMBERLESS_TOTAL_RE = re.compile(
    r"Total\s+for\s+question\s*(?:is|=|:)\s*(\d{1,3})\s*marks?", re.I
)
# 2015 May-Jun P2R closes blocks with "total = 6 marks".
MS_EQUALS_TOTAL_RE = re.compile(r"\btotal\s*=\s*(\d{1,3})\s*marks?", re.I)
MIN_TEXT_CHARS = 40

VERDICTS = (
    "PROVEN",        # number and marks agree on both sides
    "MARKS_ONLY",    # marks agree, MS prints no number to confirm
    "MS_WRONG",      # MS prints another question's number, or other marks
    "MS_BUNDLED",    # MS holds this question plus others
    "QP_WRONG",      # the question file holds a different question number
    "QP_BUNDLED",    # the question file holds more than one question
    "NO_MS",         # no mark scheme linked at all
    "MS_MISSING",    # linked URL does not download
    "LABEL_ONLY",    # scheme prints no tally; its margin number agrees
    "MS_PARTIAL",    # scheme lacks parts the question prints (cut started late)
    "UNREADABLE",    # no text layer on one side; needs the vision judge
)


@dataclass(frozen=True)
class Evidence:
    chars: int
    totals: tuple[tuple[int, int], ...]  # (question, marks) printed with a number
    tallies: tuple[int, ...]             # bare "Total M marks"
    labels: tuple[int, ...]              # margin-column question labels (MS only)
    column_marks: int | None = None      # sum of the scheme's Marks column (MS only)
    parts: tuple[str, ...] = ()          # top-level part letters printed
    column_uniform: int | None = None    # every Mark cell holds this one value
    column_codes: int | None = None      # sum of M1/A1/B1 codes in the Marks column
    column_codes_main: int | None = None # the same, skipping ALT methods


@dataclass
class RowResult:
    page_id: str
    subject: str
    paper: str
    question: str
    verdict: str
    detail: str
    qp_url: str | None
    ms_url: str | None
    qp: dict | None = field(default=None)
    ms: dict | None = field(default=None)


def _words_text(doc: fitz.Document) -> str:
    # Word stream, not lines: a tally broken across two lines is still found.
    return " ".join(w[4] for page in doc for w in page.get_text("words"))


MARK_CELL_RE = re.compile(r"^\(?(\d{1,2})\)?$")
COLUMN_SLACK = 12.0


RIGHT_FRACTION = 0.75


def _infer_column(words: list, width: float) -> tuple[float, float] | None:
    """
    The Marks column when its header is not on the page (a band that opens
    just below the header row): the x-position in the right quarter of the
    page where the most single integers stand aligned. Needs two such cells.
    """
    centres = [
        (w[0] + w[2]) / 2 for w in words
        if MARK_CELL_RE.match(w[4]) and (w[0] + w[2]) / 2 > width * RIGHT_FRACTION
    ]
    best = max(centres, key=lambda c: sum(abs(c - o) < 4 for o in centres), default=None)
    if best is None or sum(abs(best - o) < 4 for o in centres) < 2:
        return None
    return best - COLUMN_SLACK, best + COLUMN_SLACK


def marks_column_sum(doc: fitz.Document) -> tuple[int | None, int | None, list[int]]:
    """
    (sum of the Marks column, the table's own "Total | N" row, the cell values).

    Old schemes (Physics 2011-2017) print no "Total N marks" line; instead the
    table closes with a row whose Answer cell reads "Total" and whose Marks
    cell holds the question's total. That row is the scheme's printed total.
    The sum of the other cells in the column is a second, weaker reading.
    A page without the header reuses the last column seen (a segment's pages
    share one table).
    """
    column: tuple[float, float] | None = None
    total, seen, table_total = 0, False, None
    values: list[int] = []
    for page in doc:
        # Displayed coordinates: a whole page copied from a /Rotate 90 scheme
        # reports its words in UNROTATED space, where the columns run down
        # the page instead of across it.
        matrix = page.rotation_matrix
        words = [
            (*fitz.Rect(w[:4]).transform(matrix), w[4]) for w in page.get_text("words")
        ]
        header_y = -1.0
        for w in words:
            if w[4] in ("Marks", "Mark"):
                column = (w[0] - COLUMN_SLACK, w[2] + COLUMN_SLACK)
                header_y = w[3]
        if column is None:
            column = _infer_column(words, page.rect.width)
        if column is None:
            continue
        total_rows = [(w[1] + w[3]) / 2 for w in words if w[4] == "Total"]
        for w in words:
            match = MARK_CELL_RE.match(w[4])
            if not (match and w[1] > header_y and column[0] <= (w[0] + w[2]) / 2 <= column[1]):
                continue
            mid = (w[1] + w[3]) / 2
            if any(abs(mid - y) < 6 for y in total_rows):
                table_total = int(match.group(1))
                continue
            total += int(match.group(1))
            values.append(int(match.group(1)))
            seen = True
    return (total if seen else None), table_total, values


# Further Pure / Maths B award marks as codes: "M1", "A1", "dM1", "B2", "M1A1A1",
# sometimes suffixed (ft, cso, cao, oe). Their digits add up to the marks.
MARK_CODE_RE = re.compile(r"^\(?(?:[dD]?[MABE]\d(?:dep|ft|cso|cao|oe|isw)?)+\)?$")
CODE_DIGIT_RE = re.compile(r"[MABE](\d)")
CODE_SLACK = 25.0


ALT_MARKER_RE = re.compile(r"^(?:ALT\w*|Alt|Alternative\w*|ALTERNATIVE\w*|Way)$")
PART_START_RE = re.compile(r"^\d{0,2}\(?[a-h]\)?(?:\(.*)?$|^\d{1,2}\.?$")


def marks_code_sum(doc: fitz.Document) -> tuple[int | None, int | None]:
    """
    Sum of the mark codes standing in the scheme's Marks column, or None.

    The column is the "Marks"/"Mark" header's x-range (codes are wider than a
    digit, hence the wider slack); a page without the header reuses the last
    one, or failing that the right-hand x-position where most codes align.
    Alternative methods repeat codes, so an ALT scheme over-counts and stays
    unproven -- this can only fail safe.
    """
    column: tuple[float, float] | None = None
    total, main, seen, in_alt = 0, 0, False, False
    for page in doc:
        matrix = page.rotation_matrix
        words = [(*fitz.Rect(w[:4]).transform(matrix), w[4]) for w in page.get_text("words")]
        header_y = -1.0
        for w in words:
            if w[4] in ("Marks", "Mark"):
                column = (w[0] - CODE_SLACK, w[2] + CODE_SLACK)
                header_y = w[3]
        if column is None:
            centres = [(w[0] + w[2]) / 2 for w in words
                       if MARK_CODE_RE.match(w[4]) and (w[0] + w[2]) / 2 > page.rect.width * 0.6]
            best = max(centres, key=lambda c: sum(abs(c - o) < 15 for o in centres), default=None)
            if best is not None and sum(abs(best - o) < 15 for o in centres) >= 2:
                column = (best - CODE_SLACK, best + CODE_SLACK)
        if column is None:
            continue
        for w in sorted(words, key=lambda w: (round(w[1] / 3), w[0])):
            token = w[4]
            # An alternative method repeats the marks it replaces: codes after
            # "ALT" / "Alternative" / "Way 2" do not count until the next part
            # label in the margin starts a new part.
            if ALT_MARKER_RE.match(token):
                in_alt = True
                continue
            if in_alt and w[0] < page.rect.width * 0.3 and PART_START_RE.match(token):
                in_alt = False
            # "M1,A1" is one word in the older schemes (2012 Jan P2 q2).
            pieces = [p for p in re.split(r"[,;/]", token) if p]
            if w[1] <= header_y or not pieces or not all(MARK_CODE_RE.match(p) for p in pieces):
                continue
            if column[0] <= (w[0] + w[2]) / 2 <= column[1]:
                marks = sum(int(d) for p in pieces for d in CODE_DIGIT_RE.findall(p))
                total += marks
                if not in_alt:
                    main += marks
                seen = True
    return (total, main) if seen else (None, None)


QP_PART_RE = re.compile(r"^\(([a-h])\)$")
# "(a)", "5(a)(i)", "5(a)", bare "a", and the 2013 form "(bi)" / "(cii)".
MS_PART_RE = re.compile(r"^\d{0,2}\(?([a-h])(?:i{1,3}|iv|vi{0,3})?\)?(?:\(.*)?$")
MARGIN_FRACTION = 0.3


def part_letters(doc: fitz.Document, *, is_ms: bool) -> tuple[str, ...]:
    """
    The top-level part letters a file prints: "(a)", "(b)" ... on a question
    paper; "(a)", "5(a)(i)", "5(a)", or a bare "a" in the left margin column on
    a scheme (a bare letter elsewhere is the English article).

    Why this exists: a scheme cut can start too LATE and still pass on number
    and marks -- 2014 May-Jun P1R q5's cut held only 5(f) (its opening header
    printed no number, so the band snapped past (a)-(e)), and its total still
    matched. Every part the question prints must appear in its scheme.
    """
    found: list[str] = []
    for page in doc:
        matrix = page.rotation_matrix
        width = page.rect.width
        for w in page.get_text("words"):
            token = w[4]
            match = (QP_PART_RE if not is_ms else MS_PART_RE).match(token)
            if not match:
                continue
            bare = is_ms and len(token) == 1
            if bare and (fitz.Rect(w[:4]) * matrix).x0 > width * MARGIN_FRACTION:
                continue
            if match.group(1) not in found:
                found.append(match.group(1))
    letters = sorted(found)
    if not is_ms:
        # Real parts run a, b, c ... without gaps; a stray "(g)" or "(h)" after
        # (c) is a unit -- grams, hours (2018 Jan P1 q10, 2024 May-Jun P1 q10).
        run = []
        for expected in "abcdefgh":
            if expected not in letters:
                break
            run.append(expected)
        letters = run
    return tuple(letters)


def read_evidence(path: Path, *, is_ms: bool) -> Evidence:
    with fitz.open(path) as doc:
        text = _words_text(doc)
        column_marks, table_total, cells = marks_column_sum(doc) if is_ms else (None, None, [])
        # Older Maths B schemes restate the QUESTION total in the Mark column,
        # once per method (an "OR" alternative repeats it), so a sum double
        # counts; a column whose every cell is the same value states it.
        column_uniform = cells[0] if cells and len(set(cells)) == 1 else None
        parts = part_letters(doc, is_ms=is_ms)
        column_codes, column_codes_main = marks_code_sum(doc) if is_ms else (None, None)
    totals_re = MS_NUMBERED_TOTAL_RE if is_ms else QP_TOTAL_RE
    totals = tuple((int(q), int(m)) for q, m in totals_re.findall(text))
    tallies: tuple[int, ...] = ()
    labels: tuple[int, ...] = ()
    if is_ms:
        # A numbered total also matches the bare tally pattern; keep them apart.
        rest = MS_NUMBERED_TOTAL_RE.sub(" ", text)
        bare = (TALLY_RE.findall(rest) + MS_NUMBERLESS_TOTAL_RE.findall(rest)
                + MS_EQUALS_TOTAL_RE.findall(rest))
        tallies = tuple(int(m) for m in bare)
        if not tallies and table_total is not None:
            tallies = (table_total,)
        try:
            labels = tuple(h.question for h in find_question_labels(path) if h.question)
        except Exception:  # noqa: BLE001 -- a label read failure is "no labels"
            labels = ()
    return Evidence(len(text.strip()), totals, tallies, labels, column_marks, parts,
                    column_uniform, column_codes, column_codes_main)


def _dedupe(seq):
    seen: list = []
    for item in seq:
        if item not in seen:
            seen.append(item)
    return seen


def judge(question: int, qp: Evidence, ms: Evidence | None) -> tuple[str, str]:
    """Verdict for one live row. Pure: evidence in, verdict out."""
    qp_totals = _dedupe(qp.totals)
    qp_numbers = _dedupe(q for q, _ in qp_totals)
    if len(qp_numbers) > 1:
        return "QP_BUNDLED", f"question file prints totals for {qp_numbers}"
    if qp_numbers and qp_numbers[0] != question:
        return "QP_WRONG", f"labelled q{question}, file prints Question {qp_numbers[0]}"
    qp_marks = qp_totals[0][1] if qp_totals else None

    if ms is None:
        return "NO_MS", ""
    if ms.chars < MIN_TEXT_CHARS or (qp.chars < MIN_TEXT_CHARS):
        return "UNREADABLE", f"text chars qp={qp.chars} ms={ms.chars}"

    # Every part the question prints must be in its scheme. Checked only when
    # the scheme shows readable part labels at all (an unreadable layer is
    # not evidence of absence).
    if qp.parts and ms.parts:
        missing = [p for p in qp.parts if p not in ms.parts]
        if missing:
            return "MS_PARTIAL", (f"scheme lacks part(s) {missing} of question parts "
                                  f"{list(qp.parts)}")

    ms_totals = _dedupe(ms.totals)
    if ms_totals:  # Physics-style: the scheme names its question
        numbers = _dedupe(q for q, _ in ms_totals)
        if len(numbers) > 1:
            if question in numbers:
                return "MS_BUNDLED", f"scheme closes questions {numbers}"
            return "MS_WRONG", f"scheme closes questions {numbers}"
        if numbers[0] != question:
            return "MS_WRONG", f"scheme is for Question {numbers[0]}"
        if qp_marks is not None and ms_totals[0][1] != qp_marks:
            # The board misprints the total now and then (2021 Jan P2R q1/q2:
            # cells sum to 9/7, total line says 8/6). When the scheme names this
            # question AND its own mark cells add up to the question's marks, two
            # independent readings agree and the total line is the misprint.
            if ms.column_marks == qp_marks:
                return "PROVEN", (f"scheme total misprinted ({ms_totals[0][1]}); "
                                  f"its mark cells sum to {qp_marks}")
            return "MS_WRONG", f"marks: question {qp_marks}, scheme {ms_totals[0][1]}"
        if qp_marks is None:
            return "MARKS_ONLY", "scheme number agrees; question file prints no total"
        return "PROVEN", ""

    tallies = list(ms.tallies)
    if len(tallies) > 1:
        # Two equal tallies can be an ALT method of one question; different
        # tallies are two questions.
        if len(set(tallies)) > 1:
            return "MS_BUNDLED", f"scheme holds tallies {tallies}"
    if not tallies:
        labels = _dedupe(ms.labels)
        if labels and labels[0] == question:
            if qp_marks is not None and qp_marks in (ms.column_marks, ms.column_uniform,
                                                     ms.column_codes, ms.column_codes_main):
                return "PROVEN", "margin number and Marks-column sum agree"
            return "LABEL_ONLY", (f"margin number agrees; Marks column sums to "
                                  f"{ms.column_marks}, question {qp_marks}")
        if labels and question not in labels:
            return "MS_WRONG", f"scheme margin starts at Question {labels[0]}"
        return "UNREADABLE", "scheme prints no tally"
    ms_marks = tallies[-1]
    labels = _dedupe(ms.labels)
    if qp_marks is not None and ms_marks != qp_marks:
        # Same misprint rule as above; here the number comes from the margin.
        if ms.column_marks == qp_marks and labels and labels[0] == question:
            return "PROVEN", (f"scheme total misprinted ({ms_marks}); margin number "
                              f"agrees and its mark cells sum to {qp_marks}")
        return "MS_WRONG", f"marks: question {qp_marks}, scheme {ms_marks}"

    if labels:
        first = labels[0]
        if first == question and qp_marks is not None:
            return "PROVEN", ""
        if first != question and question not in labels:
            return "MS_WRONG", f"scheme margin starts at Question {first}"
    return "MARKS_ONLY", f"marks {ms_marks} agree; number not confirmed"


# ── downloading ─────────────────────────────────────────────────────────────


def cache_path(cache_dir: Path, url: str) -> Path:
    return cache_dir / (hashlib.sha1(url.encode()).hexdigest() + ".pdf")


def fetch_all(urls: list[str], cache_dir: Path, get_bytes: Callable[[str], bytes | None],
              workers: int = 24) -> dict[str, Path | None]:
    cache_dir.mkdir(parents=True, exist_ok=True)

    def one(url: str) -> tuple[str, Path | None]:
        path = cache_path(cache_dir, url)
        if path.is_file() and path.stat().st_size > 0:
            return url, path
        try:
            data = get_bytes(url)
        except Exception:  # noqa: BLE001 -- reported as MS_MISSING / unreadable
            data = None
        if not data:
            return url, None
        path.write_bytes(data)
        return url, path

    with ThreadPoolExecutor(workers) as pool:
        return dict(pool.map(one, _dedupe(urls)))


def audit_rows(subject: str, rows: list[dict], paper_label: dict[str, str],
               files: dict[str, Path | None]) -> list[RowResult]:
    results: list[RowResult] = []
    for row in rows:
        qn_text = str(row["question_number"])
        qp_url, ms_url = row["qp_page_url"], row["ms_page_url"]
        base = dict(page_id=row["id"], subject=subject, paper=paper_label[row["paper_id"]],
                    question=qn_text, qp_url=qp_url, ms_url=ms_url)
        m = re.match(r"\d+", qn_text)
        qp_path = files.get(qp_url)
        if not m or qp_path is None:
            results.append(RowResult(**base, verdict="UNREADABLE",
                                     detail="question file missing or unnumbered"))
            continue
        try:
            qp = read_evidence(qp_path, is_ms=False)
        except Exception as exc:  # noqa: BLE001
            results.append(RowResult(**base, verdict="UNREADABLE", detail=f"qp: {exc}"))
            continue
        ms = None
        if ms_url:
            ms_path = files.get(ms_url)
            if ms_path is None:
                results.append(RowResult(**base, verdict="MS_MISSING", detail="download failed",
                                         qp=asdict(qp)))
                continue
            try:
                ms = read_evidence(ms_path, is_ms=True)
            except Exception as exc:  # noqa: BLE001
                results.append(RowResult(**base, verdict="UNREADABLE", detail=f"ms: {exc}"))
                continue
        verdict, detail = judge(int(m.group()), qp, ms)
        results.append(RowResult(**base, verdict=verdict, detail=detail, qp=asdict(qp),
                                 ms=asdict(ms) if ms else None))
    return results


def summarise(results: list[RowResult]) -> Counter:
    return Counter(r.verdict for r in results)
