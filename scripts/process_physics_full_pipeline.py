"""
Complete Physics Processing Pipeline
=====================================

Step 1: Segment papers using hardened algorithm (91.4% MS linking)
Step 2: Save locally to data/processed/Physics/{YYYY}_{Season}_P{N}/
        - manifest.json
        - pages/q{n}.pdf (question papers)
        - markschemes/q{n}.pdf (mark schemes)
Step 3: Upload to database (papers + pages tables)
Step 4: Upload PDFs to storage

Based on FPM structure and validated hardened segmentation.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import PyPDF2
from collections import Counter
import io

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import the hardened processor
from scripts.process_physics_hardened import process_paper

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment
env_path = project_root / '.env.local'
load_dotenv(env_path)

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Constants
BUCKET_NAME = "question-pdfs"
SUBJECT = "Physics"
SUBJECT_ID = "0b142517-d35d-4942-91aa-b4886aaabca3"
RAW_DATA_DIR = Path("data/raw/IGCSE/Physics")
PROCESSED_DIR = Path("data/processed/Physics")

# Create processed directory
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def extract_pdf_pages(pdf_path, page_indices):
    """
    Extract specific pages from a PDF and return as bytes.
    page_indices: list of 0-based page numbers
    """
    if not page_indices:
        return None
    
    try:
        reader = PyPDF2.PdfReader(pdf_path)
        writer = PyPDF2.PdfWriter()
        
        for page_idx in page_indices:
            if 0 <= page_idx < len(reader.pages):
                writer.add_page(reader.pages[page_idx])
        
        # Write to bytes
        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        print(f"      ❌ PDF extraction error: {e}")
        return None


def save_locally(year, season, paper_number, questions, qp_path, ms_path):
    """
    Save segmented paper locally following FPM structure:
    - data/processed/Physics/{YYYY}_{Season}_P{N}/
      - manifest.json
      - pages/q{n}.pdf
      - markschemes/q{n}.pdf
    """
    # Folder name: 2024_May-Jun_P1
    folder_name = f"{year}_{season}_P{paper_number}"
    paper_dir = PROCESSED_DIR / folder_name
    pages_dir = paper_dir / "pages"
    ms_dir = paper_dir / "markschemes"
    
    # Create directories
    paper_dir.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(exist_ok=True)
    ms_dir.mkdir(exist_ok=True)
    
    print(f"      📁 Creating local folder: {folder_name}")
    
    # Build manifest
    manifest = {
        "qp_file": str(qp_path),
        "ms_file": str(ms_path),
        "total_questions": len(questions),
        "questions_with_markschemes": sum(1 for q in questions if q.get('ms_pages')),
        "questions": []
    }
    
    # Process each question
    for q in questions:
        qnum = q['qnum']
        qp_pages = q.get('qp_pages', [])
        ms_pages = q.get('ms_pages', [])
        
        question_data = {
            "question_number": str(qnum),
            "qp_pages": [p + 1 for p in qp_pages],  # Convert to 1-based
            "qp_page_count": len(qp_pages),
            "qp_pdf_path": f"Physics\\{folder_name}\\pages\\q{qnum}.pdf",
            "has_markscheme": bool(ms_pages)
        }
        
        # Extract and save QP PDF
        if qp_pages:
            qp_pdf_bytes = extract_pdf_pages(qp_path, qp_pages)
            if qp_pdf_bytes:
                qp_file_path = pages_dir / f"q{qnum}.pdf"
                with open(qp_file_path, 'wb') as f:
                    f.write(qp_pdf_bytes)
        
        # Extract and save MS PDF
        if ms_pages:
            question_data["ms_pages"] = [p + 1 for p in ms_pages]  # Convert to 1-based
            question_data["ms_pdf_path"] = f"Physics\\{folder_name}\\markschemes\\q{qnum}.pdf"
            
            ms_pdf_bytes = extract_pdf_pages(ms_path, ms_pages)
            if ms_pdf_bytes:
                ms_file_path = ms_dir / f"q{qnum}.pdf"
                with open(ms_file_path, 'wb') as f:
                    f.write(ms_pdf_bytes)
        
        manifest["questions"].append(question_data)
    
    # Save manifest
    manifest_path = paper_dir / "manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"      ✅ Saved {len(questions)} questions locally")
    return paper_dir


def discover_papers():
    """Scan raw data directory for all available papers"""
    papers = []
    
    for year_dir in sorted(RAW_DATA_DIR.iterdir()):
        if not year_dir.is_dir():
            continue
        
        year = year_dir.name
        if not year.isdigit():
            continue
        
        for season_dir in sorted(year_dir.iterdir()):
            if not season_dir.is_dir():
                continue
            
            season = season_dir.name
            
            # Look for Paper X.pdf and Paper X_MS.pdf
            for paper_file in sorted(season_dir.glob("Paper *.pdf")):
                if "_MS" in paper_file.name:
                    continue  # Skip mark schemes
                
                # Extract paper number
                paper_num = int(paper_file.stem.split()[-1])
                
                # Check if MS exists
                ms_file = season_dir / f"Paper {paper_num}_MS.pdf"
                
                if ms_file.exists():
                    papers.append({
                        'year': int(year),
                        'season': season,
                        'paper_number': paper_num,
                        'qp_path': paper_file,
                        'ms_path': ms_file
                    })
    
    return papers


def main():
    print("\n" + "="*80)
    print("🚀 COMPLETE PHYSICS PROCESSING PIPELINE")
    print("="*80)
    print("   Step 1: Segment papers (hardened algorithm - 91.4% MS linking)")
    print("   Step 2: Save locally to data/processed/Physics/")
    print("   Step 3: Upload to database")
    print("   Step 4: Upload PDFs to storage")
    print("="*80)
    
    # Discover all papers
    print("\n📂 Discovering papers...")
    papers = discover_papers()
    
    if not papers:
        print("❌ No papers found!")
        return
    
    print(f"✅ Found {len(papers)} papers to process")
    
    # Show breakdown by year
    year_counts = Counter(p['year'] for p in papers)
    print("\n📊 Breakdown by year:")
    for year in sorted(year_counts.keys()):
        print(f"   {year}: {year_counts[year]} papers")
    
    # Confirm processing
    print(f"\n⚠️  This will:")
    print(f"   1. Segment {len(papers)} papers")
    print(f"   2. Save ~{len(papers) * 10} questions locally")
    print(f"   3. Create ~{len(papers) * 10 * 2} PDF files")
    print(f"   Expected time: ~15-20 minutes")
    print(f"\n💾 Output directory: {PROCESSED_DIR.absolute()}")
    
    response = input("\n❓ Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return
    
    # STEP 1 & 2: Segment and Save Locally
    print("\n" + "="*80)
    print("STEP 1 & 2: SEGMENTATION + LOCAL SAVE")
    print("="*80)
    
    stats = {
        'total': len(papers),
        'successful': 0,
        'failed': 0,
        'total_questions': 0,
        'questions_with_ms': 0,
        'failed_papers': []
    }
    
    processed_papers = []
    
    for i, paper_info in enumerate(papers, 1):
        year = paper_info['year']
        season = paper_info['season']
        paper_num = paper_info['paper_number']
        qp_path = paper_info['qp_path']
        ms_path = paper_info['ms_path']
        
        print(f"\n[{i}/{len(papers)}] {year} {season} Paper {paper_num}")
        
        try:
            # Segment paper
            print(f"   ✂️  Segmenting...")
            result = process_paper(year, season, paper_num)
            
            if not result:
                print(f"   ❌ Segmentation failed")
                stats['failed'] += 1
                stats['failed_papers'].append(f"{year} {season} P{paper_num}")
                continue
            
            questions = result['questions']
            qs_with_ms = sum(1 for q in questions if q.get('ms_pages'))
            print(f"   ✅ {len(questions)} questions, {qs_with_ms} with MS ({qs_with_ms/len(questions)*100:.1f}%)")
            
            # Save locally
            print(f"   💾 Saving locally...")
            paper_dir = save_locally(year, season, paper_num, questions, qp_path, ms_path)
            
            # Track for database upload
            processed_papers.append({
                'year': year,
                'season': season,
                'paper_number': paper_num,
                'paper_dir': paper_dir,
                'questions': questions
            })
            
            # Update stats
            stats['successful'] += 1
            stats['total_questions'] += len(questions)
            stats['questions_with_ms'] += qs_with_ms
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            stats['failed'] += 1
            stats['failed_papers'].append(f"{year} {season} P{paper_num}")
    
    # Summary
    print("\n" + "="*80)
    print("📊 SEGMENTATION + LOCAL SAVE SUMMARY")
    print("="*80)
    
    print(f"\n✅ Successfully processed: {stats['successful']}/{stats['total']} papers")
    if stats['failed'] > 0:
        print(f"❌ Failed: {stats['failed']}/{stats['total']} papers")
        if stats['failed_papers']:
            print(f"   Failed papers: {', '.join(stats['failed_papers'][:5])}")
            if len(stats['failed_papers']) > 5:
                print(f"   ... and {len(stats['failed_papers']) - 5} more")
    
    if stats['successful'] > 0:
        print(f"\n📈 Statistics:")
        print(f"   Total questions: {stats['total_questions']}")
        print(f"   Questions with MS: {stats['questions_with_ms']}")
        ms_rate = (stats['questions_with_ms'] / stats['total_questions'] * 100) if stats['total_questions'] > 0 else 0
        print(f"   MS linking rate: {ms_rate:.1f}%")
        print(f"   Avg questions/paper: {stats['total_questions']/stats['successful']:.1f}")
    
    print(f"\n💾 All files saved to: {PROCESSED_DIR.absolute()}")
    
    # Ask if user wants to proceed with database upload
    if stats['successful'] == 0:
        print("\n❌ No papers to upload to database")
        return
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print(f"\n✅ Step 1 & 2 Complete: {stats['successful']} papers saved locally")
    print(f"\n💡 Next:")
    print(f"   1. Review the files in: {PROCESSED_DIR.absolute()}")
    print(f"   2. Run database upload script to upload to Supabase")
    print(f"   3. Run storage upload script to upload PDFs")
    
    print("\n🎯 Segmentation complete! Ready for database upload.")


if __name__ == "__main__":
    main()
