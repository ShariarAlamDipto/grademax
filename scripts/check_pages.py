from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv('.env.local')
supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

pages = supabase.table('pages').select('page_number, topics, qp_page_url, ms_page_url').order('page_number').execute()

print(f"📊 Total pages: {len(pages.data)}\n")

for p in pages.data:
    qp_status = "✅" if p.get('qp_page_url') else "❌"
    ms_status = "✅" if p.get('ms_page_url') else "❌"
    topics = p.get('topics', [])
    print(f"Q{p['page_number']}: Topics={len(topics)}, QP={qp_status}, MS={ms_status}")
    if p.get('qp_page_url'):
        print(f"  QP URL: {p['qp_page_url'][:80]}...")
