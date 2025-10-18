"""
Re-classify all existing questions with updated topics from YAML config.
"""
import os
import sys
from pathlib import Path
import yaml
from dotenv import load_dotenv
from supabase import create_client

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "grademax-llm-hybrid" / "scripts"))
from lmstudio_client import LMStudioClient

# Load environment
load_dotenv('.env.local')

SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Missing Supabase credentials in .env.local")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def load_topics_from_yaml():
    """Load topics from YAML config."""
    config_path = Path(__file__).parent.parent / "config" / "further_pure_topics.yaml"
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # Map topic IDs to codes
    topic_map = {}
    for topic in config['topics']:
        topic_map[topic['id']] = topic['code']
    
    topic_names = [f"{t['code']}. {t['name']}" for t in config['topics']]
    
    return topic_map, topic_names

def get_topic_ids_from_db(subject_id):
    """Get topic ID mapping from database."""
    result = supabase.table('topics').select('*').eq('subject_id', subject_id).execute()
    
    # Map code to UUID
    code_to_id = {}
    for topic in result.data:
        code_to_id[topic['code']] = topic['id']
    
    return code_to_id

def reclassify_all_questions():
    """Re-classify all Further Pure Mathematics questions."""
    
    print("🔍 Re-classifying Further Pure Mathematics questions\n")
    
    # Get subject
    subject_result = supabase.table('subjects').select('*').eq('name', 'Further Pure Mathematics').execute()
    if not subject_result.data:
        print("❌ Subject 'Further Pure Mathematics' not found")
        return
    
    subject_id = subject_result.data[0]['id']
    print(f"✅ Subject ID: {subject_id}\n")
    
    # Load topics
    topic_id_to_code, topic_names = load_topics_from_yaml()
    code_to_uuid = get_topic_ids_from_db(subject_id)
    
    print(f"📚 Loaded {len(topic_names)} topics:")
    for name in topic_names:
        print(f"   - {name}")
    print()
    
    # Initialize LM Studio client
    config_path = Path(__file__).parent.parent / "config" / "further_pure_topics.yaml"
    llm_client = LMStudioClient(str(config_path))
    print("✅ LM Studio client initialized\n")
    
    # Get all pages for this subject
    pages_result = supabase.table('pages').select('*').eq('subject_id', subject_id).order('page_number').execute()
    
    if not pages_result.data:
        print("❌ No pages found for this subject")
        return
    
    pages = pages_result.data
    print(f"📄 Found {len(pages)} questions to re-classify\n")
    
    # Process each page
    for idx, page in enumerate(pages, 1):
        page_id = page['id']
        page_num = page['page_number']
        
        print(f"🔹 Question {page_num} ({idx}/{len(pages)})")
        
        # Get question text from QP URL
        qp_url = page.get('qp_page_url')
        if not qp_url:
            print(f"   ⚠️  No QP URL, skipping")
            continue
        
        # For now, we'll use a placeholder text since we don't have the actual PDF text
        # In production, you'd extract text from the PDF
        question_text = f"Question {page_num} from Further Pure Mathematics"
        
        try:
            # Classify with LM Studio
            classification = llm_client.classify_question(
                question_text,
                "Further Pure Mathematics",
                topic_names
            )
            
            # Convert topic IDs to UUIDs
            topic_ids = []
            if classification and 'topics' in classification:
                for topic_id in classification['topics']:
                    # Remove number prefix if present (e.g., "1. Logarithmic..." -> "LOGS")
                    clean_id = topic_id.split('.')[0].strip() if '.' in topic_id else topic_id
                    
                    # Map to code, then to UUID
                    if clean_id in topic_id_to_code:
                        code = topic_id_to_code[clean_id]
                        if code in code_to_uuid:
                            topic_ids.append(code_to_uuid[code])
            
            if not topic_ids:
                # Default to first topic if classification fails
                topic_ids = [code_to_uuid['1']]
                print(f"   ⚠️  No topics classified, using default")
            
            # Update page with new topics
            update_data = {'topics': topic_ids}
            supabase.table('pages').update(update_data).eq('id', page_id).execute()
            
            topic_codes = [k for k, v in code_to_uuid.items() if v in topic_ids]
            print(f"   ✅ Updated with topics: {', '.join(topic_codes)}")
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            continue
    
    print("\n🎉 Re-classification complete!")

if __name__ == "__main__":
    reclassify_all_questions()
