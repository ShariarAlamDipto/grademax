import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv('.env.local')

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Get a sample page with topics
pages_response = supabase.table('pages').select('id, question_number, topics, qp_page_url, ms_page_url').limit(10).execute()

print("📋 Sample pages and their topics format:\n")
for page in pages_response.data:
    print(f"Page {page['id'][:8]}... Q{page['question_number']}")
    print(f"  Topics: {page.get('topics')} (type: {type(page.get('topics'))})")
    if page.get('topics'):
        print(f"  First topic: {page['topics'][0]} (type: {type(page['topics'][0])})")
    print(f"  QP URL: {page.get('qp_page_url')[:60] if page.get('qp_page_url') else 'NULL'}...")
    print()

# Get topics from topics table
topics_response = supabase.table('topics').select('id, topic_number, name').execute()
print("\n📋 Topics from topics table:\n")
for topic in topics_response.data[:5]:
    print(f"Topic ID: {topic['id']} (UUID)")
    print(f"  Number: {topic['topic_number']}")
    print(f"  Name: {topic['name']}")
    print()
