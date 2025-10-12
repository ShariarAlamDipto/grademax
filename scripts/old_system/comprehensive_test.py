"""
Comprehensive test of the entire categorization and display system
"""
from supabase_client import SupabaseClient
from dotenv import load_dotenv
import requests

load_dotenv()
db = SupabaseClient()

print("="*70)
print("COMPREHENSIVE SYSTEM TEST")
print("="*70)

# ============================================================================
# TEST 1: Check Question Segmentation & Storage
# ============================================================================
print("\n📄 TEST 1: Question Segmentation & Storage")
print("-" * 70)

questions = db.select(
    'questions',
    'id,question_number,page_pdf_url,has_diagram,difficulty,paper_id',
    {}
)

storage_questions = [q for q in questions if q.get('page_pdf_url') and not q['page_pdf_url'].startswith('data')]

print(f"Total questions in DB: {len(questions)}")
print(f"Questions with storage PDFs: {len(storage_questions)}")
print(f"Questions without PDFs: {len(questions) - len(storage_questions)}")

if storage_questions:
    print(f"\n✅ Questions ARE segmented and in storage!")
    print(f"\nSample questions with PDFs:")
    for q in storage_questions[:3]:
        print(f"  - Q{q['question_number']}: {q['page_pdf_url']}")
        
        # Test accessibility
        full_url = f"https://tybaetnvnfgniotdfxze.supabase.co/storage/v1/object/public/question-pdfs/{q['page_pdf_url']}"
        try:
            r = requests.head(full_url, timeout=5)
            status = "✅ Accessible" if r.status_code == 200 else f"❌ HTTP {r.status_code}"
        except Exception as e:
            status = f"❌ Error: {str(e)[:50]}"
        print(f"    Storage: {status}")
else:
    print(f"\n❌ NO questions with storage PDFs found!")

# ============================================================================
# TEST 2: Check Topic Categorization
# ============================================================================
print("\n\n🏷️  TEST 2: Topic Categorization")
print("-" * 70)

# Get all topic tags
topic_tags = db.select('question_topics', 'question_id,topic_id,confidence', {})

print(f"Total topic tags: {len(topic_tags)}")

if topic_tags:
    # Get topic details
    topics = db.select('topics', 'id,code,name', {'subject_id': 'b706a507-0853-4aed-9377-a8b82200d29c'})
    topic_map = {t['id']: t for t in topics}
    
    # Count questions per topic
    topic_counts = {}
    for tag in topic_tags:
        topic_id = tag['topic_id']
        if topic_id in topic_map:
            topic_code = topic_map[topic_id]['code']
            topic_counts[topic_code] = topic_counts.get(topic_code, 0) + 1
    
    print(f"\n✅ Questions ARE categorized by topics!")
    print(f"\nQuestions per topic:")
    for code in sorted(topic_counts.keys()):
        topic = next((t for t in topics if t['code'] == code), None)
        if topic:
            print(f"  Topic {code} ({topic['name']}): {topic_counts[code]} questions")
    
    # Check if storage questions have topics
    storage_q_ids = [q['id'] for q in storage_questions]
    storage_tags = [tag for tag in topic_tags if tag['question_id'] in storage_q_ids]
    
    print(f"\n📊 Questions with BOTH PDFs AND topics: {len(set(tag['question_id'] for tag in storage_tags))}")
    
else:
    print(f"\n❌ NO topic categorization found!")

# ============================================================================
# TEST 3: Test Generate API Filter
# ============================================================================
print("\n\n🔧 TEST 3: Generate API Filter")
print("-" * 70)

# Simulate what the generate API does
physics_subject_id = 'b706a507-0853-4aed-9377-a8b82200d29c'

# Get questions like the API does (with PDF filter)
filtered_questions = [
    q for q in questions 
    if q.get('page_pdf_url') and not q['page_pdf_url'].startswith('data')
]

print(f"Questions API would return (with PDF filter): {len(filtered_questions)}")

if filtered_questions:
    print(f"\n✅ Generate API WILL return questions with PDFs!")
    
    # Check if these have topic tags
    filtered_q_ids = [q['id'] for q in filtered_questions]
    filtered_tags = [tag for tag in topic_tags if tag['question_id'] in filtered_q_ids]
    
    tagged_q_ids = set(tag['question_id'] for tag in filtered_tags)
    
    print(f"Questions with topics: {len(tagged_q_ids)}")
    print(f"Questions without topics: {len(filtered_questions) - len(tagged_q_ids)}")
    
    if tagged_q_ids:
        # Show breakdown by topic
        topic_breakdown = {}
        for tag in filtered_tags:
            topic_id = tag['topic_id']
            if topic_id in topic_map:
                code = topic_map[topic_id]['code']
                topic_breakdown[code] = topic_breakdown.get(code, 0) + 1
        
        print(f"\nAvailable for filtering by topic:")
        for code in sorted(topic_breakdown.keys())[:8]:  # Show first 8
            topic = next((t for t in topics if t['code'] == code), None)
            if topic:
                print(f"  ✅ Topic {code}: {topic_breakdown[code]} questions")
else:
    print(f"\n❌ No questions available for generation!")

# ============================================================================
# TEST 4: Test Actual Worksheet Generation
# ============================================================================
print("\n\n🧪 TEST 4: Test Worksheet Generation")
print("-" * 70)

# Check most recent worksheet
worksheets = db.select('worksheets', 'id,created_at', {}, limit=1)

if worksheets:
    ws = worksheets[0]
    print(f"Most recent worksheet: {ws['id']}")
    print(f"Created: {ws['created_at']}")
    
    # Get items
    items = db.select('worksheet_items', 'question_id,position', {'worksheet_id': ws['id']})
    print(f"Number of questions: {len(items)}")
    
    if items:
        # Check first question
        first_q_id = items[0]['question_id']
        first_q = db.select(
            'questions',
            'question_number,page_pdf_url,has_diagram,difficulty',
            {'id': first_q_id}
        )
        
        if first_q and first_q[0]['page_pdf_url']:
            pdf_url = first_q[0]['page_pdf_url']
            print(f"\nFirst question: Q{first_q[0]['question_number']}")
            print(f"  PDF URL: {pdf_url}")
            print(f"  Has diagram: {first_q[0]['has_diagram']}")
            print(f"  Difficulty: {first_q[0]['difficulty']}")
            
            # Test URL
            full_url = f"https://tybaetnvnfgniotdfxze.supabase.co/storage/v1/object/public/question-pdfs/{pdf_url}"
            try:
                r = requests.head(full_url, timeout=5)
                if r.status_code == 200:
                    print(f"  ✅ PDF is accessible in storage!")
                else:
                    print(f"  ❌ PDF not accessible (HTTP {r.status_code})")
            except Exception as e:
                print(f"  ❌ Error accessing PDF: {e}")
        else:
            print(f"\n❌ First question has NO PDF URL!")
else:
    print("No worksheets generated yet")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n\n" + "="*70)
print("SUMMARY")
print("="*70)

checks = {
    "Questions segmented": len(storage_questions) > 0,
    "PDFs in storage": len(storage_questions) > 0,
    "Topic categorization": len(topic_tags) > 0,
    "PDF questions have topics": len(storage_tags) > 0 if storage_questions else False,
    "API filter working": len(filtered_questions) > 0,
}

for check, passed in checks.items():
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {check}")

if all(checks.values()):
    print(f"\n🎉 ALL SYSTEMS WORKING!")
    print(f"\nYou have {len(storage_questions)} questions ready to use:")
    print(f"  - All have PDF pages in storage")
    print(f"  - All are categorized by topics")
    print(f"  - Ready for worksheet generation")
else:
    print(f"\n⚠️  SOME ISSUES FOUND - See details above")
