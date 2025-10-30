#!/usr/bin/env python3
"""
Query and analyze Physics classifications in the database.

Usage:
    python scripts/query_physics_classifications.py --by-year
    python scripts/query_physics_classifications.py --by-topic
    python scripts/query_physics_classifications.py --by-difficulty
    python scripts/query_physics_classifications.py --summary
    python scripts/query_physics_classifications.py --year 2024
    python scripts/query_physics_classifications.py --topic FM
"""

import os
import sys
from pathlib import Path
from collections import defaultdict, Counter
from supabase import create_client
import argparse
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
env_path = project_root / '.env.local'
load_dotenv(env_path)

# Initialize Supabase
SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    print(f"   Tried loading from: {env_path}")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Physics subject ID (same as used in upload script)
PHYSICS_SUBJECT_ID = "123e4567-e89b-12d3-a456-426614174002"


def get_all_physics_data():
    """Fetch all Physics papers and their classified pages."""
    print("📊 Fetching Physics data from database...")
    
    # Get all Physics papers
    papers_response = supabase.table("papers").select("*").eq("subject_id", PHYSICS_SUBJECT_ID).execute()
    papers = papers_response.data
    
    print(f"   Found {len(papers)} Physics papers")
    
    # Get all pages with their classifications
    pages_data = []
    for paper in papers:
        pages_response = supabase.table("pages").select("*").eq("paper_id", paper['id']).execute()
        
        for page in pages_response.data:
            pages_data.append({
                'year': paper['year'],
                'season': paper['season'],
                'paper_number': paper['paper_number'],
                'question_number': page['question_number'],
                'topics': page.get('topics', []),
                'difficulty': page.get('difficulty'),
                'confidence': page.get('confidence'),
                'paper_id': paper['id'],
                'page_id': page['id']
            })
    
    print(f"   Found {len(pages_data)} total pages")
    
    return papers, pages_data


def show_summary(papers, pages):
    """Show overall classification summary."""
    print("\n" + "="*80)
    print("📊 PHYSICS CLASSIFICATION SUMMARY")
    print("="*80)
    
    total_pages = len(pages)
    classified_pages = [p for p in pages if p['topics'] and len(p['topics']) > 0]
    unclassified_pages = [p for p in pages if not p['topics'] or len(p['topics']) == 0]
    
    print(f"\n📄 Total Pages: {total_pages}")
    
    if total_pages == 0:
        print("\n⚠️  No Physics data found in database!")
        print("   Please run upload script first: python scripts\\upload_physics_to_database.py")
        return
    
    print(f"✅ Classified: {len(classified_pages)} ({len(classified_pages)/total_pages*100:.1f}%)")
    print(f"❌ Unclassified: {len(unclassified_pages)} ({len(unclassified_pages)/total_pages*100:.1f}%)")
    
    # Topic distribution
    topic_counts = Counter()
    for page in classified_pages:
        for topic in page['topics']:
            topic_counts[topic] += 1
    
    print(f"\n📚 Topic Distribution:")
    for topic, count in topic_counts.most_common():
        pct = count / len(classified_pages) * 100
        print(f"   {topic}: {count} ({pct:.1f}%)")
    
    # Difficulty distribution
    difficulty_counts = Counter(p['difficulty'] for p in classified_pages if p['difficulty'])
    print(f"\n⚡ Difficulty Distribution:")
    for difficulty in ['easy', 'medium', 'hard']:
        count = difficulty_counts.get(difficulty, 0)
        pct = count / len(classified_pages) * 100 if classified_pages else 0
        print(f"   {difficulty.capitalize()}: {count} ({pct:.1f}%)")
    
    # Confidence stats
    confidences = [p['confidence'] for p in classified_pages if p['confidence'] is not None]
    if confidences:
        avg_confidence = sum(confidences) / len(confidences)
        print(f"\n🎯 Average Confidence: {avg_confidence:.2f}")
        print(f"   High confidence (>0.8): {sum(1 for c in confidences if c > 0.8)} ({sum(1 for c in confidences if c > 0.8)/len(confidences)*100:.1f}%)")
        print(f"   Medium confidence (0.5-0.8): {sum(1 for c in confidences if 0.5 <= c <= 0.8)} ({sum(1 for c in confidences if 0.5 <= c <= 0.8)/len(confidences)*100:.1f}%)")
        print(f"   Low confidence (<0.5): {sum(1 for c in confidences if c < 0.5)} ({sum(1 for c in confidences if c < 0.5)/len(confidences)*100:.1f}%)")


def show_by_year(papers, pages):
    """Show classifications grouped by year."""
    print("\n" + "="*80)
    print("📅 CLASSIFICATIONS BY YEAR")
    print("="*80)
    
    # Group by year
    by_year = defaultdict(list)
    for page in pages:
        by_year[page['year']].append(page)
    
    for year in sorted(by_year.keys()):
        year_pages = by_year[year]
        classified = [p for p in year_pages if p['topics'] and len(p['topics']) > 0]
        
        print(f"\n📆 {year}: {len(year_pages)} questions, {len(classified)} classified ({len(classified)/len(year_pages)*100:.1f}%)")
        
        # Topic breakdown for this year
        topic_counts = Counter()
        for page in classified:
            for topic in page['topics']:
                topic_counts[topic] += 1
        
        if topic_counts:
            print(f"   Topics: {dict(topic_counts)}")
        
        # Papers in this year
        year_papers = [p for p in papers if p['year'] == year]
        seasons = Counter(f"{p['season']} {p['paper_number']}" for p in year_papers)
        print(f"   Papers: {dict(seasons)}")


def show_by_topic(papers, pages):
    """Show classifications grouped by topic."""
    print("\n" + "="*80)
    print("📚 CLASSIFICATIONS BY TOPIC")
    print("="*80)
    
    # Group by topic
    by_topic = defaultdict(list)
    for page in pages:
        if page['topics']:
            for topic in page['topics']:
                by_topic[topic].append(page)
    
    # Topic names (from physics_topics.yaml)
    topic_names = {
        'FM': 'Forces and Motion',
        'KIN': 'Kinematics',
        'DYN': 'Dynamics',
        'EN': 'Energy',
        'WAVE': 'Waves',
        'ELEC': 'Electricity',
        'MAG': 'Magnetism',
        'NUC': 'Nuclear Physics'
    }
    
    for topic_id in sorted(by_topic.keys()):
        topic_pages = by_topic[topic_id]
        topic_name = topic_names.get(topic_id, topic_id)
        
        print(f"\n📖 {topic_name} ({topic_id}): {len(topic_pages)} questions")
        
        # Year distribution
        year_counts = Counter(p['year'] for p in topic_pages)
        print(f"   Years: {dict(sorted(year_counts.items()))}")
        
        # Difficulty distribution
        difficulty_counts = Counter(p['difficulty'] for p in topic_pages if p['difficulty'])
        print(f"   Difficulty: {dict(difficulty_counts)}")
        
        # Average confidence
        confidences = [p['confidence'] for p in topic_pages if p['confidence'] is not None]
        if confidences:
            avg_conf = sum(confidences) / len(confidences)
            print(f"   Avg Confidence: {avg_conf:.2f}")


def show_by_difficulty(papers, pages):
    """Show classifications grouped by difficulty."""
    print("\n" + "="*80)
    print("⚡ CLASSIFICATIONS BY DIFFICULTY")
    print("="*80)
    
    classified = [p for p in pages if p['difficulty']]
    
    for difficulty in ['easy', 'medium', 'hard']:
        diff_pages = [p for p in classified if p['difficulty'] == difficulty]
        
        print(f"\n{difficulty.upper()}: {len(diff_pages)} questions ({len(diff_pages)/len(classified)*100:.1f}%)")
        
        # Topic distribution
        topic_counts = Counter()
        for page in diff_pages:
            for topic in page.get('topics', []):
                topic_counts[topic] += 1
        
        if topic_counts:
            print(f"   Topics: {dict(topic_counts.most_common())}")
        
        # Year distribution
        year_counts = Counter(p['year'] for p in diff_pages)
        print(f"   Years: {dict(sorted(year_counts.items()))}")


def query_by_year(papers, pages, year):
    """Query specific year."""
    print("\n" + "="*80)
    print(f"📅 PHYSICS CLASSIFICATIONS - {year}")
    print("="*80)
    
    year_pages = [p for p in pages if p['year'] == year]
    
    if not year_pages:
        print(f"\n❌ No data found for year {year}")
        return
    
    classified = [p for p in year_pages if p['topics'] and len(p['topics']) > 0]
    
    print(f"\n📊 Overview:")
    print(f"   Total Questions: {len(year_pages)}")
    print(f"   Classified: {len(classified)} ({len(classified)/len(year_pages)*100:.1f}%)")
    
    # Group by paper
    by_paper = defaultdict(list)
    for page in year_pages:
        key = f"{page['season']} {page['paper_number']}"
        by_paper[key].append(page)
    
    print(f"\n📄 Papers:")
    for paper_key in sorted(by_paper.keys()):
        paper_pages = by_paper[paper_key]
        paper_classified = [p for p in paper_pages if p['topics'] and len(p['topics']) > 0]
        
        print(f"\n   {paper_key}: {len(paper_pages)} questions")
        
        # List questions with their classifications
        for page in sorted(paper_pages, key=lambda x: int(x['question_number'])):
            qnum = page['question_number']
            topics = ', '.join(page['topics']) if page['topics'] else 'Unclassified'
            difficulty = page.get('difficulty', 'N/A')
            confidence = page.get('confidence', 0)
            
            status = "✅" if page['topics'] else "❌"
            print(f"      {status} Q{qnum}: {topics} | {difficulty} | conf={confidence:.2f}")


def query_by_topic(papers, pages, topic_id):
    """Query specific topic."""
    print("\n" + "="*80)
    print(f"📚 PHYSICS CLASSIFICATIONS - TOPIC: {topic_id}")
    print("="*80)
    
    topic_pages = [p for p in pages if topic_id in p.get('topics', [])]
    
    if not topic_pages:
        print(f"\n❌ No questions found for topic {topic_id}")
        return
    
    print(f"\n📊 Overview:")
    print(f"   Total Questions: {len(topic_pages)}")
    
    # Difficulty distribution
    difficulty_counts = Counter(p['difficulty'] for p in topic_pages if p['difficulty'])
    print(f"   Difficulty: {dict(difficulty_counts)}")
    
    # Average confidence
    confidences = [p['confidence'] for p in topic_pages if p['confidence'] is not None]
    if confidences:
        avg_conf = sum(confidences) / len(confidences)
        print(f"   Avg Confidence: {avg_conf:.2f}")
    
    # Group by year
    by_year = defaultdict(list)
    for page in topic_pages:
        by_year[page['year']].append(page)
    
    print(f"\n📅 By Year:")
    for year in sorted(by_year.keys()):
        year_pages = by_year[year]
        print(f"\n   {year}: {len(year_pages)} questions")
        
        # List questions
        for page in sorted(year_pages, key=lambda x: (x['season'], x['paper_number'], int(x['question_number']))):
            qnum = page['question_number']
            paper_id = f"{page['season']} {page['paper_number']}"
            difficulty = page.get('difficulty', 'N/A')
            confidence = page.get('confidence', 0)
            
            print(f"      Q{qnum} ({paper_id}): {difficulty} | conf={confidence:.2f}")


def main():
    parser = argparse.ArgumentParser(description='Query Physics classifications')
    parser.add_argument('--summary', action='store_true', help='Show overall summary')
    parser.add_argument('--by-year', action='store_true', help='Show breakdown by year')
    parser.add_argument('--by-topic', action='store_true', help='Show breakdown by topic')
    parser.add_argument('--by-difficulty', action='store_true', help='Show breakdown by difficulty')
    parser.add_argument('--year', type=int, help='Query specific year')
    parser.add_argument('--topic', type=str, help='Query specific topic (e.g., FM, KIN, ELEC)')
    
    args = parser.parse_args()
    
    # If no arguments, show summary
    if not any([args.summary, args.by_year, args.by_topic, args.by_difficulty, args.year, args.topic]):
        args.summary = True
    
    # Fetch data
    papers, pages = get_all_physics_data()
    
    # Execute queries
    if args.summary:
        show_summary(papers, pages)
    
    if args.by_year:
        show_by_year(papers, pages)
    
    if args.by_topic:
        show_by_topic(papers, pages)
    
    if args.by_difficulty:
        show_by_difficulty(papers, pages)
    
    if args.year:
        query_by_year(papers, pages, args.year)
    
    if args.topic:
        query_by_topic(papers, pages, args.topic.upper())
    
    print("\n" + "="*80)
    print("✅ Query complete!")
    print("="*80)


if __name__ == "__main__":
    main()
