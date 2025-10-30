"""
Analyze mark scheme structure to improve MS linking rules.

This script examines actual MS PDFs to understand:
- How questions are numbered in MS
- Table structure patterns
- "Total for question" patterns
- Page boundaries
"""

import pdfplumber
from pathlib import Path
import re

def analyze_ms_structure(ms_path, paper_name):
    """Deep analysis of MS structure."""
    print(f"\n{'='*80}")
    print(f"Analyzing: {paper_name}")
    print(f"{'='*80}")
    
    try:
        with pdfplumber.open(ms_path) as pdf:
            print(f"Total pages: {len(pdf.pages)}")
            
            for page_num in range(min(5, len(pdf.pages))):  # First 5 pages
                page = pdf.pages[page_num]
                print(f"\n--- Page {page_num} ---")
                
                # Extract words with positions
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                
                # Group into lines
                lines = {}
                for word in words:
                    y_pos = round(word['top'], 1)
                    if y_pos not in lines:
                        lines[y_pos] = []
                    lines[y_pos].append(word)
                
                # Show first 20 lines with positions
                for i, y_pos in enumerate(sorted(lines.keys())[:20]):
                    line_words = lines[y_pos]
                    line_text = " ".join([w['text'] for w in line_words])
                    min_x = min([w['x0'] for w in line_words])
                    
                    # Highlight lines with question markers
                    marker = ""
                    if re.match(r'^\d+\s', line_text):
                        marker = " 🔢 [Q-NUM]"
                    elif 'Total for question' in line_text.lower():
                        marker = " ✅ [TOTAL]"
                    elif 'Question' in line_text and 'number' in line_text:
                        marker = " 📋 [HEADER]"
                    
                    print(f"  x={min_x:5.1f}  |  {line_text[:70]}{marker}")
    
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Analyze multiple MS files."""
    test_papers = [
        ("2018 Jan Paper 1", r"data\raw\IGCSE\Physics\2018\Jan\Paper 1_MS.pdf"),
        ("2020 Jan Paper 1", r"data\raw\IGCSE\Physics\2020\Jan\Paper 1_MS.pdf"),
        ("2022 May-Jun Paper 2", r"data\raw\IGCSE\Physics\2022\May-Jun\Paper 2_MS.pdf"),
    ]
    
    for name, path in test_papers:
        if Path(path).exists():
            analyze_ms_structure(path, name)
        else:
            print(f"\n⚠️  {name} not found")
    
    print(f"\n\n{'='*80}")
    print("KEY OBSERVATIONS:")
    print(f"{'='*80}")
    print("\nLook for patterns in:")
    print("  1. How question numbers appear (column position, format)")
    print("  2. Where 'Total for question' markers appear")
    print("  3. Table structure (if any)")
    print("  4. Sub-question notation (a, b, c, i, ii)")


if __name__ == "__main__":
    main()
