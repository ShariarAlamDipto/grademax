"""
Process ALL Physics Papers with Hardened Algorithm v2.0

This script processes all available Physics papers from the raw data directory
and uploads them to the database with proper question segmentation.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import the hardened processor
from scripts.process_physics_hardened import process_paper

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment
env_path = project_root / '.env.local'
load_dotenv(env_path)

RAW_DATA_DIR = Path("data/raw/IGCSE/Physics")

def discover_papers():
    """Scan raw data directory for all available papers"""
    papers = []
    
    for year_dir in sorted(RAW_DATA_DIR.iterdir()):
        if not year_dir.is_dir():
            continue
        
        year = year_dir.name
        if not year.isdigit():
            continue
        
        for season_dir in sorted(year_dir.iterdir()):
            if not season_dir.is_dir():
                continue
            
            season = season_dir.name
            
            # Look for Paper X.pdf and Paper X_MS.pdf
            for paper_file in sorted(season_dir.glob("Paper *.pdf")):
                if "_MS" in paper_file.name:
                    continue  # Skip mark schemes
                
                # Extract paper number
                paper_num = int(paper_file.stem.split()[-1])
                
                # Check if MS exists
                ms_file = season_dir / f"Paper {paper_num}_MS.pdf"
                
                if ms_file.exists():
                    papers.append({
                        'year': int(year),
                        'season': season,
                        'paper_number': paper_num,
                        'qp_path': paper_file,
                        'ms_path': ms_file
                    })
    
    return papers

def main():
    print("\n" + "="*80)
    print("🚀 PROCESSING ALL PHYSICS PAPERS - HARDENED ALGORITHM v2.0")
    print("="*80)
    
    # Discover all papers
    print("\n📂 Discovering papers...")
    papers = discover_papers()
    
    if not papers:
        print("❌ No papers found!")
        return
    
    print(f"✅ Found {len(papers)} papers to process")
    
    # Show breakdown by year
    from collections import Counter
    year_counts = Counter(p['year'] for p in papers)
    print("\n📊 Breakdown by year:")
    for year in sorted(year_counts.keys()):
        print(f"   {year}: {year_counts[year]} papers")
    
    # Confirm processing
    print(f"\n⚠️  This will process {len(papers)} papers with the hardened algorithm")
    print(f"   Expected: ~{len(papers) * 12} questions (avg 12 per paper)")
    print(f"   Expected MS linking: ~90% based on validation tests")
    
    response = input("\n❓ Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return
    
    # Process all papers
    print("\n" + "="*80)
    print("PROCESSING PAPERS")
    print("="*80)
    
    results = []
    successful = 0
    failed = 0
    
    for i, paper_info in enumerate(papers, 1):
        year = paper_info['year']
        season = paper_info['season']
        paper_num = paper_info['paper_number']
        
        print(f"\n[{i}/{len(papers)}] Processing {year} {season} Paper {paper_num}...")
        
        try:
            result = process_paper(year, season, paper_num)
            
            if result:
                results.append(result)
                successful += 1
                
                # Quick summary
                qs = result['questions']
                with_ms = sum(1 for q in qs if q.get('ms_pages'))
                print(f"   ✅ {len(qs)} questions, {with_ms} with MS ({with_ms/len(qs)*100:.1f}%)")
            else:
                failed += 1
                print(f"   ❌ Failed to process")
                
        except Exception as e:
            failed += 1
            print(f"   ❌ Error: {e}")
    
    # Final summary
    print("\n" + "="*80)
    print("📊 FINAL SUMMARY")
    print("="*80)
    
    print(f"\n✅ Successfully processed: {successful}/{len(papers)} papers")
    if failed > 0:
        print(f"❌ Failed: {failed}/{len(papers)} papers")
    
    if results:
        total_questions = sum(len(r['questions']) for r in results)
        total_with_ms = sum(sum(1 for q in r['questions'] if q.get('ms_pages')) for r in results)
        
        print(f"\n📈 Overall Statistics:")
        print(f"   Total questions: {total_questions}")
        print(f"   Questions with MS: {total_with_ms}")
        print(f"   MS linking rate: {total_with_ms/total_questions*100:.1f}%")
        print(f"   Avg questions/paper: {total_questions/len(results):.1f}")
        
        # Breakdown by year
        from collections import defaultdict
        year_stats = defaultdict(lambda: {'questions': 0, 'with_ms': 0})
        
        for r in results:
            year = r['year']
            qs = r['questions']
            with_ms = sum(1 for q in qs if q.get('ms_pages'))
            year_stats[year]['questions'] += len(qs)
            year_stats[year]['with_ms'] += with_ms
        
        print(f"\n📊 MS Linking by Year:")
        for year in sorted(year_stats.keys()):
            stats = year_stats[year]
            total = stats['questions']
            linked = stats['with_ms']
            pct = (linked/total*100) if total > 0 else 0
            print(f"   {year}: {linked}/{total} ({pct:.1f}%)")
    
    print("\n" + "="*80)
    print("✨ PROCESSING COMPLETE!")
    print("="*80)
    print("\n💡 Next steps:")
    print("   1. Run monitoring script to verify database state")
    print("   2. Classify questions using Groq API")
    print("   3. Test worksheet generation")

if __name__ == "__main__":
    main()
