"""Check what URLs should be for FPM pages"""
import os
from supabase import create_client
from pathlib import Path

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

# Check one FPM page that HAS a URL
pages_with_url = supabase.table('pages')\
    .select('id, question_number, qp_page_url, ms_page_url, paper_id')\
    .not_.is_('qp_page_url', 'null')\
    .limit(5)\
    .execute()

if pages_with_url.data:
    print("✅ Pages with URLs (to see pattern):")
    for page in pages_with_url.data:
        print(f"   Q{page['question_number']}")
        print(f"   QP: {page['qp_page_url']}")
        print(f"   MS: {page['ms_page_url']}")
        
        # Get paper info
        paper = supabase.table('papers').select('year, season, paper_number').eq('id', page['paper_id']).execute()
        if paper.data:
            p = paper.data[0]
            print(f"   Paper: {p['year']} {p['season']} Paper {p['paper_number']}")
        print()

# Check local files
print("\n🔍 Checking local processed FPM files:")
base_path = Path("data/processed/Further Pure Maths Processed")
if base_path.exists():
    folders = list(base_path.glob("*"))
    print(f"   Found {len(folders)} paper folders")
    
    if folders:
        # Check first folder
        first_folder = folders[0]
        print(f"\n   Sample folder: {first_folder.name}")
        pages_dir = first_folder / "pages"
        if pages_dir.exists():
            pdfs = list(pages_dir.glob("*.pdf"))
            print(f"   PDFs in pages/: {len(pdfs)}")
            if pdfs:
                print(f"   Sample files: {[p.name for p in pdfs[:5]]}")
else:
    print(f"   ❌ Path not found: {base_path}")

# Check Supabase storage to see if files are there
print("\n🔍 Checking Supabase storage:")
try:
    # List buckets
    buckets = supabase.storage.list_buckets()
    print(f"   Buckets: {[b.name for b in buckets]}")
    
    # Check subjects bucket
    files = supabase.storage.from_('subjects').list('Further Pure Mathematics')
    if files:
        print(f"   Files in 'Further Pure Mathematics': {len(files)}")
    else:
        print(f"   No files in 'Further Pure Mathematics' folder")
except Exception as e:
    print(f"   Error checking storage: {e}")
