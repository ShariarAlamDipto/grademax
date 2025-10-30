import os
from supabase import create_client
from dotenv import load_dotenv
import requests

load_dotenv('.env.local')

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Get one page URL
page = supabase.table('pages').select('*').contains('topics', ['1']).limit(1).execute().data[0]

print("Sample page:")
print(f"  QP URL: {page['qp_page_url']}")
print(f"  MS URL: {page['ms_page_url']}")
print()

# Try to access it
print("Testing direct access:")
qp_response = requests.get(page['qp_page_url'])
print(f"  QP Status: {qp_response.status_code}")
print(f"  QP Response: {qp_response.text[:200]}")
print()

# Check if file exists in storage
print("Checking storage bucket...")
try:
    # List files in the bucket
    files = supabase.storage.from_('question-pdfs').list('subjects/Further_Pure_Mathematics/pages/2014_Jan_Paper2P')
    print(f"  Files in folder: {len(files)}")
    for f in files[:5]:
        print(f"    - {f['name']}")
except Exception as e:
    print(f"  Error: {e}")
