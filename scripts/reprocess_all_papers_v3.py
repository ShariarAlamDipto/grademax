#!/usr/bin/env python3
"""
Complete Reprocessing Script V3 - With Improvements
Integrates fuzzy matching and better detection
"""

import sys
from pathlib import Path

# Add improved detector
sys.path.insert(0, str(Path(__file__).parent))
from improved_detector import (
    ImprovedQuestionDetector, 
    detect_questions_improved,
    validate_pdf_quality
)
from reprocess_all_papers import (
    PaperProcessor,
    clean_processed_directory,
    process_all_papers
)

# Replace the detector in PaperProcessor
import reprocess_all_papers as rpp

# Monkey patch to use improved detector
original_detect = rpp.PaperProcessor.detect_questions

def improved_detect_wrapper(self, pdf_path, is_markscheme=False):
    """Use improved detector"""
    return detect_questions_improved(pdf_path, is_markscheme)

rpp.PaperProcessor.detect_questions = improved_detect_wrapper

# Also add PDF validation
def process_with_validation():
    """Process all papers with PDF quality validation"""
    print("\n" + "="*80)
    print("VALIDATING PDF QUALITY BEFORE PROCESSING")
    print("="*80)
    
    raw_base = Path("data/raw")
    physics_dir = raw_base / "IGCSE" / "Physics"
    
    needs_ocr = []
    
    for year_dir in sorted(physics_dir.iterdir()):
        if not year_dir.is_dir():
            continue
        
        for season_dir in sorted(year_dir.iterdir()):
            if not season_dir.is_dir():
                continue
            
            for pdf_file in season_dir.glob("*.pdf"):
                if "_MS" not in pdf_file.stem:  # Only check question papers
                    quality = validate_pdf_quality(pdf_file)
                    
                    if quality['needs_ocr']:
                        needs_ocr.append({
                            'file': pdf_file,
                            'reason': 'corrupted' if quality['corrupted'] else 'image-based',
                            'avg_chars': quality['avg_chars']
                        })
    
    if needs_ocr:
        print(f"\n⚠️  Found {len(needs_ocr)} PDF(s) that need OCR:")
        for item in needs_ocr:
            print(f"   - {item['file'].relative_to(raw_base)} ({item['reason']})")
        print("\n   Recommendation: Run 'python scripts/ocr_corrupted_pdfs.py' first")
        print("   Or see TESSERACT_INSTALL_GUIDE.txt for installation\n")
        
        response = input("Continue processing anyway? (yes/no): ").strip().lower()
        if response != "yes":
            print("❌ Cancelled")
            return
    
    # Continue with processing
    processed_base = Path("data/processed")
    clean_processed_directory(processed_base)
    process_all_papers(raw_base, processed_base)

if __name__ == "__main__":
    print("="*80)
    print("🔄 COMPLETE PAPER REPROCESSING V3 (WITH IMPROVEMENTS)")
    print("="*80)
    print()
    print("Improvements:")
    print("  ✅ PDF quality validation")
    print("  ✅ Improved question detection")
    print("  ✅ Better markscheme format handling")
    print("  ✅ Fuzzy matching for question numbers")
    print()
    
    process_with_validation()
