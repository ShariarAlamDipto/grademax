#!/usr/bin/env python3
import fitz
doc = fitz.open('data/raw/IGCSE/Further Pure Maths/2011/May-Jun/Paper 1.pdf')
for page_idx in range(0, 5):
    text = doc[page_idx].get_text()
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    print(f'\n=== PAGE {page_idx+1} ===')
    for i, l in enumerate(lines[:20]):
        print(f'{i}: |{l}|')
