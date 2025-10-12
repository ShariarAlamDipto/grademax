"""
Check storage bucket contents and test URLs
"""
import requests
from supabase_client import SupabaseClient
from dotenv import load_dotenv

load_dotenv()

db = SupabaseClient()

print("🔍 Checking most recent questions with storage URLs...\n")

# Get ALL questions
all_questions = db.select(
    'questions', 
    'id,question_number,page_pdf_url,created_at',
    {}
)

print(f"Total questions in DB: {len(all_questions)}\n")

# Categorize
null_count = 0
local_count = 0
storage_count = 0

storage_questions = []

for q in all_questions:
    pdf_url = q.get('page_pdf_url')
    if not pdf_url:
        null_count += 1
    elif pdf_url.startswith('data\\') or pdf_url.startswith('data/'):
        local_count += 1
    else:
        storage_count += 1
        storage_questions.append(q)

print(f"Categories:")
print(f"  NULL: {null_count}")
print(f"  Local paths: {local_count}")
print(f"  Storage URLs: {storage_count}\n")

# Group by path format
path_formats = {}
for q in storage_questions[:10]:  # Check first 10
    pdf_url = q['page_pdf_url']
    parts = pdf_url.split('/')
    format_key = f"{len(parts)} levels: {'/'.join(parts[:-1])}/..."
    
    if format_key not in path_formats:
        path_formats[format_key] = []
    path_formats[format_key].append(pdf_url)

print(f"Found {storage_count} questions with storage URLs\n")

if storage_count == 0:
    print("❌ No storage URLs found!")
    print("\nMost recent questions:")
    for q in all_questions[-5:]:
        print(f"  Q{q.get('question_number')}: {q.get('page_pdf_url', 'NULL')}")
    exit(0)

for format_key, paths in path_formats.items():
    print(f"\n📁 {format_key}")
    print(f"   Count: {len([q for q in storage_questions if q['page_pdf_url'].split('/')[:-1] == paths[0].split('/')[:-1]])}")
    
    # Test first URL in this format
    test_path = paths[0]
    full_url = db.get_public_url('question-pdfs', test_path)
    
    print(f"   Testing: {test_path}")
    
    try:
        response = requests.head(full_url, timeout=5)
        if response.status_code == 200:
            print(f"   ✅ Accessible ({response.headers.get('Content-Length', 'unknown')} bytes)")
        else:
            print(f"   ❌ HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

# Show newest format being used
if storage_questions:
    newest = storage_questions[-1]
    print(f"\n🆕 Most recent upload:")
    print(f"   Path: {newest['page_pdf_url']}")
    print(f"   URL: {db.get_public_url('question-pdfs', newest['page_pdf_url'])}")
