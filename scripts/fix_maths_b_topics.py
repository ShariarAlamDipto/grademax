"""
Fix Mathematics B topics in database to match the 10-topic specification
- Renumber existing topics
- Add Sets (topic 2) and Matrices (topic 5)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv('.env.ingest')
load_dotenv('.env.local')

from supabase_client import SupabaseClient

# Subject UUID for Mathematics B (already in database)
MATHS_B_UUID = "af08fe67-37e2-4e20-9550-30103c4fe91a"

# Correct 10 topics from specification
CORRECT_TOPICS = [
    {'number': '1', 'name': 'Number', 'desc': 'Integers, fractions, decimals, indices, surds, standard form, bounds, ratio'},
    {'number': '2', 'name': 'Sets', 'desc': 'Set notation, union, intersection, Venn diagrams, subsets, complements'},
    {'number': '3', 'name': 'Algebra', 'desc': 'Expressions, equations, inequalities, formulae, sequences, factor theorem'},
    {'number': '4', 'name': 'Functions', 'desc': 'Function notation, domain, range, composite, inverse, differentiation, graphs'},
    {'number': '5', 'name': 'Matrices', 'desc': 'Matrix operations, multiplication, determinants, inverses, transformations'},
    {'number': '6', 'name': 'Geometry', 'desc': 'Angles, polygons, congruence, similarity, circle theorems, constructions'},
    {'number': '7', 'name': 'Mensuration', 'desc': 'Perimeter, area, volume, arc, sector, similar shapes'},
    {'number': '8', 'name': 'Vectors and Transformation Geometry', 'desc': 'Vectors, transformations, position vectors, enlargement'},
    {'number': '9', 'name': 'Trigonometry', 'desc': 'Sin, cos, tan, sine rule, cosine rule, 3D, bearings'},
    {'number': '10', 'name': 'Statistics and Probability', 'desc': 'Data, averages, frequency, probability, tree diagrams'},
]

def fix_topics():
    """Delete old topics and recreate with correct 10 topics"""
    db = SupabaseClient()
    
    print("=" * 70)
    print("🔧 Fixing Mathematics B Topics")
    print("=" * 70)
    
    # Step 1: Get current topics
    print("\n1️⃣ Current topics in database...")
    current_topics = db.select('topics', filters={'subject_id': f"eq.{MATHS_B_UUID}"})
    print(f"   Found {len(current_topics)} topics")
    for t in current_topics:
        print(f"     - {t.get('code', 'N/A')}: {t.get('name', 'N/A')}")
    
    # Step 2: Delete existing topics
    print("\n2️⃣ Deleting existing topics...")
    for t in current_topics:
        try:
            db.delete('topics', filters={'id': f"eq.{t['id']}"})
            print(f"   ✅ Deleted topic: {t.get('code', 'N/A')} - {t.get('name', 'N/A')}")
        except Exception as e:
            print(f"   ⚠️ Error deleting topic {t.get('code', 'N/A')}: {e}")
    
    # Step 3: Add correct 10 topics
    print("\n3️⃣ Adding correct 10 topics...")
    for topic in CORRECT_TOPICS:
        topic_data = {
            'subject_id': MATHS_B_UUID,
            'code': topic['number'],
            'name': topic['name'],
            'description': topic['desc']
        }
        
        try:
            db.insert('topics', topic_data)
            print(f"   ✅ Topic {topic['number']}: {topic['name']}")
        except Exception as e:
            print(f"   ❌ Error adding topic {topic['number']}: {e}")
    
    # Step 4: Verify
    print("\n4️⃣ Verification...")
    final_topics = db.select('topics', filters={'subject_id': f"eq.{MATHS_B_UUID}"})
    print(f"   Total topics: {len(final_topics)}")
    for t in sorted(final_topics, key=lambda x: int(x.get('code', 0))):
        print(f"     - {t.get('code', 'N/A')}: {t.get('name', 'N/A')}")
    
    print("\n" + "=" * 70)
    if len(final_topics) == 10:
        print("✅ Mathematics B topics corrected successfully!")
    else:
        print(f"⚠️ Expected 10 topics, got {len(final_topics)}")
    print("=" * 70)

if __name__ == '__main__':
    fix_topics()
