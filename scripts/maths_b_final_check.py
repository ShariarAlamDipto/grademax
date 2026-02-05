"""
Final verification of Math B database
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('.env.local')

client = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'), 
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

def final_check():
    print("=" * 70)
    print("MATHEMATICS B - FINAL DATABASE CHECK")
    print("=" * 70)
    
    # Get subject
    subject = client.table('subjects').select('id, name, code').eq('code', '4MB1').execute().data[0]
    print(f"\nSubject: {subject['name']} ({subject['code']})")
    print(f"ID: {subject['id']}")
    
    # Get topics
    topics_data = client.table('topics').select('*').eq('subject_id', subject['id']).execute().data
    topic_map = {str(t['code']): t['name'] for t in topics_data}
    print(f"\nTopics ({len(topics_data)}):")
    for t in sorted(topics_data, key=lambda x: int(x['code']) if x['code'].isdigit() else 99):
        print(f"  {t['code']}: {t['name']}")
    
    # Get papers
    papers = client.table('papers').select('*').eq('subject_id', subject['id']).order('year', desc=True).execute().data
    print(f"\nPapers: {len(papers)}")
    
    # Summary by year
    years = {}
    for p in papers:
        year = p['year']
        if year not in years:
            years[year] = []
        years[year].append(p)
    
    print("\nPapers by year:")
    for year in sorted(years.keys(), reverse=True):
        papers_list = years[year]
        sessions = [f"{p['season']} P{p['paper_number']}" for p in papers_list]
        print(f"  {year}: {', '.join(sessions)}")
    
    # Get pages
    paper_ids = [p['id'] for p in papers]
    pages = client.table('pages').select('*').in_('paper_id', paper_ids).execute().data
    
    print(f"\nTotal Questions: {len(pages)}")
    
    # Topic distribution
    topic_counts = {}
    invalid_topics = []
    for page in pages:
        topics = page.get('topics', [])
        if topics:
            topic = topics[0]
            if topic not in topic_counts:
                topic_counts[topic] = 0
            topic_counts[topic] += 1
            
            # Check for invalid topic IDs
            if topic not in topic_map and topic not in [str(i) for i in range(1, 11)]:
                invalid_topics.append((page['id'], topic))
    
    print("\nTopic Distribution:")
    for topic_num, count in sorted(topic_counts.items(), key=lambda x: -x[1]):
        name = topic_map.get(topic_num, "Unknown")
        print(f"  {topic_num}: {count} questions ({name})")
    
    # Fix any invalid topics
    if invalid_topics:
        print(f"\nFixing {len(invalid_topics)} invalid topic IDs...")
        for page_id, bad_topic in invalid_topics:
            # Map text names to numbers
            name_to_num = {
                'GEOM': '6', 'NUM': '1', 'ALG': '3', 'FUNC': '4',
                'SETS': '2', 'MAT': '5', 'MENS': '7', 'VECT': '8',
                'TRIG': '9', 'STAT': '10'
            }
            new_topic = name_to_num.get(bad_topic.upper(), '1')
            client.table('pages').update({'topics': [new_topic]}).eq('id', page_id).execute()
            print(f"  Fixed {bad_topic} -> {new_topic}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Papers: {len(papers)}")
    print(f"  Questions: {len(pages)}")
    print(f"  Topics: {len(topics_data)}")
    print(f"  Years: {min(years.keys())}-{max(years.keys())}")
    print("=" * 70)


if __name__ == "__main__":
    final_check()
