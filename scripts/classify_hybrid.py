#!/usr/bin/env python3
"""
Hybrid Classification Runner for Physics Pages
Uses multi-pass system: Gemini → Groq → Keywords
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import requests
import fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).parent))
from hybrid_classifier import HybridClassifier

# Load environment
env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(env_path)

# Initialize Supabase
url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not service_role_key:
    service_role_key = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')

if not url or not service_role_key:
    print("❌ Missing Supabase credentials!")
    exit(1)

supabase: Client = create_client(url, service_role_key)

PHYSICS_SUBJECT_ID = '0b142517-d35d-4942-91aa-b4886aaabca3'
VALID_TOPICS = ['1', '2', '3', '4', '5', '6', '7', '8']


def is_already_classified(page_data):
    """Check if page has valid classification"""
    topics_list = page_data.get('topics', [])
    difficulty = page_data.get('difficulty')
    
    if not topics_list or not difficulty:
        return False
    
    return any(topic in VALID_TOPICS for topic in topics_list)


def download_and_extract_text(url: str) -> str:
    """Download PDF and extract text"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        doc = fitz.open(stream=response.content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        
        return text
    except Exception as e:
        return ""


def classify_paper(classifier: HybridClassifier, paper_data: dict):
    """Classify all pages from one paper"""
    paper_id = paper_data['id']
    year = paper_data['year']
    season = paper_data['season']
    paper_number = paper_data['paper_number']
    
    print(f"\n   [{paper_data.get('idx', '?')}/{paper_data.get('total', '?')}] 📄 {year} {season} Paper {paper_number}")
    
    # Get all pages for this paper
    pages_result = supabase.table('pages').select('*').eq('paper_id', paper_id).eq('is_question', True).execute()
    
    if not pages_result.data:
        print(f"      ⚠️  No pages found")
        return 0, 0
    
    # Filter out already classified
    pages_to_classify = []
    already_classified = 0
    
    for page in pages_result.data:
        if is_already_classified(page):
            already_classified += 1
        else:
            pages_to_classify.append(page)
    
    if already_classified > 0:
        print(f"      ⏭️  {already_classified} already classified")
    
    if len(pages_to_classify) == 0:
        print(f"      ✅ All pages classified")
        return already_classified, 0
    
    print(f"      🔄 Classifying {len(pages_to_classify)} pages...")
    
    # Download and extract text for all pages
    questions = []
    for page in pages_to_classify:
        text = download_and_extract_text(page['qp_page_url'])
        if text and len(text.strip()) > 20:
            questions.append({
                'number': int(page['question_number']) if page['question_number'].isdigit() else 0,
                'text': text,
                'page_id': page['id']
            })
    
    if not questions:
        print(f"      ⚠️  No text extracted")
        return already_classified, 0
    
    # Classify using hybrid approach
    classifications = classifier.classify_hybrid(questions)
    
    # Update database
    success_count = 0
    for classification in classifications:
        # Find corresponding page
        page_id = next(q['page_id'] for q in questions if q['number'] == classification.question_number)
        
        try:
            supabase.table('pages').update({
                'topics': [classification.topic],
                'difficulty': classification.difficulty
            }).eq('id', page_id).execute()
            success_count += 1
        except Exception as e:
            print(f"      ❌ DB update failed for Q{classification.question_number}: {e}")
    
    classifier.stats['total_processed'] += success_count
    
    print(f"      ✅ Classified {success_count}/{len(questions)} pages")
    return already_classified, success_count


def main():
    print("=" * 70)
    print("🚀 Hybrid Multi-Pass Classification System")
    print("=" * 70)
    print()
    
    # Initialize classifier
    print("1️⃣  Initializing hybrid classifier...")
    gemini_key = os.getenv('GEMINI_API_KEY')
    groq_key = os.getenv('GROQ_API_KEY')
    
    if not gemini_key and not groq_key:
        print("   ❌ Need at least one API key!")
        print("   Set GEMINI_API_KEY (recommended) or GROQ_API_KEY in .env.local")
        return
    
    if gemini_key:
        print("   ✅ Using Gemini 2.0 Flash (primary)")
    if groq_key:
        print("   ✅ Using Groq Llama (refinement)")
    
    classifier = HybridClassifier(gemini_key, groq_key)
    
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
    
    # Confirm
    print("\n3️⃣  Classification Strategy:")
    print("   🔹 Pass 1: Gemini bulk classification (20 questions/batch, ~2-3 min)")
    print("   🔹 Pass 2: Groq refinement for low confidence (<0.70)")
    print("   🔹 Pass 3: Keyword fallback for any failures")
    print(f"   ⏱️  Estimated time: ~10-15 minutes for {total_pages} pages")
    
    response = input("\n   Proceed? (yes/no): ").strip().lower()
    if response != 'yes':
        print("\n   ❌ Cancelled")
        return
    
    # Process papers
    print("\n4️⃣  Classifying pages...")
    total_already = 0
    total_newly = 0
    start_time = time.time()
    
    for i, paper in enumerate(papers, 1):
        paper['idx'] = i
        paper['total'] = len(papers)
        already, newly = classify_paper(classifier, paper)
        total_already += already
        total_newly += newly
        
        # Progress update every 10 papers
        if i % 10 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed * 60
            remaining = (len(papers) - i) / rate if rate > 0 else 0
            print(f"\n      ⏱️  Progress: {i}/{len(papers)} papers | {elapsed/60:.1f} min elapsed | ~{remaining:.1f} min remaining")
            stats = classifier.get_stats()
            print(f"      📊 Methods: Gemini={stats['gemini_rate']}, Groq={stats['groq_rate']}, Keywords={stats['keyword_rate']}")
    
    elapsed = time.time() - start_time
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ Classification Complete!")
    print("=" * 70)
    
    stats = classifier.get_stats()
    print(f"\n📊 Statistics:")
    print(f"   Total pages: {total_pages}")
    print(f"   Already classified: {total_already}")
    print(f"   Newly classified: {total_newly}")
    print(f"   Time elapsed: {elapsed/60:.1f} minutes")
    print(f"   Rate: {total_newly / (elapsed/60):.1f} pages/minute")
    print(f"\n📈 Classification Methods:")
    print(f"   Gemini (high quality): {stats['gemini_success']} ({stats['gemini_rate']})")
    print(f"   Groq (refinement): {stats['groq_success']} ({stats['groq_rate']})")
    print(f"   Keywords (fallback): {stats['keyword_fallback']} ({stats['keyword_rate']})")
    
    print("\n🎯 Next steps:")
    print("   1. Test worksheet generation: http://localhost:3000/generate")
    print("   2. Verify topic distribution")
    print("   3. Review low-confidence classifications if needed")
    print()


if __name__ == '__main__':
    main()
