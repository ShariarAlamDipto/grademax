"""
Sync Further Pure Mathematics topics from YAML to database
"""
from supabase import create_client
import os
from dotenv import load_dotenv
import yaml

load_dotenv(".env.local")

supabase = create_client(
    os.getenv("NEXT_PUBLIC_SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

# Load YAML config
with open("config/further_pure_topics.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

subject_name = "Further Pure Mathematics"

print(f"🔍 Syncing topics for {subject_name}\n")

# Get subject
subject = supabase.table('subjects').select('*').eq('name', subject_name).execute()
if not subject.data:
    print(f"❌ Subject not found: {subject_name}")
    exit(1)

subject_id = subject.data[0]['id']
print(f"✅ Subject ID: {subject_id}")

# Get current topics from database
current_topics = supabase.table('topics').select('*').eq('subject_id', subject_id).execute()
print(f"\n📋 Current topics in database: {len(current_topics.data)}")
for t in current_topics.data:
    print(f"   - {t['code']}: {t['name']}")

# Get topics from YAML
yaml_topics = config['topics']
print(f"\n📄 Topics in YAML: {len(yaml_topics)}")
for t in yaml_topics:
    print(f"   - {t['code']}: {t['name']}")

# Delete all current topics
print(f"\n🗑️ Deleting {len(current_topics.data)} existing topics...")
if current_topics.data:
    supabase.table('topics').delete().eq('subject_id', subject_id).execute()
    print(f"✅ Deleted")

# Insert new topics from YAML
print(f"\n➕ Inserting {len(yaml_topics)} topics from YAML...")
for topic in yaml_topics:
    topic_data = {
        'subject_id': subject_id,
        'code': topic['code'],  # "1", "2", etc.
        'name': topic['name'],
        'description': topic['description']
    }
    
    try:
        result = supabase.table('topics').insert(topic_data).execute()
        print(f"   ✅ {topic['code']}: {topic['name']}")
    except Exception as e:
        print(f"   ❌ {topic['code']}: {e}")

# Verify
final_topics = supabase.table('topics').select('*').eq('subject_id', subject_id).order('code').execute()
print(f"\n✅ Final topics in database: {len(final_topics.data)}")
for t in final_topics.data:
    print(f"   {t['code']}: {t['name']}")

print(f"\n🎉 Topics synced successfully!")
