import os
from supabase import create_client
from dotenv import load_dotenv
import requests

load_dotenv('.env.local')

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Get 3 sample pages
pages = supabase.table('pages').select('*').contains('topics', ['1']).limit(3).execute().data

print("📋 Checking sample page URLs:\n")

for i, page in enumerate(pages, 1):
    print(f"Page {i}: Q{page['question_number']}")
    qp_url = page['qp_page_url']
    ms_url = page['ms_page_url']
    
    print(f"  QP URL: {qp_url}")
    print(f"  MS URL: {ms_url}")
    
    # Test QP URL
    try:
        qp_response = requests.get(qp_url, timeout=5)
        if qp_response.status_code == 200:
            print(f"  ✅ QP accessible: {len(qp_response.content)} bytes")
        else:
            print(f"  ❌ QP Status: {qp_response.status_code}")
            print(f"     Response: {qp_response.text[:100]}")
    except Exception as e:
        print(f"  ❌ QP Error: {e}")
    
    # Test MS URL
    try:
        ms_response = requests.get(ms_url, timeout=5)
        if ms_response.status_code == 200:
            print(f"  ✅ MS accessible: {len(ms_response.content)} bytes")
        else:
            print(f"  ❌ MS Status: {ms_response.status_code}")
            print(f"     Response: {ms_response.text[:100]}")
    except Exception as e:
        print(f"  ❌ MS Error: {e}")
    
    print()
