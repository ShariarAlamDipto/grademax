"""
Reset all Physics page classifications to start fresh
"""
import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv('.env.local')

SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

def main():
    print("=" * 70)
    print("🗑️  Reset Physics Page Classifications")
    print("=" * 70)
    
    # Initialize Supabase
    print("\n1️⃣  Connecting to Supabase...")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get Physics subject ID first
    print("\n2️⃣  Loading Physics subject...")
    subjects = supabase.table('subjects').select('id, code, name').eq('name', 'Physics').execute()
    
    if not subjects.data:
        print("   ❌ Physics subject not found!")
        return
    
    physics_subject_id = subjects.data[0]['id']
    physics_code = subjects.data[0]['code']
    print(f"   ✅ Found Physics subject: {physics_code} ({physics_subject_id})")
    
    # Get all Physics pages
    print("\n3️⃣  Loading Physics pages...")
    result = supabase.table('pages').select('id, question_number, paper_id, papers!inner(subject_id, year, season, paper_number)').eq('papers.subject_id', physics_subject_id).execute()
    
    physics_pages = result.data
    
    print(f"   ✅ Found {len(physics_pages)} Physics pages")
    
    # Confirm reset
    print(f"\n⚠️  WARNING: This will reset classifications for all {len(physics_pages)} Physics pages")
    print("   All pages will be set to:")
    print("   - topics: [question_number]  (default)")
    print("   - difficulty: null")
    
    # Check for --force flag
    import sys
    if '--force' not in sys.argv:
        confirm = input("\n   Proceed with reset? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("\n❌ Reset cancelled")
            return
    else:
        print("\n   🔥 --force flag detected, proceeding without confirmation")
    
    # Reset all Physics pages
    print(f"\n4️⃣  Resetting {len(physics_pages)} pages...")
    
    reset_count = 0
    error_count = 0
    
    for i, page in enumerate(physics_pages, 1):
        page_id = page['id']
        question_num = page['question_number']
        
        try:
            # Reset to default: topics = [question_number], difficulty = null
            supabase.table('pages').update({
                'topics': [question_num],
                'difficulty': None
            }).eq('id', page_id).execute()
            
            reset_count += 1
            
            if i % 50 == 0:
                print(f"   ⏳ Progress: {i}/{len(physics_pages)} pages reset...")
        
        except Exception as e:
            print(f"   ❌ Error resetting page {page_id}: {e}")
            error_count += 1
    
    print("\n" + "=" * 70)
    print("✅ Reset Complete!")
    print("=" * 70)
    print(f"\n📊 Results:")
    print(f"   Successfully reset: {reset_count} pages")
    print(f"   Errors: {error_count} pages")
    print(f"\n🎯 Next step:")
    print(f"   Run: python scripts/classify_physics_with_mistral.py")

if __name__ == '__main__':
    main()
