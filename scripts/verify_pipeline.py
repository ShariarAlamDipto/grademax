#!/usr/bin/env python3
"""
Pipeline Verification: Check Further Pure Mathematics Data
Verifies questions, mark schemes, topics, and complete data integrity
"""

import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment
load_dotenv('.env.local')

url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not url or not key:
    print("❌ Missing Supabase credentials")
    exit(1)

supabase = create_client(url, key)

print("="*80)
print("🔍 PIPELINE VERIFICATION - FURTHER PURE MATHEMATICS")
print("="*80)

# 1. Check subjects
print("\n📚 Step 1: Checking Subjects...")
subjects = supabase.table('subjects').select('*').execute()
further_pure = [s for s in subjects.data if 'further' in s['name'].lower() and 'pure' in s['name'].lower()]

if further_pure:
    fp_subject = further_pure[0]
    print(f"✅ Found subject: {fp_subject['name']}")
    print(f"   ID: {fp_subject['id']}")
    print(f"   Code: {fp_subject.get('code', 'N/A')}")
    subject_id = fp_subject['id']
else:
    print("❌ Further Pure Mathematics subject not found")
    print("\nAvailable subjects:")
    for s in subjects.data:
        print(f"   - {s['name']} (ID: {s['id']})")
    exit(1)

# 2. Check topics
print("\n🎯 Step 2: Checking Topics...")
topics = supabase.table('topics').select('*').eq('subject_id', subject_id).execute()
print(f"✅ Found {len(topics.data)} topics for Further Pure Mathematics")
for topic in topics.data[:5]:  # Show first 5
    print(f"   - {topic['name']}")
if len(topics.data) > 5:
    print(f"   ... and {len(topics.data) - 5} more")

# 3. Check papers
print("\n📄 Step 3: Checking Papers...")
papers = supabase.table('papers').select('*').eq('subject_id', subject_id).execute()
print(f"✅ Found {len(papers.data)} papers for Further Pure Mathematics")

if papers.data:
    # Show sample papers
    for paper in papers.data[:3]:
        year = paper.get('year', 'unknown')
        code = paper.get('paper_code', 'unknown')
        print(f"   - {year} {code}: {paper.get('title', 'No title')}")
    if len(papers.data) > 3:
        print(f"   ... and {len(papers.data) - 3} more")
else:
    print("⚠️ No papers found")

# 4. Check pages (questions)
print("\n📝 Step 4: Checking Pages (Questions)...")
if papers.data:
    # Get pages for first paper
    sample_paper = papers.data[0]
    pages = supabase.table('pages').select('*').eq('paper_id', sample_paper['id']).execute()
    
    print(f"📋 Sample Paper: {sample_paper.get('year', 'unknown')} {sample_paper.get('paper_code', 'unknown')}")
    print(f"   Pages/Questions: {len(pages.data)}")
    
    if pages.data:
        # Show first 3 questions
        for i, page in enumerate(pages.data[:3], 1):
            question_text = page.get('question_text', '')
            question_preview = question_text[:100] + "..." if len(question_text) > 100 else question_text
            print(f"\n   Question {i}:")
            print(f"   {question_preview}")
            
            # Check if it has topics
            page_topics = page.get('topics', [])
            if page_topics:
                print(f"   Topics: {', '.join(page_topics)}")
            else:
                print(f"   Topics: (none assigned)")
            
            # Check mark scheme
            ms_text = page.get('mark_scheme_text', '')
            if ms_text:
                ms_preview = ms_text[:80] + "..." if len(ms_text) > 80 else ms_text
                print(f"   Mark Scheme: {ms_preview}")
            else:
                print(f"   Mark Scheme: ❌ MISSING")
        
        if len(pages.data) > 3:
            print(f"\n   ... and {len(pages.data) - 3} more questions")
    else:
        print("   ⚠️ No pages/questions found for this paper")

# 5. Statistics
print("\n" + "="*80)
print("📊 PIPELINE STATISTICS")
print("="*80)

total_papers = len(papers.data)
total_pages = 0
pages_with_ms = 0
pages_with_topics = 0

for paper in papers.data:
    paper_pages = supabase.table('pages').select('*').eq('paper_id', paper['id']).execute()
    total_pages += len(paper_pages.data)
    
    for page in paper_pages.data:
        if page.get('mark_scheme_text'):
            pages_with_ms += 1
        if page.get('topics') and len(page['topics']) > 0:
            pages_with_topics += 1

print(f"Total Papers: {total_papers}")
print(f"Total Questions: {total_pages}")
if total_pages > 0:
    print(f"Questions with Mark Schemes: {pages_with_ms} ({pages_with_ms/total_pages*100:.1f}%)")
    print(f"Questions with Topics: {pages_with_topics} ({pages_with_topics/total_pages*100:.1f}%)")
else:
    print(f"Questions with Mark Schemes: 0 (0.0%)")
    print(f"Questions with Topics: 0 (0.0%)")

# 6. Data Quality Check
print("\n" + "="*80)
print("✅ DATA QUALITY CHECK")
print("="*80)

issues = []

if total_papers == 0:
    issues.append("No papers found for Further Pure Mathematics")

if total_pages == 0:
    issues.append("No questions found")

if total_pages > 0 and pages_with_ms < total_pages * 0.8:
    issues.append(f"Low mark scheme coverage: {pages_with_ms/total_pages*100:.1f}%")

if total_pages > 0 and pages_with_topics < total_pages * 0.5:
    issues.append(f"Low topic assignment: {pages_with_topics/total_pages*100:.1f}%")

if issues:
    print("⚠️ Issues found:")
    for issue in issues:
        print(f"   - {issue}")
else:
    print("✅ All checks passed! Pipeline is working correctly.")

# 7. Sample Data Display
print("\n" + "="*80)
print("📖 SAMPLE QUESTION WITH COMPLETE DATA")
print("="*80)

# Find a page with both question and mark scheme
complete_pages = [p for p in pages.data if p.get('question_text') and p.get('mark_scheme_text')]

if complete_pages:
    sample = complete_pages[0]
    print(f"\nPaper: {sample_paper.get('year', 'unknown')} {sample_paper.get('paper_code', 'unknown')}")
    print(f"Question Number: {sample.get('question_number', 'N/A')}")
    print(f"\nQuestion Text:")
    print(f"{sample['question_text'][:300]}...")
    print(f"\nMark Scheme:")
    print(f"{sample['mark_scheme_text'][:300]}...")
    print(f"\nTopics: {', '.join(sample.get('topics', []))}")
    print(f"Marks: {sample.get('marks_available', 'N/A')}")
else:
    print("⚠️ No complete questions found (with both question and mark scheme)")

print("\n" + "="*80)
print("🎉 VERIFICATION COMPLETE")
print("="*80)
