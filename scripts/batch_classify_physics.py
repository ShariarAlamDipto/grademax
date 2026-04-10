#!/usr/bin/env python3
"""
Batch classification runner for Physics pages using optimized Groq API
Batches 5-10 questions per API call for maximum efficiency
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import fitz  # PyMuPDF
import requests

sys.path.insert(0, str(Path(__file__).parent))
from batch_classifier import GroqBatchClassifier

# Load environment
env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(env_path)

# Initialize Supabase
url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
groq_api_key = os.getenv('GROQ_API_KEY')

if not url or not service_role_key:
    print("❌ Missing Supabase credentials!")
    exit(1)

if not groq_api_key:
    print("❌ Missing GROQ_API_KEY!")
    exit(1)

supabase: Client = create_client(url, service_role_key)

PHYSICS_SUBJECT_ID = '0b142517-d35d-4942-91aa-b4886aaabca3'
TOPICS_YAML = Path(__file__).parent.parent / 'config' / 'physics_topics.yaml'
VALID_TOPICS = ['1', '2', '3', '4', '5', '6', '7', '8']

# Batch size: 5-10 questions per request (adjust based on TPM/RPM headroom)
BATCH_SIZE = 3


def download_pdf_from_url(url: str) -> bytes:
    """Download PDF from storage URL"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content
    except Exception as e:
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
        return ""


def is_already_classified(page_data):
    """Check if page already has valid classification"""
    topics_list = page_data.get('topics', [])
    difficulty = page_data.get('difficulty')
    
    if not topics_list or not difficulty:
        return False
    
    # Check if has valid topic (not just default question number)
    return any(t in VALID_TOPICS for t in topics_list)


def main():
    print("=" * 70)
    print("🚀 Batch Classifier - Optimized for Groq Llama API")
    print("=" * 70)
    print()
    
    # Initialize batch classifier
    print("1️⃣  Initializing Groq batch classifier...")
    classifier = GroqBatchClassifier(str(TOPICS_YAML), groq_api_key)
    print(f"   ✅ Using model: {classifier.model}")
    print(f"   ✅ Batch size: {BATCH_SIZE} questions per request")
    print(f"   ✅ Rate limit aware with exponential backoff")
    print()
    
    # Load Physics papers
    print("2️⃣  Loading Physics papers...")
    papers_result = supabase.table('papers').select('*').eq('subject_id', PHYSICS_SUBJECT_ID).order('year', desc=False).order('season').execute()
    
    if not papers_result.data:
        print("   ❌ No Physics papers found")
        return
    
    papers = papers_result.data
    print(f"   ✅ Found {len(papers)} Physics papers")
    
    # Count pages needing classification
    all_pages = []
    total_already_classified = 0
    
    for paper in papers:
        pages_result = supabase.table('pages').select('*').eq('paper_id', paper['id']).eq('is_question', True).execute()
        for page in pages_result.data:
            if is_already_classified(page):
                total_already_classified += 1
            else:
                page['_paper'] = paper  # Attach paper info
                all_pages.append(page)
    
    print(f"   📊 Total pages: {len(all_pages) + total_already_classified}")
    print(f"   ✅ Already classified: {total_already_classified}")
    print(f"   🔄 Need classification: {len(all_pages)}")
    
    if not all_pages:
        print("\n✅ All pages already classified!")
        return
    
    # Confirm
    print(f"\n3️⃣  Ready to classify {len(all_pages)} pages in batches of {BATCH_SIZE}")
    print(f"   ⏱️  Estimated: ~{len(all_pages) // BATCH_SIZE + 1} API calls")
    print(f"   ⏱️  Time: ~{(len(all_pages) // BATCH_SIZE + 1) * 2 / 60:.1f} minutes")
    
    response = input("\n   Proceed? (yes/no): ").strip().lower()
    if response != 'yes':
        print("\n❌ Cancelled")
        return
    
    # Process in batches
    print("\n4️⃣  Classifying pages...")
    start_time = time.time()
    classified_count = 0
    failed_pages = []
    
    for i in range(0, len(all_pages), BATCH_SIZE):
        batch = all_pages[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(all_pages) + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"\n   📦 Batch {batch_num}/{total_batches} ({len(batch)} pages)")
        
        # Download and extract text for all pages in batch
        questions = []
        for page in batch:
            pdf_bytes = download_pdf_from_url(page['qp_page_url'])
            if not pdf_bytes:
                print(f"      ❌ Q{page['question_number']}: download failed")
                failed_pages.append(page)
                continue
            
            text = extract_text_from_pdf(pdf_bytes)
            if not text or len(text.strip()) < 20:
                print(f"      ⚠️  Q{page['question_number']}: no text")
                failed_pages.append(page)
                continue
            
            questions.append({
                'number': page['question_number'],
                'text': text,
                '_page_id': page['id']
            })
        
        if not questions:
            continue
        
        # Classify batch
        try:
            results = classifier.classify_batch(questions)
            
            # Update database
            for result in results:
                matched_q = next((q for q in questions if str(q['number']) == str(result.question_number)), None)
                if matched_q is None:
                    continue
                page_id = matched_q['_page_id']
                
                # Use primary topic (highest confidence)
                primary_topic = result.topics[0]['id'] if result.topics else '1'
                confidence = result.topics[0]['confidence'] if result.topics else 0.0
                
                update_data = {
                    'topics': [primary_topic],
                    'difficulty': result.difficulty
                }
                
                try:
                    supabase.table('pages').update(update_data).eq('id', page_id).execute()
                    classified_count += 1
                    print(f"      ✅ Q{result.question_number}: Topic {primary_topic} ({result.difficulty}, {confidence:.2f})")
                except Exception as e:
                    print(f"      ❌ Q{result.question_number}: DB update failed - {e}")
                    fp = next((p for p in batch if str(p['question_number']) == str(result.question_number)), None)
                    if fp:
                        failed_pages.append(fp)
        
        except Exception as e:
            print(f"      ❌ Batch classification failed: {str(e)[:200]}")
            failed_pages.extend([p for p in batch if any(q['number'] == p['question_number'] for q in questions)])
        
        # Show stats every 5 batches
        if batch_num % 5 == 0:
            stats = classifier.get_stats()
            elapsed = time.time() - start_time
            print(f"\n      📊 Progress: {classified_count}/{len(all_pages)} | "
                  f"Requests: {stats['total_requests']} | "
                  f"Cache hits: {stats['cache_hits']} | "
                  f"Elapsed: {elapsed/60:.1f}min")
            print(f"      ⏱️  Rate limits: {stats['remaining_requests']} req, {stats['remaining_tokens']} tokens remaining")
    
    # Retry failed pages individually
    if failed_pages:
        print(f"\n5️⃣  Retrying {len(failed_pages)} failed pages individually...")
        retry_success = 0
        
        for page in failed_pages:
            pdf_bytes = download_pdf_from_url(page['qp_page_url'])
            if not pdf_bytes:
                continue
            
            text = extract_text_from_pdf(pdf_bytes)
            if not text or len(text.strip()) < 20:
                continue
            
            try:
                results = classifier.classify_batch([{
                    'number': page['question_number'],
                    'text': text,
                    '_page_id': page['id']
                }])
                
                if results:
                    result = results[0]
                    primary_topic = result.topics[0]['id'] if result.topics else '1'
                    
                    update_data = {
                        'topics': [primary_topic],
                        'difficulty': result.difficulty
                    }
                    
                    supabase.table('pages').update(update_data).eq('id', page['id']).execute()
                    retry_success += 1
                    classified_count += 1
            except Exception:
                pass
        
        print(f"      ✅ Recovered {retry_success}/{len(failed_pages)} on retry")
    
    # Final stats
    elapsed = time.time() - start_time
    final_stats = classifier.get_stats()
    
    print("\n" + "=" * 70)
    print("✅ Batch Classification Complete!")
    print("=" * 70)
    print(f"\n📊 Results:")
    print(f"   Newly classified: {classified_count}")
    print(f"   Failed: {len(all_pages) - classified_count}")
    print(f"   Already classified: {total_already_classified}")
    print(f"   Total pages: {len(all_pages) + total_already_classified}")
    print(f"\n⚡ Efficiency:")
    print(f"   API requests: {final_stats['total_requests']}")
    print(f"   Tokens used: {final_stats['total_tokens']}")
    print(f"   Cache hits: {final_stats['cache_hits']}")
    print(f"   Questions per request: {classified_count / final_stats['total_requests']:.1f}")
    print(f"   Time elapsed: {elapsed/60:.1f} minutes")
    print(f"   Rate: {classified_count / (elapsed/60):.1f} pages/minute")
    print()


if __name__ == '__main__':
    main()
