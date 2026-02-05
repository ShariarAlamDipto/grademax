import pdfplumber
import re

pdf = pdfplumber.open('data/raw/IAL/Mechanics_1/JAN 2022 M1 QP.pdf')
page5 = pdf.pages[5]

# Test QP_START pattern
QP_START = re.compile(r'(?m)^(\d{1,2})\.\s+')
text = page5.extract_text()

print("Page 5 text (first 500 chars):")
print(text[:500])
print("\n" + "="*60)

matches = list(QP_START.finditer(text))
print(f"\nQP_START matches: {len(matches)}")
for m in matches:
    print(f"  Qnum {m.group(1)} at pos {m.start()}: {repr(text[m.start():m.end()+20])}")

# Check if "3." is in the text
if "3." in text:
    idx = text.index("3.")
    print(f"\n'3.' found at index {idx}")
    print(f"Context: {repr(text[max(0,idx-20):idx+40])}")

pdf.close()
