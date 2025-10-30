#!/usr/bin/env python3
"""
Classify Physics pages with proper topics using Gemini API
- Runs ONCE to classify all unclassified pages
- Updates the pages table with proper topic codes
- Skips pages that already have valid topic classifications
"""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import fitz  # PyMuPDF
import requests
from io import BytesIO

sys.path.insert(0, str(Path(__file__).parent))
from single_topic_classifier import SingleTopicClassifier

# Load environment
load_dotenv('.env.local')

# Initialize Supabase
url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
gemini_api_key = os.getenv('GEMINI_API_KEY')
supabase: Client = create_client(url, service_role_key)

PHYSICS_SUBJECT_ID = '0b142517-d35d-4942-91aa-b4886aaabca3'
TOPICS_YAML = Path(__file__).parent.parent / 'config' / 'physics_topics.yaml'

# Valid topic codes for Physics (1-8)
VALID_TOPICS = ['1', '2', '3', '4', '5', '6', '7', '8']


def is_already_classified(topics_list):
    """Check if page already has valid topic classification"""
    if not topics_list or len(topics_list) == 0:
        return False
    
    # Check if topics are valid (1-8, not question numbers like 10, 11, 12, etc.)
    for topic in topics_list:
        if topic in VALID_TOPICS:
            return True
    
    return False


def download_pdf_from_url(url: str) -> bytes:
    """Download PDF from storage URL"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"      ❌ Error downloading PDF: {e}")
        return None


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes"""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"      ❌ Error extracting text: {e}")
        return ""


def classify_page(classifier, page_data):
    """Classify a single page"""
    page_id = page_data['id']
    qp_url = page_data['qp_page_url']
    question_number = page_data['question_number']
    
    print(f"      📄 Question {question_number}...", end=" ", flush=True)
    
    # Download and extract text from QP
    pdf_bytes = download_pdf_from_url(qp_url)
    if not pdf_bytes:
        print("❌ Download failed")
        return None
    
    text = extract_text_from_pdf(pdf_bytes)
    if not text or len(text.strip()) < 20:
        print("⚠️  No text extracted")
        return None
    
    # Classify with Gemini
    try:
        result = classifier.classify(text, question_number)
        
        if result.page_has_question:
            print(f"✅ Topic {result.topic} ({result.difficulty}, {result.confidence:.2f})")
            return {
                'topics': [result.topic],
                'difficulty': result.difficulty
            }
        else:
            print("⚠️  No question detected")
            return None
    
    except Exception as e:
        print(f"❌ Classification error: {e}")
        return None


def classify_paper_pages(classifier, paper_data):
    """Classify all pages from one paper"""
    paper_id = paper_data['id']
    year = paper_data['year']
    season = paper_data['season']
    paper_number = paper_data['paper_number']
    
    print(f"\n   📄 {year} {season} Paper {paper_number}")
    
    # Get all pages for this paper that need classification
    pages_result = supabase.table('pages').select('*').eq('paper_id', paper_id).eq('is_question', True).execute()
    
    if not pages_result.data:
        print(f"      ⚠️  No pages found")
        return 0, 0
    
    pages_to_classify = []
    already_classified = 0
    
    for page in pages_result.data:
        if is_already_classified(page['topics']):
            already_classified += 1
        else:
            pages_to_classify.append(page)
    
    if already_classified > 0:
        print(f"      ⏭️  {already_classified} pages already classified")
    
    if len(pages_to_classify) == 0:
        print(f"      ✅ All pages already classified")
        return already_classified, 0
    
    print(f"      🔄 Classifying {len(pages_to_classify)} pages...")
    
    classified_count = 0
    for page in pages_to_classify:
        classification = classify_page(classifier, page)
        
        if classification:
            # Update database
            try:
                supabase.table('pages').update(classification).eq('id', page['id']).execute()
                classified_count += 1
            except Exception as e:
                print(f"      ❌ Database update failed: {e}")
    
    return already_classified, classified_count


def main():
    print("=" * 70)
    print("🤖 Classify Physics Pages with Gemini API")
    print("=" * 70)
    print()
    
    if not gemini_api_key:
        print("❌ GEMINI_API_KEY not found in .env.local")
        return
    
    # Initialize classifier
    print("1️⃣  Initializing classifier...")
    try:
        classifier = SingleTopicClassifier(str(TOPICS_YAML), gemini_api_key)
        print(f"   ✅ Loaded {len(classifier.topics)} topics")
    except Exception as e:
        print(f"   ❌ Error initializing classifier: {e}")
        return
    
    # Get all Physics papers
    print("\n2️⃣  Loading Physics papers...")
    papers_result = supabase.table('papers').select('*').eq('subject_id', PHYSICS_SUBJECT_ID).order('year', desc=False).order('season').execute()
    
    if not papers_result.data:
        print("   ❌ No Physics papers found")
        return
    
    papers = papers_result.data
    print(f"   ✅ Found {len(papers)} Physics papers")
    
    # Count total pages
    total_pages_result = supabase.table('pages').select('id', count='exact').in_('paper_id', [p['id'] for p in papers]).eq('is_question', True).execute()
    total_pages = total_pages_result.count
    print(f"   📊 Total pages: {total_pages}")
    
    # Confirm before proceeding
    print("\n3️⃣  Ready to classify pages")
    print(f"   ⚠️  This will use the Gemini API")
    print(f"   ⚠️  Estimated API calls: ~{total_pages - 100}")  # Rough estimate
    print(f"   ⚠️  Estimated time: ~{(total_pages * 5) // 60} minutes")
    
    response = input("\n   Proceed with classification? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("\n   ❌ Cancelled by user")
        return
    
    # Process each paper
    print("\n4️⃣  Classifying pages...")
    total_already_classified = 0
    total_newly_classified = 0
    start_time = time.time()
    
    for i, paper in enumerate(papers, 1):
        print(f"\n   [{i}/{len(papers)}]", end=" ")
        already, newly = classify_paper_pages(classifier, paper)
        total_already_classified += already
        total_newly_classified += newly
    
    elapsed = time.time() - start_time
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ Classification Complete!")
    print("=" * 70)
    print(f"\n📊 Statistics:")
    print(f"   Total pages: {total_pages}")
    print(f"   Already classified: {total_already_classified}")
    print(f"   Newly classified: {total_newly_classified}")
    print(f"   Failed/Skipped: {total_pages - total_already_classified - total_newly_classified}")
    print(f"   Time elapsed: {elapsed/60:.1f} minutes")
    print()
    print("🎯 Next steps:")
    print("   1. Test worksheet generation with Physics topics")
    print("   2. Verify topic distribution: check which topics are most common")
    print("   3. Re-run this script anytime to classify new pages")
    print()


if __name__ == '__main__':
    main()
