"""
Update Physics topics to use descriptive codes matching the YAML file
This will fix the filter issue where ELEC questions weren't showing up
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

# Mapping from numeric codes to descriptive codes
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
print("UPDATING PHYSICS TOPICS TO USE DESCRIPTIVE CODES")
print("=" * 80)

# Get Physics subject
subject_resp = supabase.table('subjects').select('*').eq('name', 'Physics').execute()
subject_id = subject_resp.data[0]['id']

# Get all topics
topics = supabase.table('topics').select('*').eq('subject_id', subject_id).execute()

print(f"\nFound {len(topics.data)} topics to update:\n")

for topic in topics.data:
    old_code = topic['code']
    new_code = CODE_MAPPING.get(old_code)
    
    if new_code:
        print(f"Updating: {topic['name']}")
        print(f"  Old code: '{old_code}'")
        print(f"  New code: '{new_code}'")
        
        # Update the topic
        result = supabase.table('topics')\
            .update({'code': new_code})\
            .eq('id', topic['id'])\
            .execute()
        
        print(f"  ✅ Updated")
    else:
        print(f"⚠️  No mapping for code '{old_code}' - skipping")
    
    print()

print("=" * 80)
print("VERIFYING UPDATES")
print("=" * 80)

# Get updated topics
updated_topics = supabase.table('topics').select('*').eq('subject_id', subject_id).execute()

print(f"\nUpdated topics:\n")
for topic in sorted(updated_topics.data, key=lambda x: x['name']):
    print(f"  {topic['code']:6s} - {topic['name']}")

print("\n✅ Topics updated successfully!")
print("\nNow the frontend will filter correctly:")
print("  - ELEC will show 75 questions (instead of 7)")
print("  - FM will show 86 questions (instead of 27)")
print("  - WAVE will show 63 questions (instead of 17)")
print("  - etc.")
