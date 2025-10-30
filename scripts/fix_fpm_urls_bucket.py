"""Fix FPM page URLs to include correct bucket path"""
import os
from supabase import create_client

# Read from .env.local
def load_env():
    env_vars = {}
    with open('.env.local', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
    return env_vars

env = load_env()

supabase_url = env['NEXT_PUBLIC_SUPABASE_URL']
supabase = create_client(
    supabase_url,
    env['SUPABASE_SERVICE_ROLE_KEY']
)

# Get FPM subject
fpm_response = supabase.table('subjects').select('*').eq('code', '9FM0').execute()
fpm = fpm_response.data[0]
print(f"✅ FPM Subject: {fpm['name']} (ID: {fpm['id']})")

# Get all FPM papers
papers = supabase.table('papers')\
    .select('id, year, season, paper_number')\
    .eq('subject_id', fpm['id'])\
    .execute()

print(f"📄 Found {len(papers.data)} FPM papers")

# For each paper, update pages with correct URLs
total_updated = 0

for paper in papers.data:
    paper_id = paper['id']
    year = paper['year']
    season = paper['season']
    paper_number = paper['paper_number']
    
    # Get pages for this paper
    pages = supabase.table('pages')\
        .select('id, question_number, qp_page_url')\
        .eq('paper_id', paper_id)\
        .execute()
    
    if not pages.data:
        continue
    
    # Update each page with correct URL (add question-pdfs bucket)
    for page in pages.data:
        q_num = page['question_number']
        if not q_num:
            continue
        
        old_url = page.get('qp_page_url', '')
        
        # Check if URL needs fixing (doesn't have question-pdfs bucket)
        if old_url and '/subjects/Further_Pure_Mathematics/' in old_url and '/question-pdfs/' not in old_url:
            # Fix: Insert question-pdfs/ after /public/
            new_qp_url = old_url.replace('/public/subjects/', '/public/question-pdfs/subjects/')
            new_ms_url = new_qp_url.replace('.pdf', '_ms.pdf')
            
            # Update page
            try:
                supabase.table('pages')\
                    .update({
                        'qp_page_url': new_qp_url,
                        'ms_page_url': new_ms_url
                    })\
                    .eq('id', page['id'])\
                    .execute()
                total_updated += 1
                
                if total_updated % 50 == 0:
                    print(f"   Updated {total_updated} pages...")
            except Exception as e:
                print(f"   ❌ Error updating Q{q_num}: {str(e)[:50]}")

print(f"\n✅ Updated {total_updated} pages with correct bucket URLs")

# Verify - show sample URL
if papers.data:
    sample_page = supabase.table('pages')\
        .select('qp_page_url, ms_page_url')\
        .eq('paper_id', papers.data[0]['id'])\
        .limit(1)\
        .execute()
    
    if sample_page.data:
        print(f"\n📋 Sample URL after update:")
        print(f"   QP: {sample_page.data[0]['qp_page_url']}")
        print(f"   MS: {sample_page.data[0]['ms_page_url']}")
