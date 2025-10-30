import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv('.env.local')

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Get sample pages and their paper info
pages = supabase.table('pages').select('id, question_number, qp_page_url, paper_id').limit(10).execute().data

print("📋 Sample page URLs and paper references:\n")

for page in pages[:5]:
    print(f"Page Q{page['question_number']}:")
    
    # Get paper info
    paper = supabase.table('papers').select('*').eq('id', page['paper_id']).execute().data[0]
    
    print(f"  Paper ID: {paper['id'][:8]}...")
    print(f"  Paper fields: {paper.keys()}")
    print(f"  URL: {page['qp_page_url']}")
    
    # Extract folder from URL
    if page['qp_page_url']:
        parts = page['qp_page_url'].split('/')
        folder_in_url = parts[-2] if len(parts) > 1 else "N/A"
        print(f"  Folder in URL: {folder_in_url}")
    print()
