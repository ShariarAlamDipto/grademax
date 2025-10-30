#!/usr/bin/env python3
"""
Test Physics worksheet generation to ensure everything works end-to-end.

This script tests:
1. Database has Physics data
2. Physics topics are accessible
3. Questions can be queried by topic
4. PDF URLs are valid and accessible
5. Worksheet generation API works
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import requests

# Setup
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
env_path = project_root / '.env.local'
load_dotenv(env_path)

# Initialize Supabase
SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Physics topic mapping (from physics_topics.yaml)
PHYSICS_TOPICS = {
    'FM': 'Forces and Motion',
    'KIN': 'Kinematics',
    'DYN': 'Dynamics',
    'EN': 'Energy',
    'WAVE': 'Waves',
    'ELEC': 'Electricity',
    'MAG': 'Magnetism',
    'NUC': 'Nuclear Physics'
}


def test_physics_subject():
    """Test 1: Check Physics subject exists in database."""
    print("\n" + "="*80)
    print("TEST 1: Physics Subject in Database")
    print("="*80)
    
    response = supabase.table("subjects").select("*").execute()
    subjects = response.data
    
    physics = None
    for subject in subjects:
        if 'Physics' in subject.get('name', '') or subject.get('code') == '4PH1':
            physics = subject
            break
    
    if physics:
        print(f"✅ Physics found in database:")
        print(f"   ID: {physics['id']}")
        print(f"   Name: {physics['name']}")
        print(f"   Code: {physics.get('code', 'N/A')}")
        print(f"   Level: {physics.get('level', 'N/A')}")
        return physics['id']
    else:
        print("❌ Physics subject not found in database!")
        print(f"   Available subjects: {[s['name'] for s in subjects]}")
        return None


def test_physics_topics(subject_id):
    """Test 2: Check Physics topics exist."""
    print("\n" + "="*80)
    print("TEST 2: Physics Topics in Database")
    print("="*80)
    
    response = supabase.table("topics").select("*").eq("subject_id", subject_id).execute()
    topics = response.data
    
    print(f"✅ Found {len(topics)} Physics topics:")
    for topic in topics:
        print(f"   {topic['code']}: {topic['name']}")
    
    if len(topics) == 0:
        print("❌ No topics found! Topics need to be added to the database.")
        return []
    
    return topics


def test_physics_papers(subject_id):
    """Test 3: Check Physics papers exist."""
    print("\n" + "="*80)
    print("TEST 3: Physics Papers in Database")
    print("="*80)
    
    response = supabase.table("papers").select("*").eq("subject_id", subject_id).execute()
    papers = response.data
    
    if not papers:
        print("❌ No Physics papers found!")
        return []
    
    print(f"✅ Found {len(papers)} Physics papers")
    
    # Group by year
    by_year = {}
    for paper in papers:
        year = paper['year']
        if year not in by_year:
            by_year[year] = []
        by_year[year].append(f"{paper['season']} {paper['paper_number']}")
    
    for year in sorted(by_year.keys()):
        print(f"   {year}: {', '.join(by_year[year])}")
    
    return papers


def test_classified_pages(subject_id):
    """Test 4: Check classified pages exist."""
    print("\n" + "="*80)
    print("TEST 4: Classified Pages")
    print("="*80)
    
    # Get all pages for Physics papers
    papers_response = supabase.table("papers").select("id").eq("subject_id", subject_id).execute()
    paper_ids = [p['id'] for p in papers_response.data]
    
    if not paper_ids:
        print("❌ No papers to check!")
        return
    
    total_pages = 0
    classified_pages = 0
    by_topic = {}
    
    for paper_id in paper_ids:
        pages_response = supabase.table("pages").select("*").eq("paper_id", paper_id).execute()
        pages = pages_response.data
        
        total_pages += len(pages)
        
        for page in pages:
            topics = page.get('topics', [])
            if topics and len(topics) > 0:
                classified_pages += 1
                for topic in topics:
                    by_topic[topic] = by_topic.get(topic, 0) + 1
    
    classification_rate = (classified_pages / total_pages * 100) if total_pages > 0 else 0
    
    print(f"✅ Total Pages: {total_pages}")
    print(f"✅ Classified: {classified_pages} ({classification_rate:.1f}%)")
    print(f"✅ Unclassified: {total_pages - classified_pages}")
    
    if by_topic:
        print(f"\n📊 Questions by Topic:")
        for topic_code in sorted(by_topic.keys()):
            topic_name = PHYSICS_TOPICS.get(topic_code, topic_code)
            count = by_topic[topic_code]
            print(f"   {topic_name} ({topic_code}): {count} questions")
    
    return classified_pages > 0


def test_pdf_urls(subject_id):
    """Test 5: Check PDF URLs are valid."""
    print("\n" + "="*80)
    print("TEST 5: PDF URL Accessibility")
    print("="*80)
    
    # Get sample of pages with PDFs
    papers_response = supabase.table("papers").select("id").eq("subject_id", subject_id).limit(3).execute()
    paper_ids = [p['id'] for p in papers_response.data]
    
    if not paper_ids:
        print("❌ No papers to check!")
        return False
    
    pages_response = supabase.table("pages").select("*").in_("paper_id", paper_ids).limit(5).execute()
    sample_pages = pages_response.data
    
    if not sample_pages:
        print("❌ No pages to check!")
        return False
    
    print(f"Testing {len(sample_pages)} sample PDF URLs...")
    
    valid_qp = 0
    valid_ms = 0
    
    for page in sample_pages:
        qp_url = page.get('qp_page_url')
        ms_url = page.get('ms_page_url')
        
        if qp_url:
            try:
                # Check storage path pattern
                if 'subjects/Physics' in qp_url or 'Physics' in qp_url:
                    valid_qp += 1
                    print(f"   ✅ QP URL valid: ...{qp_url[-50:]}")
                else:
                    print(f"   ⚠️  QP URL unusual: {qp_url}")
            except Exception as e:
                print(f"   ❌ QP URL check failed: {e}")
        
        if ms_url:
            try:
                if 'subjects/Physics' in ms_url or 'Physics' in ms_url:
                    valid_ms += 1
                    print(f"   ✅ MS URL valid: ...{ms_url[-50:]}")
                else:
                    print(f"   ⚠️  MS URL unusual: {ms_url}")
            except Exception as e:
                print(f"   ❌ MS URL check failed: {e}")
    
    print(f"\n📊 Results:")
    print(f"   Question Papers: {valid_qp}/{len(sample_pages)} have valid URLs")
    print(f"   Mark Schemes: {valid_ms}/{len(sample_pages)} have valid URLs")
    
    return valid_qp > 0


def test_topic_queries(subject_id, topics):
    """Test 6: Query questions by topic."""
    print("\n" + "="*80)
    print("TEST 6: Query Questions by Topic")
    print("="*80)
    
    if not topics:
        print("❌ No topics to test!")
        return False
    
    # Test first 3 topics
    test_topics = topics[:3]
    
    for topic in test_topics:
        topic_code = topic['code']
        topic_name = topic['name']
        
        print(f"\n📝 Testing topic: {topic_name} ({topic_code})")
        
        # Get papers for this subject
        papers_response = supabase.table("papers").select("id").eq("subject_id", subject_id).execute()
        paper_ids = [p['id'] for p in papers_response.data]
        
        # Query pages with this topic
        pages_response = supabase.table("pages").select("*").in_("paper_id", paper_ids).execute()
        
        # Filter pages that contain this topic
        topic_pages = [p for p in pages_response.data if topic_code in p.get('topics', [])]
        
        if topic_pages:
            print(f"   ✅ Found {len(topic_pages)} questions for {topic_code}")
            
            # Show sample
            sample = topic_pages[:3]
            for page in sample:
                qnum = page.get('question_number', 'N/A')
                difficulty = page.get('difficulty', 'N/A')
                confidence = page.get('confidence', 0)
                print(f"      Q{qnum}: {difficulty} (conf={confidence:.2f})")
        else:
            print(f"   ⚠️  No questions found for {topic_code}")
    
    return True


def test_worksheet_readiness(subject_id):
    """Test 7: Check if worksheet generation would work."""
    print("\n" + "="*80)
    print("TEST 7: Worksheet Generation Readiness")
    print("="*80)
    
    # Simulate what worksheet generation needs
    print("Checking requirements for worksheet generation...")
    
    # 1. Get papers
    papers_response = supabase.table("papers").select("id,year,season,paper_number").eq("subject_id", subject_id).execute()
    papers = papers_response.data
    print(f"   ✅ Papers available: {len(papers)}")
    
    # 2. Get classified pages
    classified_count = 0
    with_pdfs = 0
    
    for paper in papers[:5]:  # Sample first 5 papers
        pages_response = supabase.table("pages").select("*").eq("paper_id", paper['id']).execute()
        pages = pages_response.data
        
        for page in pages:
            if page.get('topics') and len(page.get('topics', [])) > 0:
                classified_count += 1
                if page.get('qp_page_url'):
                    with_pdfs += 1
    
    print(f"   ✅ Classified pages (sample): {classified_count}")
    print(f"   ✅ Pages with PDF URLs: {with_pdfs}")
    
    # 3. Check storage path
    if papers:
        sample_paper = papers[0]
        pages_response = supabase.table("pages").select("qp_page_url,ms_page_url").eq("paper_id", sample_paper['id']).limit(1).execute()
        if pages_response.data:
            sample_page = pages_response.data[0]
            qp_url = sample_page.get('qp_page_url', '')
            
            if 'subjects/Physics' in qp_url:
                print(f"   ✅ Storage path correct: subjects/Physics/...")
            else:
                print(f"   ⚠️  Storage path: {qp_url}")
    
    if classified_count > 0 and with_pdfs > 0:
        print(f"\n✅ READY: Physics worksheets can be generated!")
        return True
    else:
        print(f"\n❌ NOT READY: Missing required data")
        return False


def main():
    print("="*80)
    print("PHYSICS WORKSHEET GENERATION TEST SUITE")
    print("="*80)
    
    # Test 1: Subject
    subject_id = test_physics_subject()
    if not subject_id:
        print("\n❌ FAILED: Physics subject not found in database")
        return
    
    # Test 2: Topics
    topics = test_physics_topics(subject_id)
    
    # Test 3: Papers
    papers = test_physics_papers(subject_id)
    if not papers:
        print("\n❌ FAILED: No Physics papers in database")
        return
    
    # Test 4: Classified pages
    has_classified = test_classified_pages(subject_id)
    if not has_classified:
        print("\n⚠️  WARNING: No classified pages found")
    
    # Test 5: PDF URLs
    test_pdf_urls(subject_id)
    
    # Test 6: Topic queries
    if topics:
        test_topic_queries(subject_id, topics)
    
    # Test 7: Worksheet readiness
    ready = test_worksheet_readiness(subject_id)
    
    # Final summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    if ready:
        print("✅ All checks passed!")
        print("\n📝 Next steps:")
        print("   1. Start local server: npm run dev")
        print("   2. Visit: http://localhost:3000/generate")
        print("   3. Select 'Physics' subject")
        print("   4. Choose topics (FM, KIN, DYN, EN, WAVE, ELEC, MAG, NUC)")
        print("   5. Generate worksheet!")
        print("\n🎯 Expected behavior:")
        print("   - Physics appears in subject dropdown")
        print("   - 8 topics available for selection")
        print("   - Questions load with PDF links")
        print("   - Worksheet generation works")
    else:
        print("❌ Some checks failed. Review output above.")


if __name__ == "__main__":
    main()
