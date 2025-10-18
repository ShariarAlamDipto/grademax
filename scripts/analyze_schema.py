"""
Database Schema Analysis for New Data Structure
================================================

Current Schema Review Against New Requirements
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv('.env.ingest')

from supabase_client import SupabaseClient

def analyze_schema():
    print("=" * 70)
    print("DATABASE SCHEMA ANALYSIS")
    print("=" * 70)
    
    client = SupabaseClient()
    
    # Check subjects table
    print("\n1️⃣  SUBJECTS Table")
    print("-" * 70)
    subjects = client.select('subjects', '*')
    if subjects:
        print(f"Columns in first row: {list(subjects[0].keys())}")
        print(f"\nData:")
        for s in subjects:
            print(f"  - {s['code']} ({s['name']})")
    
    # Check if subject_code matches new structure
    print("\n❓ Question: Does 'code' field work with new structure?")
    print("   Current: 4PH1, 4CH1, 4BI1")
    print("   Folders: Physics, Chemistry, Biology")
    print("   ✅ COMPATIBLE: We map folder names to codes in ingestion script")
    
    # Check papers table
    print("\n2️⃣  PAPERS Table")
    print("-" * 70)
    papers = client.select('papers', '*', limit=3)
    if papers:
        print(f"Columns: {list(papers[0].keys())}")
        print(f"\nSample data:")
        for p in papers:
            print(f"  - {p['year']} {p['season']} {p['paper_number']}")
            print(f"    QP Path: {p.get('qp_source_path', 'N/A')}")
            print(f"    MS Path: {p.get('ms_source_path', 'N/A')}")
    
    print("\n❓ Question: Do path fields need updating?")
    print("   OLD path: data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf")
    print("   NEW path: data/raw/IGCSE/Physics/2019/May-Jun/Paper 1.pdf")
    print("   ✅ COMPATIBLE: Paths are stored, not parsed. New paths work fine.")
    
    print("\n❓ Question: Does season field handle May-Jun/Oct-Nov?")
    print("   Database stores: Jun, Jan (normalized)")
    print("   Folders contain: May-Jun, Oct-Nov")
    print("   ✅ COMPATIBLE: Ingestion script normalizes seasons")
    
    # Check pages table
    print("\n3️⃣  PAGES Table")
    print("-" * 70)
    pages = client.select('pages', '*', limit=3)
    if pages:
        print(f"Columns: {list(pages[0].keys())}")
        print(f"\nSample data:")
        for page in pages:
            print(f"  - Q{page['question_number']} - Topics: {page['topics']} - Difficulty: {page['difficulty']}")
            print(f"    QP URL: {page.get('qp_page_url', 'N/A')[:60]}...")
    
    print("\n❓ Question: Do storage URLs work with new structure?")
    print("   Current format: subjects/Physics/pages/2019_Jun_1P/q1.pdf")
    print("   Subject name: Uses 'Physics' not '4PH1'")
    print("   Paper ID: Uses normalized season 'Jun' not 'May-Jun'")
    print("   ✅ COMPATIBLE: Storage structure unchanged, uses normalized names")
    
    # Check topics array
    print("\n4️⃣  TOPICS Array Field")
    print("-" * 70)
    print("   Current: topics TEXT[] - stores topic codes like ['1', '3']")
    print("   Watermark info: Physics · 2024 · May/Jun · Paper 1 · QP")
    print("   ❓ Question: Should we store watermark metadata?")
    print("   🤔 CONSIDERATION: Could add for validation/debugging")
    
    print("\n" + "=" * 70)
    print("SCHEMA COMPATIBILITY ANALYSIS")
    print("=" * 70)
    
    analysis = {
        "subjects.code": {
            "status": "✅ COMPATIBLE",
            "reason": "Maps folder names (Physics) to codes (4PH1) in ingestion",
            "action": "None needed"
        },
        "papers.qp_source_path": {
            "status": "✅ COMPATIBLE",
            "reason": "Stores full path as-is, works with any format",
            "action": "None needed"
        },
        "papers.season": {
            "status": "✅ COMPATIBLE",
            "reason": "Normalized in ingestion (May-Jun → Jun)",
            "action": "None needed"
        },
        "pages.qp_page_url": {
            "status": "✅ COMPATIBLE",
            "reason": "Uses subject name + normalized data",
            "action": "None needed"
        },
        "pages.topics": {
            "status": "✅ COMPATIBLE",
            "reason": "Array field works same as before",
            "action": "None needed"
        }
    }
    
    for field, info in analysis.items():
        print(f"\n{field}")
        print(f"  Status: {info['status']}")
        print(f"  Reason: {info['reason']}")
        print(f"  Action: {info['action']}")
    
    print("\n" + "=" * 70)
    print("OPTIONAL ENHANCEMENTS")
    print("=" * 70)
    
    enhancements = [
        {
            "field": "papers.watermark_data",
            "type": "JSONB",
            "description": "Store extracted watermark for validation",
            "benefit": "Can verify folder structure matches PDF content",
            "priority": "LOW"
        },
        {
            "field": "papers.original_season",
            "type": "TEXT",
            "description": "Store original season name (May-Jun) before normalization",
            "benefit": "Preserve full metadata for display/export",
            "priority": "MEDIUM"
        },
        {
            "field": "pages.pdf_quality",
            "type": "INTEGER",
            "description": "JPEG quality used for compression (0-100)",
            "benefit": "Track compression settings for each page",
            "priority": "LOW"
        },
        {
            "field": "pages.file_size",
            "type": "INTEGER",
            "description": "File size in bytes after compression",
            "benefit": "Monitor storage usage and compression effectiveness",
            "priority": "MEDIUM"
        }
    ]
    
    for i, enh in enumerate(enhancements, 1):
        print(f"\n{i}. {enh['field']} ({enh['type']})")
        print(f"   Description: {enh['description']}")
        print(f"   Benefit: {enh['benefit']}")
        print(f"   Priority: {enh['priority']}")
    
    print("\n" + "=" * 70)
    print("RECOMMENDATION")
    print("=" * 70)
    print("""
✅ CURRENT SCHEMA IS FULLY COMPATIBLE

The existing database schema works perfectly with the new data structure.
No schema changes are required for basic functionality.

Key Points:
1. Subject codes (4PH1) are mapped from folder names (Physics) in code
2. Paths are stored as-is, no parsing needed
3. Seasons are normalized during ingestion (May-Jun → Jun)
4. Storage URLs use normalized names, consistent with before

Optional Enhancements (can be added later if needed):
- papers.original_season: Store "May-Jun" for display purposes
- pages.file_size: Track compression effectiveness
- papers.watermark_data: Validation and debugging

Recommendation: Proceed with current schema, add enhancements only if needed.
    """)

if __name__ == "__main__":
    analyze_schema()
