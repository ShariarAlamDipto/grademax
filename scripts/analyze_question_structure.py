#!/usr/bin/env python3
"""
Analyze how questions are structured across pages
Identify complete questions with all their subparts
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('.env.local')

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

SUBJECT_ID = "0b142517-d35d-4942-91aa-b4886aaabca3"  # Physics

# Get all papers (remove limit to analyze all 52 papers)
papers = supabase.table('papers')\
    .select('id,year,season,paper_number')\
    .eq('subject_id', SUBJECT_ID)\
    .order('year')\
    .order('season')\
    .order('paper_number')\
    .execute()

print("="*70)
print("QUESTION STRUCTURE ANALYSIS")
print("="*70)
print()

for paper in papers.data:
    paper_info = f"{paper['year']} {paper['season']} P{paper['paper_number']}"
    
    # Get all pages for this paper
    pages = supabase.table('pages')\
        .select('id,page_number,text_excerpt')\
        .eq('paper_id', paper['id'])\
        .order('page_number')\
        .execute()
    
    print(f"\n📄 Paper: {paper_info}")
    print(f"   Total pages in DB: {len(pages.data)}")
    
    # Group by question number
    questions = {}
    for page in pages.data:
        q_num = page['page_number']
        text = page.get('text_excerpt', '')
        text_len = len(text) if text else 0
        
        if q_num not in questions:
            questions[q_num] = []
        questions[q_num].append({
            'page_id': page['id'],
            'text_length': text_len
        })
    
    print(f"   Unique question numbers: {sorted(questions.keys())}")
    print()
    
    # Show which questions have multiple pages
    for q_num in sorted(questions.keys()):
        page_count = len(questions[q_num])
        total_text = sum(p['text_length'] for p in questions[q_num])
        
        if page_count > 1:
            print(f"   ⚠️  Q{q_num}: {page_count} pages, {total_text} chars total")
        else:
            blank = " (BLANK)" if total_text < 50 else ""
            print(f"   ✓  Q{q_num}: 1 page, {total_text} chars{blank}")

print("\n" + "="*70)
print("CONCLUSION:")
print("="*70)
print("• Questions with multiple pages need text from ALL pages combined")
print("• Blank pages (< 50 chars) should be skipped")
print("• Each complete QUESTION (not page) should get ONE classification")
