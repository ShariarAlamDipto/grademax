import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv('.env.local')

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

FPM_SUBJECT_ID = '8dea5d70-f026-4e03-bb45-053f154c6898'

# Get all FPM papers
papers = supabase.table('papers').select('id').eq('subject_id', FPM_SUBJECT_ID).execute().data

print(f"✅ Found {len(papers)} FPM papers")

# Get all pages for FPM papers
all_pages = []
for paper in papers:
    pages = supabase.table('pages').select('*').eq('paper_id', paper['id']).execute().data
    all_pages.extend(pages)

print(f"📄 Found {len(all_pages)} FPM pages")

# Fix URLs by removing "Paper" from the folder name
updated_count = 0

for page in all_pages:
    qp_url = page.get('qp_page_url')
    ms_url = page.get('ms_page_url')
    
    if not qp_url or not ms_url:
        continue
    
    # Fix the URLs by removing "Paper" from folder name
    # Example: /pages/2014_Jan_Paper2P/ -> /pages/2014_Jan_2P/
    new_qp_url = qp_url.replace('/pages/', '/pages/').replace('_Paper', '_')
    new_ms_url = ms_url.replace('/pages/', '/pages/').replace('_Paper', '_')
    
    # Only update if URL changed
    if new_qp_url != qp_url or new_ms_url != ms_url:
        supabase.table('pages').update({
            'qp_page_url': new_qp_url,
            'ms_page_url': new_ms_url
        }).eq('id', page['id']).execute()
        
        updated_count += 1
        if updated_count % 50 == 0:
            print(f"   Updated {updated_count} pages...")

print(f"\n✅ Updated {updated_count} page URLs")

# Test a sample URL
print(f"\n📋 Sample URL after update:")
sample = supabase.table('pages').select('*').contains('topics', ['1']).limit(1).execute().data[0]
print(f"   QP: {sample['qp_page_url']}")
print(f"   MS: {sample['ms_page_url']}")

# Test if it's accessible
import requests
response = requests.get(sample['qp_page_url'])
print(f"\n🔍 Testing URL access:")
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    print(f"   ✅ Success! PDF size: {len(response.content)} bytes")
else:
    print(f"   ❌ Error: {response.text[:100]}")
