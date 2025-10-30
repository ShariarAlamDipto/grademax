#!/usr/bin/env python3
"""Quick check of text extraction status"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('.env.local')

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Get 10 sample pages
pages = supabase.table('pages')\
    .select('id,page_number,text_excerpt')\
    .limit(10)\
    .execute()

print("Sample of first 10 pages:")
for p in pages.data:
    text = p.get('text_excerpt') or ''
    print(f"  Q{p['page_number']}: {len(text)} chars - {text[:50] if text else '(empty)'}...")
