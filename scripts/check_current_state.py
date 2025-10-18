"""Check current database state."""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('.env.local')

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Get subject
subject = supabase.table('subjects').select('*').eq('name', 'Further Pure Mathematics').execute()
if subject.data:
    subject_id = subject.data[0]['id']
    print(f"✅ Subject: Further Pure Mathematics")
    print(f"   ID: {subject_id}\n")
    
    # Get topics
    topics = supabase.table('topics').select('*').eq('subject_id', subject_id).order('code').execute()
    print(f"📚 Topics ({len(topics.data)}):")
    for t in topics.data:
        print(f"   {t['code']}. {t['name']}")
    
    # Get pages
    pages = supabase.table('pages').select('page_number, topics').limit(5).execute()
    print(f"\n📄 Sample pages:")
    for p in pages.data:
        print(f"   Q{p['page_number']}: {len(p['topics']) if p['topics'] else 0} topics")
