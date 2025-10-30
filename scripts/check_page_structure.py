#!/usr/bin/env python3
"""Check how pages are structured"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('.env.local')

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Get pages with actual text content
print("Looking for pages with text content...\n")

# Try to find pages with text
all_pages = supabase.table('pages')\
    .select('id,page_number,text_excerpt,topics,difficulty,confidence,paper_id')\
    .limit(100)\
    .execute()

pages_with_text = [p for p in all_pages.data if p.get('text_excerpt')]

print(f"Found {len(pages_with_text)} pages with text out of 100 sampled\n")

if pages_with_text:
    print("Sample Pages with Text:\n")
    for i, page in enumerate(pages_with_text[:3], 1):
        text = page.get('text_excerpt', '')
        print(f"Page {i}:")
        print(f"  Page number: {page['page_number']}")
        print(f"  Text length: {len(text)} chars")
        print(f"  Topics: {page.get('topics')}")
        print(f"  Difficulty: {page.get('difficulty')}")
        print(f"  Confidence: {page.get('confidence')}")
        print(f"  Text preview: {text[:300]}...")
        print()
else:
    print("No pages with text_excerpt found!")
