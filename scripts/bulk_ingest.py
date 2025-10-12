#!/usr/bin/env python3
"""
Bulk Ingestion Script
Process entire directories of QPs and MSs
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from complete_pipeline import CompletePipeline

# Load environment variables from .env.ingest
load_dotenv('.env.ingest')


def find_paper_pairs(input_dir: str):
    """
    Find all QP and MS pairs in directory structure
    
    Expected structure:
    data/raw/IGCSE/4PH1/
        ├── 2019/
        │   └── Jun/
        │       ├── 4PH1_Jun19_QP_1P.pdf
        │       └── 4PH1_Jun19_MS_1P.pdf
        ├── 2020/
        │   └── Oct/
        │       ├── 4PH1_Oct20_QP_1P.pdf
        │       └── 4PH1_Oct20_MS_1P.pdf
    """
    input_path = Path(input_dir)
    pairs = []
    
    # Search for all PDF files
    for pdf_file in input_path.rglob("*.pdf"):
        filename = pdf_file.name.upper()
        
        # Check if this is a QP file
        if "_QP_" in filename or "QP" in filename.split('_'):
            # Try to find matching MS
            ms_candidates = [
                pdf_file.parent / pdf_file.name.replace('_QP_', '_MS_'),
                pdf_file.parent / pdf_file.name.replace('QP', 'MS'),
                pdf_file.parent / (pdf_file.stem + '_MS.pdf'),
            ]
            
            ms_file = None
            for candidate in ms_candidates:
                if candidate.exists():
                    ms_file = candidate
                    break
            
            if ms_file:
                pairs.append((str(pdf_file), str(ms_file)))
                print(f"✅ Found pair: {pdf_file.name} + {ms_file.name}")
            else:
                print(f"⚠️  No MS found for {pdf_file.name}")
    
    return pairs


def bulk_process(input_dir: str, max_papers: int = None):
    """
    Process all papers in directory
    
    Args:
        input_dir: Directory containing papers
        max_papers: Maximum number of papers to process (None = all)
    """
    print(f"\n{'='*70}")
    print(f"🚀 BULK INGESTION")
    print(f"{'='*70}")
    print(f"Directory: {input_dir}")
    
    # Find all paper pairs
    print(f"\n📁 Scanning for papers...")
    pairs = find_paper_pairs(input_dir)
    
    if not pairs:
        print("❌ No paper pairs found!")
        return
    
    print(f"\n✅ Found {len(pairs)} paper pairs")
    
    if max_papers:
        pairs = pairs[:max_papers]
        print(f"   (Processing first {max_papers} papers)")
    
    # Process each pair
    pipeline = CompletePipeline()
    
    total_questions = 0
    successful_papers = 0
    failed_papers = []
    
    for i, (qp_path, ms_path) in enumerate(pairs, 1):
        print(f"\n{'='*70}")
        print(f"📄 Paper {i}/{len(pairs)}")
        print(f"{'='*70}")
        
        try:
            processed = pipeline.process_paper_pair(qp_path, ms_path)
            total_questions += len(processed)
            successful_papers += 1
        except Exception as e:
            print(f"❌ ERROR processing {Path(qp_path).name}: {e}")
            failed_papers.append((qp_path, str(e)))
            continue
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 BULK PROCESSING COMPLETE")
    print(f"{'='*70}")
    print(f"✅ Successful papers: {successful_papers}/{len(pairs)}")
    print(f"📝 Total questions: {total_questions}")
    
    if failed_papers:
        print(f"\n❌ Failed papers: {len(failed_papers)}")
        for qp_path, error in failed_papers:
            print(f"   - {Path(qp_path).name}: {error}")
    
    print(f"\n{'='*70}\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python bulk_ingest.py <input_directory> [max_papers]")
        print("\nExample:")
        print("  python bulk_ingest.py data/raw/IGCSE/4PH1/")
        print("  python bulk_ingest.py data/raw/IGCSE/4PH1/ 5  # Process first 5 papers")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    max_papers = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    bulk_process(input_dir, max_papers)


if __name__ == "__main__":
    main()
