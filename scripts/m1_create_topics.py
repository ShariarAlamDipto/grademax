"""
Create IAL Mechanics 1 topics in the database
Run this ONCE before processing M1 papers
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

print("=" * 80)
print("CREATING IAL MECHANICS 1 SUBJECT AND TOPICS")
print("=" * 80)

# Check if M1 subject exists
subject_resp = supabase.table('subjects').select('*').eq('code', 'WME01').execute()

if subject_resp.data:
    print(f"\n✅ Mechanics 1 subject already exists (ID: {subject_resp.data[0]['id']})")
    subject_id = subject_resp.data[0]['id']
else:
    # Create M1 subject
    print("\n📝 Creating Mechanics 1 subject...")
    subject_data = {
        'name': 'Mechanics 1',
        'code': 'WME01',
        'level': 'IAL',
        'board': 'Pearson Edexcel'
    }
    
    subject_resp = supabase.table('subjects').insert(subject_data).execute()
    subject_id = subject_resp.data[0]['id']
    print(f"✅ Created subject: Mechanics 1 (ID: {subject_id})")

# M1 Topics (following the prompt pack specification)
M1_TOPICS = [
    {
        'code': 'M1.1',
        'name': 'Modelling & Assumptions',
        'description': 'Particle, lamina, rigid body, light strings/pulleys, smooth/rough, beads/wires/pegs',
        'keywords': None,
        'formulas': None
    },
    {
        'code': 'M1.2',
        'name': 'Vectors in Mechanics',
        'description': 'i,j; components; resultants; vector kinematics/forces',
        'keywords': None,
        'formulas': None
    },
    {
        'code': 'M1.3',
        'name': 'Kinematics',
        'description': 'Constant acceleration; SUVAT; s–t, v–t, a–t graphs',
        'keywords': None,
        'formulas': None
    },
    {
        'code': 'M1.4',
        'name': 'Dynamics',
        'description': 'F=ma; tension; connected particles; inclines; components',
        'keywords': None,
        'formulas': None
    },
    {
        'code': 'M1.5',
        'name': 'Momentum & Impulse',
        'description': 'p=mv; J=Ft; 1D conservation',
        'keywords': None,
        'formulas': None
    },
    {
        'code': 'M1.6',
        'name': 'Friction',
        'description': 'μ; limiting friction; F=μR / F≤μR; rough/smooth',
        'keywords': None,
        'formulas': None
    },
    {
        'code': 'M1.7',
        'name': 'Statics of a Particle',
        'description': 'ΣF=0; resolve; equilibrium; tension/thrust/reaction',
        'keywords': None,
        'formulas': None
    },
    {
        'code': 'M1.8',
        'name': 'Moments',
        'description': 'M=F×d; parallel coplanar forces; equilibrium about a point',
        'keywords': None,
        'formulas': None
    }
]

# Check existing topics
existing_topics = supabase.table('topics').select('code').eq('subject_id', subject_id).execute()
existing_codes = {t['code'] for t in existing_topics.data}

print(f"\n📊 Creating/updating {len(M1_TOPICS)} topics...")
print()

created = 0
updated = 0

for topic in M1_TOPICS:
    topic['subject_id'] = subject_id
    
    if topic['code'] in existing_codes:
        # Update existing
        result = supabase.table('topics')\
            .update(topic)\
            .eq('subject_id', subject_id)\
            .eq('code', topic['code'])\
            .execute()
        print(f"✓ Updated: {topic['code']} - {topic['name']}")
        updated += 1
    else:
        # Create new
        result = supabase.table('topics').insert(topic).execute()
        print(f"✓ Created: {topic['code']} - {topic['name']}")
        created += 1

print()
print("=" * 80)
print(f"✅ TOPICS CONFIGURED: {created} created, {updated} updated")
print("=" * 80)
print()
print("M1 Topics:")
for topic in M1_TOPICS:
    print(f"  {topic['code']:8s} - {topic['name']}")

print()
print("🎯 Ready to process M1 papers!")
print(f"   Subject ID: {subject_id}")
print(f"   Total topics: {len(M1_TOPICS)}")
