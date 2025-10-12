"""
Quick script to check database tables and subjects
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv('.env.ingest')

from scripts.supabase_client import SupabaseClient

def check_database():
    print("=" * 70)
    print("📊 DATABASE STATUS CHECK")
    print("=" * 70)
    
    client = SupabaseClient()
    
    # Check subjects
    print("\n1️⃣  Checking SUBJECTS table...")
    try:
        subjects = client.select('subjects', '*')
        if subjects:
            print(f"   ✅ Found {len(subjects)} subject(s):")
            for s in subjects:
                print(f"      - {s['code']}: {s['name']}")
        else:
            print("   ⚠️  No subjects found")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Check topics
    print("\n2️⃣  Checking TOPICS table...")
    try:
        topics = client.select('topics', '*', limit=100)
        if topics:
            print(f"   ✅ Found {len(topics)} topic(s):")
            for t in topics[:8]:  # Show first 8
                print(f"      - Topic {t.get('topic_number', '?')}: {t.get('name', 'Unknown')}")
            if len(topics) > 8:
                print(f"      ... and {len(topics) - 8} more")
        else:
            print("   ⚠️  No topics found")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Check papers
    print("\n3️⃣  Checking PAPERS table...")
    try:
        papers = client.select('papers', '*')
        if papers:
            print(f"   ✅ Found {len(papers)} paper(s):")
            for p in papers[:5]:
                print(f"      - {p.get('paper_name', 'Unknown')}")
            if len(papers) > 5:
                print(f"      ... and {len(papers) - 5} more")
        else:
            print("   ⚠️  No papers found (database is empty - need to process papers)")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Check pages
    print("\n4️⃣  Checking PAGES table...")
    try:
        pages = client.select('pages', '*', limit=10)
        if pages:
            print(f"   ✅ Found page data (showing first 10)")
            print(f"   📄 Total questions available for worksheet generation")
        else:
            print("   ⚠️  No pages found (need to process papers)")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    print("\n" + "=" * 70)
    print("✅ Database check complete!")
    print("=" * 70)

if __name__ == "__main__":
    check_database()
