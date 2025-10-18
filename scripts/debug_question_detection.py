import fitz
import re

pdf_path = "data/raw/IGCSE/Physics/2024/May-Jun/Paper 1.pdf"
doc = fitz.open(pdf_path)

# Question patterns from the code
QUESTION_PATTERNS = [
    r'^\s*(\d+)\s+[A-Z(]',          # "1 The" or "1 ("
    r'^\s*(\d+)\s{2,}[A-Z]',        # "1        This" (multiple spaces)
    r'^\s*(\d+)\s*\n',               # "1\n"
    r'^Question\s+(\d+)',            # "Question 1"
    r'^\s*(\d+)\s*\.',               # "1."
    r'^\s*(\d+)\s+This\s+question', # "1 This question"
]

print("Testing question detection on key pages:\n")

for page_num in [2, 3, 5, 6, 8]:
    if page_num >= len(doc):
        break
    
    page = doc[page_num]
    text = page.get_text()
    lines = text.strip().split('\n')[:20]  # First 20 lines
    
    print(f"Page {page_num + 1}:")
    print("First 20 lines:")
    for i, line in enumerate(lines):
        # Skip common headers in display
        if any(skip in line for skip in ['DO NOT WRITE', 'Turn over', '*P']):
            continue
        print(f"  {i}: '{line}'")
    
    # Try matching
    matched = False
    for pattern in QUESTION_PATTERNS:
        for line in lines:
            match = re.search(pattern, line, re.MULTILINE)
            if match:
                print(f"  ✅ MATCHED with pattern: {pattern}")
                print(f"     Question number: {match.group(1)}")
                matched = True
                break
        if matched:
            break
    
    if not matched:
        print(f"  ❌ NO MATCH")
    print()

doc.close()
