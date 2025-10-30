"""
Analyze question counts by year to verify detection accuracy
"""
import os
import json
from pathlib import Path
from collections import defaultdict

processed_dir = Path('data/processed/Further Pure Maths Processed')

# Group by year
by_year = defaultdict(list)

for paper_dir in sorted(processed_dir.iterdir()):
    if not paper_dir.is_dir():
        continue
    
    manifest_path = paper_dir / 'manifest.json'
    if not manifest_path.exists():
        continue
    
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    # Parse directory name: e.g., "2011_Jun_1P"
    parts = paper_dir.name.split('_')
    year = int(parts[0])
    session = parts[1]
    paper_num = parts[2].replace('P', '')
    
    q_count = manifest['total_questions']
    
    by_year[year].append({
        'session': session,
        'paper': paper_num,
        'questions': q_count
    })

# Print summary
print("Question counts by year:")
print("=" * 70)

for year in sorted(by_year.keys()):
    papers = by_year[year]
    total_q = sum(p['questions'] for p in papers)
    avg_q = total_q / len(papers) if papers else 0
    
    print(f"\n{year}: {len(papers)} papers, {total_q} total questions (avg {avg_q:.1f} per paper)")
    
    # Show individual papers
    for paper in papers:
        status = "✓" if 9 <= paper['questions'] <= 11 else "⚠"
        print(f"  {status} {paper['session']} P{paper['paper']}: {paper['questions']} questions")

# Check for papers with unusual counts
print("\n" + "=" * 70)
print("Papers with unusual question counts:")
print("=" * 70)

for year in sorted(by_year.keys()):
    for paper in by_year[year]:
        if paper['questions'] < 8 or paper['questions'] > 11:
            print(f"⚠ {year} {paper['session']} P{paper['paper']}: {paper['questions']} questions")
