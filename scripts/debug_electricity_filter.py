"""
Debug script to investigate Electricity filter issue
Checks database query logic and topic configuration
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load environment
project_root = Path(__file__).parent.parent
env_path = project_root / '.env.local'
load_dotenv(env_path)

SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing Supabase credentials in .env.local")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def debug_electricity_filter():
    print("=" * 80)
    print("DEBUGGING ELECTRICITY FILTER ISSUE")
    print("=" * 80)
    
    # Step 1: Get Physics subject
    print("\n1️⃣ Getting Physics subject...")
    subject_resp = supabase.table('subjects').select('*').eq('name', 'Physics').execute()
    
    if not subject_resp.data:
        print("❌ Physics subject not found!")
        return
    
    subject = subject_resp.data[0]
    subject_id = subject['id']
    print(f"✅ Physics found: {subject['name']} (ID: {subject_id})")
    
    # Step 2: Get Electricity topic
    print("\n2️⃣ Getting Electricity topic...")
    topic_resp = supabase.table('topics').select('*').eq('subject_id', subject_id).execute()
    
    if not topic_resp.data:
        print("❌ No topics found for Physics!")
        return
    
    print(f"✅ Found {len(topic_resp.data)} topics for Physics:")
    electricity_topic = None
    for topic in topic_resp.data:
        print(f"   - {topic['topic_number']}: {topic['name']} (code: {topic.get('code', 'N/A')})")
        if 'electr' in topic['name'].lower():
            electricity_topic = topic
    
    if not electricity_topic:
        print("\n❌ No Electricity topic found!")
        return
    
    print(f"\n✅ Electricity topic: {electricity_topic['name']}")
    print(f"   Topic number: {electricity_topic['topic_number']}")
    print(f"   Code: {electricity_topic.get('code', 'N/A')}")
    
    # Step 3: Check how pages are filtered
    print("\n3️⃣ Checking page filtering methods...")
    
    # Method A: Filter by topic_number in topics array
    print("\n📊 Method A: Filter by topic_number in array")
    topic_num = electricity_topic['topic_number']
    
    # Use contains to check if topic_number is in topics array
    pages_by_number = supabase.table('pages')\
        .select('id, question_number, topics, difficulty')\
        .eq('subject_id', subject_id)\
        .contains('topics', [str(topic_num)])\
        .execute()
    
    print(f"   Results with topic_number '{topic_num}': {len(pages_by_number.data)} pages")
    if pages_by_number.data:
        print(f"   Sample: {pages_by_number.data[0]}")
    
    # Method B: Filter by code (ELEC) in topics array
    if electricity_topic.get('code'):
        print("\n📊 Method B: Filter by topic code in array")
        topic_code = electricity_topic['code']
        
        pages_by_code = supabase.table('pages')\
            .select('id, question_number, topics, difficulty')\
            .eq('subject_id', subject_id)\
            .contains('topics', [topic_code])\
            .execute()
        
        print(f"   Results with code '{topic_code}': {len(pages_by_code.data)} pages")
        if pages_by_code.data:
            print(f"   Sample: {pages_by_code.data[0]}")
    
    # Method C: Get ALL pages and check topics array manually
    print("\n📊 Method C: Manual inspection of all pages")
    all_pages = supabase.table('pages')\
        .select('id, question_number, topics, difficulty')\
        .eq('subject_id', subject_id)\
        .not_.is_('topics', 'null')\
        .execute()
    
    print(f"   Total classified pages: {len(all_pages.data)}")
    
    # Count pages with different electricity identifiers
    count_with_2 = 0
    count_with_elec = 0
    count_with_electricity = 0
    
    sample_pages_2 = []
    sample_pages_elec = []
    
    for page in all_pages.data:
        topics = page.get('topics', [])
        if topics:
            # Check for different representations
            if '2' in topics:
                count_with_2 += 1
                if len(sample_pages_2) < 3:
                    sample_pages_2.append(page)
            
            if 'ELEC' in topics:
                count_with_elec += 1
                if len(sample_pages_elec) < 3:
                    sample_pages_elec.append(page)
            
            # Check if any topic contains "electric"
            for t in topics:
                if 'electric' in str(t).lower():
                    count_with_electricity += 1
                    break
    
    print(f"\n   Pages with '2' in topics array: {count_with_2}")
    if sample_pages_2:
        print(f"   Sample: {sample_pages_2[0]}")
    
    print(f"\n   Pages with 'ELEC' in topics array: {count_with_elec}")
    if sample_pages_elec:
        print(f"   Sample: {sample_pages_elec[0]}")
    
    print(f"\n   Pages with 'electric*' in topics: {count_with_electricity}")
    
    # Step 4: Check actual topic values in database
    print("\n4️⃣ Analyzing unique topic values...")
    
    unique_topics = set()
    for page in all_pages.data:
        topics = page.get('topics', [])
        if topics:
            unique_topics.update(topics)
    
    print(f"   Total unique topic values: {len(unique_topics)}")
    print(f"   Values: {sorted(unique_topics)}")
    
    # Step 5: Check what frontend query would return
    print("\n5️⃣ Simulating frontend query...")
    print(f"   Frontend likely queries: topics.contains(['{topic_num}'])")
    print(f"   Or: topics.contains(['{electricity_topic.get('code', 'N/A')}'])")
    
    # Try both possible frontend queries
    frontend_query_1 = supabase.table('pages')\
        .select('id, question_number, topics')\
        .eq('subject_id', subject_id)\
        .contains('topics', [str(topic_num)])\
        .limit(10)\
        .execute()
    
    print(f"\n   Query by topic_number '{topic_num}': {len(frontend_query_1.data)} results")
    
    if electricity_topic.get('code'):
        frontend_query_2 = supabase.table('pages')\
            .select('id, question_number, topics')\
            .eq('subject_id', subject_id)\
            .contains('topics', [electricity_topic['code']])\
            .limit(10)\
            .execute()
        
        print(f"   Query by code '{electricity_topic['code']}': {len(frontend_query_2.data)} results")
    
    # Step 6: Recommendations
    print("\n" + "=" * 80)
    print("DIAGNOSIS & RECOMMENDATIONS")
    print("=" * 80)
    
    if count_with_elec > 0 and count_with_2 == 0:
        print("\n✅ Pages have 'ELEC' but topic is configured with number '2'")
        print("   → Frontend is filtering by number '2', but pages have 'ELEC'")
        print("   → SOLUTION: Update topic configuration to use 'ELEC' instead of '2'")
    elif count_with_2 > 0 and count_with_elec == 0:
        print("\n✅ Pages have '2' but topic might be configured differently")
        print("   → Check topic configuration in topics table")
    elif count_with_elec > 0 and count_with_2 > 0:
        print("\n⚠️  Pages have BOTH '2' and 'ELEC' - inconsistent classification!")
        print("   → Need to standardize topic codes")
    else:
        print("\n❓ Unable to find Electricity pages with expected identifiers")
        print(f"   → Check actual topic values: {sorted(unique_topics)}")

if __name__ == "__main__":
    debug_electricity_filter()
