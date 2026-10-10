"""
Maths B (4MB1) Chapter 3 Algebra assessment: 20 workbook questions, one paper.

Reuses the print workbook's layout engine (trim, working space, renumbering) so
the exam looks like the book. Questions come from the verified print index,
spread across all eight Algebra sections, ordered roughly easy to hard and
numbered 1-20. Writes the paper and its mark scheme to data/workbook/mathsb/exams/.

    python scripts/build_mathsb_algebra_exam.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_mathsb_workbook_print as book  # noqa: E402

OUT_DIR = book.SEGMENT_DIR / "exams"
TITLE = "Chapter 3: Algebra"
DURATION = "1 hour 30 minutes"

# (section, source) -- the source string exactly as print_index.json writes it.
PICKS = [
    ("3.7", "2022 May/June Paper 1 Q1"),
    ("3.1", "2021 May/June Paper 1 Q1"),
    ("3.2", "2020 October/November Paper 1 Q1"),
    ("3.6", "2022 May/June Paper 1 Q4"),
    ("3.1", "2022 January Paper 1 Q2"),
    ("3.2", "2022 May/June Paper 1 Q9"),
    ("3.2", "2020 January Paper 1 Q9"),
    ("3.7", "2022 January Paper 1 Q6"),
    ("3.3", "2021 May/June Paper 1 Q5"),
    ("3.5", "2021 May/June Paper 1 Q12"),
    ("3.1", "2022 May/June Paper 1 Q13"),
    ("3.4", "2019 January Paper 1R Q14"),
    ("3.2", "2021 May/June Paper 1 Q17"),
    ("3.1", "2022 January Paper 1 Q22"),
    ("3.3", "2021 October/November Paper 1 Q19"),
    ("3.8", "2021 January Paper 1 Q19"),
    ("3.5", "2021 October/November Paper 1 Q24"),
    ("3.2", "2018 January Paper 1R Q22"),
    ("3.8", "2021 May/June Paper 1 Q24"),
    ("3.4", "2022 January Paper 1 Q25"),
]
# Removed after review: 2022 May/June P2 Q3 (indices), 2022 May/June P1 Q18
# (surds), 2021 January P1 Q4 (substitution) and 2021 Oct/Nov P1 Q18 (matrices).

# Segments the segmenter mis-cut, replaced by hand-cut ones. 2020 Jan P1 Q9's
# mark scheme sits on a /Rotate 90 page and came out as a sideways strip with
# its left edge missing; the override is cut upright from the full board page.
OVERRIDES = {
    ("ms", "2020_jan_1", 9): OUT_DIR / "override_2020_jan_1_ms_q9.pdf",
}

SEASON_KEY = {label: key for key, label in book.SESSION_LABEL.items()}
INSTRUCTIONS = (
    "Use black ink or ball-point pen.",
    "Answer ALL questions in the spaces provided.",
    "Show all your working. Answers without working may not gain full marks.",
    "Calculators may be used.",
    "The marks for each question are shown beside it.",
)


def paper_key(source: str) -> tuple[str, int]:
    """'2021 October/November Paper 1R Q19' -> ('2021_oct-nov_1R', 19)."""
    head, number = source.rsplit(" Q", 1)
    year, rest = head.split(" ", 1)
    season, paper = rest.rsplit(" Paper ", 1)
    return f"{year}_{SEASON_KEY[season]}_{paper}", int(number)


def load_questions() -> list[dict]:
    index = json.loads((book.BOOK_DIR / "print_index.json").read_text(encoding="utf-8"))
    by_source = {(q["section"], q["source"]): q for q in index["questions"]}
    rows = []
    for pick in PICKS:
        entry = by_source.get(pick)
        if entry is None:
            raise SystemExit(f"not in the print index: {pick}")
        key, number = paper_key(entry["source"])
        rows.append({**entry, "source_paper_key": key, "source_question_number": number})
    return rows


def text(page: fitz.Page, at: tuple[float, float], value: str, size: float,
         bold: bool = False, muted: bool = False) -> None:
    page.insert_text(at, value, fontname="hebo" if bold else "helv", fontsize=size,
                     color=book.MUTED if muted else book.INK)


def cover(total: int, marks: int) -> fitz.Document:
    doc = fitz.open()
    page = doc.new_page(width=book.PAGE_WIDTH, height=book.PAGE_HEIGHT)
    x, right, y = book.MARGIN, book.PAGE_WIDTH - book.MARGIN, 110
    text(page, (x, y), book.BRAND, 13, bold=True, muted=True)
    text(page, (x, y + 26), f"{book.SUBJECT_TITLE} {book.SUBJECT_NAME} ({book.SUBJECT_CODE})",
         12, muted=True)
    text(page, (x, y + 74), "Chapterwise Assessment", 28, bold=True)
    text(page, (x, y + 110), TITLE, 19, bold=True)
    text(page, (x, y + 138), f"Time: {DURATION}      Total: {marks} marks      "
         f"Questions: {total}", 11.5)

    y += 200
    for label in ("Name", "Class", "Date"):
        text(page, (x, y), label, 11, bold=True)
        page.draw_line((x + 60, y + 2), (right, y + 2), color=book.MUTED, width=0.6)
        y += 34

    y += 20
    text(page, (x, y), "Instructions", 12, bold=True)
    for line in INSTRUCTIONS:
        y += 20
        text(page, (x + 10, y), f"-  {line}", 10.5)

    y += 50
    text(page, (x, y), "For marking", 12, bold=True)
    y += 12
    cols, cell_h = 10, 22
    cell_w = (right - x) / cols
    for i in range(total):
        row, col = divmod(i, cols)
        rx, ry = x + col * cell_w, y + row * cell_h * 2
        for top in (ry, ry + cell_h):
            page.draw_rect(fitz.Rect(rx, top, rx + cell_w, top + cell_h),
                           color=book.MUTED, width=0.6)
        text(page, (rx + 4, ry + 15), f"Q{i + 1}", 8.5, muted=True)
    y += -(-total // cols) * cell_h * 2 + 34
    text(page, (x, y), f"Total:  ______ / {marks}", 14, bold=True)
    return doc


def body(questions: list[dict], kind: str) -> tuple[fitz.Document, list[str]]:
    doc, warnings = fitz.open(), []
    suffix = "  ·  Mark scheme" if kind == "ms" else ""
    running = f"{book.BRAND}  ·  {book.SUBJECT_NAME}  ·  {TITLE} Assessment{suffix}"
    space = book.NO_SPACE if kind == "ms" else book.SPACE_POLICIES[book.DEFAULT_SPACE]
    flow = book.Flow(doc, running, space)
    flow.section_break(f"{TITLE}{suffix}")
    for printed, question in enumerate(questions, 1):
        path = OVERRIDES.get(
            (kind, question["source_paper_key"], question["source_question_number"]),
            book.segment_path(question, kind))
        if not path.is_file():
            warnings.append(f"Q{printed} {question['source']}: missing {path.name}")
            continue
        right = f"{question['marks']} marks   ·   {question['source']}"
        with book.open_segment(path) as source:
            # A hand-cut override is already trimmed, and the ink trim
            # misreads its raster edges, so it goes on whole.
            bands, masks = ((book.whole_page_bands(source), {})
                            if path.parent == OUT_DIR else book.trimmed_layout(source))
            if not bands:
                bands = book.whole_page_bands(source)
            renumber, label = None, str(printed)
            if kind == "qp":
                box = book.question_number_box(
                    source, question["source_question_number"], bands[0])
                if box is not None and box.x0 <= bands[0].x0 + book.NUMBER_ZONE:
                    renumber, label = (box, str(printed)), ""
            flow.add(source, bands, label, right, question["marks"], False,
                     renumber=renumber, masks=masks)
    return doc, warnings


def number_pages(doc: fitz.Document) -> None:
    total = doc.page_count
    for i, page in enumerate(doc, 1):
        label = f"Page {i} of {total}"
        width = fitz.get_text_length(label, fontname="helv", fontsize=8)
        text(page, (book.PAGE_WIDTH - book.MARGIN - width, book.PAGE_HEIGHT - 12),
             label, 8, muted=True)


def main() -> int:
    questions = load_questions()
    marks = sum(q["marks"] for q in questions)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    books = (("qp", "MathsB_Algebra_Exam_v3.pdf"),
             ("ms", "MathsB_Algebra_Exam_MarkScheme_v3.pdf"))
    for kind, name in books:
        doc, warnings = body(questions, kind)
        if kind == "qp":
            front = cover(len(questions), marks)
            front.insert_pdf(doc)
            doc = front
        number_pages(doc)
        target = OUT_DIR / name
        doc.save(target, deflate=True, garbage=3)
        print(f"{name}: {doc.page_count} pages, {target.stat().st_size // 1024} KB")
        for warning in warnings:
            print(f"  WARN {warning}")
    print(f"{len(questions)} questions, {marks} marks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
