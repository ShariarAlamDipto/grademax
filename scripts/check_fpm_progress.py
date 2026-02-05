#!/usr/bin/env python3
"""
Check FPM classification progress
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
print("FPM CLASSIFICATION PROGRESS")
print("="*80)

# Get FPM subject
fpm = supabase.table("subjects").select("*").eq("code", "9FM0").execute()
if not fpm.data:
    print("ERROR: FPM subject not found")
    sys.exit(1)

fpm_id = fpm.data[0]['id']
print(f"\n[OK] Subject: {fpm.data[0]['name']} ({fpm.data[0]['code']})")

# Get paper count
papers = supabase.table("papers").select("id", count="exact").eq("subject_id", fpm_id).execute()
paper_count = papers.count if papers.count else 0
print(f"[INFO] Papers in database: {paper_count}")

# Get total pages
all_pages = supabase.table("pages")\
    .select("id, paper_id", count="exact")\
    .in_("paper_id", [p['id'] for p in papers.data if papers.data])\
    .execute()
total_pages = all_pages.count if all_pages.count else 0
print(f"[INFO] Total pages: {total_pages}")

# Get classified pages (topics array not empty)
if papers.data:
    classified = supabase.table("pages")\
        .select("id", count="exact")\
        .in_("paper_id", [p['id'] for p in papers.data])\
        .neq("topics", "{}")\
        .execute()
    classified_count = classified.count if classified.count else 0
    
    print(f"[OK] Classified pages: {classified_count}")
    print(f"[WAIT] Remaining: {total_pages - classified_count}")
    
    if total_pages > 0:
        progress = (classified_count / total_pages) * 100
        print(f"[PROGRESS] Progress: {progress:.1f}%")
    
    # Get topic distribution
    print(f"\n[TOPICS] Topic Distribution:")
    for i in range(1, 11):
        topic_pages = supabase.table("pages")\
            .select("id", count="exact")\
            .in_("paper_id", [p['id'] for p in papers.data])\
            .contains("topics", [str(i)])\
            .execute()
        count = topic_pages.count if topic_pages.count else 0
        if count > 0:
            print(f"   Topic {i}: {count} pages")

print()
