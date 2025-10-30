"""
Check Physics subject current state in database
"""
from supabase import create_client
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(env_path)

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

PHYSICS_CODE = '4PH1'

# Get Physics subject
result = supabase.table('subjects').select('*').eq('code', PHYSICS_CODE).execute()

if result.data:
    subject = result.data[0]
    print(f"✅ Physics Subject Found:")
    print(f"   Name: {subject['name']}")
    print(f"   Code: {subject['code']}")
    print(f"   ID: {subject['id']}")
    
    # Check papers
    papers = supabase.table('papers').select('*').eq('subject_id', subject['id']).execute()
    print(f"\n📄 Papers: {len(papers.data)}")
    if papers.data:
        print(f"   Sample: {papers.data[0]['paper_code']}")
    
    # Check pages
    pages = supabase.table('pages').select('id, question_number, topics, qp_page_url').eq('subject_id', subject['id']).limit(5).execute()
    print(f"\n📋 Pages: {len(pages.data)} (showing first 5)")
    
    # Count total pages
    total_pages = supabase.table('pages').select('id', count='exact').eq('subject_id', subject['id']).execute()
    print(f"   Total pages: {total_pages.count}")
    
    # Check classification status
    if pages.data:
        for page in pages.data:
            topics_str = f"Topics: {page['topics']}" if page['topics'] else "⚠️ Not classified"
            url_str = "✅ Has URL" if page['qp_page_url'] else "❌ No URL"
            print(f"   Q{page['question_number']}: {topics_str} | {url_str}")
    
    # Get topics for Physics
    topics = supabase.table('topics').select('*').eq('subject_id', subject['id']).order('id').execute()
    print(f"\n🏷️  Topics: {len(topics.data)}")
    for topic in topics.data:
        print(f"   [{topic['id']}] {topic['name']} ({topic['short_name']})")
    
else:
    print(f"❌ Physics subject with code '{PHYSICS_CODE}' not found!")
