#!/usr/bin/env python3
"""
Clean Markscheme Files from Processed Directory
Deletes all markscheme PDF files but preserves directory structure
"""

import os
from pathlib import Path
import shutil

def clean_markschemes(processed_dir: str = "data/processed"):
    """
    Delete all markscheme PDF files from processed directory
    Preserve the markschemes/ directory structure
    """
    processed_path = Path(processed_dir)
    
    if not processed_path.exists():
        print(f"❌ Directory not found: {processed_dir}")
        return
    
    print("="*70)
    print("🧹 CLEANING MARKSCHEME FILES")
    print("="*70)
    print()
    
    total_deleted = 0
    total_dirs_cleaned = 0
    
    # Walk through all paper directories
    for paper_dir in processed_path.iterdir():
        if not paper_dir.is_dir():
            continue
        
        markscheme_dir = paper_dir / "markschemes"
        
        if markscheme_dir.exists():
            print(f"📁 {paper_dir.name}")
            
            # Count files before deletion
            pdf_files = list(markscheme_dir.glob("*.pdf"))
            
            if pdf_files:
                # Delete all PDF files
                for pdf_file in pdf_files:
                    pdf_file.unlink()
                    total_deleted += 1
                
                print(f"   ✅ Deleted {len(pdf_files)} markscheme PDF files")
                total_dirs_cleaned += 1
            else:
                print(f"   ⏭️  No markscheme PDFs found")
    
    print()
    print("="*70)
    print(f"✅ CLEANUP COMPLETE")
    print(f"   Directories cleaned: {total_dirs_cleaned}")
    print(f"   Files deleted: {total_deleted}")
    print("="*70)


if __name__ == "__main__":
    # Confirm before deletion
    print("\n⚠️  WARNING: This will DELETE all markscheme PDF files from data/processed/")
    print("   Directory structure will be preserved")
    print()
    response = input("Continue? (yes/no): ").strip().lower()
    
    if response == "yes":
        clean_markschemes()
    else:
        print("❌ Cancelled")
