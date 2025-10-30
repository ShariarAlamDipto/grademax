#!/usr/bin/env python3
"""
Run Hybrid Classification v2.3 for Physics
- Uses Groq Llama 3.1 70B (no Gemini)
- 4000 char context for better accuracy
- Disambiguation rules applied
- Better handling of incomplete questions
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.hybrid_classifier_v23 import HybridClassifierV23, Classification


# Configuration
SUBJECT_ID = "0b142517-d35d-4942-91aa-b4886aaabca3"  # Physics UUID (correct)
VALID_TOPICS = ["1", "2", "3", "4", "5", "6", "7", "8"]
BATCH_SIZE = 10  # Groq batch size (smaller for 70B model)


def load_env():
    """Load environment variables"""
    env_path = project_root / '.env.local'
    if not env_path.exists():
        print("❌ .env.local not found!")
        exit(1)
    load_dotenv(env_path)


def init_supabase() -> Client:
    """Initialize Supabase client"""
    url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not url or not key:
        print("❌ Missing Supabase credentials in .env.local")
        exit(1)
    
    return create_client(url, key)


def get_unclassified_pages(supabase: Client):
    """Get all Physics pages that need classification, organized by paper"""
    # Get all papers for Physics, ordered by year/season/paper
    papers_response = supabase.table('papers')\
        .select('id, year, season, paper_number')\
        .eq('subject_id', SUBJECT_ID)\
        .order('year')\
        .order('season')\
        .order('paper_number')\
        .execute()
    
    papers = papers_response.data
    print(f"   ✅ Found {len(papers)} Physics papers")
    
    # Get all pages organized by paper, in sequential order
    all_pages = []
    for paper in papers:
        pages_response = supabase.table('pages')\
            .select('id, page_number, text_excerpt, topics, difficulty, confidence')\
            .eq('paper_id', paper['id'])\
            .order('page_number')\
            .execute()
        
        for page in pages_response.data:
            page['paper'] = paper
            all_pages.append(page)
    
    print(f"   📊 Total pages: {len(all_pages)}")
    
    # Filter unclassified (topics is null, empty, or just question number)
    unclassified = []
    for page in all_pages:
        topics = page.get('topics', [])
        page_num_str = str(page.get('page_number', 0))
        # Unclassified if: no topics, or topics = [page_number]
        if not topics or topics == [page_num_str]:
            unclassified.append(page)
    
    print(f"   ✅ Already classified: {len(all_pages) - len(unclassified)}")
    print(f"   🔄 Need classification: {len(unclassified)}")
    
    return all_pages, unclassified


def group_pages_into_questions(pages: list) -> dict:
    """
    Group pages by question number.
    Multiple pages with same page_number = ONE complete question with subparts.
    Combine all text from pages of the same question.
    Skip blank pages (< 50 chars).
    
    Returns: Dict[question_number, {'pages': [...], 'combined_text': str}]
    """
    from collections import defaultdict
    
    questions = defaultdict(lambda: {'pages': [], 'combined_text': ''})
    
    for page in pages:
        q_num = page.get('page_number')
        text = page.get('text_excerpt', '').strip()
        
        # Skip blank pages
        if len(text) < 50:
            continue
        
        questions[q_num]['pages'].append(page)
        questions[q_num]['combined_text'] += f" {text}"
    
    # Clean up combined text
    for q_num in questions:
        questions[q_num]['combined_text'] = questions[q_num]['combined_text'].strip()
    
    return questions


def classify_page_batch(classifier: HybridClassifierV23, pages: list, supabase: Client):
    """
    Classify a batch of pages.
    Groups pages by question number, combines text, classifies once per complete question,
    then applies classification to all pages of that question.
    """
    results_summary = {
        'classified': 0,
        'failed': 0,
        'high_confidence': 0,
        'low_confidence': 0
    }
    
    # Group pages by question number
    questions = group_pages_into_questions(pages)
    
    if not questions:
        print(f"      ⚠️  No valid questions found (all pages blank < 50 chars)")
        return results_summary
    
    # Prepare questions for classification
    all_questions = []
    question_counter = 1
    
    for q_num in sorted(questions.keys()):
        q_data = questions[q_num]
        
        question = {
            'number': question_counter,  # Sequential for Groq (1, 2, 3...)
            'text': q_data['combined_text'],
            'actual_question_number': q_num,  # Real Q# from paper
            'pages': q_data['pages']  # All pages for this question
        }
        
        all_questions.append(question)
        question_counter += 1
    
    # Classify all questions together
    print(f"      📦 Classifying {len(all_questions)} complete questions from {len(pages)} pages...")
    print(f"          (Questions: {sorted(questions.keys())})")
    classifications = classifier.classify_hybrid(all_questions)
    
    # Apply classification to ALL pages of each question
    for i, classification in enumerate(classifications):
        question = all_questions[i]
        pages_for_this_question = question['pages']
        
        try:
            # Update ALL pages of this question with the SAME classification
            for page in pages_for_this_question:
                topics = [classification.topic]
                difficulties = [classification.difficulty]
                confidences = [classification.confidence]
                
                # Get existing classifications
                existing_topics = page.get('topics') or []
                
                # Combine (take most common topic)
                from collections import Counter
                all_topics = existing_topics + topics
                final_topic = Counter(all_topics).most_common(1)[0][0] if all_topics else topics[0]
                
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
                final_difficulty = Counter(difficulties).most_common(1)[0][0] if difficulties else 'medium'
                
                # Update page
                supabase.table('pages').update({
                    'topics': [final_topic],
                    'difficulty': final_difficulty,
                    'confidence': round(avg_confidence, 2)
                }).eq('id', page['id']).execute()
                
                results_summary['classified'] += 1
                if avg_confidence >= 0.8:
                    results_summary['high_confidence'] += 1
                else:
                    results_summary['low_confidence'] += 1
                
                print(f"         ✅ Q{question['actual_question_number']} (Page ID {page['id']}): Topic {final_topic}, {final_difficulty} ({avg_confidence:.2f})")
                    
        except Exception as e:
            print(f"         ❌ Error updating Q{question['actual_question_number']}: {e}")
            results_summary['failed'] += 1
    
    return results_summary


def main():
    print("=" * 70)
    print("🎯 HIGH ACCURACY CLASSIFIER v2.3 - Groq Edition")
    print("=" * 70)
    print()
    
    # Setup
    load_env()
    
    # Check for OpenRouter API key first, fallback to Groq
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    groq_key = os.getenv('GROQ_API_KEY')
    
    if not groq_key:
        print("❌ Missing GROQ_API_KEY in .env.local")
        exit(1)
    
    print("Strategy:")
    print("  🎯 HIGH ACCURACY MODE: Groq Llama 4 Scout 17B")
    print("  📊 One question at a time for maximum accuracy")
    print("  📝 FULL question text (no truncation)")
    print("  ⏱️  Rate Limit: 30 RPM / 1K RPD (2.5 sec delay)")
    print("  Note: Each PAGE = ONE QUESTION (Q1, Q2, Q3...)")
    print()
    
    print("1️⃣  Initializing v2.3 classifier...")
    classifier = HybridClassifierV23(groq_key)
    
    print("\n2️⃣  Loading Physics pages...")
    supabase = init_supabase()
    all_pages, unclassified = get_unclassified_pages(supabase)
    
    if not unclassified:
        print("\n   ✅ All pages already classified!")
        return
    
    print(f"\n3️⃣  Classifying {len(unclassified)} pages...")
    print()
    
    start_time = time.time()
    total_results = {
        'classified': 0,
        'failed': 0,
        'high_confidence': 0,
        'low_confidence': 0
    }
    
    # Process in batches
    current_paper_id = None
    for i in range(0, len(unclassified), BATCH_SIZE):
        batch = unclassified[i:i+BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(unclassified) + BATCH_SIZE - 1) // BATCH_SIZE
        
        # Show paper info if we're starting a new paper
        if batch and batch[0].get('paper'):
            paper = batch[0]['paper']
            if paper['id'] != current_paper_id:
                current_paper_id = paper['id']
                print(f"\n   📄 Paper: {paper['year']} {paper['season']} Paper {paper['paper_number']}")
        
        print(f"   📦 Batch {batch_num}/{total_batches} ({len(batch)} pages)")
        
        batch_results = classify_page_batch(classifier, batch, supabase)
        
        # Update totals
        for key in total_results:
            total_results[key] += batch_results[key]
        
        # Progress update
        elapsed = time.time() - start_time
        pages_done = min(i + BATCH_SIZE, len(unclassified))
        rate = pages_done / elapsed if elapsed > 0 else 0
        remaining = (len(unclassified) - pages_done) / rate if rate > 0 else 0
        
        print()
        print(f"      ⏱️  Progress: {pages_done}/{len(unclassified)} | {elapsed/60:.1f}min elapsed | ~{remaining/60:.1f}min remaining")
        print()
    
    # Final summary
    elapsed = time.time() - start_time
    
    print("=" * 70)
    print("✅ CLASSIFICATION COMPLETE!")
    print("=" * 70)
    print()
    print("📊 Results:")
    print(f"   Total pages: {len(all_pages)}")
    print(f"   Already classified: {len(all_pages) - len(unclassified)}")
    print(f"   Newly classified: {total_results['classified']}")
    print(f"   Failed: {total_results['failed']}")
    print(f"   Time elapsed: {elapsed/60:.1f} minutes")
    print(f"   Rate: {total_results['classified'] / (elapsed/60):.1f} pages/minute")
    print()
    print("📈 Classification Quality:")
    print(f"   High confidence (>0.7): {total_results['high_confidence']} ({total_results['high_confidence']/max(1,total_results['classified'])*100:.1f}%)")
    print(f"   Low confidence (<0.7): {total_results['low_confidence']} ({total_results['low_confidence']/max(1,total_results['classified'])*100:.1f}%)")
    print()
    print("🎯 Quality Metrics:")
    stats = classifier.get_stats()
    print(f"   Keywords: {stats['keyword_success']} ({stats['keyword_rate']})")
    print(f"   Groq refined: {stats['groq_refine_success']} ({stats['groq_refine_rate']})")
    print(f"   Groq failed: {stats['groq_refine_failed']} ({stats['groq_failed_rate']})")
    print()
    print("🎉 Next steps:")
    print("   1. Run: python scripts/analyze_classifications.py")
    print("   2. Test worksheet generation at http://localhost:3000/generate")
    print("   3. Review low-confidence classifications if needed")


if __name__ == "__main__":
    main()
