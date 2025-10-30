"""Update FPM pages with correct storage URLs"""
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

# For each paper, update pages with URLs
total_updated = 0
total_pages = 0

for paper in papers.data:
    paper_id = paper['id']
    year = paper['year']
    season = paper['season']
    paper_number = paper['paper_number']
    
    # Get pages for this paper that don't have URLs
    pages = supabase.table('pages')\
        .select('id, question_number')\
        .eq('paper_id', paper_id)\
        .is_('qp_page_url', 'null')\
        .execute()
    
    if not pages.data:
        continue
    
    total_pages += len(pages.data)
    
    # Update each page with URL
    for page in pages.data:
        q_num = page['question_number']
        if not q_num:
            continue
        
        # Construct URLs based on the pattern we saw
        # Format: subjects/Further_Pure_Mathematics/pages/{year}_{season}_Paper{number}/q{num}.pdf
        folder_name = f"{year}_{season}_Paper{paper_number}"
        qp_url = f"{supabase_url}/storage/v1/object/public/subjects/Further_Pure_Mathematics/pages/{folder_name}/q{q_num}.pdf"
        ms_url = f"{supabase_url}/storage/v1/object/public/subjects/Further_Pure_Mathematics/pages/{folder_name}/q{q_num}_ms.pdf"
        
        # Update page
        try:
            supabase.table('pages')\
                .update({
                    'qp_page_url': qp_url,
                    'ms_page_url': ms_url
                })\
                .eq('id', page['id'])\
                .execute()
            total_updated += 1
        except Exception as e:
            print(f"   ❌ Error updating Q{q_num}: {str(e)[:50]}")

print(f"\n✅ Updated {total_updated}/{total_pages} pages with URLs")

# Verify
verify = supabase.table('pages')\
    .select('id', count='exact')\
    .eq('paper_id', papers.data[0]['id'])\
    .not_.is_('qp_page_url', 'null')\
    .execute()

print(f"📊 Pages with URLs now: {verify.count}")
