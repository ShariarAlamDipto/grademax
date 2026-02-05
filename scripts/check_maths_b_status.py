"""Quick check of Maths B classification status in database"""

from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv('.env.local')
client = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'), 
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Get subject
subject = client.table('subjects').select('id, name').eq('code', '4MB1').execute().data[0]
print(f"Subject: {subject['name']} (ID: {subject['id'][:8]}...)")

# Count papers
papers = client.table('papers').select('id').eq('subject_id', subject['id']).execute().data
print(f"Papers in database: {len(papers)}")

if papers:
    # Count all pages
    all_pages = client.table('pages').select('id, topics, paper_id').in_('paper_id', [p['id'] for p in papers]).execute().data
    print(f"Pages in database: {len(all_pages)}")
    
    # Count classified pages
    classified = [p for p in all_pages if p.get('topics') and len(p['topics']) > 0]
    print(f"Pages classified: {len(classified)}")
    
    # Count by topic
    topic_counts = {}
    for p in classified:
        topic = p['topics'][0] if p['topics'] else 'None'
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
    
    print("\nClassification by topic:")
    for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {topic}: {count}")
