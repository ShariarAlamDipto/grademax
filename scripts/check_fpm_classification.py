#!/usr/bin/env python3
"""Check FPM classification results"""

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

# Get FPM subject
subject = supabase.table('subjects').select('id, name').eq('code', '9FM0').execute()
if not subject.data:
    print("❌ FPM not found")
    exit(1)

subject_id = subject.data[0]['id']
subject_name = subject.data[0]['name']

print(f"\n📚 {subject_name} Classification Results")
print("="*60)

# Get papers
papers = supabase.table('papers')\
    .select('id, year, season, paper_number')\
    .eq('subject_id', subject_id)\
    .order('year')\
    .order('season')\
    .order('paper_number')\
    .execute()

for paper in papers.data:
    print(f"\n📄 {paper['year']} {paper['season']} Paper {paper['paper_number']}")
    print("-"*60)
    
    # Get pages
    pages = supabase.table('pages')\
        .select('page_number, topics, difficulty, confidence, text_excerpt')\
        .eq('paper_id', paper['id'])\
        .order('page_number')\
        .execute()
    
    for page in pages.data:
        topics = page.get('topics', [])
        topic_str = topics[0] if topics else 'None'
        difficulty = page.get('difficulty', 'N/A')
        confidence = page.get('confidence', 0.0)
        
        text_preview = (page.get('text_excerpt') or '')[:100].replace('\n', ' ')
        
        print(f"  Q{page['page_number']}: Topic {topic_str} | {difficulty} | {confidence:.2f} | {text_preview}...")

print("\n" + "="*60)
print("✅ Classification check complete")
