import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv('.env.local')

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Get all subjects
subjects = supabase.table('subjects').select('*').execute()

print("📚 Subjects in database:\n")
for subject in subjects.data:
    print(f"  - {subject['name']}")
    print(f"    Code: {subject['code']}")
    print(f"    ID: {subject['id']}")
    
    # Get paper count
    papers = supabase.table('papers').select('id').eq('subject_id', subject['id']).execute()
    print(f"    Papers: {len(papers.data)}")
    
    # Get page count
    if papers.data:
        page_count = 0
        for paper in papers.data:
            pages = supabase.table('pages').select('id').eq('paper_id', paper['id']).execute()
            page_count += len(pages.data)
        print(f"    Pages: {page_count}")
    print()
