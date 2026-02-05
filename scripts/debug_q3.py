import pdfplumber

pdf = pdfplumber.open('data/raw/IAL/Mechanics_1/JAN 2022 M1 QP.pdf')
page = pdf.pages[5]
words = page.extract_words()

print("Page 5 (Q3 start) - Looking for '3.':")
q3_words = [w for w in words if '3' in w['text']][:10]
for w in q3_words:
    x_rel = w['x0'] / page.width
    print(f"  '{w['text']}': x={w['x0']:.1f}, x_rel={x_rel:.3f}")

print(f"\nExpected margin range: 0.135-0.175")
print(f"Page width: {page.width}")
pdf.close()
