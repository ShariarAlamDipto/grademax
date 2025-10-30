"""Fix FPM papers that have wrong subject_id"""
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

supabase = create_client(
    env['NEXT_PUBLIC_SUPABASE_URL'],
    env['SUPABASE_SERVICE_ROLE_KEY']
)

# Get all subjects
response = supabase.table('subjects').select('*').execute()
print("📚 All subjects:")
for subject in response.data:
    print(f"   {subject['code']}: {subject['name']} (ID: {subject['id']})")

# Get FPM subject
fpm_response = supabase.table('subjects').select('*').eq('code', '9FM0').execute()
fpm = fpm_response.data[0]
print(f"\n✅ FPM Subject: {fpm['name']} (ID: {fpm['id']})")

# Check papers with wrong subject_id (0b142517...)
wrong_subject_id = '0b142517-d35d-4942-91aa-b4886aaabca3'
response = supabase.table('papers').select('id, year, season, paper_number', count='exact').eq('subject_id', wrong_subject_id).execute()

if response.data:
    print(f"\n⚠️  Found {response.count} papers with wrong subject_id ({wrong_subject_id[:8]}...)")
    print(f"   These are likely FPM papers that need to be fixed")
    
    # Show sample
    print(f"\n   Sample papers (showing first 10):")
    for paper in response.data[:10]:
        print(f"   {paper['year']} {paper['season']} Paper {paper['paper_number']}")
    
    # Ask to fix
    print(f"\n🔧 Ready to update {response.count} papers to correct FPM subject_id?")
    confirm = input("   Type 'yes' to continue: ")
    
    if confirm.lower() == 'yes':
        # Update all papers
        update_response = supabase.table('papers')\
            .update({'subject_id': fpm['id']})\
            .eq('subject_id', wrong_subject_id)\
            .execute()
        
        print(f"\n✅ Updated papers! Checking results...")
        
        # Verify
        verify_response = supabase.table('papers').select('id', count='exact').eq('subject_id', fpm['id']).execute()
        print(f"   FPM papers now: {verify_response.count}")
        
        # Check pages
        page_response = supabase.table('pages').select('id', count='exact').execute()
        print(f"   Total pages: {page_response.count}")
    else:
        print("   ❌ Cancelled")
else:
    print(f"\n✅ No papers found with wrong subject_id")
    
# Show current FPM paper count
fpm_papers = supabase.table('papers').select('id', count='exact').eq('subject_id', fpm['id']).execute()
print(f"\n📊 Current FPM papers: {fpm_papers.count}")
