#!/usr/bin/env python3
"""
Run Hybrid Classification on All Physics Pages
Uses multi-pass system for optimal speed and accuracy
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
service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
gemini_key = os.getenv('GEMINI_API_KEY')
groq_key = os.getenv('GROQ_API_KEY')

if not url or not service_key:
    print("❌ Missing Supabase credentials!")
    exit(1)

if not gemini_key and not groq_key:
    print("❌ Need at least one API key (GEMINI_API_KEY or GROQ_API_KEY)")
    exit(1)

supabase: Client = create_client(url, service_key)

PHYSICS_SUBJECT_ID = '0b142517-d35d-4942-91aa-b4886aaabca3'
VALID_TOPICS = ['1', '2', '3', '4', '5', '6', '7', '8']


def download_and_extract_text(url: str) -> str:
    """Download PDF and extract text"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        pdf_bytes = response.content
        
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        
        return text
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return ""


def is_classified(page_data):
    """Check if page is already classified"""
    topics = page_data.get('topics', [])
    difficulty = page_data.get('difficulty')
    
    if not topics or not difficulty:
        return False
    
    # Check if has valid topic codes (1-8)
    return any(t in VALID_TOPICS for t in topics)


def chunks(lst, n):
    """Split list into chunks of size n"""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def main():
    print("=" * 70)
    print("🚀 HYBRID MULTI-PASS CLASSIFIER")
    print("=" * 70)
    print()
    print("Strategy:")
    print("  Pass 1: Gemini 2.0 Flash - Bulk classification (20 q/batch, 1500 RPM)")
    print("  Pass 2: Groq Llama - Refine low confidence (<0.70)")
    print("  Pass 3: Enhanced keywords - Safety net for failures")
    print()
    
    # Initialize classifier
    print("1️⃣  Initializing hybrid classifier...")
    classifier = HybridClassifier(gemini_key, groq_key)
    print()
    
    # Load Physics papers
    print("2️⃣  Loading Physics pages...")
    papers_result = supabase.table('papers').select('*').eq('subject_id', PHYSICS_SUBJECT_ID).order('year', desc=False).order('season').execute()
    
    if not papers_result.data:
        print("   ❌ No Physics papers found")
        return
    
    papers = papers_result.data
    print(f"   ✅ Found {len(papers)} Physics papers")
    
    # Get all pages that need classification
    all_pages_result = supabase.table('pages').select('*').in_('paper_id', [p['id'] for p in papers]).eq('is_question', True).execute()
    
    all_pages = all_pages_result.data
    print(f"   📊 Total pages: {len(all_pages)}")
    
    # Filter unclassified pages
    pages_to_classify = [p for p in all_pages if not is_classified(p)]
    already_classified = len(all_pages) - len(pages_to_classify)
    
    print(f"   ✅ Already classified: {already_classified}")
    print(f"   🔄 Need classification: {len(pages_to_classify)}")
    
    if len(pages_to_classify) == 0:
        print("\n   ✅ All pages already classified!")
        return
    
    # Confirm
    print(f"\n3️⃣  Ready to classify {len(pages_to_classify)} pages")
    
    # Estimate time
    gemini_batches = len(pages_to_classify) // 20 + 1
    estimated_gemini = gemini_batches * 1.5  # 1.5 seconds per batch
    estimated_groq = len(pages_to_classify) * 0.1  # Assume 10% need refinement
    estimated_total = (estimated_gemini + estimated_groq) / 60
    
    print(f"   ⏱️  Estimated time: ~{estimated_total:.1f} minutes")
    print(f"   💰 Cost: $0 (using free tiers)")
    print()
    
    response = input("   Proceed? (yes/no): ").strip().lower()
    if response != 'yes':
        print("\n   ❌ Cancelled")
        return
    
    # Download and prepare questions
    print("\n4️⃣  Downloading PDFs and extracting text...")
    questions = []
    failed_downloads = []
    
    for i, page in enumerate(pages_to_classify):
        if (i + 1) % 50 == 0:
            print(f"   📥 Downloaded {i + 1}/{len(pages_to_classify)}...")
        
        text = download_and_extract_text(page['qp_page_url'])
        
        if text and len(text.strip()) > 20:
            questions.append({
                'page_id': page['id'],
                'number': page['question_number'],
                'text': text,
                'paper_id': page['paper_id']
            })
        else:
            failed_downloads.append(page)
    
    print(f"   ✅ Successfully extracted: {len(questions)}")
    print(f"   ❌ Failed downloads: {len(failed_downloads)}")
    
    if len(questions) == 0:
        print("\n   ❌ No questions to classify")
        return
    
    # Classify in batches
    print(f"\n5️⃣  Classifying {len(questions)} questions...")
    print()
    
    batch_size = 20  # Gemini can handle 20 per request
    total_classified = 0
    failed_classifications = []
    start_time = time.time()
    
    for i, batch in enumerate(chunks(questions, batch_size)):
        batch_num = i + 1
        total_batches = (len(questions) + batch_size - 1) // batch_size
        
        print(f"   📦 Batch {batch_num}/{total_batches} ({len(batch)} questions)")
        
        try:
            # Classify batch with hybrid approach
            results = classifier.classify_hybrid(batch)
            
            # Update database
            for result in results:
                page_id = next(q['page_id'] for q in batch if q['number'] == result.question_number)
                
                try:
                    supabase.table('pages').update({
                        'topics': [result.topic],
                        'difficulty': result.difficulty
                    }).eq('id', page_id).execute()
                    
                    total_classified += 1
                    
                    # Show confidence indicator
                    if result.confidence >= 0.80:
                        status = "✅"
                    elif result.confidence >= 0.50:
                        status = "⚠️"
                    else:
                        status = "❓"
                    
                    print(f"         Q{result.question_number}: {status} Topic {result.topic}, {result.difficulty} ({result.confidence:.2f} via {result.method})")
                    
                except Exception as e:
                    print(f"         ❌ Database update failed for Q{result.question_number}: {e}")
                    failed_classifications.append(result)
            
        except Exception as e:
            print(f"      ❌ Batch {batch_num} failed: {e}")
            failed_classifications.extend(batch)
        
        # Progress update every 5 batches
        if batch_num % 5 == 0:
            elapsed = time.time() - start_time
            rate = total_classified / elapsed if elapsed > 0 else 0
            remaining = (len(questions) - total_classified) / rate if rate > 0 else 0
            print(f"\n      ⏱️  Progress: {total_classified}/{len(questions)} | {elapsed/60:.1f}min elapsed | ~{remaining/60:.1f}min remaining\n")
    
    elapsed = time.time() - start_time
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ CLASSIFICATION COMPLETE!")
    print("=" * 70)
    print(f"\n📊 Results:")
    print(f"   Total pages: {len(all_pages)}")
    print(f"   Already classified: {already_classified}")
    print(f"   Newly classified: {total_classified}")
    print(f"   Failed: {len(failed_classifications) + len(failed_downloads)}")
    print(f"   Time elapsed: {elapsed/60:.1f} minutes")
    print(f"   Rate: {total_classified / (elapsed/60):.1f} pages/minute")
    print()
    
    # Method breakdown
    stats = classifier.get_stats()
    print(f"📈 Classification Methods:")
    print(f"   Gemini (bulk): {stats['gemini_success']} ({stats['gemini_rate']})")
    print(f"   Groq (refine): {stats['groq_success']} ({stats['groq_rate']})")
    print(f"   Keywords (fallback): {stats['keyword_fallback']} ({stats['keyword_rate']})")
    print()
    
    # Quality metrics
    high_conf = (stats['gemini_success'] + stats['groq_success'])
    total = stats['total_processed']
    quality = high_conf / total * 100 if total > 0 else 0
    print(f"🎯 Quality Metrics:")
    print(f"   High confidence (>0.7): {high_conf} ({quality:.1f}%)")
    print(f"   Low confidence (<0.7): {stats['keyword_fallback']} ({100-quality:.1f}%)")
    print()
    
    print("🎉 Next steps:")
    print("   1. Test worksheet generation at http://localhost:3000/generate")
    print("   2. Verify topic distribution is balanced")
    print("   3. Re-run anytime to classify new pages")
    print()


if __name__ == '__main__':
    main()
