"""
Verify PDF URLs in database
"""
import os
from dotenv import load_dotenv
from supabase_client import SupabaseClient

load_dotenv()

db = SupabaseClient()

print("\n🔍 Checking questions in database...\n")

# Get all questions
questions = db.select('questions', 'id,question_number,page_pdf_url,ms_pdf_url', {})

if not questions:
    print("❌ No questions found in database")
    exit(1)

print(f"Found {len(questions)} questions:\n")

null_count = 0
local_path_count = 0
storage_url_count = 0

for q in questions:
    q_num = q.get('question_number')
    pdf_url = q.get('page_pdf_url')
    
    if pdf_url is None:
        print(f"❌ Q{q_num}: NULL")
        null_count += 1
    elif pdf_url.startswith('data\\') or pdf_url.startswith('data/'):
        print(f"⚠️  Q{q_num}: LOCAL PATH - {pdf_url}")
        local_path_count += 1
    else:
        # Check if accessible
        full_url = db.get_public_url('question-pdfs', pdf_url)
        print(f"✅ Q{q_num}: {pdf_url}")
        storage_url_count += 1

print(f"\n📊 Summary:")
print(f"   Storage URLs: {storage_url_count}")
print(f"   Local paths: {local_path_count}")
print(f"   NULL: {null_count}")
print(f"   Total: {len(questions)}")

if storage_url_count > 0:
    print(f"\n✅ Success! {storage_url_count} questions have storage URLs")
    
    # Show first one as example
    example = next((q for q in questions if q.get('page_pdf_url') and not q['page_pdf_url'].startswith('data')), None)
    if example:
        url = db.get_public_url('question-pdfs', example['page_pdf_url'])
        print(f"   Example: {url}")
