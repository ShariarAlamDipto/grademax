"""Check if FPM PDF files exist in storage"""
import os
from supabase import create_client
import requests

# Read from .env.local
def load_env():
    env_vars = {}
    with open('.env.local', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
    return env_vars

env = load_env()

supabase = create_client(
    env['NEXT_PUBLIC_SUPABASE_URL'],
    env['SUPABASE_SERVICE_ROLE_KEY']
)

# Get FPM subject
fpm_response = supabase.table('subjects').select('*').eq('code', '9FM0').execute()
fpm = fpm_response.data[0]
print(f"✅ FPM Subject: {fpm['name']}")

# Get some sample pages with URLs
pages = supabase.table('pages')\
    .select('id, question_number, qp_page_url, paper_id, papers(year, season, paper_number)')\
    .overlaps('topics', ['1'])\
    .limit(5)\
    .execute()

print(f"\n🔍 Testing {len(pages.data)} sample URLs:")
for page in pages.data:
    url = page['qp_page_url']
    print(f"\n   Q{page['question_number']} | {url[:80]}...")
    
    # Try to access the URL
    try:
        response = requests.head(url, timeout=5)
        if response.status_code == 200:
            print(f"   ✅ File exists (200 OK)")
        else:
            print(f"   ❌ Status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:50]}")

# Check what's actually in the storage bucket
print(f"\n🔍 Checking Supabase storage structure:")
try:
    # List what's in subjects bucket
    subjects_list = supabase.storage.from_('subjects').list()
    print(f"   Folders in 'subjects' bucket: {[f.name for f in subjects_list]}")
    
    # Check if Further_Pure_Mathematics exists
    if any(f.name == 'Further_Pure_Mathematics' for f in subjects_list):
        print(f"\n   ✅ 'Further_Pure_Mathematics' folder exists")
        
        # List what's inside
        fpm_contents = supabase.storage.from_('subjects').list('Further_Pure_Mathematics')
        print(f"   Contents: {[f.name for f in fpm_contents]}")
        
        # Check pages folder
        if any(f.name == 'pages' for f in fpm_contents):
            pages_contents = supabase.storage.from_('subjects').list('Further_Pure_Mathematics/pages')
            print(f"   Paper folders in pages/: {len(pages_contents)} folders")
            if pages_contents:
                print(f"   Sample folders: {[f.name for f in pages_contents[:5]]}")
    else:
        print(f"\n   ❌ 'Further_Pure_Mathematics' folder NOT found in storage")
        print(f"   Available folders: {[f.name for f in subjects_list]}")
        
except Exception as e:
    print(f"   ❌ Error checking storage: {e}")

# Check if files need to be uploaded
print(f"\n💡 SOLUTION:")
print(f"   The FPM PDFs need to be uploaded to Supabase storage!")
print(f"   Local files are in: data/processed/Further Pure Maths Processed/")
print(f"   They should be uploaded to: subjects/Further_Pure_Mathematics/pages/")
