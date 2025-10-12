"""
Check what PDF URLs are actually in the database and test them
"""
from supabase_client import SupabaseClient
from dotenv import load_dotenv
import requests

load_dotenv()

db = SupabaseClient()

print("🔍 Checking questions with page_pdf_url...\n")

# Get questions with storage URLs
questions = db.select(
    'questions',
    'id,question_number,page_pdf_url,paper_id',
    {}
)

# Filter to those with storage URLs
storage_questions = [
    q for q in questions
    if q.get('page_pdf_url') 
    and not q['page_pdf_url'].startswith('data')
]

print(f"Found {len(storage_questions)} questions with storage URLs\n")

# Test first 5
print("Testing first 5 URLs:\n")
for q in storage_questions[:5]:
    pdf_url = q['page_pdf_url']
    full_url = db.get_public_url('question-pdfs', pdf_url)
    
    print(f"Q{q['question_number']}: {pdf_url}")
    print(f"  Full URL: {full_url}")
    
    try:
        response = requests.head(full_url, timeout=5)
        if response.status_code == 200:
            size = response.headers.get('Content-Length', '?')
            print(f"  ✅ Accessible ({int(size)/1024:.1f} KB)\n")
        elif response.status_code == 404:
            print(f"  ❌ 404 NOT FOUND\n")
        else:
            print(f"  ❌ HTTP {response.status_code}\n")
    except Exception as e:
        print(f"  ❌ Error: {e}\n")

# Show what the API would return
print("\n📊 What the generate API returns:")
print("   It should return 'pagePdfUrl' field with the relative path")
print(f"   Example: {storage_questions[0]['page_pdf_url'] if storage_questions else 'N/A'}")
