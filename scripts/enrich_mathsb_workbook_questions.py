"""
Enrich the segmented Maths B (4MB1) questions with everything Phase 3 needs to
classify them and Phase 5 needs to print them.

Reads the Phase 1 output (data/workbook/mathsb/) and writes a single inventory
at data/workbook/mathsb_questions.json: marks, difficulty, sub-parts, and the
question stem as plain text.

DIFFICULTY IS NOT COPIED FROM FPM
---------------------------------
The FPM bands (<=6 easy, <=10 medium) would call 77% of Maths B easy, because
Maths B Paper 1 is a short-answer paper with a median of 3 marks. Bands here
come from this subject's own distribution across all 1,069 questions:

    <=3 marks   easy     ~40%
    <=6 marks   medium   ~37%
    >=7 marks   hard     ~23%

Banding globally rather than per-paper is deliberate: Paper 1 IS the easier
paper, so its questions landing mostly in "easy" is the right answer, not a
distortion to correct for.

Difficulty is derived from the mark tariff rather than asked of a model. On FPM
the model called 317 questions medium, 116 hard and 2 easy at a mean confidence
of 0.93 -- confident and useless. The tariff is what the examiner actually
assigned.

TEXT REPAIR
-----------
Several Maths B papers carry font subsets with a broken ToUnicode CMap, where
character codes sit 29 below their true value. The repair is applied PER SPAN,
never per page: font metadata cannot separate broken spans from intact ones, and
decoding a whole page corrupts everything that was already correct. A repair
also has to earn its place by reading better than the original.

USAGE
-----
    python scripts/enrich_mathsb_workbook_questions.py
    python scripts/enrich_mathsb_workbook_questions.py --execute
    python scripts/enrich_mathsb_workbook_questions.py --show 2016_jan_1 7
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
WORKBOOK_DIR = REPO_ROOT / "data" / "workbook" / "mathsb"
OUTPUT_PATH = REPO_ROOT / "data" / "workbook" / "mathsb_questions.json"

# See the module docstring -- derived from the 2016-2022 mark distribution.
DIFFICULTY_BANDS = ((3, "easy"), (6, "medium"))  # else "hard"
HARD_LABEL = "hard"

# Boilerplate stripped from every stem: answer-space furniture, the printer's
# barcode, and our own GradeMax stamp. None of it describes the question.
BOILERPLATE_PATTERNS = (
    re.compile(r"\*[A-Z]?\d{5,}[A-Z]?\d*\*"),           # printer barcode
    re.compile(r"DO NOT WRITE IN THIS AREA", re.I),
    re.compile(r"Question\s+\d+\s+continued", re.I),
    re.compile(r"\(?\s*Total for Question\s+\d+\s*(?:is|=|:)?\s*\d+\s+marks?\s*\)?", re.I),
    re.compile(r"TOTAL FOR PAPER.*", re.I),
    re.compile(r"Turn over", re.I),
    re.compile(r"Mathematics B\s*[·|].*", re.I),         # GradeMax stamp line 1
    re.compile(r"4MB\d\s*\|.*", re.I),                   # GradeMax stamp line 2
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

# Common words in Maths B question stems, used only to judge whether text is
# readable and whether a repair improved it. Weighted toward this syllabus --
# sets, matrices, transformations and statistics barely appear in FPM.
EXAM_WORDS = frozenset(
    """the and of that find given show value values solve point line where such
    hence for are is to in with prove sketch state calculate work out write
    express diagram figure form exact answer working correct constant function
    graph range roots real angle triangle circle area perimeter volume surface
    length radius diameter gradient tangent equation curve set sets shade region
    universal element subset matrix matrices determinant inverse transformation
    reflection rotation translation enlargement vector probability tree
    frequency histogram median mean mode range cumulative estimate percentage
    ratio fraction bearing scale factor sequence term nth simplify factorise
    expand nearest degrees centimetres metres speed distance time""".split()
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


# A SECOND, OPPOSITE CMap variant, found while auditing cropped segments.
#
# The variant CMAP_OFFSET handles stores each character 29 BELOW its true value,
# which is detectable because space (32) lands on 3, a control character.
#
# This one stores characters 29 ABOVE, and only for characters whose true value
# was <= 90 -- so uppercase, digits, space and punctuation shift while lowercase
# is left intact:
#
#     "19 Solve the simultaneous equations"
#     -> "19&=polve=the=simultaneous=equations"
#         space(32) -> "="(61)      "S"(83) -> "p"(112)      "olve" untouched
#
# Nothing lands in the control range, so the existing detector never fires. A
# blanket -29 is NOT the answer: it would also rewrite the intact lowercase
# ("the" -> "QEB"). Per character the two cases are genuinely ambiguous.
#
# So only the unambiguous part is repaired -- "=" acting as a word separator
# between two letters is a shifted space and nothing else. The rest is left
# alone and the question is flagged, because inventing the missing capitals
# would be guessing at the text of an exam question.
GARBLED_SEPARATOR_RE = re.compile(r"(?<=[A-Za-z])=(?=[A-Za-z])")


def repair_shifted_separators(text: str) -> tuple[str, bool]:
    """Turn the shifted spaces back into spaces. Returns (text, was_garbled)."""
    if len(GARBLED_SEPARATOR_RE.findall(text)) < 3:
        return text, False
    return GARBLED_SEPARATOR_RE.sub(" ", text), True


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
    cropped: bool
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
    at all.

    Cropped segments report only the text inside their crop box, so a Paper 1
    question that shares a page still yields its own stem and nothing else.
    """
    lines: list[str] = []
    repaired_spans = 0

    with fitz.open(pdf_path) as doc:
        for page in doc:
            try:
                blocks = page.get_text("dict")["blocks"]
            except Exception:  # noqa: BLE001 - a bad page must not kill the paper
                continue
            for block in blocks:
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
    cleaned, was_garbled = repair_shifted_separators(cleaned)

    # Maths B Paper 1 stems are genuinely short -- "Factorise 6x + 9x - 4" is a
    # complete question -- so the readability floor is lower than FPM's.
    if len(cleaned) < 20 or word_score(cleaned) < 1:
        return cleaned, "needs_vision"

    if was_garbled:
        # Readable enough to classify and to search, but some capitals are
        # still wrong. Flagged so it is never presented as the exam's own
        # wording -- the book prints the PDF, which renders correctly.
        return cleaned, "partially_garbled"

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

        if not qp_pdf.is_file():
            continue

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
                    if entry["has_markscheme"] and ms_pdf.is_file()
                    else None
                ),
                has_markscheme=bool(entry["has_markscheme"] and ms_pdf.is_file()),
                qp_page_count=page_count,
                cropped=bool(entry.get("cropped")),
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
        print(
            f"No segments found at {WORKBOOK_DIR}. "
            f"Run build_mathsb_workbook_segments.py --execute first."
        )
        return 1

    paper_dirs = sorted(p for p in WORKBOOK_DIR.iterdir() if (p / "manifest.json").is_file())
    all_questions: list[EnrichedQuestion] = []
    for paper_dir in paper_dirs:
        all_questions.extend(enrich_paper(paper_dir))

    if not all_questions:
        print("No questions found in the segment tree.")
        return 1

    if args.show:
        key, number = args.show[0], int(args.show[1])
        for question in all_questions:
            if question.paper_key == key and question.question_number == number:
                print(json.dumps(asdict(question), indent=2)[:4000])
                return 0
        print(f"No question {number} in {key}")
        return 1

    total = len(all_questions)
    status_counts = Counter(q.text_status for q in all_questions)
    difficulty_counts = Counter(q.difficulty for q in all_questions)
    by_paper = Counter(q.paper_number.rstrip("R") for q in all_questions)
    with_parts = sum(1 for q in all_questions if q.sub_parts)
    verified_parts = sum(1 for q in all_questions if q.sub_parts_verified)

    print(f"{'=' * 74}\nMATHS B WORKBOOK ENRICHMENT\n{'=' * 74}")
    print(f"  papers                 : {len(paper_dirs)}")
    print(f"  questions              : {total}")
    print(f"  total marks            : {sum(q.marks for q in all_questions)}")
    print(f"  cropped segments       : {sum(1 for q in all_questions if q.cropped)}")
    print(f"  with mark scheme       : {sum(1 for q in all_questions if q.has_markscheme)}")
    for paper in sorted(by_paper):
        print(f"    from Paper {paper:<11}: {by_paper[paper]}")

    print("\n  Text")
    for status in ("ok", "repaired", "partially_garbled", "needs_vision"):
        print(f"    {status:<20} : {status_counts.get(status, 0)}")
    usable = total - status_counts.get("needs_vision", 0)
    print(f"    usable for Phase 3   : {usable} ({usable / total:.0%})")

    print("\n  Difficulty (from mark tariff)")
    for label in ("easy", "medium", "hard"):
        count = difficulty_counts.get(label, 0)
        print(f"    {label:<20} : {count:>4} ({count / total:.0%})")

    print("\n  Sub-parts")
    print(f"    parsed               : {with_parts}")
    print(f"    marks verified       : {verified_parts}")
    print(f"    single-part questions: {total - with_parts}")

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
