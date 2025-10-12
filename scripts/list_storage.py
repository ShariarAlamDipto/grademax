"""
List all files in Supabase Storage bucket
"""
from supabase_client import SupabaseClient
from dotenv import load_dotenv
import requests

# Load environment variables from .env.ingest
load_dotenv('.env.ingest')

db = SupabaseClient()

print("📦 Listing files in 'question-pdfs' bucket...\n")

# Use Supabase REST API to list files
storage_url = f"{db.url}/storage/v1/object/list/question-pdfs"

headers = {
    'apikey': db.key,
    'Authorization': f'Bearer {db.key}',
}

# List root folder
try:
    response = requests.post(
        storage_url,
        headers=headers,
        json={
            "limit": 1000,
            "offset": 0,
            "sortBy": {"column": "name", "order": "asc"}
        }
    )
    
    if response.status_code == 200:
        files = response.json()
        print(f"Found {len(files)} items in root:\n")
        
        folders = [f for f in files if f.get('id') is None]
        files_list = [f for f in files if f.get('id') is not None]
        
        print(f"📁 Folders: {len(folders)}")
        for folder in folders[:10]:
            print(f"   - {folder['name']}/")
        
        print(f"\n📄 Files in root: {len(files_list)}")
        for file in files_list[:10]:
            print(f"   - {file['name']}")
            
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ Error: {e}")

# Now check what's in database
print("\n\n🗄️  Checking database for page_pdf_url...")
questions = db.select('questions', 'page_pdf_url', {})

storage_urls = [q['page_pdf_url'] for q in questions if q.get('page_pdf_url') and not q['page_pdf_url'].startswith('data')]

if storage_urls:
    print(f"\nFound {len(storage_urls)} storage URLs in database")
    print("\nSample URLs:")
    for url in storage_urls[:5]:
        print(f"   - {url}")
        
    # Test first one
    test_url = storage_urls[0]
    full_url = db.get_public_url('question-pdfs', test_url)
    print(f"\n🧪 Testing: {test_url}")
    print(f"   Full URL: {full_url}")
    
    try:
        r = requests.head(full_url, timeout=5)
        if r.status_code == 200:
            print(f"   ✅ Accessible")
        else:
            print(f"   ❌ HTTP {r.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
else:
    print("❌ No storage URLs found in database!")
