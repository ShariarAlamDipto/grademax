"""Fix empty topic classifications and reclassify"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('.env.local')

client = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'), 
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Get subject
subject = client.table('subjects').select('id').eq('code', '4MB1').execute().data[0]
print(f"Subject ID: {subject['id'][:8]}...")

# Get all papers
papers = client.table('papers').select('id, year, season, paper_number').eq('subject_id', subject['id']).execute().data
print(f"Papers: {len(papers)}")

# Get all pages
paper_ids = [p['id'] for p in papers]
pages = client.table('pages').select('id, paper_id, question_number, text_excerpt, topics').in_('paper_id', paper_ids).execute().data
print(f"Total pages: {len(pages)}")

# Find pages with empty topics
empty = [p for p in pages if not p.get('topics') or p['topics'] == [''] or p['topics'] == [] or '' in p.get('topics', [])]
print(f"Pages with empty/invalid topics: {len(empty)}")

# Show some examples
print("\nExamples of empty topic pages:")
for p in empty[:5]:
    excerpt = p.get('text_excerpt', 'NO TEXT')[:80] if p.get('text_excerpt') else 'NO TEXT'
    print(f"  Q{p['question_number']}: {excerpt}...")
