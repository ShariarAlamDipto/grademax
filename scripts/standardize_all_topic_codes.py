"""
Standardize ALL topic codes in the database
Convert numeric codes (1,2,3...) to descriptive codes (FM, ELEC, WAVE...)
This ensures frontend filtering works correctly
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load environment
project_root = Path(__file__).parent.parent
env_path = project_root / '.env.local'
load_dotenv(env_path)

SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Code mapping for Physics
CODE_MAPPING = {
    '1': 'FM',      # Forces and motion
    '2': 'ELEC',    # Electricity
    '3': 'WAVE',    # Waves
    '4': 'ENRG',    # Energy resources
    '5': 'SLG',     # Solids, liquids and gases
    '6': 'MAG',     # Magnetism and electromagnetism
    '7': 'RAD',     # Radioactivity and particles
    '8': 'ASTRO',   # Astrophysics
}

print("=" * 80)
print("STANDARDIZING ALL PHYSICS TOPIC CODES IN DATABASE")
print("=" * 80)

# Get Physics subject
subject_resp = supabase.table('subjects').select('*').eq('name', 'Physics').execute()
subject_id = subject_resp.data[0]['id']

# Get all Physics papers
papers_resp = supabase.table('papers').select('id').eq('subject_id', subject_id).execute()
paper_ids = [p['id'] for p in papers_resp.data]

print(f"\nFound {len(paper_ids)} Physics papers")

# Get all pages with topics
all_pages = supabase.table('pages')\
    .select('id, question_number, topics, paper_id')\
    .in_('paper_id', paper_ids)\
    .not_.is_('topics', 'null')\
    .execute()

print(f"Found {len(all_pages.data)} classified pages")

# Track changes
pages_updated = 0
pages_unchanged = 0
updates_by_code = {}

print("\n" + "=" * 80)
print("UPDATING PAGES")
print("=" * 80)

for page in all_pages.data:
    old_topics = page['topics']
    new_topics = []
    changed = False
    
    for topic_code in old_topics:
        if topic_code in CODE_MAPPING:
            # Convert numeric to descriptive
            new_code = CODE_MAPPING[topic_code]
            new_topics.append(new_code)
            changed = True
            
            # Track conversion
            key = f"{topic_code} → {new_code}"
            updates_by_code[key] = updates_by_code.get(key, 0) + 1
        else:
            # Already descriptive or unknown - keep as is
            new_topics.append(topic_code)
    
    if changed:
        # Update the page
        result = supabase.table('pages')\
            .update({'topics': new_topics})\
            .eq('id', page['id'])\
            .execute()
        
        pages_updated += 1
        
        if pages_updated <= 5:
            print(f"Updated Q{page['question_number']}: {old_topics} → {new_topics}")
    else:
        pages_unchanged += 1

print(f"\n✅ Updated {pages_updated} pages")
print(f"✅ {pages_unchanged} pages already had correct codes")

if updates_by_code:
    print("\n📊 Conversions performed:")
    for conversion, count in sorted(updates_by_code.items()):
        print(f"   {conversion}: {count} pages")

# Verify final state
print("\n" + "=" * 80)
print("VERIFICATION: FINAL TOPIC DISTRIBUTION")
print("=" * 80)

all_pages_final = supabase.table('pages')\
    .select('topics')\
    .in_('paper_id', paper_ids)\
    .not_.is_('topics', 'null')\
    .execute()

topic_counts = {}
for page in all_pages_final.data:
    for topic in page.get('topics', []):
        topic_counts[topic] = topic_counts.get(topic, 0) + 1

print(f"\nFinal topic distribution:")
for topic_code in sorted(topic_counts.keys()):
    count = topic_counts[topic_code]
    print(f"   {topic_code:10s}: {count:3d} pages")

# Check for any remaining numeric codes
numeric_codes = [code for code in topic_counts.keys() if code.isdigit()]
if numeric_codes:
    print(f"\n⚠️  Warning: Still have numeric codes: {numeric_codes}")
    print("   These pages might not filter correctly!")
else:
    print(f"\n✅ All codes are now descriptive - filtering should work correctly!")

print("\n" + "=" * 80)
print("EXPECTED COUNTS (from classification)")
print("=" * 80)
print("""
From test suite, we should have approximately:
   FM (Forces and motion):           86 pages (was 27 with code '1')
   ELEC (Electricity):                75 pages (was 7 with code '2')
   WAVE (Waves):                      63 pages (was 17 with code '3')
   ENRG (Energy resources):           40 pages (was 9 with code '4')
   SLG (Solids, liquids and gases):   48 pages (was 16 with code '5')
   MAG (Magnetism):                   43 pages (was 29 with code '6' + 14 legacy)
   RAD (Radioactivity):               56 pages (was 52 with code '7' + 4 legacy)
   ASTRO (Astrophysics):              38 pages (was 22 with code '8' + 16 legacy)
""")

print("\n✅ Standardization complete!")
print("\nNow refresh your browser and try filtering:")
print("   - ELEC should show ~75 questions")
print("   - FM should show ~86 questions")
print("   - All filters should work correctly")
