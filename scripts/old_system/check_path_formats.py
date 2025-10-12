"""
Check which path formats are in the database
"""
from supabase_client import SupabaseClient
from dotenv import load_dotenv

load_dotenv()

db = SupabaseClient()

questions = db.select('questions', 'id,question_number,page_pdf_url,paper_id', {})

# Group by path format
formats = {}

for q in questions:
    pdf_url = q.get('page_pdf_url')
    
    if not pdf_url or pdf_url.startswith('data'):
        format_key = "NULL or local"
    elif pdf_url.startswith('papers/'):
        format_key = "papers/"
    elif '/' in pdf_url:
        parts = pdf_url.split('/')
        format_key = f"{len(parts)} levels ({parts[0]}/...)"
    else:
        format_key = "other"
    
    if format_key not in formats:
        formats[format_key] = []
    formats[format_key].append(q)

print("📊 Path formats in database:\n")

for format_key, questions_list in formats.items():
    print(f"{format_key}: {len(questions_list)} questions")
    if questions_list and questions_list[0].get('page_pdf_url'):
        print(f"  Example: {questions_list[0]['page_pdf_url']}")
    print()

# Check the most recent worksheet
worksheets = db.select('worksheets', 'id,created_at', {}, limit=1)

if worksheets:
    ws_id = worksheets[0]['id']
    print(f"\n🔍 Checking most recent worksheet: {ws_id}")
    
    # Get worksheet items
    items = db.select(
        'worksheet_items',
        'question_id,position',
        {'worksheet_id': ws_id}
    )
    
    if items:
        print(f"   Has {len(items)} items")
        
        # Get first question details
        first_q_id = items[0]['question_id']
        first_q = db.select('questions', 'question_number,page_pdf_url', {'id': first_q_id})
        
        if first_q:
            print(f"   First question: Q{first_q[0]['question_number']}")
            print(f"   PDF URL: {first_q[0].get('page_pdf_url', 'NULL')}")
