#!/usr/bin/env python3
"""
Reset all Physics page classifications to force re-classification
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load environment
env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(env_path)

SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
PHYSICS_SUBJECT_ID = '0b142517-d35d-4942-91aa-b4886aaabca3'

def main():
    print("=" * 70)
    print("🗑️  Reset Physics Page Classifications")
    print("=" * 70)
    print()
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get all Physics pages
    print("Loading Physics pages...")
    
    # Get all papers for Physics subject
    papers = supabase.table('papers').select('id').eq('subject_id', PHYSICS_SUBJECT_ID).execute()
    paper_ids = [p['id'] for p in papers.data]
    
    # Get all pages for these papers
    pages = supabase.table('pages').select('id, question_number, topics, difficulty').in_('paper_id', paper_ids).eq('is_question', True).execute()
    
    print(f"Found {len(pages.data)} Physics pages")
    print()
    
    # Show current state
    classified = sum(1 for p in pages.data if p.get('difficulty'))
    print(f"Currently classified: {classified}/{len(pages.data)}")
    print()
    
    # Confirm
    confirm = input("⚠️  Reset ALL classifications? This will set topics=[question_number], difficulty=null (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("\n❌ Cancelled")
        return
    
    # Reset all pages
    print(f"\nResetting {len(pages.data)} pages...")
    success = 0
    failed = 0
    
    for page in pages.data:
        try:
            supabase.table('pages').update({
                'topics': [page['question_number']],  # Reset to default
                'difficulty': None
            }).eq('id', page['id']).execute()
            success += 1
            
            if success % 50 == 0:
                print(f"   Progress: {success}/{len(pages.data)}")
        except Exception as e:
            print(f"   ❌ Failed page {page['id']}: {e}")
            failed += 1
    
    print()
    print("=" * 70)
    print("✅ Reset Complete!")
    print("=" * 70)
    print(f"\nReset: {success} pages")
    print(f"Failed: {failed} pages")
    print()
    print("Next step: Run batch_classify_physics.py to re-classify with improved prompt")
    print()

if __name__ == '__main__':
    main()
