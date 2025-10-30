"""
Complete Physics Processing Pipeline - Segmentation + Database + Storage Upload

This script performs the full pipeline:
1. Segment papers using hardened algorithm (91.4% MS linking achieved)
2. Save papers and pages to database
3. Split and upload question PDFs to storage
4. Update database with public URLs

Based on validated processing of 53/56 papers with 525 questions detected.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import PyPDF2
from collections import defaultdict
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


def save_paper_to_database(year, season, paper_number, questions, total_qp_pages):
    """
    Save paper and its pages to database.
    Returns paper_id if successful, None otherwise.
    """
    try:
        # Create paper entry
        paper_data = {
            'subject_id': SUBJECT_ID,
            'year': year,
            'season': season,
            'paper_number': paper_number,
            'total_pages': total_qp_pages,
            'total_questions': len(questions)
        }
        
        paper_response = supabase.table('papers').insert(paper_data).execute()
        
        if not paper_response.data:
            print(f"      ❌ Failed to create paper in database")
            return None
        
        paper_id = paper_response.data[0]['id']
        print(f"      ✅ Paper created in database: {paper_id}")
        
        # Create page entries for each question
        pages_data = []
        for q in questions:
            qnum = q['qnum']
            qp_pages = q.get('qp_pages', [])
            ms_pages = q.get('ms_pages', [])
            
            page_entry = {
                'paper_id': paper_id,
                'question_number': qnum,
                'qp_start_page': qp_pages[0] + 1 if qp_pages else None,
                'qp_end_page': qp_pages[-1] + 1 if qp_pages else None,
                'ms_start_page': ms_pages[0] + 1 if ms_pages else None,
                'ms_end_page': ms_pages[-1] + 1 if ms_pages else None,
                'has_markscheme': bool(ms_pages)
            }
            pages_data.append(page_entry)
        
        if pages_data:
            pages_response = supabase.table('pages').insert(pages_data).execute()
            
            if pages_response.data:
                print(f"      ✅ Created {len(pages_response.data)} page entries")
            else:
                print(f"      ⚠️  Failed to create page entries")
        
        return paper_id
        
    except Exception as e:
        print(f"      ❌ Database error: {e}")
        return None


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


def upload_question_pdfs(paper_id, year, season, paper_number, questions, qp_path, ms_path):
    """
    Split QP and MS by question and upload to storage.
    Updates database with public URLs.
    Returns (uploaded_qp, uploaded_ms) counts.
    """
    uploaded_qp = 0
    uploaded_ms = 0
    
    # Folder name: Phy_2024_May-Jun_P1
    folder_name = f"Phy_{year}_{season}_P{paper_number}"
    
    for q in questions:
        qnum = q['qnum']
        qp_pages = q.get('qp_pages', [])
        ms_pages = q.get('ms_pages', [])
        
        # Upload QP
        if qp_pages:
            qp_pdf_bytes = extract_pdf_pages(qp_path, qp_pages)
            
            if qp_pdf_bytes:
                qp_storage_path = f"subjects/Physics/pages/{folder_name}/Q{qnum}_qp.pdf"
                
                try:
                    supabase.storage.from_(BUCKET_NAME).upload(
                        qp_storage_path,
                        qp_pdf_bytes,
                        file_options={"content-type": "application/pdf", "upsert": "true"}
                    )
                    
                    # Get public URL
                    qp_url = supabase.storage.from_(BUCKET_NAME).get_public_url(qp_storage_path)
                    
                    # Update database
                    supabase.table('pages').update({
                        'qp_pdf_url': qp_url
                    }).eq('paper_id', paper_id).eq('question_number', qnum).execute()
                    
                    uploaded_qp += 1
                    
                except Exception as e:
                    print(f"      ⚠️  QP upload failed for Q{qnum}: {e}")
        
        # Upload MS
        if ms_pages:
            ms_pdf_bytes = extract_pdf_pages(ms_path, ms_pages)
            
            if ms_pdf_bytes:
                ms_storage_path = f"subjects/Physics/pages/{folder_name}/Q{qnum}_ms.pdf"
                
                try:
                    supabase.storage.from_(BUCKET_NAME).upload(
                        ms_storage_path,
                        ms_pdf_bytes,
                        file_options={"content-type": "application/pdf", "upsert": "true"}
                    )
                    
                    # Get public URL
                    ms_url = supabase.storage.from_(BUCKET_NAME).get_public_url(ms_storage_path)
                    
                    # Update database
                    supabase.table('pages').update({
                        'ms_pdf_url': ms_url
                    }).eq('paper_id', paper_id).eq('question_number', qnum).execute()
                    
                    uploaded_ms += 1
                    
                except Exception as e:
                    print(f"      ⚠️  MS upload failed for Q{qnum}: {e}")
    
    return uploaded_qp, uploaded_ms


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
    print("   Segmentation → Database → Storage Upload")
    print("   Based on hardened algorithm achieving 91.4% MS linking")
    print("="*80)
    
    # Discover all papers
    print("\n📂 Discovering papers...")
    papers = discover_papers()
    
    if not papers:
        print("❌ No papers found!")
        return
    
    print(f"✅ Found {len(papers)} papers to process")
    
    # Show breakdown by year
    from collections import Counter
    year_counts = Counter(p['year'] for p in papers)
    print("\n📊 Breakdown by year:")
    for year in sorted(year_counts.keys()):
        print(f"   {year}: {year_counts[year]} papers")
    
    # Confirm processing
    print(f"\n⚠️  This will:")
    print(f"   1. Segment {len(papers)} papers (hardened algorithm)")
    print(f"   2. Save ~{len(papers) * 10} questions to database")
    print(f"   3. Upload ~{len(papers) * 10 * 2} PDFs to storage")
    print(f"   Expected time: ~30-45 minutes (PDF uploads are slow)")
    
    response = input("\n❓ Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return
    
    # Process all papers
    print("\n" + "="*80)
    print("PROCESSING PAPERS")
    print("="*80)
    
    stats = {
        'total': len(papers),
        'successful': 0,
        'failed': 0,
        'total_questions': 0,
        'questions_with_ms': 0,
        'uploaded_qp': 0,
        'uploaded_ms': 0,
        'failed_papers': []
    }
    
    for i, paper_info in enumerate(papers, 1):
        year = paper_info['year']
        season = paper_info['season']
        paper_num = paper_info['paper_number']
        qp_path = paper_info['qp_path']
        ms_path = paper_info['ms_path']
        
        print(f"\n[{i}/{len(papers)}] {year} {season} Paper {paper_num}")
        
        try:
            # Step 1: Segment paper
            print(f"   ✂️  Segmenting...")
            result = process_paper(year, season, paper_num)
            
            if not result:
                print(f"   ❌ Segmentation failed")
                stats['failed'] += 1
                stats['failed_papers'].append(f"{year} {season} P{paper_num}")
                continue
            
            questions = result['questions']
            n_qp = result['n_qp']
            
            # Count pages in QP
            try:
                with open(qp_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    total_qp_pages = len(reader.pages)
            except:
                total_qp_pages = max(q['end_page'] for q in questions) + 1 if questions else 0
            
            qs_with_ms = sum(1 for q in questions if q.get('ms_pages'))
            print(f"   ✅ {len(questions)} questions, {qs_with_ms} with MS ({qs_with_ms/len(questions)*100:.1f}%)")
            
            # Step 2: Save to database
            print(f"   💾 Saving to database...")
            paper_id = save_paper_to_database(year, season, paper_num, questions, total_qp_pages)
            
            if not paper_id:
                print(f"   ❌ Database save failed")
                stats['failed'] += 1
                stats['failed_papers'].append(f"{year} {season} P{paper_num}")
                continue
            
            # Step 3: Upload PDFs to storage
            print(f"   📤 Uploading PDFs to storage...")
            uploaded_qp, uploaded_ms = upload_question_pdfs(
                paper_id, year, season, paper_num, questions, qp_path, ms_path
            )
            
            print(f"   ✅ Uploaded {uploaded_qp} QP, {uploaded_ms} MS PDFs")
            
            # Update stats
            stats['successful'] += 1
            stats['total_questions'] += len(questions)
            stats['questions_with_ms'] += qs_with_ms
            stats['uploaded_qp'] += uploaded_qp
            stats['uploaded_ms'] += uploaded_ms
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            stats['failed'] += 1
            stats['failed_papers'].append(f"{year} {season} P{paper_num}")
    
    # Final summary
    print("\n" + "="*80)
    print("📊 FINAL SUMMARY")
    print("="*80)
    
    print(f"\n✅ Successfully processed: {stats['successful']}/{stats['total']} papers")
    if stats['failed'] > 0:
        print(f"❌ Failed: {stats['failed']}/{stats['total']} papers")
        if stats['failed_papers']:
            print(f"   Failed papers: {', '.join(stats['failed_papers'][:5])}")
            if len(stats['failed_papers']) > 5:
                print(f"   ... and {len(stats['failed_papers']) - 5} more")
    
    if stats['successful'] > 0:
        print(f"\n📈 Database Statistics:")
        print(f"   Total questions saved: {stats['total_questions']}")
        print(f"   Questions with MS: {stats['questions_with_ms']}")
        ms_rate = (stats['questions_with_ms'] / stats['total_questions'] * 100) if stats['total_questions'] > 0 else 0
        print(f"   MS linking rate: {ms_rate:.1f}%")
        print(f"   Avg questions/paper: {stats['total_questions']/stats['successful']:.1f}")
        
        print(f"\n📤 Storage Statistics:")
        print(f"   Question papers uploaded: {stats['uploaded_qp']}")
        print(f"   Mark schemes uploaded: {stats['uploaded_ms']}")
        print(f"   Total PDFs uploaded: {stats['uploaded_qp'] + stats['uploaded_ms']}")
    
    print("\n" + "="*80)
    print("✨ PIPELINE COMPLETE!")
    print("="*80)
    print("\n💡 Next steps:")
    print("   1. Run monitor script to verify: python scripts/monitor_physics_processing.py")
    print("   2. Classify questions: ~56 minutes with Groq API")
    print("   3. Test worksheet generation")
    print("\n🎯 Your Physics data is now ready for classification!")


if __name__ == "__main__":
    main()
