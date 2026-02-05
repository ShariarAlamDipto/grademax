"""Check Physics page URLs to understand the pattern"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('.env.local')
c = create_client(os.getenv('NEXT_PUBLIC_SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

# Get Physics pages with qp_page_url
physics_sub = c.table('subjects').select('id').eq('code', '4PH1').execute().data[0]
physics_papers = c.table('papers').select('id').eq('subject_id', physics_sub['id']).limit(1).execute().data
pages = c.table('pages').select('qp_page_url, ms_page_url, question_number').eq('paper_id', physics_papers[0]['id']).limit(3).execute().data

print('Physics page URLs:')
for p in pages:
    print(f"  Q{p['question_number']}:")
    print(f"    QP: {p['qp_page_url']}")
    print(f"    MS: {p['ms_page_url']}")
