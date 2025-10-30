"""
Check if Physics PDFs exist in Supabase storage
"""
from supabase import create_client
from pathlib import Path
from dotenv import load_dotenv
import os

env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(env_path)

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

BUCKET_NAME = 'question-pdfs'
PHYSICS_PATH = 'subjects/Physics/pages'

print("🔍 Checking Physics PDFs in Supabase storage...")
print(f"   Bucket: {BUCKET_NAME}")
print(f"   Path: {PHYSICS_PATH}")
print()

try:
    # List all files in Physics pages folder
    result = supabase.storage.from_(BUCKET_NAME).list(PHYSICS_PATH)
    
    if not result:
        print("❌ No Physics folders found in storage")
    else:
        print(f"✅ Found {len(result)} folders in Physics/pages:")
        print()
        
        # Sample first few folders
        folders = [item for item in result if item.get('name')]
        folders_sorted = sorted(folders, key=lambda x: x['name'])
        
        print("   Sample folders:")
        for folder in folders_sorted[:10]:
            folder_name = folder['name']
            print(f"   • {folder_name}")
            
            # Check contents of first folder
            if folders_sorted.index(folder) == 0:
                try:
                    folder_contents = supabase.storage.from_(BUCKET_NAME).list(f"{PHYSICS_PATH}/{folder_name}")
                    if folder_contents:
                        pdf_files = [f for f in folder_contents if f['name'].endswith('.pdf')]
                        print(f"      → Contains {len(pdf_files)} PDF files")
                        for pdf in pdf_files[:5]:
                            print(f"         - {pdf['name']}")
                except Exception as e:
                    print(f"      → Error reading folder: {e}")
        
        print()
        print(f"   Total folders: {len(folders)}")
        
        # Try to count total PDFs in a few folders
        print()
        print("   Sampling PDF counts:")
        total_sampled = 0
        for folder in folders_sorted[:5]:
            try:
                folder_contents = supabase.storage.from_(BUCKET_NAME).list(f"{PHYSICS_PATH}/{folder['name']}")
                pdf_files = [f for f in folder_contents if f['name'].endswith('.pdf')]
                total_sampled += len(pdf_files)
                print(f"   • {folder['name']}: {len(pdf_files)} PDFs")
            except:
                pass
        
        estimated_total = (total_sampled / min(5, len(folders))) * len(folders) if folders else 0
        print(f"\n   📊 Estimated total PDFs: ~{int(estimated_total)}")
        
        print()
        print("="*60)
        print("CONCLUSION:")
        print("="*60)
        print("✅ Physics PDFs exist in storage!")
        print("   Action needed: Create database records for these PDFs")
        print("   Steps:")
        print("   1. Parse folder names to create papers")
        print("   2. Parse PDF filenames to create pages")
        print("   3. Set correct URLs pointing to storage")
        print("   4. Classify pages using multi-model LLM")
        
except Exception as e:
    print(f"❌ Error accessing storage: {e}")
    print()
    print("Note: The path structure might be different.")
    print("Try checking Supabase Storage UI directly.")

