"""
Reset and reprocess all Maths B papers with corrected question detection (up to 30 questions)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('.env.local')

client = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'), 
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

SUBJECT_CODE = "4MB1"

def reset_maths_b():
    print("=" * 70)
    print("RESETTING MATHS B DATA")
    print("=" * 70)
    
    # Get subject
    subject = client.table('subjects').select('id').eq('code', SUBJECT_CODE).execute().data
    if not subject:
        print("Subject not found!")
        return
    
    subject_id = subject[0]['id']
    print(f"Subject ID: {subject_id}")
    
    # Get all papers
    papers = client.table('papers').select('id').eq('subject_id', subject_id).execute().data
    paper_ids = [p['id'] for p in papers]
    print(f"Papers to reset: {len(paper_ids)}")
    
    # Delete all pages for these papers
    if paper_ids:
        for paper_id in paper_ids:
            client.table('pages').delete().eq('paper_id', paper_id).execute()
        print(f"Deleted pages from {len(paper_ids)} papers")
    
    # Delete papers
    client.table('papers').delete().eq('subject_id', subject_id).execute()
    print("Deleted all papers")
    
    print("\nReset complete. Run process_maths_b_complete.py to reprocess.")


if __name__ == "__main__":
    reset_maths_b()
