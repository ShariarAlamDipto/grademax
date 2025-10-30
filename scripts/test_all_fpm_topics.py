import os
from supabase import create_client
from dotenv import load_dotenv
import requests

load_dotenv('.env.local')

SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

print(f"Using Supabase URL: {SUPABASE_URL[:30]}..." if SUPABASE_URL else "ERROR: No Supabase URL")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# FPM Subject ID
FPM_SUBJECT_ID = '8dea5d70-f026-4e03-bb45-053f154c6898'

# Get all topics
topics_response = supabase.table('topics').select('*').eq('subject_id', FPM_SUBJECT_ID).order('id').execute()
topics = topics_response.data

print(f"📋 Testing worksheet generation for {len(topics)} FPM topics\n")
print("=" * 80)

results = []

for i, topic in enumerate(topics, 1):
    topic_id = str(i)  # Use topic number (1-10) instead of UUID
    topic_name = topic['name']
    
    print(f"\n🧪 Testing Topic {topic_id}: {topic_name}")
    print("-" * 80)
    
    # Get pages for this topic
    pages_response = supabase.table('pages').select('*').contains('topics', [topic_id]).limit(5).execute()
    pages = pages_response.data
    
    print(f"   Found {len(pages)} sample pages")
    
    if len(pages) == 0:
        print(f"   ⚠️  No pages found for this topic")
        results.append({
            'topic_id': topic_id,
            'topic_name': topic_name,
            'status': 'NO_PAGES',
            'qp_accessible': 0,
            'ms_accessible': 0,
            'total_tested': 0
        })
        continue
    
    qp_accessible = 0
    ms_accessible = 0
    
    for i_page, page in enumerate(pages[:3], 1):  # Test first 3 pages
        qp_url = page.get('qp_page_url')
        ms_url = page.get('ms_page_url')
        
        # Extract paper info from URL if available
        paper_info = ""
        if qp_url:
            parts = qp_url.split('/')
            if len(parts) > 0:
                folder = parts[-2] if len(parts) > 1 else ""
                paper_info = folder
        
        print(f"\n   Page {i_page} (Q{page.get('question_number')} - {paper_info})")
        
        # Test QP URL
        if qp_url:
            try:
                qp_response = requests.head(qp_url, timeout=5)
                if qp_response.status_code == 200:
                    print(f"      ✅ QP accessible (200)")
                    qp_accessible += 1
                else:
                    print(f"      ❌ QP not accessible ({qp_response.status_code})")
            except Exception as e:
                print(f"      ❌ QP error: {str(e)[:50]}")
        else:
            print(f"      ⚠️  QP URL is NULL")
        
        # Test MS URL
        if ms_url:
            try:
                ms_response = requests.head(ms_url, timeout=5)
                if ms_response.status_code == 200:
                    print(f"      ✅ MS accessible (200)")
                    ms_accessible += 1
                else:
                    print(f"      ❌ MS not accessible ({ms_response.status_code})")
            except Exception as e:
                print(f"      ❌ MS error: {str(e)[:50]}")
        else:
            print(f"      ⚠️  MS URL is NULL")
    
    tested = min(len(pages), 3)
    status = 'OK' if qp_accessible == tested and ms_accessible == tested else 'PARTIAL' if qp_accessible > 0 or ms_accessible > 0 else 'FAILED'
    
    results.append({
        'topic_id': topic_id,
        'topic_name': topic_name,
        'status': status,
        'qp_accessible': qp_accessible,
        'ms_accessible': ms_accessible,
        'total_tested': tested
    })
    
    print(f"\n   📊 Result: {qp_accessible}/{tested} QP accessible, {ms_accessible}/{tested} MS accessible")

print("\n" + "=" * 80)
print("📊 SUMMARY")
print("=" * 80)

for result in results:
    status_icon = '✅' if result['status'] == 'OK' else '⚠️' if result['status'] == 'PARTIAL' else '❌'
    print(f"{status_icon} Topic {result['topic_id']}: {result['topic_name']:<30} | "
          f"QP: {result['qp_accessible']}/{result['total_tested']} | "
          f"MS: {result['ms_accessible']}/{result['total_tested']}")

ok_count = sum(1 for r in results if r['status'] == 'OK')
partial_count = sum(1 for r in results if r['status'] == 'PARTIAL')
failed_count = sum(1 for r in results if r['status'] in ['FAILED', 'NO_PAGES'])

print(f"\n📈 Overall: {ok_count} OK, {partial_count} Partial, {failed_count} Failed/No Pages")
