import pdfplumber
import re

pdf = pdfplumber.open('data/raw/IAL/Mechanics_1/JAN 2022 M1 MS.pdf')

# Check for headers
pattern = re.compile(r'Question\s*Number.*Scheme.*Marks', re.I | re.DOTALL)
print("=== HEADER DETECTION ===")
for i, page in enumerate(pdf.pages[:10]):
    text = page.extract_text() or ""
    has_header = bool(pattern.search(text))
    print(f"Page {i}: {'HAS HEADER' if has_header else 'no header'}")

# Check for question rows
row_pattern = re.compile(
    r'(?m)^\s*(\d{1,2})\s+(?:\(([a-h]|ix|iv|v?i{0,3})\)|([a-h])\b|(?:ix|iv|v?i{0,3})\b)',
    re.IGNORECASE
)

print("\n=== QUESTION ROW DETECTION ===")
for i in range(6, 15):
    page = pdf.pages[i]
    text = page.extract_text() or ""
    matches = list(row_pattern.finditer(text))
    if matches:
        qnums = [int(m.group(1)) for m in matches]
        print(f"Page {i}: Questions {sorted(set(qnums))}")
    else:
        print(f"Page {i}: No matches")

pdf.close()
