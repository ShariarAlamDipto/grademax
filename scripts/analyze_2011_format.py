#!/usr/bin/env python3
"""Analyze 2011 paper format to understand question structure"""

import fitz

doc = fitz.open('data/raw/IGCSE/Further Pure Maths/2011/May-Jun/Paper 1.pdf')

print(f'Total pages: {len(doc)}\n')

# Check pages 4-15 (likely contains multiple questions)
for page_idx in range(3, min(15, len(doc))):
    text = doc[page_idx].get_text()
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    print(f'=== PAGE {page_idx+1} ===')
    # Show first 15 lines
    for i, line in enumerate(lines[:15]):
        print(f'{i}: |{line}|')
    print()
