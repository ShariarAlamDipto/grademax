"""Check watermark pattern in PDFs"""
import fitz
import sys

pdf_path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/IGCSE/Physics/2024/May-Jun/Paper 1.pdf"
doc = fitz.open(pdf_path)

print(f"Checking: {pdf_path}")
print(f"Total pages: {len(doc)}")
print("\nWatermarks found:\n")

for page_num in [0, 2, 5, 10, 15]:
    if page_num >= len(doc):
        break
    
    page = doc[page_num]
    blocks = page.get_text('blocks')
    
    # Look for watermarks (usually at bottom left or top left)
    watermarks = []
    for b in blocks:
        x, y, text = b[0], b[1], b[4].strip()
        # Check bottom area (y > 800) or left area (x < 30)
        if (y > 800 or x < 30) and any(keyword in text for keyword in ['Physics', 'PMT', 'Chemistry', 'Biology', 'Mathematics']):
            watermarks.append((x, y, text))
    
    print(f"Page {page_num + 1}:")
    for x, y, text in watermarks:
        print(f"  X:{x:.1f}, Y:{y:.1f} -> {text[:100]}")
    print()

doc.close()
