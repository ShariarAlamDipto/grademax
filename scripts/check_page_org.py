#!/usr/bin/env python3
"""Check how pages are organized per paper"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('.env.local')

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Get first 3 papers
papers = supabase.table('papers')\
    .select('id,year,season,paper_number')\
    .eq('subject_id', '0b142517-d35d-4942-91aa-b4886aaabca3')\
    .order('year')\
    .order('season')\
    .order('paper_number')\
    .limit(3)\
    .execute()

print("="*70)
print("PAGE ORGANIZATION CHECK")
print("="*70)

for paper in papers.data:
    paper_name = f"{paper['year']} {paper['season']} P{paper['paper_number']}"
    print(f"\n📄 Paper: {paper_name}")
    
    # Get pages for this paper
    pages = supabase.table('pages')\
        .select('id,page_number,text_excerpt')\
        .eq('paper_id', paper['id'])\
        .order('page_number')\
        .execute()
    
    print(f"   Total pages: {len(pages.data)}")
    print(f"   Page numbers: {[p['page_number'] for p in pages.data]}")
    
    # Check text length
    for page in pages.data[:5]:  # Show first 5
        text_len = len(page.get('text_excerpt') or '')
        preview = (page.get('text_excerpt') or '')[:100].replace('\n', ' ')
        print(f"   Q{page['page_number']}: {text_len} chars - {preview}...")
