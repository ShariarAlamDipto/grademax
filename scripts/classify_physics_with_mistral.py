#!/usr/bin/env python3
"""
Classify Physics pages with proper topics using Local LM Studio
Connects to http://127.0.0.1:1234
- Runs ONCE to classify all unclassified pages
- Updates the pages table with proper topic codes
- Skips pages that already have valid topic classifications
- Uses local model for faster, unlimited processing
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

sys.path.insert(0, str(Path(__file__).parent))
from mistral_classifier import MistralTopicClassifier

# Load environment
env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(env_path)

# Initialize Supabase
url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')  
# Try anon key if service role fails
if not service_role_key:
    service_role_key = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
groq_api_key = os.getenv('GROQ_API_KEY')

# Debug: Check if keys are loaded
if not url or not service_role_key:
    print(f"❌ Missing Supabase credentials!")
    print(f"URL: {'✅' if url else '❌ Missing'}")
    print(f"Service Key: {'✅' if service_role_key else '❌ Missing'}")
    exit(1)

supabase: Client = create_client(url, service_role_key)

PHYSICS_SUBJECT_ID = '0b142517-d35d-4942-91aa-b4886aaabca3'
TOPICS_YAML = Path(__file__).parent.parent / 'config' / 'physics_topics.yaml'

# Valid topic codes for Physics (1-8)
VALID_TOPICS = ['1', '2', '3', '4', '5', '6', '7', '8']


def is_already_classified(page_data):
    """Check if page already has valid topic classification"""
    topics_list = page_data.get('topics', [])
    difficulty = page_data.get('difficulty')
    
    # Must have both valid topics AND difficulty to be considered classified
    if not topics_list or len(topics_list) == 0:
        return False
    
    if not difficulty:
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


def classify_page(classifier, page_data, max_retries=3):
    """Classify a single page with retry logic"""
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
    
    # Classify with retry logic
    for attempt in range(max_retries):
        try:
            result = classifier.classify(text, question_number)
            
            if result.page_has_question:
                retry_indicator = f" (retry {attempt + 1})" if attempt > 0 else ""
                print(f"✅ Topic {result.topic} ({result.difficulty}, {result.confidence:.2f}){retry_indicator}")
                return {
                    'topics': [result.topic],
                    'difficulty': result.difficulty
                }
            else:
                print("⚠️  No question detected")
                return None
        
        except Exception as e:
            error_msg = str(e).lower()
            is_timeout = 'timeout' in error_msg or 'timed out' in error_msg
            is_rate_limit = 'rate limit' in error_msg or '429' in error_msg
            
            if attempt < max_retries - 1:
                # Special handling for rate limits
                if is_rate_limit:
                    wait_time = 60  # Wait full minute for rate limit
                    print(f"⏳ Rate limit (attempt {attempt + 1}), waiting {wait_time}s...", end=" ", flush=True)
                elif is_timeout:
                    wait_time = 2 ** (attempt + 1)  # Exponential backoff: 2s, 4s, 8s
                    print(f"⏱️  Timeout (attempt {attempt + 1}), retrying in {wait_time}s...", end=" ", flush=True)
                else:
                    wait_time = 2 ** (attempt + 1)
                    print(f"⚠️  Attempt {attempt + 1} failed, retrying in {wait_time}s...", end=" ", flush=True)
                time.sleep(wait_time)
            else:
                print(f"❌ Classification error: {e}")
                # Don't return None - let it fall through to keyword fallback
                return None
    
    return None


def classify_paper_pages(classifier, paper_data):
    """Classify all pages from one paper - returns (already_classified, newly_classified, failed_pages)"""
    paper_id = paper_data['id']
    year = paper_data['year']
    season = paper_data['season']
    paper_number = paper_data['paper_number']
    
    print(f"\n   📄 {year} {season} Paper {paper_number}")
    
    # Get all pages for this paper that need classification
    pages_result = supabase.table('pages').select('*').eq('paper_id', paper_id).eq('is_question', True).execute()
    
    if not pages_result.data:
        print(f"      ⚠️  No pages found")
        return 0, 0, []
    
    pages_to_classify = []
    already_classified = 0
    
    for page in pages_result.data:
        if is_already_classified(page):
            already_classified += 1
        else:
            pages_to_classify.append(page)
    
    if already_classified > 0:
        print(f"      ⏭️  {already_classified} pages already classified")
    
    if len(pages_to_classify) == 0:
        print(f"      ✅ All pages already classified")
        return already_classified, 0, []
    
    print(f"      🔄 Classifying {len(pages_to_classify)} pages...")
    
    classified_count = 0
    failed_pages = []
    
    for page in pages_to_classify:
        classification = classify_page(classifier, page)
        
        if classification:
            # Update database
            try:
                supabase.table('pages').update(classification).eq('id', page['id']).execute()
                classified_count += 1
            except Exception as e:
                print(f"      ❌ Database update failed: {e}")
                failed_pages.append(page)
        else:
            # Classification failed - add to retry list
            failed_pages.append(page)
        
        # Minimal delay between requests (rate limiting handled in classifier)
        time.sleep(0.1)
    
    return already_classified, classified_count, failed_pages


def main():
    print("=" * 70)
    print("Classify Physics Pages with Groq API")
    print("=" * 70)
    print()
    
    # Initialize classifier
    print("1️⃣  Initializing Groq/Llama classifier...")

    try:
        model_name = "llama-3.1-8b-instant"
        classifier = MistralTopicClassifier(str(TOPICS_YAML), groq_api_key, model_name=model_name)
        print(f"   ✅ Loaded {len(classifier.topics)} topics")
        print(f"   ✅ Using model: {classifier.model}")
        print(f"   ✅ API endpoint: {classifier.api_url}")
        classifier.min_delay = 0.1  # Groq is very fast
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
    print(f"   🔗 Using Groq API (Llama 3.1 8B Instant)")
    print(f"   ⚡ Very fast inference with generous rate limits")
    print(f"   ⏱️  Estimated time: ~{(total_pages * 0.2) // 60} minutes (~0.2s per page)")
    
    response = input("\n   Proceed with classification? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("\n   ❌ Cancelled by user")
        return
    
    # Process each paper
    print("\n4️⃣  Classifying pages...")
    total_already_classified = 0
    total_newly_classified = 0
    failed_pages = []  # Track failed classifications for retry
    start_time = time.time()
    
    for i, paper in enumerate(papers, 1):
        print(f"\n   [{i}/{len(papers)}]", end=" ")
        already, newly, failed = classify_paper_pages(classifier, paper)
        total_already_classified += already
        total_newly_classified += newly
        failed_pages.extend(failed)
        
        # Show progress every 10 papers
        if i % 10 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed * 60  # papers per minute
            remaining = (len(papers) - i) / rate if rate > 0 else 0
            print(f"\n      ⏱️  Progress: {i}/{len(papers)} papers | {elapsed/60:.1f} min elapsed | ~{remaining:.1f} min remaining")
    
    # Retry failed classifications
    if failed_pages:
        print(f"\n5️⃣  Retrying {len(failed_pages)} failed classifications...")
        retry_success = 0
        for page in failed_pages:
            classification = classify_page(classifier, page, max_retries=2)
            if classification:
                try:
                    supabase.table('pages').update(classification).eq('id', page['id']).execute()
                    retry_success += 1
                    total_newly_classified += 1
                except Exception as e:
                    print(f"\n      ❌ Database update failed: {e}")
        
        print(f"      ✅ Successfully classified {retry_success}/{len(failed_pages)} on retry")
    
    elapsed = time.time() - start_time
    total_failed = total_pages - total_already_classified - total_newly_classified
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ Classification Complete!")
    print("=" * 70)
    print(f"\n📊 Statistics:")
    print(f"   Total pages: {total_pages}")
    print(f"   Already classified: {total_already_classified}")
    print(f"   Newly classified: {total_newly_classified}")
    print(f"   Failed/Skipped: {total_failed}")
    print(f"   Time elapsed: {elapsed/60:.1f} minutes")
    print(f"   Rate: {total_newly_classified / (elapsed/60):.1f} pages/minute")
    print()
    print("🎯 Next steps:")
    print("   1. Test worksheet generation with Physics topics")
    print("   2. Verify topic distribution: check which topics are most common")
    print("   3. Re-run this script anytime to classify new pages")
    print()


if __name__ == '__main__':
    main()
