"""
Fix Mathematics B topics - Update names to match specification
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv('.env.ingest')
load_dotenv('.env.local')

from supabase_client import SupabaseClient
import requests

# Subject UUID for Mathematics B
MATHS_B_UUID = "af08fe67-37e2-4e20-9550-30103c4fe91a"

# Correct 10 topics from specification
CORRECT_TOPICS = {
    '1': {'name': 'Number', 'desc': 'Integers, fractions, decimals, indices, surds, standard form, bounds, ratio'},
    '2': {'name': 'Sets', 'desc': 'Set notation, union, intersection, Venn diagrams, subsets, complements'},
    '3': {'name': 'Algebra', 'desc': 'Expressions, equations, inequalities, formulae, sequences, factor theorem'},
    '4': {'name': 'Functions', 'desc': 'Function notation, domain, range, composite, inverse, differentiation, graphs'},
    '5': {'name': 'Matrices', 'desc': 'Matrix operations, multiplication, determinants, inverses, transformations'},
    '6': {'name': 'Geometry', 'desc': 'Angles, polygons, congruence, similarity, circle theorems, constructions'},
    '7': {'name': 'Mensuration', 'desc': 'Perimeter, area, volume, arc, sector, similar shapes'},
    '8': {'name': 'Vectors and Transformation Geometry', 'desc': 'Vectors, transformations, position vectors, enlargement'},
    '9': {'name': 'Trigonometry', 'desc': 'Sin, cos, tan, sine rule, cosine rule, 3D, bearings'},
    '10': {'name': 'Statistics and Probability', 'desc': 'Data, averages, frequency, probability, tree diagrams'},
}

def fix_topics():
    """Update topic names and descriptions to match specification"""
    db = SupabaseClient()
    
    print("=" * 70)
    print("🔧 Fixing Mathematics B Topics (Names and Descriptions)")
    print("=" * 70)
    
    # Get current topics
    print("\n1️⃣ Getting current topics...")
    current_topics = db.select('topics', filters={'subject_id': f"eq.{MATHS_B_UUID}"})
    print(f"   Found {len(current_topics)} topics")
    
    # Update each topic
    print("\n2️⃣ Updating topic names and descriptions...")
    for topic in current_topics:
        topic_code = topic.get('code')
        topic_id = topic.get('id')
        current_name = topic.get('name')
        
        if topic_code in CORRECT_TOPICS:
            correct = CORRECT_TOPICS[topic_code]
            if current_name != correct['name']:
                print(f"   📝 Topic {topic_code}: '{current_name}' -> '{correct['name']}'")
            else:
                print(f"   ✓ Topic {topic_code}: '{correct['name']}' (correct)")
            
            # Update using direct REST API call with ID
            url = f"{db.rest_url}/topics?id=eq.{topic_id}"
            response = requests.patch(
                url,
                headers=db.headers,
                json={
                    'name': correct['name'],
                    'description': correct['desc']
                }
            )
            if response.status_code == 200:
                print(f"      ✅ Updated")
            else:
                print(f"      ❌ Error: {response.status_code} - {response.text}")
        else:
            print(f"   ⚠️ Unknown topic code: {topic_code}")
    
    # Final verification
    print("\n3️⃣ Verification...")
    final_topics = db.select('topics', filters={'subject_id': f"eq.{MATHS_B_UUID}"})
    print(f"\n   📚 Final Topics for Mathematics B:")
    for t in sorted(final_topics, key=lambda x: int(x.get('code', 0))):
        print(f"      {t.get('code')}: {t.get('name')}")
    
    print("\n" + "=" * 70)
    print("✅ Topic names corrected!")
    print("=" * 70)

if __name__ == '__main__':
    fix_topics()
