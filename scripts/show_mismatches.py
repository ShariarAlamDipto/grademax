#!/usr/bin/env python3
"""
Show specific question number mismatches
"""

import json
from pathlib import Path

processed_dir = Path('data/processed')

print("="*80)
print("SPECIFIC QUESTION NUMBER MISMATCHES")
print("="*80)
print()

papers_to_check = [
    '2012_Jan_1P', '2012_Jun_2P', '2013_Jun_2P', '2014_Jun_1P',
    '2015_Jan_1P', '2015_Jan_2P', '2016_Jan_1P', '2017_Jun_1P',
    '2021_Jun_1P', '2022_Jan_2P', '2023_Jan_2P', '2023_Jun_1P',
    '2024_Jun_2P'
]

for paper_name in papers_to_check:
    paper_dir = processed_dir / paper_name
    manifest_file = paper_dir / "manifest.json"
    
    if not manifest_file.exists():
        continue
    
    with open(manifest_file, 'r') as f:
        data = json.load(f)
    
    # Find unlinked questions
    unlinked = [q for q in data['questions'] if not q['has_markscheme']]
    
    if unlinked:
        print(f"\n📄 {paper_name}")
        print("-"*80)
        
        # Show all question numbers available
        qp_numbers = [q['question_number'] for q in data['questions']]
        ms_numbers = [q['question_number'] for q in data['questions'] if q['has_markscheme']]
        
        print(f"   QP Questions: {', '.join(qp_numbers)}")
        print(f"   MS Matched:   {', '.join(ms_numbers)}")
        print(f"   Unmatched:    {', '.join(q['question_number'] for q in unlinked)}")

print("\n" + "="*80)
print("Note: Common patterns:")
print("  - Q0 = Cover/instructions page (not a real question)")
print("  - Q230, Q188, Q199 = Page numbering errors or appendix pages")
print("  - Missing middle numbers (Q7) = Likely numbering error in original PDF")
print("="*80)
