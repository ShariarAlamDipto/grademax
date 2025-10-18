"""
Helper script to add a new subject to the database
This makes it easier to add Chemistry, Biology, Maths, etc.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv('.env.ingest')

from supabase_client import SupabaseClient

# Predefined subjects with their topics
SUBJECTS = {
    'chemistry': {
        'code': '4CH1',
        'name': 'Chemistry',
        'level': 'IGCSE',
        'exam_board': 'Edexcel',
        'topics': [
            {'number': '1', 'name': 'Principles of Chemistry', 'desc': 'States of matter, atoms, elements, compounds'},
            {'number': '2', 'name': 'Chemistry of the Elements', 'desc': 'Periodic table, groups, metals, non-metals'},
            {'number': '3', 'name': 'Organic Chemistry', 'desc': 'Hydrocarbons, alkanes, alkenes, alcohols'},
            {'number': '4', 'name': 'Physical Chemistry', 'desc': 'Energetics, rates, equilibrium, electrolysis'},
            {'number': '5', 'name': 'Chemistry in Society', 'desc': 'Industrial processes, atmosphere, earth'},
        ]
    },
    'biology': {
        'code': '4BI1',
        'name': 'Biology',
        'level': 'IGCSE',
        'exam_board': 'Edexcel',
        'topics': [
            {'number': '1', 'name': 'Nature and Variety of Living Organisms', 'desc': 'Characteristics, classification'},
            {'number': '2', 'name': 'Structures and Functions', 'desc': 'Cells, enzymes, nutrition, respiration'},
            {'number': '3', 'name': 'Reproduction and Inheritance', 'desc': 'Reproduction, genetics, evolution'},
            {'number': '4', 'name': 'Ecology and the Environment', 'desc': 'Ecosystems, food chains, conservation'},
            {'number': '5', 'name': 'Human Influences', 'desc': 'Pollution, food production, selective breeding'},
        ]
    },
    'maths': {
        'code': '4MA1',
        'name': 'Mathematics',
        'level': 'IGCSE',
        'exam_board': 'Edexcel',
        'topics': [
            {'number': '1', 'name': 'Number', 'desc': 'Integers, fractions, decimals, percentages, ratio'},
            {'number': '2', 'name': 'Algebra', 'desc': 'Expressions, equations, inequalities, sequences'},
            {'number': '3', 'name': 'Graphs', 'desc': 'Coordinates, linear graphs, quadratic graphs, curves'},
            {'number': '4', 'name': 'Geometry', 'desc': 'Shapes, angles, transformations, vectors'},
            {'number': '5', 'name': 'Mensuration', 'desc': 'Perimeter, area, volume, circle theorems'},
            {'number': '6', 'name': 'Trigonometry', 'desc': 'Sin, cos, tan, Pythagoras, bearings'},
            {'number': '7', 'name': 'Statistics and Probability', 'desc': 'Data, averages, probability, diagrams'},
        ]
    }
}


def add_subject(subject_key: str):
    """Add a subject and its topics to the database"""
    
    if subject_key not in SUBJECTS:
        print(f"❌ Unknown subject: {subject_key}")
        print(f"   Available: {', '.join(SUBJECTS.keys())}")
        return
    
    subject_info = SUBJECTS[subject_key]
    db = SupabaseClient()
    
    print("=" * 70)
    print(f"📚 Adding {subject_info['name']} to Database")
    print("=" * 70)
    
    # Step 1: Check if subject already exists
    print(f"\n1️⃣  Checking if {subject_info['code']} already exists...")
    existing = db.select('subjects', filters={'code': f"eq.{subject_info['code']}"})
    
    if existing:
        print(f"   ⚠️  Subject {subject_info['code']} already exists!")
        subject_uuid = existing[0]['id']
        print(f"   Using existing UUID: {subject_uuid}")
    else:
        # Step 2: Insert subject
        print(f"\n2️⃣  Creating subject record...")
        subject_data = {
            'code': subject_info['code'],
            'name': subject_info['name'],
            'level': subject_info['level'],
            'exam_board': subject_info['exam_board']
        }
        
        result = db.insert('subjects', subject_data)
        subject_uuid = result['id']
        print(f"   ✅ Created: {subject_info['code']} - {subject_info['name']}")
        print(f"   UUID: {subject_uuid}")
    
    # Step 3: Add topics
    print(f"\n3️⃣  Adding topics...")
    for topic in subject_info['topics']:
        # Check if topic exists
        existing_topic = db.select('topics', filters={
            'subject_id': f"eq.{subject_uuid}",
            'topic_number': f"eq.{topic['number']}"
        })
        
        if existing_topic:
            print(f"   ⏭️  Topic {topic['number']} already exists: {topic['name']}")
        else:
            topic_data = {
                'subject_id': subject_uuid,
                'topic_number': topic['number'],
                'name': topic['name'],
                'description': topic['desc']
            }
            
            db.insert('topics', topic_data)
            print(f"   ✅ Topic {topic['number']}: {topic['name']}")
    
    # Step 4: Verify
    print(f"\n4️⃣  Verification...")
    topics = db.select('topics', filters={'subject_id': f"eq.{subject_uuid}"})
    print(f"   ✅ Total topics: {len(topics)}")
    
    print("\n" + "=" * 70)
    print(f"✅ {subject_info['name']} setup complete!")
    print("=" * 70)
    print("\n📋 Next Steps:")
    print(f"   1. Create topic config: config/{subject_key}_topics.yaml")
    print(f"   2. Create ingestion script: scripts/{subject_key}_ingest.py")
    print(f"   3. Add PDFs to: data/raw/IGCSE/{subject_info['code']}/YYYY/Season/")
    print(f"   4. Run: python scripts/{subject_key}_ingest.py <QP.pdf> <MS.pdf>")
    print("\n")


def list_subjects():
    """List all available subjects"""
    print("=" * 70)
    print("📚 Available Subjects to Add")
    print("=" * 70)
    
    for key, info in SUBJECTS.items():
        print(f"\n{key.upper()}:")
        print(f"  Code:   {info['code']}")
        print(f"  Name:   {info['name']}")
        print(f"  Topics: {len(info['topics'])}")
        print(f"  Usage:  python scripts/add_subject.py {key}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/add_subject.py <subject_name>")
        print("\nExamples:")
        print("  python scripts/add_subject.py chemistry")
        print("  python scripts/add_subject.py biology")
        print("  python scripts/add_subject.py maths")
        print("\nOr list available subjects:")
        print("  python scripts/add_subject.py list")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'list':
        list_subjects()
    elif command in SUBJECTS:
        add_subject(command)
    else:
        print(f"❌ Unknown subject: {command}")
        print("\nAvailable subjects:")
        for key in SUBJECTS.keys():
            print(f"  - {key}")
        print("\nRun 'python scripts/add_subject.py list' for more details")


if __name__ == '__main__':
    main()
