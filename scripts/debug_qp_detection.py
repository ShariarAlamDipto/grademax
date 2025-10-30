"""
Debug script to understand why question detection fails on some papers
"""

import pdfplumber
import re
import json
from pathlib import Path

# Test papers - expanded to find x-position range
test_papers = [
    ("2011 May-Jun P1", r"data\raw\IGCSE\Physics\2011\May-Jun\Paper 1.pdf"),
    ("2012 Jan P2", r"data\raw\IGCSE\Physics\2012\Jan\Paper 2.pdf"),
    ("2013 May-Jun P1", r"data\raw\IGCSE\Physics\2013\May-Jun\Paper 1.pdf"),
    ("2015 Jan P1", r"data\raw\IGCSE\Physics\2015\Jan\Paper 1.pdf"),
    ("2018 Jan P1", r"data\raw\IGCSE\Physics\2018\Jan\Paper 1.pdf"),
    ("2020 Jan P1", r"data\raw\IGCSE\Physics\2020\Jan\Paper 1.pdf"),
    ("2024 May-Jun P1", r"data\raw\IGCSE\Physics\2024\May-Jun\Paper 1.pdf"),
]

# Load rules
with open("config/physics_segmentation_rules.json", 'r') as f:
    rules = json.load(f)

qp_rules = rules['qp_rules']
question_pattern = re.compile(qp_rules['question_start']['text_pattern'])

def analyze_paper(name, pdf_path):
    """Analyze a paper to see what's happening with detection"""
    print(f"\n{'='*80}")
    print(f"Analyzing: {name}")
    print(f"{'='*80}")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Total pages: {len(pdf.pages)}")
            
            # Check first 5 pages for question starts
            for page_num in range(min(5, len(pdf.pages))):
                page = pdf.pages[page_num]
                text = page.extract_text()
                
                if not text:
                    print(f"\nPage {page_num + 1}: [NO TEXT EXTRACTED]")
                    continue
                
                print(f"\n--- Page {page_num + 1} ---")
                
                # Extract words with positions
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                
                # Group into lines
                lines_dict = {}
                for word in words:
                    y = round(word['top'], 1)
                    if y not in lines_dict:
                        lines_dict[y] = []
                    lines_dict[y].append(word)
                
                # Check each line
                for y in sorted(lines_dict.keys())[:20]:  # First 20 lines
                    line_words = sorted(lines_dict[y], key=lambda w: w['x0'])
                    line_text = ' '.join(w['text'] for w in line_words)
                    x_pos = line_words[0]['x0'] if line_words else 0
                    
                    # Check if matches pattern
                    match = question_pattern.match(line_text.strip())
                    
                    if match:
                        print(f"  [MATCH] x={x_pos:5.1f} | {line_text[:80]}")
                    elif line_text.strip() and line_text[0].isdigit():
                        print(f"          x={x_pos:5.1f} | {line_text[:80]}")
                
                # Check for "Total for Question" markers
                if "(Total for Question" in text or "(Total for question" in text:
                    print(f"  [OK] Found 'Total for Question' marker")
                
                # Check first line format
                first_lines = text.split('\n')[:5]
                print(f"\nFirst 5 text lines:")
                for i, line in enumerate(first_lines, 1):
                    print(f"  {i}. {line[:100]}")
    
    except Exception as e:
        print(f"[ERROR] Error: {e}")

if __name__ == "__main__":
    for name, path in test_papers:
        analyze_paper(name, path)
    
    print(f"\n{'='*80}")
    print(f"Pattern being used: {qp_rules['question_start']['text_pattern']}")
    print(f"Position range: x {qp_rules['question_start']['position_rules']['x_min']}-{qp_rules['question_start']['position_rules']['x_max']}")
    print(f"{'='*80}")
