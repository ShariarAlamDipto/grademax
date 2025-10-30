"""
Check current Physics database state to understand what data exists
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

PHYSICS_CODE = '4PH1'

# Get Physics subject
result = supabase.table('subjects').select('*').eq('code', PHYSICS_CODE).execute()

if not result.data:
    print(f"❌ Physics subject not found!")
    exit(1)

subject = result.data[0]
print(f"✅ Physics Subject:")
print(f"   Name: {subject['name']}")
print(f"   Code: {subject['code']}")
print(f"   ID: {subject['id']}")

PHYSICS_ID = subject['id']

# Check papers
papers_result = supabase.table('papers').select('*').eq('subject_id', PHYSICS_ID).execute()
print(f"\n📄 Papers: {len(papers_result.data)}")

if papers_result.data:
    print(f"\n   Sample papers:")
    for paper in papers_result.data[:5]:
        print(f"   • {paper['year']}_{paper['season']}_{paper['paper_number']} (ID: {paper['id']})")
    
    # Check pages
    pages_result = supabase.table('pages').select('id, question_number, topics, qp_page_url, ms_page_url').eq('subject_id', PHYSICS_ID).limit(10).execute()
    
    total_pages_result = supabase.table('pages').select('id', count='exact').eq('subject_id', PHYSICS_ID).execute()
    print(f"\n📋 Total Pages: {total_pages_result.count}")
    
    if pages_result.data:
        print(f"\n   Sample pages:")
        classified_count = 0
        has_url_count = 0
        
        for page in pages_result.data:
            has_topics = page['topics'] and len(page['topics']) > 0
            has_url = page['qp_page_url'] is not None
            
            if has_topics:
                classified_count += 1
            if has_url:
                has_url_count += 1
                
            topics_str = f"Topics: {page['topics']}" if has_topics else "❌ Not classified"
            url_str = "✅ Has URL" if has_url else "❌ No URL"
            print(f"   • Q{page['question_number']}: {topics_str} | {url_str}")
        
        # Get classification stats
        all_pages = supabase.table('pages').select('topics, qp_page_url').eq('subject_id', PHYSICS_ID).execute()
        total = len(all_pages.data)
        classified = sum(1 for p in all_pages.data if p['topics'] and len(p['topics']) > 0)
        with_urls = sum(1 for p in all_pages.data if p['qp_page_url'])
        
        print(f"\n📊 Statistics:")
        print(f"   Total pages: {total}")
        print(f"   Classified: {classified} ({classified/total*100:.1f}%)")
        print(f"   With URLs: {with_urls} ({with_urls/total*100:.1f}%)")
        print(f"   Unclassified: {total - classified}")
else:
    print("\n   ⚠️  No papers found for Physics!")
    print("\n   This means Physics needs to be processed from raw data.")

# Check topics
topics_result = supabase.table('topics').select('*').eq('subject_id', PHYSICS_ID).order('id').execute()
print(f"\n🏷️  Topics: {len(topics_result.data)}")
for topic in topics_result.data:
    print(f"   [{topic['id']}] {topic['name']} ({topic['short_name']})")

print("\n" + "="*60)
print("CONCLUSION:")
print("="*60)

if not papers_result.data:
    print("❌ No Physics papers in database")
    print("   Action needed: Process Physics from raw data")
    print("   Note: Processed folders were deleted during FPM cleanup")
elif total_pages_result.count == 0:
    print("❌ Papers exist but no pages")
    print("   Action needed: Extract pages from papers")
elif classified < total:
    print(f"⚠️  Physics has {total} pages but only {classified} classified")
    print(f"   Action needed: Classify {total - classified} remaining pages")
    print(f"   Can run: python scripts/reclassify_physics.py")
else:
    print("✅ Physics is fully set up and classified!")
