import fitz
import sys

pdf_path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/IGCSE/Physics/2024/May-Jun/Paper 1.pdf"
doc = fitz.open(pdf_path)

print(f"Checking question format in: {pdf_path}\n")

for i in [2, 3, 4, 5]:
    if i >= len(doc):
        break
    
    print(f"{'='*70}")
    print(f"Page {i+1}")
    print(f"{'='*70}")
    text = doc[i].get_text()
    print(text[:1000])
    print("\n")

doc.close()
