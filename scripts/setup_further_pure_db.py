"""
Add Further Pure Mathematics subject and topics to database
Run this ONCE before processing papers
"""

import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from supabase_client import SupabaseClient

# Load environment
load_dotenv('.env.ingest')


def add_further_pure_subject():
    """Add Further Pure Mathematics subject and its 10 topics"""
    
    db = SupabaseClient()
    
    # Load config to get topic definitions
    config_path = Path('config/further_pure_topics.yaml')
    if not config_path.exists():
        print(f"❌ Config not found: {config_path}")
        return False
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    subject_info = config['subject']
    topics = config['topics']
    
    print(f"\n{'='*70}")
    print(f"📚 Adding {subject_info['name']} to database")
    print(f"{'='*70}")
    
    # 1. Check if subject already exists
    print(f"\n1️⃣  Checking if subject exists...")
    existing = db.select('subjects', filters={'code': subject_info['code']})
    
    if existing:
        subject_id = existing[0]['id']
        print(f"   ✅ Subject already exists (ID: {subject_id})")
    else:
        # Insert subject
        print(f"   ➕ Adding subject {subject_info['code']}...")
        result = db.insert('subjects', {
            'code': subject_info['code'],
            'name': subject_info['name'],
            'board': subject_info['board'],
            'level': subject_info['level']
        })
        
        if result:
            subject_id = result[0]['id']
            print(f"   ✅ Subject added (ID: {subject_id})")
        else:
            print(f"   ❌ Failed to add subject")
            return False
    
    # 2. Add topics
    print(f"\n2️⃣  Adding {len(topics)} topics...")
    
    # Check existing topics
    existing_topics = db.select('topics', filters={'subject_id': subject_id})
    
    existing_codes = {t['code'] for t in existing_topics} if existing_topics else set()
    
    added_count = 0
    skipped_count = 0
    
    for topic in topics:
        topic_code = topic['code']
        topic_name = topic['name']
        topic_id = topic['id']
        
        if topic_code in existing_codes:
            print(f"   ⏭️  Topic {topic_code} ({topic_id}) already exists")
            skipped_count += 1
            continue
        
        # Build description from topic details
        description_parts = [topic_name]
        
        # Add key concepts
        if 'lexical' in topic and 'any' in topic['lexical']:
            key_concepts = topic['lexical']['any'][:3]  # First 3
            if key_concepts:
                description_parts.append(f"Includes: {', '.join(key_concepts)}")
        
        # Add symbol hints
        if 'symbols' in topic and 'any_sets' in topic['symbols']:
            symbol_sets = topic['symbols']['any_sets'][:3]
            if symbol_sets:
                description_parts.append(f"Symbols: {', '.join(symbol_sets)}")
        
        description = ' | '.join(description_parts)
        
        # Insert topic
        try:
            result = db.insert('topics', {
                'subject_id': subject_id,
                'code': topic_code,
                'name': topic_name,
                'description': description
            })
            
            if result:
                print(f"   ✅ Added topic {topic_code}: {topic_name} ({topic_id})")
                added_count += 1
            else:
                print(f"   ❌ Failed to add topic {topic_code}")
        except Exception as e:
            print(f"   ❌ Error adding topic {topic_code}: {e}")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 SUMMARY")
    print(f"{'='*70}")
    print(f"✅ Topics added: {added_count}")
    print(f"⏭️  Topics skipped (already exist): {skipped_count}")
    print(f"📚 Total topics: {len(topics)}")
    
    if added_count > 0 or (added_count == 0 and skipped_count == len(topics)):
        print(f"\n🎉 {subject_info['name']} is ready for paper processing!")
        return True
    else:
        print(f"\n⚠️  Some topics failed to add")
        return False


def verify_setup():
    """Verify the setup is correct"""
    db = SupabaseClient()
    
    print(f"\n{'='*70}")
    print(f"🔍 VERIFICATION")
    print(f"{'='*70}")
    
    # Get subject
    subjects = db.select('subjects', filters={'code': '9FM0'})
    
    if not subjects:
        print(f"❌ Subject 9FM0 not found")
        return False
    
    subject_id = subjects[0]['id']
    subject_name = subjects[0]['name']
    
    print(f"✅ Subject: {subject_name} (ID: {subject_id})")
    
    # Get topics
    topics = db.select('topics', filters={'subject_id': subject_id})
    
    if not topics:
        print(f"❌ No topics found")
        return False
    
    print(f"✅ Topics: {len(topics)}")
    
    # List topics
    print(f"\nTopics:")
    for topic in sorted(topics, key=lambda t: int(t['code']) if t['code'].isdigit() else 999):
        print(f"   {topic['code']}: {topic['name']}")
    
    return True


def main():
    """Main entry point"""
    
    print(f"\n{'='*70}")
    print(f"🚀 Further Pure Mathematics Database Setup")
    print(f"{'='*70}")
    
    # Add subject and topics
    success = add_further_pure_subject()
    
    if success:
        # Verify
        verify_setup()
        
        print(f"\n{'='*70}")
        print(f"✅ Setup complete! You can now run:")
        print(f"   python scripts/batch_process_further_pure.py")
        print(f"{'='*70}")
    else:
        print(f"\n❌ Setup failed")


if __name__ == '__main__':
    main()
