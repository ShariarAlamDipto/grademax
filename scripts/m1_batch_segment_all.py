#!/usr/bin/env python3
"""
Batch segment ALL M1 papers from data/raw/IAL/Mechanics_1/
Processes each year/season paper and saves to data/processed/Mechanics_1/
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from m1_hardened_segmentation import M1Processor

def find_all_m1_papers(base_dir: Path):
    """Find all M1 papers in the directory structure"""
    papers = []
    
    # Walk through year directories
    for year_dir in sorted(base_dir.iterdir()):
        if not year_dir.is_dir():
            continue
        
        year = year_dir.name
        
        # Walk through season directories
        for season_dir in sorted(year_dir.iterdir()):
            if not season_dir.is_dir():
                continue
            
            season = season_dir.name
            
            # Check for Paper.pdf and Paper_MS.pdf
            qp_pdf = season_dir / "Paper.pdf"
            ms_pdf = season_dir / "Paper_MS.pdf"
            
            if qp_pdf.exists():
                papers.append({
                    'year': year,
                    'season': season,
                    'qp_path': qp_pdf,
                    'ms_path': ms_pdf if ms_pdf.exists() else None
                })
    
    return papers

def normalize_season(season: str) -> str:
    """Normalize season names"""
    season_map = {
        'Jan': 'Jan',
        'May-Jun': 'Jun',
        'Oct-Nov': 'Oct'
    }
    return season_map.get(season, season)

def main():
    """Process all M1 papers"""
    
    # Paths
    base_dir = Path(__file__).parent.parent
    raw_dir = base_dir / 'data' / 'raw' / 'IAL' / 'Mechanics_1'
    output_dir = base_dir / 'data' / 'processed' / 'Mechanics_1'
    
    # Find all papers
    print(f"\n{'='*80}")
    print(f"M1 BATCH SEGMENTATION")
    print(f"{'='*80}")
    print(f"Source: {raw_dir}")
    print(f"Output: {output_dir}")
    
    papers = find_all_m1_papers(raw_dir)
    print(f"\nFound {len(papers)} M1 papers")
    
    # Initialize segmenter
    segmenter = M1Processor()
    
    # Statistics
    total_papers = len(papers)
    successful = 0
    failed = []
    total_questions = 0
    
    # Process each paper
    for i, paper in enumerate(papers, 1):
        year = paper['year']
        season = paper['season']
        season_short = normalize_season(season)
        qp_path = paper['qp_path']
        ms_path = paper['ms_path']
        
        print(f"\n{'='*80}")
        print(f"[{i}/{total_papers}] Processing: {year} {season}")
        print(f"{'='*80}")
        print(f"QP: {qp_path.name}")
        print(f"MS: {ms_path.name if ms_path else 'NOT FOUND'}")
        
        try:
            # Process paper
            result = segmenter.process_paper(
                qp_path=str(qp_path),
                ms_path=str(ms_path) if ms_path else None,
                year=int(year),
                season=season_short,
                paper_number='P1'  # All M1 papers are P1
            )
            
            if result and 'error' not in result:
                n_questions = len(result.get('questions', []))
                
                # Save JSON result
                json_filename = f"{year}_{season_short}_P1_segmented.json"
                json_path = output_dir / json_filename
                
                with open(json_path, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                # Extract question PDFs
                segmenter.extract_question_pdfs(
                    qp_path=str(qp_path),
                    ms_path=str(ms_path) if ms_path else None,
                    questions=result['questions'],
                    output_dir=output_dir,
                    year=int(year),
                    season=season_short,
                    paper_number='P1'
                )
                
                total_questions += n_questions
                successful += 1
                print(f"SUCCESS: {n_questions} questions detected")
                print(f"Saved: {json_filename}")
            else:
                failed.append(f"{year}_{season}")
                print(f"FAILED: No result returned")
                
        except KeyboardInterrupt:
            print(f"\n\nInterrupted by user. Stopping...")
            break
        except Exception as e:
            failed.append(f"{year}_{season}")
            print(f"ERROR: {str(e)[:200]}")
            continue
    
    # Final summary
    print(f"\n{'='*80}")
    print(f"BATCH SEGMENTATION COMPLETE")
    print(f"{'='*80}")
    print(f"Successful: {successful}/{total_papers} ({successful/total_papers*100:.1f}%)")
    print(f"Total Questions: {total_questions}")
    
    if failed:
        print(f"\nFailed Papers ({len(failed)}):")
        for paper_id in failed:
            print(f"   - {paper_id}")
    
    print(f"\nOutput directory: {output_dir}")
    print(f"   - JSON files: {output_dir}/*.json")
    print(f"   - QP PDFs: {output_dir}/pages/")
    print(f"   - MS PDFs: {output_dir}/markschemes/")

if __name__ == '__main__':
    main()
