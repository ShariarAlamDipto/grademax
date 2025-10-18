#!/usr/bin/env python3
"""
Simple ingestion check for Further Pure Mathematics
Checks what data we have and shows sample questions
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import PyPDF2

# Load environment
load_dotenv('.env.local')

url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

supabase = create_client(url, key)

print("="*80)
print("🔍 FURTHER PURE MATHEMATICS - PIPELINE CHECK")
print("="*80)

# 1. Check raw PDFs
print("\n📁 Step 1: Checking Raw PDF Files...")
pdf_dir = Path("data/raw/IGCSE/Further Pure Maths")

if not pdf_dir.exists():
    print(f"❌ Directory not found: {pdf_dir}")
    exit(1)

pdf_files = list(pdf_dir.rglob("*.pdf"))
qp_files = [f for f in pdf_files if not '_MS' in f.name]
ms_files = [f for f in pdf_files if '_MS' in f.name]

print(f"✅ Found {len(qp_files)} question papers")
print(f"✅ Found {len(ms_files)} mark schemes")

# Show sample
if qp_files:
    print("\nSample files:")
    for pdf in qp_files[:3]:
        rel_path = pdf.relative_to(pdf_dir)
        print(f"   📄 {rel_path}")
        
        # Try to extract first page text
        try:
            with open(pdf, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                if len(reader.pages) > 0:
                    first_page = reader.pages[0]
                    text = first_page.extract_text()
                    # Show first 200 chars
                    preview = text[:200].replace('\n', ' ')
                    print(f"      Preview: {preview}...")
                print(f"      Pages: {len(reader.pages)}")
        except Exception as e:
            print(f"      Error reading PDF: {e}")

# 2. Check processed data
print("\n📊 Step 2: Checking Processed Data...")
processed_dir = Path("data/processed")

fp_processed = list(processed_dir.rglob("*9FM*"))
print(f"Found {len(fp_processed)} processed Further Pure files")

if fp_processed:
    for item in fp_processed[:5]:
        print(f"   - {item.relative_to(processed_dir)}")

# 3. Check database
print("\n💾 Step 3: Checking Database...")

# Get subject
subjects = supabase.table('subjects').select('*').execute()
fp_subject = [s for s in subjects.data if 'further' in s['name'].lower() and 'pure' in s['name'].lower()]

if fp_subject:
    subject = fp_subject[0]
    subject_id = subject['id']
    print(f"✅ Subject found: {subject['name']} (ID: {subject_id})")
    
    # Get papers
    papers = supabase.table('papers').select('*').eq('subject_id', subject_id).execute()
    print(f"   Papers in DB: {len(papers.data)}")
    
    # Get pages
    total_pages = 0
    for paper in papers.data:
        pages = supabase.table('pages').select('*').eq('paper_id', paper['id']).execute()
        total_pages += len(pages.data)
        if len(pages.data) > 0:
            print(f"      {paper.get('year', 'unknown')} {paper.get('paper_code', 'unknown')}: {len(pages.data)} questions")
    
    print(f"   Total Questions: {total_pages}")
else:
    print("❌ Subject not found in database")

# 4. Check topics
print("\n🎯 Step 4: Checking Topics...")
if fp_subject:
    topics = supabase.table('topics').select('*').eq('subject_id', subject_id).execute()
    print(f"✅ Found {len(topics.data)} topics")
    for topic in topics.data:
        print(f"   - {topic['name']}")

# 5. Recommendations
print("\n" + "="*80)
print("📋 RECOMMENDATIONS")
print("="*80)

if len(qp_files) > 0 and total_pages == 0:
    print("\n⚠️ PDFs exist but no questions in database!")
    print("\nNext steps:")
    print("1. Create/update ingestion pipeline to work with LM Studio")
    print("2. Process PDFs: Extract questions and mark schemes")
    print("3. Run LM Studio classification on questions")
    print("4. Upload to database")
    print("\nAlternative: Upload pre-processed JSON if available")

elif total_pages > 0:
    print(f"\n✅ Pipeline working! {total_pages} questions loaded.")
    print("\nYou can now:")
    print("1. View questions in dashboard")
    print("2. Generate worksheets")
    print("3. Test LM Studio classification on new PDFs")

else:
    print("\n❌ No PDFs found!")
    print("Add PDF files to: data/raw/IGCSE/Further Pure Maths/")

print("\n" + "="*80)
