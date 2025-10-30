"""
Step 3: Upload Physics Papers to Database + Storage

This script:
1. Deletes existing Physics pages from database
2. Reads all locally saved papers from data/processed/Physics/
3. Uploads to database (papers + pages tables) using actual database schema:
   - Papers: subject_id, year, season, paper_number, total_pages
   - Pages: paper_id, page_number, question_number, qp_page_url, ms_page_url, etc.
4. Uploads PDFs to Supabase storage
5. Updates database with public URLs

Note: Database schema uses page_number/question_number, not page ranges.
Each page entry represents one question.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from collections import Counter

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment
env_path = Path('.env.local')
load_dotenv(env_path)

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Constants
BUCKET_NAME = "question-pdfs"
SUBJECT = "Physics"
SUBJECT_ID = "0b142517-d35d-4942-91aa-b4886aaabca3"
PROCESSED_DIR = Path("data/processed/Physics")


def delete_existing_physics_pages():
    """Delete existing Physics pages from database"""
    print("\n🗑️  Deleting existing Physics pages from database...")
    
    # Get all Physics paper IDs
    papers = supabase.table('papers').select('id').eq('subject_id', SUBJECT_ID).execute()
    
    if not papers.data:
        print("   No existing Physics papers found")
        return
    
    paper_ids = [p['id'] for p in papers.data]
    print(f"   Found {len(paper_ids)} existing Physics papers")
    
    # Delete pages (FK constraint)
    for paper_id in paper_ids:
        supabase.table('pages').delete().eq('paper_id', paper_id).execute()
    
    # Delete papers
    supabase.table('papers').delete().eq('subject_id', SUBJECT_ID).execute()
    
    print(f"   ✅ Deleted {len(paper_ids)} papers and their pages")


def upload_paper_to_database(manifest_path, folder_name):
    """
    Upload a single paper to database following actual database schema.
    Returns paper_id if successful.
    """
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    
    # Parse folder name: 2024_May-Jun_P1
    parts = folder_name.split('_')
    year = int(parts[0])
    season = parts[1]
    paper_number = parts[2]  # Keep as string (P1, P2, etc.)
    
    # Create paper entry (actual schema has: subject_id, year, season, paper_number, total_pages)
    paper_data = {
        'subject_id': SUBJECT_ID,
        'year': year,
        'season': season,
        'paper_number': paper_number,
        'total_pages': len(manifest.get('questions', []))
    }
    
    try:
        paper_response = supabase.table('papers').insert(paper_data).execute()
        
        if not paper_response.data:
            print(f"      ❌ Failed to create paper in database")
            return None
        
        paper_id = paper_response.data[0]['id']
        
        # Create page entries (actual schema: paper_id, page_number, question_number, is_question, topics, etc.)
        pages_data = []
        for q in manifest['questions']:
            qnum = int(q['question_number'])
            
            page_entry = {
                'paper_id': paper_id,
                'page_number': qnum,
                'question_number': str(qnum),
                'is_question': True,
                'topics': [],  # Will be filled by classification
                'text_excerpt': '',  # Will be filled when we have OCR
                'has_diagram': False,
                'page_count': len(q.get('qp_pages', []))
            }
            pages_data.append(page_entry)
        
        if pages_data:
            supabase.table('pages').insert(pages_data).execute()
        
        return paper_id
        
    except Exception as e:
        print(f"      ❌ Database error: {e}")
        return None


def upload_pdfs_to_storage(manifest_path, folder_name, paper_id):
    """
    Upload question PDFs to storage and update database with URLs.
    Follows FPM structure: subjects/Physics/pages/{folder}/q{n}.pdf
    Actual schema uses: qp_page_url and ms_page_url fields
    """
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    
    paper_dir = PROCESSED_DIR / folder_name
    pages_dir = paper_dir / "pages"
    ms_dir = paper_dir / "markschemes"
    
    uploaded_qp = 0
    uploaded_ms = 0
    
    for q in manifest['questions']:
        qnum = int(q['question_number'])
        
        # Upload QP PDF
        qp_file = pages_dir / f"q{qnum}.pdf"
        if qp_file.exists():
            storage_path = f"subjects/Physics/pages/{folder_name}/q{qnum}.pdf"
            
            try:
                with open(qp_file, 'rb') as f:
                    file_data = f.read()
                
                supabase.storage.from_(BUCKET_NAME).upload(
                    storage_path,
                    file_data,
                    file_options={"content-type": "application/pdf", "upsert": "true"}
                )
                
                # Get public URL
                qp_url = supabase.storage.from_(BUCKET_NAME).get_public_url(storage_path)
                
                # Update database (actual schema uses qp_page_url)
                supabase.table('pages').update({
                    'qp_page_url': qp_url
                }).eq('paper_id', paper_id).eq('question_number', str(qnum)).execute()
                
                uploaded_qp += 1
                
            except Exception as e:
                if 'already exists' not in str(e).lower():
                    print(f"      ⚠️  QP upload failed for Q{qnum}: {e}")
        
        # Upload MS PDF
        ms_file = ms_dir / f"q{qnum}.pdf"
        if ms_file.exists():
            storage_path = f"subjects/Physics/pages/{folder_name}/q{qnum}_ms.pdf"
            
            try:
                with open(ms_file, 'rb') as f:
                    file_data = f.read()
                
                supabase.storage.from_(BUCKET_NAME).upload(
                    storage_path,
                    file_data,
                    file_options={"content-type": "application/pdf", "upsert": "true"}
                )
                
                # Get public URL
                ms_url = supabase.storage.from_(BUCKET_NAME).get_public_url(storage_path)
                
                # Update database (actual schema uses ms_page_url)
                supabase.table('pages').update({
                    'ms_page_url': ms_url
                }).eq('paper_id', paper_id).eq('question_number', str(qnum)).execute()
                
                uploaded_ms += 1
                
            except Exception as e:
                if 'already exists' not in str(e).lower():
                    print(f"      ⚠️  MS upload failed for Q{qnum}: {e}")
    
    return uploaded_qp, uploaded_ms


def discover_processed_papers():
    """Find all processed papers in local directory"""
    papers = []
    
    for folder in sorted(PROCESSED_DIR.iterdir()):
        if not folder.is_dir():
            continue
        
        manifest_path = folder / "manifest.json"
        if manifest_path.exists():
            papers.append({
                'folder_name': folder.name,
                'manifest_path': manifest_path
            })
    
    return papers


def main():
    print("\n" + "="*80)
    print("🚀 STEP 3: DATABASE + STORAGE UPLOAD")
    print("="*80)
    print("   Source: data/processed/Physics/")
    print("   Target: Supabase database + storage")
    print("="*80)
    
    # Discover processed papers
    print("\n📂 Discovering processed papers...")
    papers = discover_processed_papers()
    
    if not papers:
        print("❌ No processed papers found!")
        print(f"   Expected location: {PROCESSED_DIR.absolute()}")
        return
    
    print(f"✅ Found {len(papers)} processed papers")
    
    # Confirm deletion and upload
    print(f"\n⚠️  This will:")
    print(f"   1. Delete all existing Physics data from database")
    print(f"   2. Upload {len(papers)} papers to database")
    print(f"   3. Upload PDFs to storage")
    print(f"   Expected time: ~30-45 minutes (storage uploads are slow)")
    
    response = input("\n❓ Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return
    
    # Step 1: Delete existing Physics data
    delete_existing_physics_pages()
    
    # Step 2 & 3: Upload to database and storage
    print("\n" + "="*80)
    print("DATABASE + STORAGE UPLOAD")
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
        folder_name = paper_info['folder_name']
        manifest_path = paper_info['manifest_path']
        
        print(f"\n[{i}/{len(papers)}] {folder_name}")
        
        try:
            # Load manifest to get stats
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            total_qs = manifest['total_questions']
            qs_with_ms = manifest['questions_with_markschemes']
            
            # Upload to database
            print(f"   💾 Uploading to database...")
            paper_id = upload_paper_to_database(manifest_path, folder_name)
            
            if not paper_id:
                print(f"   ❌ Database upload failed")
                stats['failed'] += 1
                stats['failed_papers'].append(folder_name)
                continue
            
            print(f"   ✅ Paper created: {paper_id}")
            
            # Upload PDFs to storage
            print(f"   📤 Uploading PDFs to storage...")
            uploaded_qp, uploaded_ms = upload_pdfs_to_storage(manifest_path, folder_name, paper_id)
            
            print(f"   ✅ Uploaded {uploaded_qp} QP, {uploaded_ms} MS PDFs")
            
            # Update stats
            stats['successful'] += 1
            stats['total_questions'] += total_qs
            stats['questions_with_ms'] += qs_with_ms
            stats['uploaded_qp'] += uploaded_qp
            stats['uploaded_ms'] += uploaded_ms
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            stats['failed'] += 1
            stats['failed_papers'].append(folder_name)
    
    # Final summary
    print("\n" + "="*80)
    print("📊 UPLOAD SUMMARY")
    print("="*80)
    
    print(f"\n✅ Successfully uploaded: {stats['successful']}/{stats['total']} papers")
    if stats['failed'] > 0:
        print(f"❌ Failed: {stats['failed']}/{stats['total']} papers")
        if stats['failed_papers']:
            print(f"   Failed papers: {', '.join(stats['failed_papers'][:5])}")
            if len(stats['failed_papers']) > 5:
                print(f"   ... and {len(stats['failed_papers']) - 5} more")
    
    if stats['successful'] > 0:
        print(f"\n📈 Database Statistics:")
        print(f"   Total questions: {stats['total_questions']}")
        print(f"   Questions with MS: {stats['questions_with_ms']}")
        ms_rate = (stats['questions_with_ms'] / stats['total_questions'] * 100) if stats['total_questions'] > 0 else 0
        print(f"   MS coverage: {ms_rate:.1f}%")
        
        print(f"\n📤 Storage Statistics:")
        print(f"   Question papers uploaded: {stats['uploaded_qp']}")
        print(f"   Mark schemes uploaded: {stats['uploaded_ms']}")
        print(f"   Total PDFs uploaded: {stats['uploaded_qp'] + stats['uploaded_ms']}")
    
    print("\n" + "="*80)
    print("✨ UPLOAD COMPLETE!")
    print("="*80)
    print("\n💡 Next steps:")
    print("   1. Run monitor script to verify: python scripts/monitor_physics_processing.py")
    print("   2. Classify questions using Groq API (~56 minutes)")
    print("   3. Test worksheet generation")
    print("\n🎯 Your Physics data is now live in the database!")


if __name__ == "__main__":
    main()
