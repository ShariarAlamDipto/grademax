#!/usr/bin/env python3
"""Check page numbers in database"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('.env.local')

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Get 2011 Jun Paper 1P
paper = supabase.table('papers')\
    .select('id,year,season,paper_number')\
    .eq('year', 2011)\
    .eq('season', 'Jun')\
    .eq('paper_number', '1P')\
    .execute()

if paper.data:
    paper_id = paper.data[0]['id']
    print(f"Paper: 2011 Jun P1P (ID: {paper_id})")
    print()
    
    # Get pages for this paper
    pages = supabase.table('pages')\
        .select('id,page_number')\
        .eq('paper_id', paper_id)\
        .order('page_number')\
        .execute()
    
    print(f"Total pages: {len(pages.data)}")
    print("\nPage numbers:")
    for p in pages.data:
        print(f"  Page ID {p['id']}: page_number = {p['page_number']}")
