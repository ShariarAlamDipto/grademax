#!/usr/bin/env python3
"""
Detailed analysis of papers with linking issues
"""

import fitz
import json
from pathlib import Path

def check_pdf_text_quality(pdf_path):
    """Check if PDF has readable text or is image-based"""
    doc = fitz.open(str(pdf_path))
    
    total_chars = 0
    readable_pages = 0
    page_count = len(doc)
    check_pages = min(5, page_count)
    
    for page_num in range(check_pages):
        text = doc[page_num].get_text()
        total_chars += len(text)
        
        # Check for readable text (not garbled)
        if len(text) > 50 and text.count('␦') < len(text) * 0.1:
            readable_pages += 1
    
    avg_chars = total_chars / check_pages if check_pages > 0 else 0
    
    doc.close()
    
    return {
        'avg_chars_per_page': avg_chars,
        'readable_pages': readable_pages,
        'is_readable': readable_pages >= 3 and avg_chars > 200
    }

def analyze_markscheme_format(pdf_path):
    """Analyze markscheme format"""
    doc = fitz.open(str(pdf_path))
    
    formats_found = []
    
    for page_num in range(min(5, len(doc))):
        text = doc[page_num].get_text()
        
        if 'Question\nnumber' in text or 'Question number' in text:
            formats_found.append('table_format')
        elif 'Question' in text and any(f'({i})' in text for i in range(1, 10)):
            formats_found.append('old_format')
    
    doc.close()
    
    return list(set(formats_found))

# Load all problem papers
processed_dir = Path('data/processed')

print("="*80)
print("DETAILED ANALYSIS OF PROBLEM PAPERS")
print("="*80)
print()

problem_papers = [
    '2013_Jun_1P',
    '2019_Jun_1P', 
    '2017_Specimen_1P',
    '2017_Specimen_2P'
]

for paper_name in problem_papers:
    paper_dir = processed_dir / paper_name
    manifest_file = paper_dir / "manifest.json"
    
    if not manifest_file.exists():
        print(f"⚠️  {paper_name}: No manifest found")
        continue
    
    with open(manifest_file, 'r') as f:
        data = json.load(f)
    
    print(f"\n📄 {paper_name}")
    print("-"*80)
    
    # Check QP
    qp_path = Path(data['qp_file'])
    if qp_path.exists():
        qp_quality = check_pdf_text_quality(qp_path)
        print(f"   QP Text Quality:")
        print(f"      Avg chars/page: {qp_quality['avg_chars_per_page']:.0f}")
        print(f"      Readable pages: {qp_quality['readable_pages']}/5")
        print(f"      Is readable: {'✅' if qp_quality['is_readable'] else '❌'}")
    else:
        print(f"   QP: File not found - {qp_path}")
    
    # Check MS
    if data['ms_file']:
        ms_path = Path(data['ms_file'])
        if ms_path.exists():
            ms_quality = check_pdf_text_quality(ms_path)
            ms_formats = analyze_markscheme_format(ms_path)
            print(f"   MS Text Quality:")
            print(f"      Avg chars/page: {ms_quality['avg_chars_per_page']:.0f}")
            print(f"      Readable pages: {ms_quality['readable_pages']}/5")
            print(f"      Is readable: {'✅' if ms_quality['is_readable'] else '❌'}")
            print(f"      Formats detected: {ms_formats if ms_formats else 'None'}")
        else:
            print(f"   MS: File not found - {ms_path}")
    
    print(f"   Questions detected: {data['total_questions']}")
    print(f"   Markschemes linked: {data['questions_with_markschemes']}")

print("\n" + "="*80)
print("RECOMMENDATIONS")
print("="*80)
print()
print("1. 2013 Jun P1 & 2019 Jun P1: PDFs have corrupted/image-based text")
print("   → These papers need OCR processing or manual re-upload with text layer")
print()
print("2. 2017 Specimen papers: Markscheme uses different format (old style)")
print("   → Need to add detection for old-style markscheme format")
print()
print("3. Other papers with 1-2 missing links: Likely question number mismatch")
print("   → Questions numbered differently in QP vs MS (e.g., Q0, Q230)")
