"""
Phase 2: enrich the segmented FPM workbook questions.

Reads the clean segments produced by `build_fpm_workbook_segments.py` and
derives, for every question:

  * stem text      -- cleaned of answer-space boilerplate, ready for the Phase 3
                      classifier and archetype clustering.
  * sub-parts      -- the (a)/(b)/(c) breakdown with per-part marks, taken from
                      the question paper's own margin tallies.
  * difficulty     -- derived from the mark tariff, NOT from an LLM. The
                      existing LLM labels are useless here: of 435 questions it
                      called 317 medium, 116 hard and 2 easy, at a mean
                      confidence of 0.93. Marks are an honest, explainable
                      signal and correlate cleanly with position in the paper
                      (mean rises 4.8 -> 13.3 from Q1 to Q11).
  * text_status    -- whether the stem is usable, was repaired, or needs vision.

TEXT REPAIR
-----------
Some questions extract as garbled uppercase ("The nWK\x03WHUP\x03RI\x03DQ"),
because those PDFs embed a Times subset whose ToUnicode CMap is offset: every
character code sits 29 below its true value, so "W"->"t", "\x03"->" ",
"\x11"->".", "*"->"G". Adding 29 back recovers the text exactly.

The repair MUST be applied per span, not per page. A single page mixes broken
and intact fonts under the same font name (`TimesNewRomanPSMT`), so decoding the
whole page corrupts everything that was already correct -- "DO NOT WRITE IN THIS
AREA" becomes "al=klq=tofqb...". A span is treated as broken when it contains
control characters, which valid text never does, or when decoding it
demonstrably reads better against a list of common exam words.

Font metadata cannot make this call: broken and intact spans in the same
document report the identical font name, size and flags, so the decision has to
be made from the text itself.

Known cosmetic residue in repaired stems: a lone encoded space sometimes
survives as "=" ("(a) =find"), and legacy Symbol-font glyphs render as "i" or
"±" for minus and inequality signs. Both are left alone deliberately -- stripping
them would eat the "=" in real equations. The stem is classifier input only; the
workbook itself prints the original PDF pages, never this text.

A further 11 questions (2019 May-Jun Paper 1) are a scan with no text at all.
They are flagged `needs_vision` so Phase 3 routes them to a vision model rather
than silently classifying an empty string.

USAGE
-----
    python scripts/enrich_fpm_workbook_questions.py
    python scripts/enrich_fpm_workbook_questions.py --execute
    python scripts/enrich_fpm_workbook_questions.py --show 2022_jan_2 4
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import fitz  # PyMuPDF

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKBOOK_DIR = REPO_ROOT / "data" / "workbook" / "fpm"
OUTPUT_PATH = REPO_ROOT / "data" / "workbook" / "fpm_questions.json"

# Mark tariff bands. Chosen from the actual distribution across all 431
# questions (3-18 marks, median 9) to give a usable three-way split rather than
# the LLM's 2/317/116.
DIFFICULTY_BANDS = ((6, "easy"), (10, "medium"))  # else "hard"
HARD_LABEL = "hard"

# Boilerplate stripped from every stem. These are answer-space furniture and
# our own watermark, none of which describes the question.
BOILERPLATE_PATTERNS = (
    re.compile(r"\*[A-Z]?\d{5,}[A-Z]?\d*\*"),           # printer barcode
    re.compile(r"DO NOT WRITE IN THIS AREA", re.I),
    re.compile(r"Question\s+\d+\s+continued", re.I),
    re.compile(r"\(?\s*Total for Question\s+\d+\s*(?:is|=|:)\s*\d+\s+marks?\s*\)?", re.I),
    re.compile(r"Turn over", re.I),
    re.compile(r"Further Pure Maths\s*[·|].*", re.I),    # GradeMax stamp line 1
    re.compile(r"4PM\d\s*\|.*", re.I),                   # GradeMax stamp line 2
    re.compile(r"^\s*GradeMax\s*$", re.I | re.M),
    re.compile(r"\.{4,}"),                               # dotted answer leaders
    re.compile(r"_{4,}"),
    re.compile(r"BLANK PAGE", re.I),
)

# Sub-part label, e.g. "(a)" / "(b)". Roman sub-sub-parts "(i)" are deliberately
# excluded -- the workbook's unit is the lettered part.
PART_LABEL_RE = re.compile(r"\(\s*([a-e])\s*\)")
# A standalone bracketed integer is the margin mark tally for the part above it.
PART_MARKS_RE = re.compile(r"\(\s*(\d{1,2})\s*\)")

# Common words in FPM question stems, used only to judge whether text is
# readable and whether a repair improved it.
EXAM_WORDS = frozenset(
    """the and of that find given show value values curve equation solve point line
    where such hence for are is to in with prove sketch state expand series terms
    term sum first second angle triangle circle area gradient tangent normal
    coordinates vector integrate differentiate respect diagram figure form exact
    answer working correct constant express function graph range roots real""".split()
)


def word_score(text: str) -> int:
    """How many common exam words appear. The readability signal."""
    return sum(1 for w in re.findall(r"[a-z]{2,}", text.lower()) if w in EXAM_WORDS)


# Character codes in the broken font subsets sit this far below their true
# Unicode value. Established by decoding: "W"+29 -> "t", "\x03"+29 -> " ".
CMAP_OFFSET = 29

# Control characters are the giveaway for a broken span: the offset maps space,
# comma and full stop into the 0x01-0x1F range, and valid text never goes there.
CONTROL_CHARS_RE = re.compile(r"[\x01-\x08\x0b\x0c\x0e-\x1f]")


def decode_offset_span(text: str) -> str:
    """Undo the CMap offset for one span of text."""
    return "".join(
        chr(ord(ch) + CMAP_OFFSET) if 0x01 <= ord(ch) <= 0x5A else ch for ch in text
    )


def repair_span(text: str) -> tuple[str, bool]:
    """
    Return (text, was_repaired) for a single span.

    Control characters are conclusive. Otherwise the repair has to earn its
    place by reading better than the original, so intact spans are left alone.
    """
    if CONTROL_CHARS_RE.search(text):
        return decode_offset_span(text), True

    letters = sum(1 for ch in text if ch.isalpha())
    if letters < 4:
        return text, False

    decoded = decode_offset_span(text)
    if word_score(decoded) > word_score(text):
        return decoded, True

    return text, False


def strip_boilerplate(text: str) -> str:
    for pattern in BOILERPLATE_PATTERNS:
        text = pattern.sub(" ", text)
    return re.sub(r"[ \t]+", " ", re.sub(r"\s*\n\s*", "\n", text)).strip()


@dataclass(frozen=True)
class SubPart:
    label: str
    marks: int


@dataclass
class EnrichedQuestion:
    paper_key: str
    year: int
    season: str
    paper_number: str
    question_number: int
    marks: int
    difficulty: str
    qp_pdf: str
    ms_pdf: str | None
    has_markscheme: bool
    qp_page_count: int
    stem: str
    stem_chars: int
    text_status: str  # "ok" | "repaired" | "needs_vision"
    sub_parts: list[dict] | None
    sub_parts_verified: bool


def difficulty_for(marks: int) -> str:
    for ceiling, label in DIFFICULTY_BANDS:
        if marks <= ceiling:
            return label
    return HARD_LABEL


def extract_stem(pdf_path: Path) -> tuple[str, str]:
    """
    Return (stem, status).

    Status is "ok" for clean text, "repaired" when at least one span needed the
    CMap offset undone, and "needs_vision" when the page carries no usable text
    at all (a scan).
    """
    lines: list[str] = []
    repaired_spans = 0

    with fitz.open(pdf_path) as doc:
        for page in doc:
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    pieces: list[str] = []
                    for span in line.get("spans", []):
                        text, was_repaired = repair_span(span["text"])
                        repaired_spans += was_repaired
                        pieces.append(text)
                    joined = "".join(pieces).strip()
                    if joined:
                        lines.append(joined)

    cleaned = strip_boilerplate("\n".join(lines))

    if len(cleaned) < 40 or word_score(cleaned) < 2:
        return cleaned, "needs_vision"

    return cleaned, "repaired" if repaired_spans else "ok"


def extract_sub_parts(stem: str, total_marks: int) -> tuple[list[SubPart] | None, bool]:
    """
    Pair each (a)/(b)/(c) label with the bracketed mark tally that follows it.

    Returns (parts, verified). `verified` is True only when the part marks sum
    to the question's own total -- the same verify-or-drop discipline used for
    mark scheme blocks in Phase 1. Unverified parts are still returned so they
    can be inspected, but callers should not print them as fact.
    """
    labels = list(PART_LABEL_RE.finditer(stem))
    if not labels:
        return None, False

    parts: list[SubPart] = []
    for index, label_match in enumerate(labels):
        end = labels[index + 1].start() if index + 1 < len(labels) else len(stem)
        window = stem[label_match.end() : end]

        # The part's tally is the last bracketed integer before the next part.
        tallies = PART_MARKS_RE.findall(window)
        if not tallies:
            return None, False
        parts.append(SubPart(label=label_match.group(1), marks=int(tallies[-1])))

    # Labels must read a, b, c... in order; anything else means we matched
    # bracketed letters from inside the maths rather than real part labels.
    expected = [chr(ord("a") + i) for i in range(len(parts))]
    if [p.label for p in parts] != expected:
        return None, False

    return parts, sum(p.marks for p in parts) == total_marks


def enrich_paper(paper_dir: Path) -> list[EnrichedQuestion]:
    manifest = json.loads((paper_dir / "manifest.json").read_text(encoding="utf-8"))
    questions: list[EnrichedQuestion] = []

    for entry in manifest["questions"]:
        number = entry["question_number"]
        marks = entry["marks"]
        qp_pdf = paper_dir / "questions" / f"q{number}.pdf"
        ms_pdf = paper_dir / "markschemes" / f"q{number}.pdf"

        stem, status = extract_stem(qp_pdf)
        parts, verified = extract_sub_parts(stem, marks)

        with fitz.open(qp_pdf) as doc:
            page_count = len(doc)

        questions.append(
            EnrichedQuestion(
                paper_key=manifest["key"],
                year=manifest["year"],
                season=manifest["season"],
                paper_number=manifest["paper_number"],
                question_number=number,
                marks=marks,
                difficulty=difficulty_for(marks),
                qp_pdf=str(qp_pdf.relative_to(REPO_ROOT)).replace("\\", "/"),
                ms_pdf=(
                    str(ms_pdf.relative_to(REPO_ROOT)).replace("\\", "/")
                    if entry["has_markscheme"]
                    else None
                ),
                has_markscheme=entry["has_markscheme"],
                qp_page_count=page_count,
                stem=stem,
                stem_chars=len(stem),
                text_status=status,
                sub_parts=[asdict(p) for p in parts] if parts else None,
                sub_parts_verified=verified,
            )
        )

    return questions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="write the JSON inventory")
    parser.add_argument("--show", nargs=2, metavar=("PAPER_KEY", "Q"), help="print one question")
    args = parser.parse_args()

    if not WORKBOOK_DIR.is_dir():
        print(f"No segments found at {WORKBOOK_DIR}. Run build_fpm_workbook_segments.py first.")
        return 1

    paper_dirs = sorted(p for p in WORKBOOK_DIR.iterdir() if (p / "manifest.json").is_file())
    all_questions: list[EnrichedQuestion] = []
    for paper_dir in paper_dirs:
        all_questions.extend(enrich_paper(paper_dir))

    if args.show:
        key, number = args.show[0], int(args.show[1])
        for question in all_questions:
            if question.paper_key == key and question.question_number == number:
                print(json.dumps(asdict(question), indent=2)[:4000])
                return 0
        print(f"No question {number} in {key}")
        return 1

    status_counts = Counter(q.text_status for q in all_questions)
    difficulty_counts = Counter(q.difficulty for q in all_questions)
    with_parts = sum(1 for q in all_questions if q.sub_parts)
    verified_parts = sum(1 for q in all_questions if q.sub_parts_verified)
    single_part = sum(1 for q in all_questions if not q.sub_parts)

    print(f"{'=' * 74}\nFPM WORKBOOK ENRICHMENT\n{'=' * 74}")
    print(f"  papers                 : {len(paper_dirs)}")
    print(f"  questions              : {len(all_questions)}")
    print(f"  total marks            : {sum(q.marks for q in all_questions)}")

    print("\n  Text")
    for status in ("ok", "repaired", "needs_vision"):
        print(f"    {status:<20} : {status_counts.get(status, 0)}")
    usable = len(all_questions) - status_counts.get("needs_vision", 0)
    print(f"    usable for Phase 3   : {usable} ({usable / len(all_questions):.0%})")

    print("\n  Difficulty (from mark tariff)")
    for label in ("easy", "medium", "hard"):
        count = difficulty_counts.get(label, 0)
        print(f"    {label:<20} : {count:>3} ({count / len(all_questions):.0%})")

    print("\n  Sub-parts")
    print(f"    parsed               : {with_parts}")
    print(f"    marks verified       : {verified_parts}")
    print(f"    single-part questions: {single_part}")

    if args.execute:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(
            json.dumps([asdict(q) for q in all_questions], indent=2), encoding="utf-8"
        )
        print(f"\n  written: {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    else:
        print("\n  Dry run -- nothing written. Re-run with --execute.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
