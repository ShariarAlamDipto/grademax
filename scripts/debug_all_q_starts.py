import pdfplumber
import re

pdf = pdfplumber.open('data/raw/IAL/Mechanics_1/JAN 2022 M1 QP.pdf')

question_starts = [
    (1, 1), (2, 3), (3, 5), (4, 9), (5, 13), (6, 17), (7, 21), (8, 25)
]

print("Question start positions:")
for qnum, page_idx in question_starts:
    page = pdf.pages[page_idx]
    words = page.extract_words()
    
    # Find "N." where N is the question number
    target = f"{qnum}."
    q_word = next((w for w in words if w['text'] == target), None)
    
    if q_word:
        x_rel = q_word['x0'] / page.width
        print(f"Q{qnum}: x_rel = {x_rel:.3f}")
    else:
        print(f"Q{qnum}: NOT FOUND")

pdf.close()
