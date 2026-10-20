"""Build a second 67-mark algebra assessment without reusing Test 1 questions."""
from __future__ import annotations

import json
from pathlib import Path

import fitz

import build_mathsb_algebra_exam as first

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output" / "pdf"
QA = ROOT / "tmp" / "pdfs" / "algebra_test_2"
PICKS = [
    ("3.7", "2020 January Paper 1 Q7"),
    ("3.1", "2022 May/June Paper 1 Q6"),
    ("3.2", "2022 May/June Paper 1R Q6"),
    ("3.6", "2021 May/June Paper 1 Q3"),
    ("3.1", "2019 May/June Paper 1 Q7"),
    ("3.2", "2020 October/November Paper 1 Q11"),
    ("3.2", "2020 January Paper 1R Q9"),
    ("3.7", "2019 January Paper 1R Q7"),
    ("3.3", "2018 May/June Paper 1R Q7"),
    ("3.5", "2020 January Paper 1 Q11"),
    ("3.4", "2020 October/November Paper 1R Q11"),
    ("3.8", "2020 January Paper 1 Q12"),
    ("3.1", "2021 January Paper 1 Q16"),
    ("3.2", "2019 May/June Paper 1R Q18"),
    ("3.3", "2019 May/June Paper 1R Q21"),
    ("3.1", "2018 May/June Paper 1 Q19"),
    ("3.1", "2018 May/June Paper 1R Q19"),
    ("3.3", "2022 January Paper 1 Q24"),
    ("3.4", "2018 May/June Paper 1R Q23"),
    ("3.8", "2022 January Paper 1R Q29"),
]


def questions():
    index = json.loads((first.book.BOOK_DIR / "print_index.json").read_text(encoding="utf-8"))
    lookup = {(q["section"], q["source"]): q for q in index["questions"]}
    rows = []
    old_sources = {source for _, source in first.PICKS}
    assert len(PICKS) == len(set(PICKS)) == 20
    for pick in PICKS:
        assert pick[1] not in old_sources, f"Repeated question: {pick}"
        entry = lookup[pick]
        key, number = first.paper_key(entry["source"])
        row = {**entry, "source_paper_key": key, "source_question_number": number}
        assert first.book.segment_path(row, "qp").is_file()
        assert first.book.segment_path(row, "ms").is_file()
        rows.append(row)
    assert sum(q["marks"] for q in rows) == 67
    assert {q["section"] for q in rows} == {f"3.{i}" for i in range(1, 9)}
    return rows


def make_question_paper(rows):
    first.TITLE = "Chapter 3: Algebra - Test 2"
    book = first.book
    body = fitz.open()
    flow = book.Flow(body, "GradeMax  |  Mathematics B  |  Algebra Test 2",
                     book.SPACE_POLICIES[book.DEFAULT_SPACE])
    flow.section_break(first.TITLE)
    for printed, question in enumerate(rows, 1):
        with book.open_segment(book.segment_path(question, "qp")) as source:
            bands, masks = book.trimmed_layout(source)
            # On a y-crop the original full-page frame is not a filled mask.
            masks = {p: [r for r in rects if not (r.width > 100 and r.height > 100)]
                     for p, rects in masks.items()}
            # This crop ends with the original page number and barcode.
            if printed == 13:
                bands = [b for b in bands if b.y0 < 340]
            needed = (sum(flow._scaled_height(source, band) for band in bands)
                      + 12 * len(bands) + flow.policy.space_for(question["marks"]) + 30)
            if flow.page is not None and needed > flow._room():
                flow._start_page()
            box = book.question_number_box(source, question["source_question_number"], bands[0])
            renumber = (box, str(printed)) if box is not None else None
            flow.add(source, bands, "" if renumber else str(printed),
                     f"{question['marks']} marks   |   {question['source']}",
                     question["marks"], False, renumber=renumber, masks=masks)
    # The working-space allocator can end on an empty separator-only sheet.
    while len(body) > 1 and len(body[-1].get_text().splitlines()) <= 1:
        body.delete_page(-1)
    doc = first.cover(20, 67)
    doc.insert_pdf(body)
    first.number_pages(doc)
    doc.set_metadata({"title": "GradeMax Mathematics B - Algebra Test 2",
                      "subject": "20 questions, 67 marks, 90 minutes",
                      "author": "GradeMax"})
    target = OUTPUT / "MathsB_Algebra_Test_2.pdf"
    doc.save(target, deflate=True, garbage=3)
    print(f"{target}: {len(doc)} pages")


# Working is checked algebraically and against the source marking guidance.
# Each step: text or mathematical expression, followed by its marking note.
SOLUTIONS = [
    [(r"a_3=2-5(3)=-13,\quad a_4=-18,\quad a_5=-23", "2 marks"),
     ("1 mark for two correct terms, or three integer terms decreasing by 5.", ""),
     ("2 marks for all three correct terms in order.", "")],
    [(r"2mc^2+6p^2c^4=2c^2(m+3p^2c^2)", "M1 A1"),
     ("Take out a common factor, then factorise completely.", "")],
    [(r"3-2x<5+6x\;\Rightarrow\;-2<8x", "M1"),
     (r"x>-\frac{1}{4}", "A1")],
    [(r"y-4y^2=tx", "M1"), (r"x=\frac{y-4y^2}{t}", "A1")],
    [(r"(4x-5)(2x+3)=8x^2+12x-10x-15", "M1"),
     (r"8x^2+2x-15", "A1")],
    [(r"5(x+5)+4(x-3)=40", "M1"),
     (r"5x+25+4x-12=40\;\Rightarrow\;9x=27", "M1"),
     (r"x=3", "A1")],
    [(r"x-10<3x+4\;\Rightarrow\;x>-7", "M1"),
     (r"3x+4\leq20-5x\;\Rightarrow\;x\leq2", "M1"),
     (r"-7<x\leq2", "A1")],
    [(r"16,\quad -4", "B1 + B1"),
     (r"\mathrm{Multiply\ each\ term\ by}\;-\frac{1}{4}", "B1")],
    [(r"4x-y=4,\quad4x+7y=-20\;\Rightarrow\;8y=-24", "M1"),
     (r"y=-3,\quad4x+3=4", "M1"),
     (r"x=\frac{1}{4},\quad y=-3", "A1")],
    [(r"\frac{5(2+5x)-2(3-2x)}{(3-2x)(2+5x)}", "M1"),
     (r"\frac{10+25x-6+4x}{(3-2x)(2+5x)}", "M1"),
     (r"\frac{29x+4}{(3-2x)(2+5x)}", "A1")],
    [(r"-3x^2+6x+2=-3(x^2-2x)+2", "M1"),
     (r"-3(x-1)^2+5", "M1"),
     (r"a=-3,\quad b=-1,\quad c=5", "A1")],
    [(r"4x^3-8x^2-12x=(2x+k)Q(x)", "B1"),
     (r"4x(x-3)(x+1)=(2x+2)\,[2x(x-3)]", "M1"),
     (r"k=2", "A1")],
    [(r"\mathrm{(a)}\quad10ab-24a^2=2a(5b-12a)", "M1 A1"),
     (r"\mathrm{(b)}\quad p^2+10p-24=(p+12)(p-2)", "M1 A1")],
    [(r"\mathrm{(a)}\quad x+3x+(3x-7)=56", "M1 A1"),
     (r"\mathrm{(b)}\quad7x=63\;\Rightarrow\;x=9", "M1"),
     (r"\mathrm{Suzy:}\quad3(9)-7=20\ \mathrm{crayons}", "A1")],
    [(r"9x+12y=13.5,\quad8x-12y=46", "M1"),
     (r"17x=59.5\;\Rightarrow\;x=3.5", "A1"),
     (r"10.5+4y=4.5\;\Rightarrow\;y=-1.5", "M1 A1")],
    [(r"10x+5y-2x^2-xy=5(2x+y)-x(2x+y)", "M1"),
     (r"4x^2-y^2=(2x-y)(2x+y)", "M1"),
     (r"\frac{(5-x)(2x+y)}{(2x-y)(2x+y)}=\frac{5-x}{2x-y}", "M1 A1")],
    [(r"(3x+2)\,\frac{5}{3x^2-7x-6}-\frac{5}{x+3}", "M1"),
     (r"3x^2-7x-6=(3x+2)(x-3)", "M1"),
     (r"\frac{5}{x-3}-\frac{5}{x+3}=\frac{5(x+3)-5(x-3)}{(x-3)(x+3)}", "M1"),
     (r"\frac{30}{x^2-9}", "A1")],
    [(r"M=10p+q,\quad N=10q+p", "M1"),
     (r"(10q+p)-(10p+q)=9\;\Rightarrow\;q-p=1", "M1"),
     (r"q=p+1,\quad2p+1=13\;\Rightarrow\;p=6,\quad q=7", "A1"),
     (r"M=10(6)+7=67", "M1 A1")],
    [(r"\mathrm{(a)}\quad x^2+10x-7=(x+5)^2-32", "B1 + B1"),
     (r"\mathrm{(b)}\quad(x+5)^2=32", "M1"),
     (r"x+5=\pm\sqrt{32}", "M1"),
     (r"x=-5\pm\sqrt{32}", "A1"),
     ("Use the requested form a +/- sqrt(b).", "")],
    [(r"\mathrm{(a)}\quad3(5)^3-20(5)^2+5k+10=0", "M1"),
     (r"375-500+5k+10=0\;\Rightarrow\;5k=115,\quad k=23", "A1"),
     (r"\mathrm{(b)}\quad(x-5)(3x^2-5x-2)=0", "M1 A1"),
     (r"(x-5)(3x+1)(x-2)=0", "M1"),
     (r"x=5,\quad x=-\frac{1}{3},\quad x=2", "A1")],
]


def make_mark_scheme(rows):
    from io import BytesIO
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from matplotlib.mathtext import math_to_image
    from PIL import Image

    target = OUTPUT / "MathsB_Algebra_Test_2_Mark_Scheme.pdf"
    c = canvas.Canvas(str(target), pagesize=(595, 842))
    c.setTitle("GradeMax Mathematics B - Algebra Test 2 Mark Scheme")
    c.setAuthor("GradeMax")
    for page_index in range(5):
        c.setFillColorRGB(.13, .17, .22)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(42, 795, "Algebra Test 2 - Mark Scheme")
        c.setFont("Helvetica", 9)
        c.drawString(42, 776, "Mathematics B (4MB1)  |  20 questions  |  67 marks")
        c.setFont("Helvetica", 8)
        c.drawString(42, 759, "M = method, A = accuracy, B = independent mark. Accept equivalent valid methods.")
        for offset in range(4):
            number = page_index * 4 + offset + 1
            top = 730 - offset * 165
            c.setStrokeColorRGB(.82, .85, .88)
            c.line(42, top + 9, 553, top + 9)
            c.setFont("Helvetica-Bold", 10.5)
            c.drawString(42, top - 6, f"Question {number}")
            c.drawRightString(553, top - 6, f"{rows[number-1]['marks']} marks")
            y = top - 32
            for expression, mark in SOLUTIONS[number - 1]:
                c.setFont("Helvetica", 9)
                if mark:
                    buffer = BytesIO()
                    math_to_image(f"${expression}$", buffer, dpi=240, format="png", color="#212b38")
                    buffer.seek(0)
                    im = Image.open(buffer)
                    width, height = im.width * 72 / 240, im.height * 72 / 240
                    scale = min(1, 420 / width)
                    width, height = width * scale, height * scale
                    c.drawImage(ImageReader(im), 52, y-height, width=width, height=height, mask="auto")
                    c.drawRightString(553, y - min(height, 11), mark)
                    y -= max(17, height + 8)
                else:
                    c.drawString(52, y-9, expression)
                    y -= 21
            assert y > top - 155, f"Question {number} overflows its block"
        c.setFont("Helvetica", 8)
        c.drawString(42, 30, "GradeMax  |  Teacher copy")
        c.drawRightString(553, 30, f"Page {page_index+1} of 5")
        c.showPage()
    c.save()
    print(f"{target}: 5 pages")


def render_contacts(path, prefix, columns=3):
    from PIL import Image, ImageDraw
    with fitz.open(path) as doc:
        for start in range(0, len(doc), columns * 2):
            canvas = Image.new("RGB", (columns * 430, 2 * 635), "#d9dde1")
            draw = ImageDraw.Draw(canvas)
            for offset, page in enumerate(doc.pages(start, min(start + columns * 2, len(doc)))):
                pix = page.get_pixmap(matrix=fitz.Matrix(0.7, 0.7), alpha=False)
                im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                im.thumbnail((414, 596))
                col, row = offset % columns, offset // columns
                canvas.paste(im, (col * 430 + 8, row * 635 + 25))
                draw.text((col * 430 + 8, row * 635 + 6), f"Page {start + offset + 1}", fill="black")
            canvas.save(QA / f"{prefix}_{start // (columns * 2) + 1}.png")


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    rows = questions()
    make_question_paper(rows)
    make_mark_scheme(rows)
    render_contacts(OUTPUT / "MathsB_Algebra_Test_2.pdf", "paper")
    render_contacts(OUTPUT / "MathsB_Algebra_Test_2_Mark_Scheme.pdf", "scheme")
    print("20 fresh questions; 67 marks; all eight algebra sections")


if __name__ == "__main__":
    main()
