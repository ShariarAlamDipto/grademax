"""
PDF Merger for GradeMax Phase 2
Merges question page PDFs into a single worksheet PDF
"""

import sys
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict
import json


def merge_question_pdfs(
    question_pdfs: List[str],
    output_path: str,
    include_markschemes: bool = False,
    markscheme_pdfs: List[str] = None
) -> Dict:
    """
    Merge multiple question PDFs into a single worksheet
    
    Args:
        question_pdfs: List of paths to question PDF files
        output_path: Path to save the merged PDF
        include_markschemes: Whether to append mark schemes
        markscheme_pdfs: List of paths to mark scheme PDFs
        
    Returns:
        Dict with metadata about the merge
    """
    # Create output document
    merged = fitz.open()
    
    questions_merged = 0
    markschemes_merged = 0
    total_pages = 0
    
    # Merge question PDFs
    for pdf_path in question_pdfs:
        try:
            if not Path(pdf_path).exists():
                print(f"⚠️  Warning: PDF not found: {pdf_path}")
                continue
            
            doc = fitz.open(pdf_path)
            merged.insert_pdf(doc)
            questions_merged += 1
            total_pages += len(doc)
            doc.close()
            
        except Exception as e:
            print(f"❌ Error merging {pdf_path}: {e}")
    
    # Add page break before mark schemes
    if include_markschemes and markscheme_pdfs:
        # Insert a blank page as separator
        page = merged.new_page()
        
        # Add "MARK SCHEME" text
        page.insert_text(
            (72, 72),  # Top left margin
            "MARK SCHEME",
            fontsize=24,
            fontname="helv-bold"
        )
        
        # Merge markscheme PDFs
        for pdf_path in markscheme_pdfs:
            try:
                if not pdf_path or not Path(pdf_path).exists():
                    continue
                
                doc = fitz.open(pdf_path)
                merged.insert_pdf(doc)
                markschemes_merged += 1
                total_pages += len(doc)
                doc.close()
                
            except Exception as e:
                print(f"❌ Error merging markscheme {pdf_path}: {e}")
    
    # Save merged PDF
    merged.save(output_path)
    merged.close()
    
    return {
        'output_path': output_path,
        'questions_merged': questions_merged,
        'markschemes_merged': markschemes_merged,
        'total_pages': total_pages,
        'success': True
    }


if __name__ == "__main__":
    # Test merge
    if len(sys.argv) < 3:
        print("Usage: python merge_pdfs.py <output.pdf> <input1.pdf> <input2.pdf> ... [--markschemes ms1.pdf ms2.pdf ...]")
        sys.exit(1)
    
    output_path = sys.argv[1]
    
    # Parse arguments - split at --markschemes
    if '--markschemes' in sys.argv:
        ms_index = sys.argv.index('--markschemes')
        input_pdfs = sys.argv[2:ms_index]
        markscheme_pdfs = sys.argv[ms_index+1:]
        include_ms = True
    else:
        input_pdfs = sys.argv[2:]
        markscheme_pdfs = None
        include_ms = False
    
    print(f"📄 Merging {len(input_pdfs)} question PDFs...")
    if include_ms:
        print(f"📝 Including {len(markscheme_pdfs)} mark scheme PDFs...")
    
    result = merge_question_pdfs(
        input_pdfs, 
        output_path,
        include_markschemes=include_ms,
        markscheme_pdfs=markscheme_pdfs
    )
    
    print(f"✅ Merged PDF saved: {result['output_path']}")
    print(f"   Questions: {result['questions_merged']}")
    print(f"   Total pages: {result['total_pages']}")
    if result.get('markschemes_merged'):
        print(f"   Mark schemes: {result['markschemes_merged']}")
