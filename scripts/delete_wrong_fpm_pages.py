"""Delete FPM pages that have Physics URLs (they're wrong)"""
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

# Get all pages with Physics URLs
print(f"\n🔍 Finding pages with Physics URLs...")
all_pages = supabase.table('pages')\
    .select('id, qp_page_url, paper_id, question_number')\
    .in_('paper_id', paper_ids)\
    .execute()

pages_to_delete = []
for page in all_pages.data:
    if page['qp_page_url'] and 'Physics' in page['qp_page_url']:
        pages_to_delete.append(page)

print(f"   Found {len(pages_to_delete)} pages with Physics URLs")

if pages_to_delete:
    print(f"\n⚠️  These pages will be DELETED:")
    for page in pages_to_delete[:10]:
        print(f"   Page {page['id'][:8]}... Q{page['question_number']} | URL: {page['qp_page_url'][:60]}...")
    if len(pages_to_delete) > 10:
        print(f"   ... and {len(pages_to_delete) - 10} more")
    
    confirm = input(f"\n🗑️  Delete {len(pages_to_delete)} pages with wrong Physics URLs? (yes/no): ")
    
    if confirm.lower() == 'yes':
        page_ids_to_delete = [p['id'] for p in pages_to_delete]
        
        # Delete in batches of 100
        batch_size = 100
        for i in range(0, len(page_ids_to_delete), batch_size):
            batch = page_ids_to_delete[i:i+batch_size]
            supabase.table('pages').delete().in_('id', batch).execute()
            print(f"   Deleted batch {i//batch_size + 1}/{(len(page_ids_to_delete) + batch_size - 1)//batch_size}")
        
        print(f"\n✅ Deleted {len(pages_to_delete)} pages!")
        
        # Check final count
        final_count = supabase.table('pages').select('id', count='exact').in_('paper_id', paper_ids).execute()
        print(f"📊 Remaining FPM pages: {final_count.count}")
    else:
        print("   ❌ Cancelled")
else:
    print("   ✅ No pages with Physics URLs found")
