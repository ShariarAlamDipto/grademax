#!/usr/bin/env python3
"""
Sync Physics pages from storage to database
- Physics pages already exist in storage at: question-pdfs/subjects/Physics/pages/
- Need to create database records in pages table
- Link to existing papers in the papers table
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment
load_dotenv('.env.local')

# Initialize Supabase
url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
supabase: Client = create_client(url, service_role_key)

PHYSICS_SUBJECT_ID = '0b142517-d35d-4942-91aa-b4886aaabca3'
STORAGE_BUCKET = 'question-pdfs'
STORAGE_BASE = 'subjects/Physics/pages'


def parse_paper_folder(folder_name: str):
    """
    Parse folder name to extract metadata
    Examples: 2011_Jun_1P, 2012_Jan_2P, 2023_Jun_1P
    Returns: (year, season, paper_number) or None
    """
    parts = folder_name.split('_')
    if len(parts) != 3:
        return None
    
    year_str = parts[0]
    season = parts[1]
    paper_str = parts[2]  # e.g., "1P" or "2P"
    
    try:
        year = int(year_str)
        paper_number = paper_str  # Keep full paper number "1P" or "2P"
        return (year, season, paper_number)
    except:
        return None


def get_public_url(file_path: str) -> str:
    """Generate public URL for storage file"""
    return f"https://{url.replace('https://', '').replace('http://', '')}/storage/v1/object/public/{STORAGE_BUCKET}/{file_path}"


def find_paper_id(year: int, season: str, paper_number: str):
    """Find paper ID from database"""
    result = supabase.table('papers').select('id').eq('subject_id', PHYSICS_SUBJECT_ID).eq('year', year).eq('season', season).eq('paper_number', paper_number).execute()
    
    if result.data and len(result.data) > 0:
        return result.data[0]['id']
    return None


def extract_question_number(filename: str) -> str:
    """Extract question number from filename (e.g., q1.pdf -> 1, q10_ms.pdf -> 10)"""
    if filename.startswith('q'):
        # Remove 'q' prefix and any suffix like '_ms.pdf'
        num_str = filename[1:].split('_')[0].split('.')[0]
        return num_str
    return None


def sync_paper_folder(folder_name: str):
    """Sync all pages from a paper folder"""
    parsed = parse_paper_folder(folder_name)
    if not parsed:
        print(f"   ⚠️  Could not parse folder name: {folder_name}")
        return 0
    
    year, season, paper_number = parsed
    
    # Find corresponding paper in database
    paper_id = find_paper_id(year, season, paper_number)
    if not paper_id:
        print(f"   ⚠️  Paper not found in DB: {year} {season} Paper {paper_number}")
        return 0
    
    print(f"   📄 Processing {year} {season} Paper {paper_number} (paper_id: {paper_id})")
    
    # List files in this folder
    folder_path = f"{STORAGE_BASE}/{folder_name}"
    try:
        files = supabase.storage.from_(STORAGE_BUCKET).list(folder_path)
    except Exception as e:
        print(f"      ❌ Error listing files: {e}")
        return 0
    
    # Group files by question number
    questions = {}
    for file_info in files:
        filename = file_info['name']
        
        if not filename.endswith('.pdf'):
            continue
        
        q_num = extract_question_number(filename)
        if not q_num:
            continue
        
        if q_num not in questions:
            questions[q_num] = {'qp': None, 'ms': None}
        
        if '_ms' in filename.lower():
            questions[q_num]['ms'] = filename
        else:
            questions[q_num]['qp'] = filename
    
    # Create page records
    pages_created = 0
    for q_num in sorted(questions.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        files = questions[q_num]
        
        if not files['qp']:
            print(f"      ⚠️  No QP file for question {q_num}")
            continue
        
        # Build storage URLs
        qp_url = get_public_url(f"{folder_path}/{files['qp']}")
        ms_url = get_public_url(f"{folder_path}/{files['ms']}") if files['ms'] else None
        
        # Check if page already exists
        existing = supabase.table('pages').select('id').eq('paper_id', paper_id).eq('question_number', q_num).execute()
        
        if existing.data and len(existing.data) > 0:
            print(f"      ⏭️  Question {q_num} already exists, skipping")
            continue
        
        # Create page record
        page_data = {
            'paper_id': paper_id,
            'page_number': int(q_num) if q_num.isdigit() else 1,
            'question_number': q_num,
            'topics': [q_num],  # Default: use question number as topic
            'difficulty': 'medium',  # Default
            'qp_page_url': qp_url,
            'ms_page_url': ms_url,
            'is_question': True,
            'has_diagram': False,  # Default
            'text_excerpt': f"Question {q_num}"
        }
        
        try:
            result = supabase.table('pages').insert(page_data).execute()
            pages_created += 1
            print(f"      ✅ Created page for question {q_num}")
        except Exception as e:
            print(f"      ❌ Error creating page for question {q_num}: {e}")
    
    return pages_created


def main():
    print("=" * 70)
    print("🔄 Sync Physics Pages from Storage to Database")
    print("=" * 70)
    print()
    
    # List all paper folders in storage
    print("1️⃣  Scanning storage for Physics paper folders...")
    try:
        folders = supabase.storage.from_(STORAGE_BUCKET).list(STORAGE_BASE)
    except Exception as e:
        print(f"   ❌ Error accessing storage: {e}")
        return
    
    paper_folders = [f['name'] for f in folders if '_' in f['name']]
    print(f"   ✅ Found {len(paper_folders)} paper folders")
    print()
    
    # Process each folder
    print("2️⃣  Processing paper folders...")
    total_pages = 0
    
    for i, folder_name in enumerate(sorted(paper_folders), 1):
        print(f"\n   [{i}/{len(paper_folders)}] {folder_name}")
        pages_created = sync_paper_folder(folder_name)
        total_pages += pages_created
    
    # Summary
    print()
    print("=" * 70)
    print("✅ Sync Complete!")
    print("=" * 70)
    print(f"\n📊 Statistics:")
    print(f"   Paper folders processed: {len(paper_folders)}")
    print(f"   Pages created: {total_pages}")
    print()
    print("🎯 Next steps:")
    print("   1. Review pages: Check the pages table in Supabase")
    print("   2. Update topics: Use ML classifier or manual tagging")
    print("   3. Test worksheet generation with Physics topics")
    print()


if __name__ == '__main__':
    main()
