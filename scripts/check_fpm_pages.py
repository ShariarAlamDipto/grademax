"""Check FPM pages structure in database"""
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
response = supabase.table('subjects').select('*').eq('code', '9FM0').execute()
fpm = response.data[0] if response.data else None

if not fpm:
    print("❌ FPM subject not found")
    exit(1)

print(f"✅ FPM Subject: {fpm['name']} (ID: {fpm['id']})")

# Get a sample of pages with topic "1"
print("\n🔍 Sample pages with Topic 1:")
response = supabase.table('pages')\
    .select('id, paper_id, topics, difficulty, confidence')\
    .contains('topics', ['1'])\
    .limit(5)\
    .execute()

if response.data:
    for page in response.data:
        print(f"   Page {page['id'][:8]}... | Topics: {page['topics']} | Difficulty: {page['difficulty']} | Confidence: {page['confidence']}")
        
        # Get paper info
        paper_response = supabase.table('papers').select('*').eq('id', page['paper_id']).execute()
        if paper_response.data:
            paper = paper_response.data[0]
            paper_type = paper.get('paper_type', paper.get('type', 'Unknown'))
            print(f"      Paper: {paper['year']} {paper['season']} {paper_type} | Subject: {paper['subject_id']}")
else:
    print("   ❌ No pages found with Topic 1")

# Check if papers have correct subject_id
print("\n🔍 Checking FPM papers:")
response = supabase.table('papers')\
    .select('id, year, season, paper_type, subject_id')\
    .eq('subject_id', fpm['id'])\
    .limit(5)\
    .execute()

if response.data:
    print(f"   ✅ Found {len(response.data)} FPM papers (showing first 5)")
    for paper in response.data:
        paper_type = paper.get('paper_type', paper.get('type', 'Unknown'))
        print(f"   Paper {paper['id'][:8]}... | {paper['year']} {paper['season']} {paper_type} | Subject: {paper['subject_id'][:8]}...")
        
        # Count pages for this paper
        page_response = supabase.table('pages').select('id', count='exact').eq('paper_id', paper['id']).execute()
        print(f"      Pages: {page_response.count}")
else:
    print("   ❌ No FPM papers found")

print("\n🔍 Checking all papers (any subject):")
response = supabase.table('papers')\
    .select('id, year, season, paper_type, subject_id')\
    .limit(5)\
    .execute()

if response.data:
    for paper in response.data:
        paper_type = paper.get('paper_type', paper.get('type', 'Unknown'))
        print(f"   Paper {paper['id'][:8]}... | {paper['year']} {paper['season']} {paper_type} | Subject: {paper['subject_id'][:8]}...")
