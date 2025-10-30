#!/usr/bin/env python3
"""Check what data is in FPM pages"""

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

# Get FPM subject
subject = supabase.table("subjects").select("*").eq("code", "9FM0").execute()
print(f"Subject: {subject.data[0]}")
subject_id = subject.data[0]["id"]

# Get papers
papers = supabase.table("papers").select("*").eq("subject_id", subject_id).execute()
print(f"\nPapers: {len(papers.data)}")
for p in papers.data:
    print(f"  {p['year']} {p['season']} Paper {p['paper_number']}")

# Get pages
if papers.data:
    paper_id = papers.data[0]["id"]
    pages = supabase.table("pages").select("*").eq("paper_id", paper_id).limit(3).execute()
    print(f"\nSample Pages from first paper:")
    for p in pages.data:
        print(f"\nPage {p['page_number']}:")
        print(f"  Question: {p.get('question_number')}")
        print(f"  Topics: {p.get('topics')}")
        print(f"  text_excerpt length: {len(p.get('text_excerpt') or '')}")
        print(f"  qp_page_url: {p.get('qp_page_url')}")
        print(f"  has_diagram: {p.get('has_diagram')}")
