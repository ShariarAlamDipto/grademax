"""
Test the LLM analyzer on multiple papers to verify robustness.
Also test which APIs are working (OpenRouter vs Groq).
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.analyze_physics_llm import analyze_paper_with_llm

# Test papers from different years
test_cases = [
    {
        "year": 2015,
        "season": "Jan",
        "paper": 1,
        "qp": r"data\raw\IGCSE\Physics\2015\Jan\Paper 1.pdf",
        "ms": r"data\raw\IGCSE\Physics\2015\Jan\Paper 1_MS.pdf"
    },
    {
        "year": 2020,
        "season": "Jan",
        "paper": 1,
        "qp": r"data\raw\IGCSE\Physics\2020\Jan\Paper 1.pdf",
        "ms": r"data\raw\IGCSE\Physics\2020\Jan\Paper 1_MS.pdf"
    },
    {
        "year": 2024,
        "season": "May-Jun",
        "paper": 1,
        "qp": r"data\raw\IGCSE\Physics\2024\May-Jun\Paper 1.pdf",
        "ms": r"data\raw\IGCSE\Physics\2024\May-Jun\Paper 1_MS.pdf"
    },
    {
        "year": 2022,
        "season": "May-Jun",
        "paper": 2,
        "qp": r"data\raw\IGCSE\Physics\2022\May-Jun\Paper 2.pdf",
        "ms": r"data\raw\IGCSE\Physics\2022\May-Jun\Paper 2_MS.pdf"
    }
]

print("="*80)
print("TESTING MULTIPLE PHYSICS PAPERS")
print("="*80)
print(f"\nTesting {len(test_cases)} papers across different years\n")

results = []

for i, test in enumerate(test_cases, 1):
    print(f"\n{'='*80}")
    print(f"TEST {i}/{len(test_cases)}: {test['year']} {test['season']} Paper {test['paper']}")
    print(f"{'='*80}")
    
    # Check if files exist
    if not Path(test['qp']).exists():
        print(f"❌ QP not found: {test['qp']}")
        results.append({"test": i, "status": "missing_qp"})
        continue
    
    if not Path(test['ms']).exists():
        print(f"❌ MS not found: {test['ms']}")
        results.append({"test": i, "status": "missing_ms"})
        continue
    
    try:
        analysis = analyze_paper_with_llm(
            test['qp'],
            test['ms'],
            test['year'],
            test['season'],
            test['paper']
        )
        
        if analysis and "questions" in analysis:
            num_questions = len(analysis["questions"])
            print(f"\n✅ SUCCESS: Found {num_questions} questions")
            
            # Show first 3 questions as sample
            print(f"\nSample questions:")
            for q in analysis["questions"][:3]:
                print(f"  Q{q['qnum']}: QP pages {q['qp_pages']}, MS pages {q['ms_pages']}")
            
            results.append({
                "test": i,
                "status": "success",
                "questions": num_questions,
                "year": test['year'],
                "season": test['season'],
                "paper": test['paper']
            })
        else:
            print(f"\n❌ FAILED: No analysis returned")
            results.append({"test": i, "status": "failed"})
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        results.append({"test": i, "status": "error", "error": str(e)})
    
    # Wait between tests to avoid rate limits
    if i < len(test_cases):
        print(f"\n⏳ Waiting 60 seconds before next test to avoid rate limits...")
        import time
        time.sleep(60)

# Summary
print("\n\n" + "="*80)
print("SUMMARY")
print("="*80)

success_count = sum(1 for r in results if r.get("status") == "success")
print(f"\n✅ Successful: {success_count}/{len(test_cases)}")
print(f"❌ Failed: {len(test_cases) - success_count}/{len(test_cases)}")

print("\nDetailed results:")
for r in results:
    status_icon = "✅" if r.get("status") == "success" else "❌"
    if r.get("status") == "success":
        print(f"  {status_icon} Test {r['test']}: {r['year']} {r['season']} Paper {r['paper']} - {r['questions']} questions")
    else:
        print(f"  {status_icon} Test {r['test']}: {r.get('status', 'unknown')}")
