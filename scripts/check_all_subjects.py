#!/usr/bin/env python3
"""
Check all subjects and their data in database
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
print("📚 ALL SUBJECTS IN DATABASE")
print("="*80)

# Get all subjects
subjects = supabase.table("subjects").select("*").execute()
print(f"\nFound {len(subjects.data)} subjects:\n")

for subj in subjects.data:
    print(f"• {subj['name']} ({subj['code']})")
    print(f"  ID: {subj['id']}")
    
    # Count papers
    papers = supabase.table("papers").select("id", count="exact").eq("subject_id", subj['id']).execute()
    paper_count = papers.count if papers.count else 0
    print(f"  Papers: {paper_count}")
    
    if paper_count > 0:
        # Get sample paper
        sample_papers = supabase.table("papers").select("*").eq("subject_id", subj['id']).limit(1).execute()
        if sample_papers.data:
            p = sample_papers.data[0]
            print(f"  Sample: {p['year']} {p['season']} Paper {p['paper_number']}")
            
            # Get pages
            pages = supabase.table("pages").select("id", count="exact").eq("paper_id", p['id']).execute()
            page_count = pages.count if pages.count else 0
            print(f"  Pages in sample: {page_count}")
            
            # Check if pages have topic classifications
            if page_count > 0:
                classified = supabase.table("pages")\
                    .select("id", count="exact")\
                    .eq("paper_id", p['id'])\
                    .neq("topics", "{}")\
                    .execute()
                classified_count = classified.count if classified.count else 0
                print(f"  Classified pages: {classified_count}/{page_count}")
    print()
