import re
import PyPDF2

pdf = open('data/raw/IGCSE/Further Pure Maths/2012/Jan/Paper 1.pdf', 'rb')
reader = PyPDF2.PdfReader(pdf)

for page_num in [9, 29, 33]:
    text = reader.pages[page_num].extract_text()
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    search_lines = lines[3:15]
    
    print(f"\n=== PAGE {page_num} ===")
    print(f"First 5 search lines: {search_lines[:5]}")
    
    for i, line in enumerate(search_lines):
        if re.match(r'^\d{1,2}$', line):
            next_line = search_lines[i+1] if i+1 < len(search_lines) else "NONE"
            print(f"  Found number: |{line}|")
            print(f"  Next line: |{next_line}|")
            print(f"  Next line len: {len(next_line)}")
            print(f"  Would detect: {len(next_line) > 1}")
