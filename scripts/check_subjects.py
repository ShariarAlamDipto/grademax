#!/usr/bin/env python3
"""Check what subjects are in the database"""

from dotenv import load_dotenv
import os
from supabase import create_client
from pathlib import Path

# Load env
project_root = Path(__file__).parent.parent
load_dotenv(project_root / '.env.local')

# Connect
url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
supabase = create_client(url, key)

# Get subjects
subjects = supabase.table('subjects').select('code, name, id').execute()

print('\n📚 Available subjects in database:')
print('='*60)
for s in subjects.data:
    # Check papers
    papers = supabase.table('papers').select('id').eq('subject_id', s['id']).execute()
    paper_count = len(papers.data)
    
    # Check pages
    if paper_count > 0:
        pages = supabase.table('pages')\
            .select('id')\
            .in_('paper_id', [p['id'] for p in papers.data])\
            .execute()
        page_count = len(pages.data)
    else:
        page_count = 0
    
    print(f"  {s['code']}: {s['name']}")
    print(f"     ID: {s['id']}")
    print(f"     Papers: {paper_count}, Pages: {page_count}")
    print()
