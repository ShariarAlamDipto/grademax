import pdfplumber
import re
from collections import defaultdict

pdf = pdfplumber.open('data/raw/IAL/Mechanics_1/JAN 2022 M1 MS.pdf')

# MS row pattern
MS_ROW = re.compile(
    r'(?m)^\s*(\d{1,2})\s+(?:\(([a-h]|ix|iv|v?i{0,3})\)|([a-h])\b|(?:ix|iv|v?i{0,3})\b)',
    re.IGNORECASE
)

# Header detection
MS_HEADER = re.compile(r'(?i)Question\s*Number.*Scheme.*Marks(?:.*Notes)?')

# Find header page
header_page = None
for i, page in enumerate(pdf.pages):
    if MS_HEADER.search(page.extract_text() or ""):
        header_page = i
        break

print(f"Header page: {header_page}")

# Detect all rows by page
N_QP = [1, 2, 3, 4, 5, 6, 7, 8]
rows_by_page = defaultdict(set)

for page_data in pdf.pages:
    page_idx = page_data.page_number - 1
    
    # Skip before header
    if header_page is not None and page_idx < header_page:
        continue
    
    text = page_data.extract_text() or ""
    
    for match in MS_ROW.finditer(text):
        qnum = int(match.group(1))
        
        # Gate to N_QP
        if qnum not in N_QP:
            continue
        
        rows_by_page[page_idx].add(qnum)

print("\n=== MS Rows by Page (gated to N_QP) ===")
for page_idx in sorted(rows_by_page.keys()):
    print(f"Page {page_idx}: {sorted(rows_by_page[page_idx])}")

# Build MS spans
ms_spans = {}
MS_END = re.compile(r'(?i)Total\s+for\s+Question\s+(\d{1,2})')

for qnum in N_QP:
    # Find start page
    start_page = None
    for page_idx in sorted(rows_by_page.keys()):
        if qnum in rows_by_page[page_idx]:
            start_page = page_idx
            break
    
    if start_page is None:
        print(f"\nQ{qnum}: NO START PAGE FOUND")
        continue
    
    # Find end page
    end_page = start_page
    for page_idx in range(start_page, len(pdf.pages)):
        text = pdf.pages[page_idx].extract_text() or ""
        if re.search(rf"(?i)Total\s+for\s+[Qq]uestion\s+{qnum}\b", text):
            end_page = page_idx
            break
    
    ms_spans[qnum] = list(range(start_page, end_page + 1))
    print(f"\nQ{qnum}: MS pages {ms_spans[qnum]}")

pdf.close()
