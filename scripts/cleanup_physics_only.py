"""
Cleanup script for Physics data ONLY
Safely deletes Physics papers, pages, and storage files without touching FPM
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from supabase import create_client
import json

# UTF-8 encoding for Windows
sys.stdout.reconfigure(encoding='utf-8')

# Load environment
env_path = project_root / '.env.local'
load_dotenv(env_path)

# Initialize Supabase
supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Physics subject ID (from database)
PHYSICS_SUBJECT_ID = '0b142517-d35d-4942-91aa-b4886aaabca3'
FPM_SUBJECT_ID = '8dea5d70-f026-4e03-bb45-053f154c6898'  # For verification

def verify_subject_ids():
    """Verify we have the correct subject IDs"""
    print("🔍 Verifying subject IDs...")
    
    subjects = supabase.table('subjects').select('id, name').execute()
    
    for subj in subjects.data:
        print(f"   {subj['name']}: {subj['id']}")
    
    physics = next((s for s in subjects.data if s['name'] == 'Physics'), None)
    fpm = next((s for s in subjects.data if 'Pure' in s['name'] and 'Math' in s['name']), None)
    
    if not physics or physics['id'] != PHYSICS_SUBJECT_ID:
        print(f"❌ ERROR: Physics subject ID mismatch!")
        return False
    
    if not fpm or fpm['id'] != FPM_SUBJECT_ID:
        print(f"❌ ERROR: FPM subject ID mismatch!")
        return False
    
    print(f"✅ Subject IDs verified correctly")
    return True

def get_physics_stats():
    """Get current Physics data statistics"""
    print("\n📊 Current Physics data:")
    
    # Count papers
    papers = supabase.table('papers')\
        .select('id, year, season, paper_number')\
        .eq('subject_id', PHYSICS_SUBJECT_ID)\
        .execute()
    
    print(f"   Papers: {len(papers.data)}")
    
    if papers.data:
        # Count pages
        paper_ids = [p['id'] for p in papers.data]
        pages = supabase.table('pages')\
            .select('id, question_number')\
            .in_('paper_id', paper_ids)\
            .execute()
        
        print(f"   Pages: {len(pages.data)}")
        
        # Count unique questions
        questions = set(p['question_number'] for p in pages.data if p['question_number'])
        print(f"   Unique questions: {len(questions)}")
        
        # Sample papers
        print(f"\n   Sample papers:")
        for paper in papers.data[:5]:
            print(f"      {paper['year']} {paper['season']} P{paper['paper_number']}")
        if len(papers.data) > 5:
            print(f"      ... and {len(papers.data) - 5} more")
    
    return papers.data

def get_fpm_stats():
    """Get FPM statistics to ensure we don't touch them"""
    print("\n📊 FPM data (should remain unchanged):")
    
    papers = supabase.table('papers')\
        .select('id')\
        .eq('subject_id', FPM_SUBJECT_ID)\
        .execute()
    
    print(f"   Papers: {len(papers.data)}")
    
    if papers.data:
        paper_ids = [p['id'] for p in papers.data]
        pages = supabase.table('pages')\
            .select('id')\
            .in_('paper_id', paper_ids)\
            .execute()
        
        print(f"   Pages: {len(pages.data)}")
    
    return len(papers.data), len(pages.data) if papers.data else 0

def delete_physics_pages(paper_ids):
    """Delete all pages for Physics papers"""
    print(f"\n🗑️  Deleting Physics pages...")
    
    result = supabase.table('pages')\
        .delete()\
        .in_('paper_id', paper_ids)\
        .execute()
    
    print(f"✅ Deleted {len(result.data)} pages")
    return len(result.data)

def delete_physics_papers():
    """Delete all Physics papers"""
    print(f"\n🗑️  Deleting Physics papers...")
    
    result = supabase.table('papers')\
        .delete()\
        .eq('subject_id', PHYSICS_SUBJECT_ID)\
        .execute()
    
    print(f"✅ Deleted {len(result.data)} papers")
    return len(result.data)

def cleanup_storage():
    """Delete Physics files from storage"""
    print(f"\n🗑️  Cleaning up Physics storage...")
    
    try:
        # List all files in Physics folder
        files = supabase.storage.from_('question-pdfs')\
            .list('subjects/Physics/pages')
        
        if not files:
            print("   No Physics storage files found")
            return 0
        
        print(f"   Found {len(files)} Physics folders")
        
        deleted = 0
        for item in files:
            if item['name'].startswith('Phy_'):
                path = f"subjects/Physics/pages/{item['name']}"
                try:
                    supabase.storage.from_('question-pdfs').remove([path])
                    deleted += 1
                    if deleted % 10 == 0:
                        print(f"   Deleted {deleted} folders...")
                except Exception as e:
                    print(f"   ⚠️  Failed to delete {path}: {e}")
        
        print(f"✅ Deleted {deleted} Physics storage folders")
        return deleted
        
    except Exception as e:
        print(f"⚠️  Storage cleanup error: {e}")
        return 0

def main():
    print("="*60)
    print("🧹 PHYSICS DATA CLEANUP (FPM SAFE)")
    print("="*60)
    
    # Verify subject IDs
    if not verify_subject_ids():
        print("\n❌ Subject ID verification failed. Aborting for safety.")
        return
    
    # Get initial stats
    physics_papers = get_physics_stats()
    fpm_papers_before, fpm_pages_before = get_fpm_stats()
    
    if not physics_papers:
        print("\n✅ No Physics data found. Nothing to clean.")
        return
    
    # Confirm deletion
    print("\n" + "="*60)
    print("⚠️  WARNING: This will delete ALL Physics data")
    print("="*60)
    print(f"   Papers to delete: {len(physics_papers)}")
    print(f"   FPM data will NOT be touched: {fpm_papers_before} papers, {fpm_pages_before} pages")
    print()
    
    confirm = input("Type 'DELETE PHYSICS' to confirm: ")
    
    if confirm != "DELETE PHYSICS":
        print("\n❌ Cleanup cancelled")
        return
    
    # Execute cleanup
    print("\n🚀 Starting cleanup...")
    
    # Extract paper IDs
    paper_ids = [p['id'] for p in physics_papers]
    
    # Delete pages first (foreign key constraint)
    pages_deleted = delete_physics_pages(paper_ids)
    
    # Delete papers
    papers_deleted = delete_physics_papers()
    
    # Cleanup storage
    storage_deleted = cleanup_storage()
    
    # Verify FPM untouched
    print("\n🔍 Verifying FPM data integrity...")
    fpm_papers_after, fpm_pages_after = get_fpm_stats()
    
    if fpm_papers_after == fpm_papers_before and fpm_pages_after == fpm_pages_before:
        print(f"✅ FPM data verified intact: {fpm_papers_after} papers, {fpm_pages_after} pages")
    else:
        print(f"❌ ERROR: FPM data changed!")
        print(f"   Before: {fpm_papers_before} papers, {fpm_pages_before} pages")
        print(f"   After: {fpm_papers_after} papers, {fpm_pages_after} pages")
        return
    
    # Final summary
    print("\n" + "="*60)
    print("✅ CLEANUP COMPLETE")
    print("="*60)
    print(f"   Physics papers deleted: {papers_deleted}")
    print(f"   Physics pages deleted: {pages_deleted}")
    print(f"   Storage folders deleted: {storage_deleted}")
    print(f"   FPM data: UNTOUCHED ✅")
    print("="*60)

if __name__ == "__main__":
    main()
