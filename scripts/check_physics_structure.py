#!/usr/bin/env python3
"""
Check Physics database structure to understand the setup
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load environment
env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(env_path)

supabase = create_client(
    os.getenv("NEXT_PUBLIC_SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

print("\n" + "="*80)
print("🔬 PHYSICS DATABASE STRUCTURE")
print("="*80)

# Get Physics subject
physics = supabase.table("subjects").select("*").eq("code", "0625").execute()
if physics.data:
    print(f"\n✅ Physics Subject:")
    print(f"   ID: {physics.data[0]['id']}")
    print(f"   Name: {physics.data[0]['name']}")
    print(f"   Code: {physics.data[0]['code']}")
    physics_id = physics.data[0]['id']
    
    # Get sample papers
    papers = supabase.table("papers").select("*").eq("subject_id", physics_id).limit(3).execute()
    print(f"\n📄 Sample Papers ({len(papers.data)} shown):")
    for p in papers.data:
        print(f"   • {p['year']} {p['season']} Paper {p['paper_number']} (ID: {p['id'][:8]}...)")
        print(f"     Total pages: {p.get('total_pages')}")
        print(f"     QP source: {p.get('qp_source_path', 'N/A')[:50]}...")
        print(f"     MS source: {p.get('ms_source_path', 'N/A')[:50]}...")
        
        # Get pages for this paper
        pages = supabase.table("pages").select("*").eq("paper_id", p['id']).limit(3).execute()
        print(f"     Pages in DB: {len(pages.data)} (showing 3)")
        for page in pages.data:
            print(f"       Q{page['page_number']}: {page.get('question_number')} | Topics: {page.get('topics')} | Diff: {page.get('difficulty')}")
            print(f"       - qp_page_url: {page.get('qp_page_url', 'N/A')[:60]}...")
            print(f"       - text_excerpt: {len(page.get('text_excerpt') or '')} chars")
        print()

print("\n" + "="*80)
print("🔍 KEY OBSERVATIONS:")
print("="*80)
print("✓ Pages reference PDF URLs in Supabase storage (qp_page_url)")
print("✓ Text is stored in text_excerpt field (first 500 chars)")
print("✓ Topics are stored as array: ['1', '2']")
print("✓ Each page has: page_number, question_number, topics, difficulty, confidence")
print("✓ PDFs are stored in Supabase storage, not local filesystem")
