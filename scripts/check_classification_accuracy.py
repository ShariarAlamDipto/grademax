#!/usr/bin/env python3
"""Check classification accuracy by sampling results"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('.env.local')

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

SUBJECT_ID = "0b142517-d35d-4942-91aa-b4886aaabca3"  # Physics

# Get classified pages
pages = supabase.table('pages')\
    .select('id,page_number,text_excerpt,topics,difficulty,confidence,paper_id')\
    .neq('topics', None)\
    .limit(50)\
    .execute()

print("="*70)
print("CLASSIFICATION ACCURACY CHECK - Sample of 50 Pages")
print("="*70)
print()

for page in pages.data:
    text = page.get('text_excerpt', '')[:200].replace('\n', ' ')
    topics = page.get('topics', [])
    topic = topics[0] if topics else 'None'
    confidence = page.get('confidence', 0)
    
    print(f"Q{page['page_number']}: Topic {topic} ({confidence:.2f})")
    print(f"   Text: {text}...")
    print()
