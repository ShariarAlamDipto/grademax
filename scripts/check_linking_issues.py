#!/usr/bin/env python3
"""
Check for papers with linking issues
"""

import json
from pathlib import Path

processed_dir = Path('data/processed')

print("="*80)
print("PAPERS WITH LINKING ISSUES")
print("="*80)
print()

issues = []
zero_questions = []

for paper_dir in sorted(processed_dir.iterdir()):
    if not paper_dir.is_dir():
        continue
    
    manifest_file = paper_dir / "manifest.json"
    
    if not manifest_file.exists():
        continue
    
    with open(manifest_file, 'r') as f:
        data = json.load(f)
    
    total_q = data['total_questions']
    linked = data['questions_with_markschemes']
    missing = total_q - linked
    
    if total_q == 0:
        zero_questions.append({
            'paper': paper_dir.name,
            'qp_file': data['qp_file'],
            'ms_file': data['ms_file']
        })
    elif missing > 0:
        issues.append({
            'paper': paper_dir.name,
            'questions': total_q,
            'linked': linked,
            'missing': missing,
            'qp_file': data['qp_file'],
            'ms_file': data['ms_file']
        })

# Show papers with zero questions
if zero_questions:
    print("❌ PAPERS WITH ZERO QUESTIONS DETECTED:")
    print("-"*80)
    for item in zero_questions:
        print(f"\n📄 {item['paper']}")
        print(f"   QP: {item['qp_file']}")
        print(f"   MS: {item['ms_file']}")

print("\n")

# Show papers with missing links
if issues:
    print("⚠️  PAPERS WITH MISSING MARKSCHEME LINKS:")
    print("-"*80)
    print(f"{'Paper':<25} {'Questions':<12} {'Linked':<12} {'Missing':<12}")
    print("-"*80)
    
    for item in sorted(issues, key=lambda x: x['missing'], reverse=True):
        print(f"{item['paper']:<25} {item['questions']:<12} {item['linked']:<12} {item['missing']:<12}")
    
    print()
    print(f"Total papers with issues: {len(issues)}")
    print(f"Total missing links: {sum(i['missing'] for i in issues)}")
else:
    print("✅ All papers with questions have complete markscheme links!")

print("\n")
print("="*80)
print("SUMMARY")
print("="*80)
print(f"Papers with zero questions: {len(zero_questions)}")
print(f"Papers with missing links: {len(issues)}")
print(f"Total issues: {len(zero_questions) + len(issues)}")
