#!/usr/bin/env python3
"""
Run Hybrid Classification v2.3 for Further Pure Mathematics
- Uses Groq Llama 3.1 70B
- 4000 char context for better accuracy
- FPM-specific topics (LOGS, QUAD, IDENT, GRAPHS, SERIES, BINOM, VECT, COORD, CALC, TRIG)
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

from scripts.mistral_classifier import MistralTopicClassifier


# Configuration - FURTHER PURE MATHS
SUBJECT_CODES = ["4PM1", "9FM0"]  # Canonical IGCSE code + legacy alias
SUBJECT_NAME = "Further Pure Mathematics"
VALID_TOPICS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]  # FPM has 10 topics
BATCH_SIZE = 10  # Groq batch size


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


def get_subject_id(supabase: Client) -> tuple[str, str]:
    """Resolve Further Pure Maths subject ID from canonical/legacy codes."""
    candidates = []

    for code in SUBJECT_CODES:
        response = supabase.table('subjects')\
            .select('id, code')\
            .eq('code', code)\
            .execute()

        for row in (response.data or []):
            # Prefer subjects that already have paper data attached.
            papers_resp = supabase.table('papers')\
                .select('id')\
                .eq('subject_id', row['id'])\
                .execute()
            paper_count = len(papers_resp.data or [])
            candidates.append({
                'id': row['id'],
                'code': row['code'],
                'paper_count': paper_count,
                'priority': SUBJECT_CODES.index(code)
            })

    if not candidates:
        print(f"❌ Subject codes {SUBJECT_CODES} not found in database!")
        print("   Please add Further Pure Mathematics to the subjects table.")
        exit(1)

    candidates.sort(key=lambda c: (-c['paper_count'], c['priority']))
    selected = candidates[0]
    return selected['id'], selected['code']


def get_unclassified_pages(supabase: Client, subject_id: str):
    """Get all FPM pages that need classification, organized by paper"""
    # Get all papers for FPM, ordered by year/season/paper
    papers_response = supabase.table('papers')\
        .select('id, year, season, paper_number')\
        .eq('subject_id', subject_id)\
        .order('year')\
        .order('season')\
        .order('paper_number')\
        .execute()
    
    papers = papers_response.data
    print(f"   ✅ Found {len(papers)} {SUBJECT_NAME} papers")
    
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
    
    Returns: {question_key: {'pages': [page_objs], 'combined_text': str}}
    """
    questions = {}
    
    for page in pages:
        paper = page['paper']
        q_num = page['page_number']
        
        # Create unique key for this question
        key = f"{paper['year']}_{paper['season']}_P{paper['paper_number']}_Q{q_num}"
        
        # Skip essentially blank pages
        text = page.get('text_excerpt', '') or ''
        if len(text.strip()) < 50:
            continue
        
        if key not in questions:
            questions[key] = {
                'pages': [],
                'combined_text': '',
                'paper': paper,
                'question_number': q_num
            }
        
        questions[key]['pages'].append(page)
        questions[key]['combined_text'] += '\n\n' + text
    
    return questions


def classify_page_batch(classifier: MistralTopicClassifier, pages: list, supabase: Client):
    """
    Classify a batch of pages.
    Groups pages by question (same page_number = same question with subparts),
    then applies classification to all pages of that question.
    """
    if not pages:
        return
    
    # Group pages into questions (by page_number within each paper)
    questions = group_pages_into_questions(pages)
    
    if not questions:
        print("   ⚠️  No valid questions to classify (all blank pages)")
        return
    
    print(f"   📦 Grouped {len(pages)} pages into {len(questions)} questions")
    
    # Prepare questions for classification
    all_questions = []
    for key, q_data in questions.items():
        # Truncate to 4000 chars for LLM context
        text = q_data['combined_text'][:4000]
        all_questions.append({
            'key': key,
            'text': text,
            'pages': q_data['pages'],
            'paper': q_data['paper'],
            'question_number': q_data['question_number']
        })
    
    if not all_questions:
        print("   ⚠️  No questions to classify")
        return
    
    print(f"   🤖 Classifying {len(all_questions)} questions...")
    
    # Classify each question individually
    for i, question in enumerate(all_questions):
        try:
            # Use Mistral classifier
            classification = classifier.classify(question['text'], str(question['question_number']))
            
            if classification.topic:
                print(f"   ✅ {question['key']}: {classification.topic} ({classification.confidence:.2f}) - {classification.difficulty}")
                
                # Update ALL pages of this question with the SAME classification
                for page in question['pages']:
                    update_data = {
                        'topics': [classification.topic],
                        'difficulty': classification.difficulty,
                        'confidence': classification.confidence
                    }
                    
                    try:
                        supabase.table('pages')\
                            .update(update_data)\
                            .eq('id', page['id'])\
                            .execute()
                    except Exception as e:
                        print(f"      ⚠️  Failed to update page {page['id']}: {e}")
            else:
                print(f"   ⚠️  {question['key']}: No valid topic assigned")
                
        except Exception as e:
            print(f"   ❌ {question['key']}: Classification failed - {e}")
            continue


def run_classification():
    """Main classification workflow"""
    print("\n" + "="*80)
    print(f"🔬 FURTHER PURE MATHEMATICS CLASSIFICATION v2.3")
    print("="*80)
    
    # Load environment
    load_env()
    
    # Initialize
    print("\n1️⃣  Initializing...")
    supabase = init_supabase()
    subject_id, resolved_code = get_subject_id(supabase)
    print(f"   ✅ Subject ID: {subject_id}")
    print(f"   ✅ Subject Code: {resolved_code}")
    
    # Load classifier with FPM topics
    topics_yaml = project_root / 'classification' / 'further_pure_maths_topics.yaml'
    if not topics_yaml.exists():
        print(f"❌ Classification file not found: {topics_yaml}")
        exit(1)
    
    groq_api_key = os.getenv('GROQ_API_KEY')
    if not groq_api_key:
        print("❌ GROQ_API_KEY not found in .env.local")
        exit(1)
    
    print(f"\n2️⃣  Loading classifier...")
    print(f"   📄 Topics: {topics_yaml.name}")
    classifier = MistralTopicClassifier(str(topics_yaml), groq_api_key)
    print(f"   ✅ Loaded {len(classifier.topics)} topics:")
    for topic in classifier.topics[:5]:  # Show first 5
        print(f"      • {topic['code']}: {topic['name']}")
    if len(classifier.topics) > 5:
        print(f"      ... and {len(classifier.topics) - 5} more")
    
    # Get unclassified pages
    print(f"\n3️⃣  Finding pages to classify...")
    all_pages, unclassified = get_unclassified_pages(supabase, subject_id)
    
    if not unclassified:
        print("\n✅ All pages already classified!")
        return
    
    # Process in batches
    print(f"\n4️⃣  Processing {len(unclassified)} pages in batches of {BATCH_SIZE}...")
    total_batches = (len(unclassified) + BATCH_SIZE - 1) // BATCH_SIZE
    
    start_time = time.time()
    
    for i in range(0, len(unclassified), BATCH_SIZE):
        batch = unclassified[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        
        print(f"\n   📦 Batch {batch_num}/{total_batches} ({len(batch)} pages)")
        
        try:
            classify_page_batch(classifier, batch, supabase)
        except Exception as e:
            print(f"   ❌ Batch {batch_num} failed: {e}")
            continue
        
        # Rate limiting delay (Groq allows 30 req/min for 70B model)
        if i + BATCH_SIZE < len(unclassified):
            time.sleep(2)  # 2 second delay between batches
    
    elapsed = time.time() - start_time
    
    # Summary
    print("\n" + "="*80)
    print("✅ CLASSIFICATION COMPLETE")
    print("="*80)
    print(f"   Total pages processed: {len(unclassified)}")
    print(f"   Time elapsed: {elapsed:.1f}s")
    print(f"   Average: {elapsed/len(unclassified):.2f}s per page")
    
    # Check results
    print(f"\n5️⃣  Verifying results...")
    _, still_unclassified = get_unclassified_pages(supabase, subject_id)
    
    classified_count = len(unclassified) - len(still_unclassified)
    success_rate = (classified_count / len(unclassified) * 100) if unclassified else 100
    
    print(f"   ✅ Successfully classified: {classified_count}/{len(unclassified)} ({success_rate:.1f}%)")
    
    if still_unclassified:
        print(f"   ⚠️  Still unclassified: {len(still_unclassified)}")


if __name__ == "__main__":
    try:
        run_classification()
    except KeyboardInterrupt:
        print("\n\n⚠️  Classification interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
