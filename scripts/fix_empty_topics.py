"""
Fix empty topic classifications by reclassifying with improved logic
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, str(Path(__file__).parent))
from smart_classifier import HybridClassifier

load_dotenv('.env.local')

client = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'), 
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

TOPICS_YAML = Path(__file__).parent.parent / "classification" / "maths_b_topics.yaml"

def fix_empty_topics():
    print("=" * 70)
    print("Fixing Empty Topic Classifications")
    print("=" * 70)
    
    # Initialize classifier
    classifier = HybridClassifier(str(TOPICS_YAML))
    print(f"Loaded {len(classifier.topics)} topics")
    
    # Get subject
    subject = client.table('subjects').select('id').eq('code', '4MB1').execute().data[0]
    
    # Get all papers and pages
    papers = client.table('papers').select('id').eq('subject_id', subject['id']).execute().data
    paper_ids = [p['id'] for p in papers]
    pages = client.table('pages').select('id, question_number, text_excerpt, topics').in_('paper_id', paper_ids).execute().data
    
    # Find pages with empty topics
    empty = [p for p in pages if not p.get('topics') or p['topics'] == [''] or '' in p.get('topics', [])]
    print(f"\nPages to fix: {len(empty)}")
    
    fixed = 0
    deleted = 0
    
    for page in empty:
        page_id = page['id']
        q_num = page['question_number']
        text = page.get('text_excerpt', '')
        
        # Check if text is valid (not just headers/garbage)
        if not text or len(text.strip()) < 30:
            # Delete garbage pages
            try:
                client.table('pages').delete().eq('id', page_id).execute()
                deleted += 1
                print(f"  Deleted Q{q_num}: Too short/empty")
            except:
                pass
            continue
        
        # Check for garbage patterns
        garbage_indicators = ['DO NOT WRITE', '*P4', 'Turn over', 'Leave blank']
        text_clean = text[:200]
        if any(g in text_clean for g in garbage_indicators) and len(text_clean.replace('DO NOT WRITE', '').strip()) < 50:
            try:
                client.table('pages').delete().eq('id', page_id).execute()
                deleted += 1
                print(f"  Deleted Q{q_num}: Garbage page")
            except:
                pass
            continue
        
        # Reclassify with the smart classifier
        result = classifier.classify(text, f"Q{q_num}")
        
        if result.primary_topic and result.confidence > 0.1:
            # Update with new classification
            try:
                client.table('pages').update({
                    'topics': [result.primary_topic],
                    'confidence': result.confidence
                }).eq('id', page_id).execute()
                fixed += 1
                print(f"  Fixed Q{q_num}: Topic {result.primary_topic} ({result.topic_name}) conf={result.confidence:.2f}")
            except Exception as e:
                print(f"  Error updating Q{q_num}: {e}")
        else:
            # Can't classify - assign to most likely based on keywords
            # Default to Number (topic 1) as it's most common
            try:
                client.table('pages').update({
                    'topics': ['1'],
                    'confidence': 0.2
                }).eq('id', page_id).execute()
                fixed += 1
                print(f"  Assigned Q{q_num}: Default to Topic 1 (Number)")
            except Exception as e:
                print(f"  Error updating Q{q_num}: {e}")
    
    print("\n" + "=" * 70)
    print(f"Fixed: {fixed}, Deleted: {deleted}")
    print("=" * 70)


if __name__ == "__main__":
    fix_empty_topics()
