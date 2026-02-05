"""
Check pages table structure for Math B
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('.env.local')
c = create_client(os.getenv('NEXT_PUBLIC_SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

# Get a sample of pages for Math B
papers = c.table('papers').select('id').eq('subject_id', 'af08fe67-37e2-4e20-9550-30103c4fe91a').limit(3).execute().data
paper_ids = [p['id'] for p in papers]

print(f"Paper IDs: {paper_ids[:3]}...")

pages = c.table('pages').select('*').in_('paper_id', paper_ids).limit(10).execute().data

print(f"\nFound {len(pages)} pages")
print("\nSample pages:")
for p in pages:
    q_num = p.get('question_number', 'N/A')
    topics = p.get('topics', [])
    is_q = p.get('is_question')
    qp_url = p.get('qp_page_url')
    print(f"  Q{q_num}: topics={topics}, is_question={is_q}, has_qp_url={bool(qp_url)}")

# Check columns
if pages:
    print(f"\nPage columns: {list(pages[0].keys())}")
