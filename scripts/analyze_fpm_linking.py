#!/usr/bin/env python3
"""Analyze Further Pure Maths markscheme linking issues"""

import json
from pathlib import Path

processed_dir = Path("data/processed/Further Pure Maths Processed")

total_papers = 0
total_questions = 0
total_linked = 0
papers_with_issues = []

for paper_dir in sorted(processed_dir.iterdir()):
    if not paper_dir.is_dir():
        continue
    
    manifest_path = paper_dir / "manifest.json"
    if not manifest_path.exists():
        continue
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    total_papers += 1
    qp_questions = manifest.get("total_questions", 0)
    ms_linked = manifest.get("questions_with_markschemes", 0)
    
    total_questions += qp_questions
    total_linked += ms_linked
    
    # Flag papers with low linking rates
    if qp_questions > 0:
        link_rate = ms_linked / qp_questions
        if link_rate < 0.5 and qp_questions > 5:  # Less than 50% linked
            papers_with_issues.append({
                'name': paper_dir.name,
                'qp_questions': qp_questions,
                'ms_linked': ms_linked,
                'rate': link_rate,
                'qp_file': manifest.get('qp_file', ''),
                'ms_file': manifest.get('ms_file', '')
            })

print("="*70)
print("FURTHER PURE MATHS MARKSCHEME LINKING ANALYSIS")
print("="*70)
print(f"Total papers: {total_papers}")
print(f"Total questions: {total_questions}")
print(f"Markschemes linked: {total_linked}")
print(f"Success rate: {100*total_linked/total_questions:.1f}%")
print()
print(f"Papers with <50% linking rate: {len(papers_with_issues)}")
print()

if papers_with_issues:
    print("Sample papers with low linking:")
    for paper in papers_with_issues[:15]:
        print(f"  {paper['name']}: {paper['ms_linked']}/{paper['qp_questions']} linked ({100*paper['rate']:.0f}%)")
    
    # Check if markscheme files exist
    print("\nChecking if markscheme files exist for low-rate papers:")
    for paper in papers_with_issues[:5]:
        ms_file = Path(paper['ms_file'])
        exists = "✓" if ms_file.exists() else "✗"
        print(f"  {exists} {paper['name']}: {ms_file.name if ms_file.exists() else 'MISSING'}")
