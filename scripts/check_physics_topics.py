"""
Quick script to check Physics topics configuration
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load environment
project_root = Path(__file__).parent.parent
env_path = project_root / '.env.local'
load_dotenv(env_path)

SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Get Physics subject
subject_resp = supabase.table('subjects').select('*').eq('name', 'Physics').execute()
subject_id = subject_resp.data[0]['id']

print("=" * 80)
print("PHYSICS TOPICS CONFIGURATION")
print("=" * 80)

# Get all topics
topics = supabase.table('topics').select('*').eq('subject_id', subject_id).execute()

print(f"\nFound {len(topics.data)} topics:\n")
for topic in sorted(topics.data, key=lambda x: x.get('id', '')):
    print(f"Topic: {topic}")
    print()

print("=" * 80)
print("SAMPLE PAGES WITH TOPICS")
print("=" * 80)

# Get Physics paper first
papers = supabase.table('papers').select('id').eq('subject_id', subject_id).limit(1).execute()
if not papers.data:
    print("No Physics papers found!")
    exit(1)

sample_paper_id = papers.data[0]['id']

# Get sample pages through paper_id
pages = supabase.table('pages')\
    .select('question_number, topics')\
    .eq('paper_id', sample_paper_id)\
    .not_.is_('topics', 'null')\
    .limit(10)\
    .execute()

print(f"\nShowing 10 sample pages:\n")
for page in pages.data:
    print(f"Q{page['question_number']}: topics = {page['topics']}")

# Count by topic - get all Physics papers first
print("\n" + "=" * 80)
print("TOPIC DISTRIBUTION IN DATABASE")
print("=" * 80)

all_papers = supabase.table('papers').select('id').eq('subject_id', subject_id).execute()
paper_ids = [p['id'] for p in all_papers.data]

print(f"\nFound {len(paper_ids)} Physics papers")

all_pages = supabase.table('pages')\
    .select('topics')\
    .in_('paper_id', paper_ids)\
    .not_.is_('topics', 'null')\
    .execute()

topic_counts = {}
for page in all_pages.data:
    for topic in page.get('topics', []):
        topic_counts[topic] = topic_counts.get(topic, 0) + 1

print(f"\nPages by topic code:")
for topic_code in sorted(topic_counts.keys()):
    print(f"  {topic_code}: {topic_counts[topic_code]} pages")
