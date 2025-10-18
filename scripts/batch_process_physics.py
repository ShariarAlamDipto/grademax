"""
Batch Process All Physics Papers
Processes all papers in data/raw/IGCSE/Physics/
Handles errors gracefully and continues processing
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import json

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from page_based_ingest import PageBasedPipeline


def find_all_paper_pairs(base_dir: str = "data/raw/IGCSE/Physics"):
    """
    Find all paper pairs (QP + MS) in Physics directory
    
    Returns: List of (qp_path, ms_path, year, season, paper_num) tuples
    """
    base_path = Path(base_dir)
    pairs = []
    
    if not base_path.exists():
        print(f"❌ Directory not found: {base_dir}")
        return pairs
    
    # Walk through year folders
    for year_dir in sorted(base_path.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        
        year = year_dir.name
        
        # Walk through season folders
        for season_dir in sorted(year_dir.iterdir()):
            if not season_dir.is_dir():
                continue
            
            season = season_dir.name
            
            # Find all Paper X.pdf files
            qp_files = list(season_dir.glob("Paper *.pdf"))
            
            for qp_file in qp_files:
                # Skip if it's a mark scheme
                if '_MS' in qp_file.name or ' MS' in qp_file.name:
                    continue
                
                # Extract paper number
                paper_num = qp_file.stem.replace('Paper ', '').strip()
                
                # Find corresponding MS
                ms_candidates = [
                    season_dir / f"Paper {paper_num}_MS.pdf",
                    season_dir / f"Paper {paper_num} MS.pdf",
                    season_dir / f"{qp_file.stem}_MS.pdf"
                ]
                
                ms_file = None
                for candidate in ms_candidates:
                    if candidate.exists():
                        ms_file = candidate
                        break
                
                if ms_file:
                    pairs.append((str(qp_file), str(ms_file), year, season, paper_num))
                else:
                    print(f"   ⚠️  No MS found for: {year}/{season}/Paper {paper_num}")
    
    return pairs


def process_batch(papers, skip_existing=True, start_from=0):
    """
    Process a batch of papers
    
    Args:
        papers: List of (qp_path, ms_path, year, season, paper_num) tuples
        skip_existing: If True, skip papers already in database
        start_from: Index to start from (for resuming)
    """
    pipeline = PageBasedPipeline()
    
    total = len(papers)
    processed = 0
    failed = 0
    skipped = 0
    
    print(f"\n{'='*70}")
    print(f"📚 BATCH PROCESSING: {total} papers")
    print(f"{'='*70}\n")
    
    # Create log file
    log_file = f"batch_process_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = Path("logs") / log_file
    log_path.parent.mkdir(exist_ok=True)
    
    with open(log_path, 'w', encoding='utf-8') as log:
        log.write(f"Batch Processing Log - {datetime.now()}\n")
        log.write(f"Total papers: {total}\n")
        log.write(f"Starting from index: {start_from}\n\n")
        
        for i, (qp_path, ms_path, year, season, paper_num) in enumerate(papers[start_from:], start=start_from):
            paper_id = f"{year}_{season}_Paper{paper_num}"
            
            print(f"\n[{i+1}/{total}] Processing: {paper_id}")
            log.write(f"\n[{i+1}/{total}] {paper_id}\n")
            log.write(f"  QP: {qp_path}\n")
            log.write(f"  MS: {ms_path}\n")
            
            # Check if already processed
            if skip_existing:
                # Query database to check if paper exists
                try:
                    # Extract watermark to get normalized season
                    watermark = pipeline._extract_watermark_metadata(qp_path)
                    if watermark:
                        normalized_season = pipeline._normalize_season(watermark['season'])
                        paper_num_formatted = f"{watermark['paper']}P"
                    else:
                        normalized_season = 'Jun' if 'May' in season or 'Jun' in season else 'Jan'
                        paper_num_formatted = f"{paper_num}P"
                    
                    # Check database
                    subjects = pipeline.db.select('subjects', filters={'code': 'eq.4PH1'})
                    if subjects:
                        subject_uuid = subjects[0]['id']
                        filters = {
                            'subject_id': f'eq.{subject_uuid}',
                            'year': f'eq.{year}',
                            'season': f'eq.{normalized_season}',
                            'paper_number': f'eq.{paper_num_formatted}'
                        }
                        existing = pipeline.db.select('papers', filters=filters)
                        
                        if existing:
                            print(f"   ⏭️  Already processed, skipping...")
                            log.write(f"  Status: SKIPPED (already exists)\n")
                            skipped += 1
                            continue
                except Exception as e:
                    print(f"   ⚠️  Could not check database: {e}")
                    log.write(f"  Warning: Could not check database - {e}\n")
            
            # Process paper
            try:
                pipeline.process_paper_pair(qp_path, ms_path)
                processed += 1
                log.write(f"  Status: SUCCESS\n")
                print(f"   ✅ Success!")
                
            except KeyboardInterrupt:
                print(f"\n\n⚠️  Interrupted by user!")
                log.write(f"\n\nInterrupted by user at paper {i+1}/{total}\n")
                log.write(f"\nSummary:\n")
                log.write(f"  Processed: {processed}/{total}\n")
                log.write(f"  Failed: {failed}\n")
                log.write(f"  Skipped: {skipped}\n")
                print(f"\n📊 Progress saved. Resume from index {i} with:")
                print(f"   python scripts/batch_process_physics.py --start-from {i}")
                return
                
            except Exception as e:
                failed += 1
                error_msg = str(e)
                print(f"   ❌ Failed: {error_msg}")
                log.write(f"  Status: FAILED\n")
                log.write(f"  Error: {error_msg}\n")
                
                # Continue to next paper
                continue
        
        # Final summary
        log.write(f"\n{'='*70}\n")
        log.write(f"BATCH COMPLETE\n")
        log.write(f"{'='*70}\n")
        log.write(f"Processed: {processed}/{total}\n")
        log.write(f"Failed: {failed}\n")
        log.write(f"Skipped: {skipped}\n")
    
    print(f"\n{'='*70}")
    print(f"📊 BATCH COMPLETE!")
    print(f"{'='*70}")
    print(f"✅ Processed: {processed}/{total}")
    print(f"❌ Failed: {failed}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"\n📝 Log saved to: {log_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch process all Physics papers')
    parser.add_argument('--skip-existing', action='store_true', default=True,
                       help='Skip papers already in database (default: True)')
    parser.add_argument('--no-skip', dest='skip_existing', action='store_false',
                       help='Process all papers, even if already in database')
    parser.add_argument('--start-from', type=int, default=0,
                       help='Start from specific index (for resuming)')
    parser.add_argument('--list-only', action='store_true',
                       help='Only list papers, don\'t process')
    
    args = parser.parse_args()
    
    print("🔍 Scanning for paper pairs...")
    papers = find_all_paper_pairs()
    
    if not papers:
        print("❌ No papers found!")
        return
    
    print(f"✅ Found {len(papers)} paper pairs\n")
    
    if args.list_only:
        print("Papers found:")
        for i, (qp, ms, year, season, paper_num) in enumerate(papers):
            print(f"  [{i}] {year} {season} Paper {paper_num}")
        return
    
    # Show summary
    years = set(p[2] for p in papers)
    print(f"📅 Years: {min(years)} - {max(years)}")
    print(f"📄 Total papers: {len(papers)}")
    
    if args.start_from > 0:
        print(f"▶️  Starting from index: {args.start_from}")
    
    print()
    
    # Confirm before starting
    if args.start_from == 0:
        response = input("🚀 Start batch processing? (yes/no): ").strip().lower()
        if response != 'yes':
            print("❌ Cancelled")
            return
    
    # Process
    process_batch(papers, skip_existing=args.skip_existing, start_from=args.start_from)


if __name__ == "__main__":
    main()
