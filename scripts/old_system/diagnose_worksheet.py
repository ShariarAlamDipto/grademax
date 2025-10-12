"""
Check what the most recent worksheet contains
"""
from supabase_client import SupabaseClient
from dotenv import load_dotenv
import requests

load_dotenv()
db = SupabaseClient()

print("🔍 Checking most recent worksheets...\n")

# Get most recent worksheet
worksheets = db.select('worksheets', 'id,created_at,params', {}, limit=3)

if not worksheets:
    print("❌ No worksheets found!")
    exit(1)

for ws in worksheets[:1]:  # Check first one
    print(f"Worksheet: {ws['id']}")
    print(f"Created: {ws['created_at']}")
    print(f"Params: {ws.get('params', {})}")
    
    # Get items
    items = db.select(
        'worksheet_items',
        'question_id,position',
        {'worksheet_id': ws['id']}
    )
    
    print(f"\nQuestions ({len(items)} items):")
    
    for item in items[:5]:  # Check first 5
        q_id = item['question_id']
        
        # Get question details
        questions = db.select(
            'questions',
            'question_number,page_pdf_url,has_diagram',
            {'id': q_id}
        )
        
        if questions:
            q = questions[0]
            pdf_url = q.get('page_pdf_url')
            
            print(f"\n  Q{q['question_number']}:")
            print(f"    PDF URL in DB: {pdf_url or 'NULL'}")
            
            if pdf_url and not pdf_url.startswith('data'):
                # Test if accessible
                full_url = f"https://tybaetnvnfgniotdfxze.supabase.co/storage/v1/object/public/question-pdfs/{pdf_url}"
                print(f"    Full URL: {full_url}")
                
                try:
                    r = requests.head(full_url, timeout=5)
                    if r.status_code == 200:
                        size = int(r.headers.get('Content-Length', 0))
                        print(f"    Status: ✅ ACCESSIBLE ({size/1024:.1f} KB)")
                    else:
                        print(f"    Status: ❌ HTTP {r.status_code}")
                except Exception as e:
                    print(f"    Status: ❌ ERROR: {e}")
            elif pdf_url and pdf_url.startswith('data'):
                print(f"    Status: ⚠️  LOCAL PATH (not uploaded)")
            else:
                print(f"    Status: ❌ NULL")

print("\n\n💡 Diagnosis:")
print("If PDFs show NULL or local paths → Need to re-run ingestion")
print("If PDFs show 404 → Path mismatch between DB and storage")
print("If PDFs are accessible → Frontend issue with bucket name")
