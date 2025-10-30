"""Find and fix pages with wrong storage URLs"""
import os
from supabase import create_client

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
print(f"✅ FPM Subject: {fpm['name']} (ID: {fpm['id']})")

# Get FPM papers
papers_response = supabase.table('papers').select('id').eq('subject_id', fpm['id']).execute()
paper_ids = [p['id'] for p in papers_response.data]
print(f"📄 Found {len(paper_ids)} FPM papers")

# Get pages from FPM papers and check their URLs
pages_response = supabase.table('pages')\
    .select('id, qp_page_url, ms_page_url, paper_id')\
    .in_('paper_id', paper_ids)\
    .limit(100)\
    .execute()

physics_url_pages = []
fpm_url_pages = []
other_url_pages = []

for page in pages_response.data:
    qp_url = page['qp_page_url'] or ''
    if 'Physics' in qp_url:
        physics_url_pages.append(page)
    elif 'Further Pure' in qp_url or 'Further_Pure' in qp_url or '9FM0' in qp_url:
        fpm_url_pages.append(page)
    else:
        other_url_pages.append(page)

print(f"\n📊 URL Analysis (sample of 100 pages):")
print(f"   ❌ Pages with Physics URLs: {len(physics_url_pages)}")
print(f"   ✅ Pages with FPM URLs: {len(fpm_url_pages)}")
print(f"   ❓ Pages with other/no URLs: {len(other_url_pages)}")

if physics_url_pages:
    print(f"\n⚠️  Sample pages with Physics URLs:")
    for page in physics_url_pages[:5]:
        print(f"   Page {page['id'][:8]}... URL: {page['qp_page_url'][:80]}...")

if fpm_url_pages:
    print(f"\n✅ Sample pages with FPM URLs:")
    for page in fpm_url_pages[:5]:
        print(f"   Page {page['id'][:8]}... URL: {page['qp_page_url'][:80]}...")

# Check all pages (not just sample)
print(f"\n🔍 Checking ALL FPM pages...")
all_pages_response = supabase.table('pages')\
    .select('id, qp_page_url', count='exact')\
    .in_('paper_id', paper_ids)\
    .execute()

print(f"   Total FPM pages: {all_pages_response.count}")

# Count how many have Physics URLs
physics_count = 0
for page in all_pages_response.data:
    if page['qp_page_url'] and 'Physics' in page['qp_page_url']:
        physics_count += 1

print(f"   Pages with Physics URLs: {physics_count}")
print(f"   Pages with correct URLs: {all_pages_response.count - physics_count}")

if physics_count > 0:
    print(f"\n⚠️  Need to fix {physics_count} pages with wrong URLs!")
    print(f"   These pages are linked to FPM papers but have Physics storage URLs")
