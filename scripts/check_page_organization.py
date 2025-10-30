#!/usr/bin/env python3
"""Check how pages are organized by year/paper"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('.env.local')

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Get Physics papers with pages
papers = supabase.table('papers')\
    .select('id,year,season,paper_number')\
    .eq('subject_id', '0b142517-d35d-4942-91aa-b4886aaabca3')\
    .order('year')\
    .order('season')\
    .order('paper_number')\
    .limit(5)\
    .execute()

print("Sample Papers Organization:\n")

for paper in papers.data:
    print(f"\n{'='*60}")
    print(f"Paper: {paper['year']} {paper['season']} Paper {paper['paper_number']}")
    print(f"Paper ID: {paper['id']}")
    
    # Get pages for this paper
    pages = supabase.table('pages')\
        .select('id,page_number,topics,difficulty,confidence,text_excerpt')\
        .eq('paper_id', paper['id'])\
        .order('page_number')\
        .execute()
    
    print(f"Total pages: {len(pages.data)}")
    
    # Check for gaps
    page_numbers = [p['page_number'] for p in pages.data]
    if page_numbers:
        expected = list(range(min(page_numbers), max(page_numbers) + 1))
        missing = set(expected) - set(page_numbers)
        if missing:
            print(f"⚠️  MISSING PAGE NUMBERS: {sorted(missing)}")
        else:
            print(f"✅ No gaps (pages {min(page_numbers)} to {max(page_numbers)})")
    
    # Show first 5 pages
    print("\nFirst 5 pages:")
    for p in pages.data[:5]:
        text_preview = (p.get('text_excerpt') or '')[:30]
        print(f"  Q{p['page_number']}: Topic {p.get('topics')}, {p.get('difficulty')}, text: '{text_preview}...'")
