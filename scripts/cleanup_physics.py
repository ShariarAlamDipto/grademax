"""
Cleanup script to remove old Physics processing data
Deletes papers, pages from database and files from storage
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment
env_path = project_root / '.env.local'
load_dotenv(env_path)

# Initialize Supabase
supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not supabase_url or not supabase_key:
    print("❌ Missing Supabase credentials")
    sys.exit(1)

supabase: Client = create_client(supabase_url, supabase_key)

# Physics subject ID
PHYSICS_SUBJECT_ID = "0b142517-d35d-4942-91aa-b4886aaabca3"

def get_physics_stats():
    """Get current Physics statistics"""
    # Count papers
    papers_response = supabase.table('papers').select('id', count='exact').eq('subject_id', PHYSICS_SUBJECT_ID).execute()
    papers_count = papers_response.count or 0
    
    # Count pages
    if papers_count > 0:
        paper_ids = [p['id'] for p in papers_response.data]
        pages_response = supabase.table('pages').select('id', count='exact').in_('paper_id', paper_ids).execute()
        pages_count = pages_response.count or 0
    else:
        pages_count = 0
    
    return papers_count, pages_count

def delete_storage_files():
    """Delete all Physics files from storage"""
    print("\n📦 Checking storage...")
    
    try:
        # List all folders in subjects/Physics/pages/
        storage = supabase.storage.from_('question-pdfs')
        
        # List folders
        folders = storage.list('subjects/Physics/pages/')
        
        if not folders:
            print("   No folders found in storage")
            return 0
        
        print(f"   Found {len(folders)} folders")
        
        deleted_count = 0
        for folder in folders:
            folder_name = folder['name']
            folder_path = f'subjects/Physics/pages/{folder_name}'
            
            try:
                # List files in folder
                files = storage.list(folder_path)
                
                if files:
                    # Delete all files in folder
                    file_paths = [f'{folder_path}/{f["name"]}' for f in files]
                    storage.remove(file_paths)
                    deleted_count += len(files)
                    print(f"   ✅ Deleted {len(files)} files from {folder_name}")
            except Exception as e:
                print(f"   ⚠️  Error deleting folder {folder_name}: {e}")
        
        print(f"\n   Total files deleted: {deleted_count}")
        return deleted_count
        
    except Exception as e:
        print(f"   ❌ Storage error: {e}")
        return 0

def delete_database_records():
    """Delete all Physics papers and pages from database"""
    print("\n🗄️  Deleting database records...")
    
    # Get all Physics papers
    papers_response = supabase.table('papers').select('id').eq('subject_id', PHYSICS_SUBJECT_ID).execute()
    
    if not papers_response.data:
        print("   No papers found")
        return 0, 0
    
    paper_ids = [p['id'] for p in papers_response.data]
    papers_count = len(paper_ids)
    
    # Delete pages first (foreign key constraint)
    print(f"   Deleting pages for {papers_count} papers...")
    pages_response = supabase.table('pages').delete().in_('paper_id', paper_ids).execute()
    pages_count = len(pages_response.data) if pages_response.data else 0
    print(f"   ✅ Deleted {pages_count} pages")
    
    # Delete papers
    print(f"   Deleting {papers_count} papers...")
    supabase.table('papers').delete().eq('subject_id', PHYSICS_SUBJECT_ID).execute()
    print(f"   ✅ Deleted {papers_count} papers")
    
    return papers_count, pages_count

def main():
    print("="*60)
    print("🧹 PHYSICS DATA CLEANUP")
    print("="*60)
    
    # Get initial stats
    print("\n📊 Current state:")
    papers_before, pages_before = get_physics_stats()
    print(f"   Papers: {papers_before}")
    print(f"   Pages: {pages_before}")
    
    if papers_before == 0:
        print("\n✅ No Physics data found - database already clean!")
        return
    
    # Confirm deletion
    print(f"\n⚠️  This will delete:")
    print(f"   - {papers_before} papers from database")
    print(f"   - {pages_before} pages from database")
    print(f"   - All associated files from storage")
    
    response = input("\n❓ Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return
    
    # Delete storage files
    files_deleted = delete_storage_files()
    
    # Delete database records
    papers_deleted, pages_deleted = delete_database_records()
    
    # Verify cleanup
    print("\n📊 Final state:")
    papers_after, pages_after = get_physics_stats()
    print(f"   Papers: {papers_after}")
    print(f"   Pages: {pages_after}")
    
    print("\n" + "="*60)
    print("✅ CLEANUP COMPLETE!")
    print("="*60)
    print(f"   Papers deleted: {papers_deleted}")
    print(f"   Pages deleted: {pages_deleted}")
    print(f"   Files deleted: {files_deleted}")
    print("\n✨ Ready for fresh processing with hardened algorithm!")

if __name__ == "__main__":
    main()
