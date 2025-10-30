#!/usr/bin/env python3
"""Analyze classification quality"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from collections import Counter

env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(env_path)

url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
supabase = create_client(url, service_key)

# Get all Physics pages
pages_result = supabase.table('pages').select('topics, difficulty').eq('is_question', True).execute()
pages = pages_result.data

print("=" * 70)
print("📊 CLASSIFICATION ANALYSIS")
print("=" * 70)
print()

# Basic stats
total = len(pages)
with_difficulty = sum(1 for p in pages if p.get('difficulty'))
with_valid_topics = sum(1 for p in pages if p.get('topics') and any(t in ['1','2','3','4','5','6','7','8'] for t in p['topics']))

print(f"📈 Coverage:")
print(f"   Total pages: {total}")
print(f"   With difficulty: {with_difficulty} ({with_difficulty/total*100:.1f}%)")
print(f"   With valid topics: {with_valid_topics} ({with_valid_topics/total*100:.1f}%)")
print()

# Difficulty distribution
diff_counts = Counter(p.get('difficulty') for p in pages if p.get('difficulty'))
print(f"🎯 Difficulty Distribution:")
print(f"   Easy: {diff_counts.get('easy', 0)} ({diff_counts.get('easy', 0)/with_difficulty*100:.1f}%)")
print(f"   Medium: {diff_counts.get('medium', 0)} ({diff_counts.get('medium', 0)/with_difficulty*100:.1f}%)")
print(f"   Hard: {diff_counts.get('hard', 0)} ({diff_counts.get('hard', 0)/with_difficulty*100:.1f}%)")
print()

# Topic distribution
topic_counts = Counter()
for p in pages:
    if p.get('topics'):
        topic_counts.update(p['topics'])

print(f"📚 Topic Distribution:")
valid_topic_counts = {t: topic_counts[t] for t in ['1','2','3','4','5','6','7','8'] if t in topic_counts}
for topic, count in sorted(valid_topic_counts.items()):
    pct = count / with_valid_topics * 100 if with_valid_topics > 0 else 0
    print(f"   Topic {topic}: {count:3d} ({pct:5.1f}%)")
print()

# Topic names for reference
topic_names = {
    "1": "Forces & Motion",
    "2": "Electricity",
    "3": "Waves",
    "4": "Energy",
    "5": "Matter",
    "6": "Magnetism",
    "7": "Nuclear",
    "8": "Astrophysics"
}

print("📖 Topic Reference:")
for topic, name in sorted(topic_names.items()):
    count = valid_topic_counts.get(topic, 0)
    print(f"   {topic}. {name}: {count} questions")
print()

# Quality assessment
print("✅ Quality Assessment:")
if diff_counts.get('medium', 0) / with_difficulty > 0.8:
    print("   ⚠️  WARNING: >80% questions marked as 'medium' difficulty")
    print("      This suggests the classifier is defaulting to medium for uncertainty")
else:
    print("   ✅ Difficulty distribution looks reasonable")

topic_balance = max(valid_topic_counts.values()) / min(valid_topic_counts.values()) if valid_topic_counts else 0
if topic_balance > 3:
    print(f"   ⚠️  WARNING: Topic distribution is unbalanced (ratio: {topic_balance:.1f}:1)")
    print("      Most common vs least common topic differs by >3x")
else:
    print(f"   ✅ Topic distribution is reasonably balanced (ratio: {topic_balance:.1f}:1)")

print()
print("🎉 Classification complete! Test at http://localhost:3000/generate")
