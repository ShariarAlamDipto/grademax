"""Check what topic codes are stored in FPM pages"""
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

# Get FPM topics from topics table
topics_response = supabase.table('topics').select('*').eq('subject_id', fpm['id']).execute()
print(f"\n📚 FPM Topics in database:")
for topic in topics_response.data:
    print(f"   Topic {topic['code']}: {topic['name']}")

# Get FPM papers
papers_response = supabase.table('papers').select('id').eq('subject_id', fpm['id']).execute()
paper_ids = [p['id'] for p in papers_response.data]
print(f"\n📄 Found {len(paper_ids)} FPM papers")

# Get sample pages from first FPM paper
if paper_ids:
    sample_pages = supabase.table('pages')\
        .select('id, question_number, topics, paper_id')\
        .eq('paper_id', paper_ids[0])\
        .limit(5)\
        .execute()
    
    print(f"\n🔍 Sample pages from first FPM paper:")
    for page in sample_pages.data:
        print(f"   Q{page['question_number']}: Topics = {page['topics']}")

# Check what unique topic values exist in FPM pages
print(f"\n🔍 Checking all unique topic codes in FPM pages...")
all_pages = supabase.table('pages')\
    .select('topics')\
    .in_('paper_id', paper_ids[:20])\
    .execute()

unique_topics = set()
for page in all_pages.data:
    if page['topics']:
        for topic in page['topics']:
            unique_topics.add(topic)

print(f"   Unique topic codes found: {sorted(unique_topics)}")

# Now try to query with topic code "1"
print(f"\n🔍 Testing query with topic code '1':")
test_query = supabase.table('pages')\
    .select('id, question_number, topics, paper_id', count='exact')\
    .in_('paper_id', paper_ids)\
    .overlaps('topics', ['1'])\
    .limit(5)\
    .execute()

print(f"   Found {test_query.count} pages with topic '1'")
if test_query.data:
    for page in test_query.data[:3]:
        print(f"   Q{page['question_number']}: Topics = {page['topics']}")

# Check the paper info for these pages
if test_query.data:
    test_page = test_query.data[0]
    paper_info = supabase.table('papers').select('year, season, paper_number, subject_id, subjects(code, name)').eq('id', test_page['paper_id']).execute()
    if paper_info.data:
        p = paper_info.data[0]
        print(f"\n   Paper info: {p['year']} {p['season']} Paper {p['paper_number']}")
        print(f"   Subject: {p['subjects']['code']} - {p['subjects']['name']}")
        print(f"   Subject ID: {p['subject_id']}")
