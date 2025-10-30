import os
from supabase import create_client
from dotenv import load_dotenv
import requests

load_dotenv('.env.local')

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Get Physics subject
physics_response = supabase.table('subjects').select('*').eq('code', '9PH0').execute()
if not physics_response.data:
    print("❌ Physics subject not found!")
    exit(1)

physics = physics_response.data[0]
print(f"✅ Physics Subject: {physics['name']} (ID: {physics['id']})")

# Get Physics papers
papers_response = supabase.table('papers').select('*').eq('subject_id', physics['id']).execute()
print(f"📄 Found {len(papers_response.data)} Physics papers")

# Get Physics pages
pages_response = supabase.table('pages').select('*').limit(10).execute()
physics_pages = [p for p in pages_response.data if any(paper['id'] == p['paper_id'] for paper in papers_response.data)]

print(f"📋 Sample Physics pages: {len(physics_pages)}")

if physics_pages:
    sample = physics_pages[0]
    print(f"\n🔍 Sample page:")
    print(f"   ID: {sample['id'][:8]}...")
    print(f"   Question: {sample.get('question_number')}")
    print(f"   Topics: {sample.get('topics')}")
    print(f"   QP URL: {sample.get('qp_page_url')}")
    print(f"   MS URL: {sample.get('ms_page_url')}")
    
    # Test URLs
    if sample.get('qp_page_url'):
        print(f"\n📡 Testing QP URL...")
        try:
            response = requests.get(sample['qp_page_url'], timeout=5)
            print(f"   Status: {response.status_code}")
            if response.status_code != 200:
                print(f"   Error: {response.text[:100]}")
        except Exception as e:
            print(f"   Error: {e}")
    
    # Check storage
    if sample.get('qp_page_url'):
        # Extract folder from URL
        parts = sample['qp_page_url'].split('/')
        if 'pages' in parts:
            idx = parts.index('pages')
            if idx + 1 < len(parts):
                folder = parts[idx + 1]
                print(f"\n📂 Checking storage folder: {folder}")
                try:
                    files = supabase.storage.from_('question-pdfs').list(f'subjects/Physics/pages/{folder}')
                    print(f"   Found {len(files)} files")
                    for f in files[:5]:
                        print(f"      - {f['name']}")
                except Exception as e:
                    print(f"   Error: {e}")
