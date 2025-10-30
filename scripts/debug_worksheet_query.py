"""Debug worksheet generation query"""
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
print(f"✅ FPM Subject ID: {fpm['id']}")

# Step 1: Get papers matching subject
print(f"\n🔍 Step 1: Get FPM papers")
papers = supabase.table('papers')\
    .select('id, year, season, paper_number')\
    .eq('subject_id', fpm['id'])\
    .execute()

print(f"   Found {len(papers.data)} papers")
paper_ids = [p['id'] for p in papers.data]

# Step 2: Get pages matching criteria (like the API does)
print(f"\n🔍 Step 2: Get pages with topic '1'")

# Check pages with proper filters
pages = supabase.table('pages')\
    .select('id, question_number, topics, difficulty, qp_page_url, is_question, paper_id')\
    .in_('paper_id', paper_ids)\
    .overlaps('topics', ['1'])\
    .limit(10)\
    .execute()

print(f"   Found {len(pages.data)} pages (before filters)")

# Check each filter
print(f"\n🔍 Step 3: Check individual filters")

# Check is_question filter
is_question_pages = supabase.table('pages')\
    .select('id, is_question', count='exact')\
    .in_('paper_id', paper_ids)\
    .eq('is_question', True)\
    .execute()

print(f"   Pages with is_question=true: {is_question_pages.count}")

# Check qp_page_url not null
url_pages = supabase.table('pages')\
    .select('id, qp_page_url', count='exact')\
    .in_('paper_id', paper_ids)\
    .not_.is_('qp_page_url', 'null')\
    .execute()

print(f"   Pages with qp_page_url not null: {url_pages.count}")

# Check with topic '1'
topic_pages = supabase.table('pages')\
    .select('id, topics', count='exact')\
    .in_('paper_id', paper_ids)\
    .overlaps('topics', ['1'])\
    .execute()

print(f"   Pages with topic '1': {topic_pages.count}")

# Check ALL filters combined (like the API)
combined = supabase.table('pages')\
    .select('id, question_number, topics, difficulty, qp_page_url, is_question', count='exact')\
    .eq('is_question', True)\
    .not_.is_('qp_page_url', 'null')\
    .in_('paper_id', paper_ids)\
    .overlaps('topics', ['1'])\
    .execute()

print(f"   Pages with ALL filters: {combined.count}")

if combined.data:
    print(f"\n✅ Sample results:")
    for page in combined.data[:5]:
        print(f"   Q{page['question_number']} | Topics: {page['topics']} | URL: {page['qp_page_url'][:60] if page['qp_page_url'] else 'None'}...")
else:
    print(f"\n❌ No results found!")
    
    # Debug: Check what's in the pages
    print(f"\n🔍 Debugging: Check sample FPM pages")
    sample = supabase.table('pages')\
        .select('id, question_number, topics, is_question, qp_page_url')\
        .in_('paper_id', paper_ids)\
        .limit(10)\
        .execute()
    
    for page in sample.data:
        print(f"   Q{page['question_number']} | is_question={page.get('is_question')} | topics={page['topics']} | has_url={bool(page['qp_page_url'])}")
