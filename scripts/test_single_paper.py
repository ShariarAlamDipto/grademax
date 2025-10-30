"""
Test the complete pipeline on a single paper.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.process_physics_with_llm import process_paper

# Test on 2018 Jan Paper 1 (we know this works from LLM test)
year = 2018
season = "Jan"
paper_number = 1

qp_path = r"data\raw\IGCSE\Physics\2018\Jan\Paper 1.pdf"
ms_path = r"data\raw\IGCSE\Physics\2018\Jan\Paper 1_MS.pdf"

print("Testing complete pipeline on single paper...")
print(f"Paper: {year} {season} Paper {paper_number}")
print()

try:
    process_paper(year, season, paper_number, qp_path, ms_path)
    print("\n✅ TEST SUCCESSFUL")
except Exception as e:
    print(f"\n❌ TEST FAILED: {e}")
    import traceback
    traceback.print_exc()
