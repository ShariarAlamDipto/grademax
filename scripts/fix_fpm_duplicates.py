"""Fix FPM papers - delete duplicates from Physics, keep FPM ones"""
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

# Subject IDs
physics_id = '0b142517-d35d-4942-91aa-b4886aaabca3'
fpm_id = '8dea5d70-f026-4e03-bb45-053f154c6898'

print("🔍 Analyzing FPM papers in database...")

# Get papers with "1P" or "2P" paper_number (these are FPM papers)
# These are currently under Physics subject_id
physics_fpm_papers = supabase.table('papers')\
    .select('id, year, season, paper_number')\
    .eq('subject_id', physics_id)\
    .or_('paper_number.eq.1P,paper_number.eq.2P')\
    .execute()

print(f"\n📋 Found {len(physics_fpm_papers.data)} FPM papers under Physics subject")

# Get papers already under FPM subject_id  
fpm_papers = supabase.table('papers')\
    .select('id, year, season, paper_number')\
    .eq('subject_id', fpm_id)\
    .execute()

print(f"📋 Found {len(fpm_papers.data)} papers already under FPM subject")

# Find which Physics-FPM papers are duplicates
fpm_keys = {(p['year'], p['season'], p['paper_number']) for p in fpm_papers.data}
duplicates = [p for p in physics_fpm_papers.data if (p['year'], p['season'], p['paper_number']) in fpm_keys]
non_duplicates = [p for p in physics_fpm_papers.data if (p['year'], p['season'], p['paper_number']) not in fpm_keys]

print(f"\n⚠️  {len(duplicates)} papers are duplicates (exist in both Physics and FPM)")
print(f"✅ {len(non_duplicates)} papers only exist under Physics (need to be moved)")

if duplicates:
    print(f"\n🗑️  Will delete {len(duplicates)} duplicate papers from Physics:")
    for p in duplicates[:10]:
        print(f"   {p['year']} {p['season']} Paper {p['paper_number']}")
    if len(duplicates) > 10:
        print(f"   ... and {len(duplicates) - 10} more")
    
    confirm = input(f"\nDelete {len(duplicates)} duplicate papers? (yes/no): ")
    if confirm.lower() == 'yes':
        for paper in duplicates:
            # Delete pages first
            supabase.table('pages').delete().eq('paper_id', paper['id']).execute()
            # Delete paper
            supabase.table('papers').delete().eq('id', paper['id']).execute()
        print(f"✅ Deleted {len(duplicates)} duplicate papers")

if non_duplicates:
    print(f"\n🔧 Will update {len(non_duplicates)} papers to FPM subject:")
    for p in non_duplicates[:10]:
        print(f"   {p['year']} {p['season']} Paper {p['paper_number']}")
    if len(non_duplicates) > 10:
        print(f"   ... and {len(non_duplicates) - 10} more")
    
    confirm2 = input(f"\nUpdate {len(non_duplicates)} papers to FPM subject? (yes/no): ")
    if confirm2.lower() == 'yes':
        for paper in non_duplicates:
            supabase.table('papers').update({'subject_id': fpm_id}).eq('id', paper['id']).execute()
        print(f"✅ Updated {len(non_duplicates)} papers")

# Final count
final_fpm = supabase.table('papers').select('id', count='exact').eq('subject_id', fpm_id).execute()
print(f"\n📊 Final FPM paper count: {final_fpm.count}")

# Count pages
pages = supabase.table('pages').select('id', count='exact').execute()
print(f"📊 Total pages in database: {pages.count}")
