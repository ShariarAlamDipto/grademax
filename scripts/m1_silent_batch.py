#!/usr/bin/env python3
"""
Silent M1 batch segmentation - no emojis, minimal output
Processes all M1 papers and saves results
"""

import os
import sys
import json
from pathlib import Path
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from m1_hardened_segmentation import M1Processor

def find_all_m1_papers(base_dir: Path):
    """Find all M1 papers"""
    papers = []
    for year_dir in sorted(base_dir.iterdir()):
        if not year_dir.is_dir():
            continue
        year = year_dir.name
        for season_dir in sorted(year_dir.iterdir()):
            if not season_dir.is_dir():
                continue
            season = season_dir.name
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
    return {'Jan': 'Jan', 'May-Jun': 'Jun', 'Oct-Nov': 'Oct'}.get(season, season)

def main():
    """Process all M1 papers silently"""
    base_dir = Path(__file__).parent.parent
    raw_dir = base_dir / 'data' / 'raw' / 'IAL' / 'Mechanics_1'
    output_dir = base_dir / 'data' / 'processed' / 'Mechanics_1'
    
    print(f"M1 Batch Segmentation")
    print(f"Source: {raw_dir}")
    print(f"Output: {output_dir}\n")
    
    papers = find_all_m1_papers(raw_dir)
    print(f"Found {len(papers)} papers\n")
    
    segmenter = M1Processor()
    successful = 0
    failed = []
    total_questions = 0
    
    for i, paper in enumerate(papers, 1):
        year = paper['year']
        season = paper['season']
        season_short = normalize_season(season)
        
        # Check if already processed
        json_filename = f"{year}_{season_short}_P1_segmented.json"
        json_path = output_dir / json_filename
        if json_path.exists():
            print(f"[{i}/{len(papers)}] {year} {season}... SKIP (exists)")
            # Count questions from existing file
            try:
                with open(json_path, 'r', encoding='utf-8') as jf:
                    existing_data = json.load(jf)
                    n_q = len(existing_data.get('questions', []))
                    if n_q > 0:
                        total_questions += n_q
                        successful += 1
            except:
                pass
            continue
        
        print(f"[{i}/{len(papers)}] {year} {season}...", end=' ', flush=True)
        
        try:
            # Redirect stdout/stderr to suppress emoji output
            f = StringIO()
            with redirect_stdout(f), redirect_stderr(f):
                result = segmenter.process_paper(
                    qp_path=str(paper['qp_path']),
                    ms_path=str(paper['ms_path']) if paper['ms_path'] else None,
                    year=int(year),
                    season=season_short,
                    paper_number='P1'
                )
            
            if result and 'error' not in result:
                n_questions = len(result.get('questions', []))
                
                if n_questions > 0:
                    # Save JSON
                    json_filename = f"{year}_{season_short}_P1_segmented.json"
                    json_path = output_dir / json_filename
                    with open(json_path, 'w', encoding='utf-8') as jf:
                        json.dump(result, jf, indent=2, ensure_ascii=False)
                    
                    # Extract PDFs (also silent)
                    f2 = StringIO()
                    with redirect_stdout(f2), redirect_stderr(f2):
                        segmenter.extract_question_pdfs(
                            qp_path=str(paper['qp_path']),
                            ms_path=str(paper['ms_path']) if paper['ms_path'] else None,
                            questions=result['questions'],
                            output_dir=output_dir,
                            year=int(year),
                            season=season_short,
                            paper_number='P1'
                        )
                    
                    total_questions += n_questions
                    successful += 1
                    print(f"OK ({n_questions}Q)")
                else:
                    failed.append(f"{year}_{season}")
                    print("SKIP (0Q)")
            else:
                failed.append(f"{year}_{season}")
                print("FAIL")
                
        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
            break
        except Exception as e:
            failed.append(f"{year}_{season}")
            print(f"ERROR: {str(e)[:80]}")
    
    print(f"\n{'='*60}")
    print(f"COMPLETE")
    print(f"{'='*60}")
    print(f"Success: {successful}/{len(papers)} ({successful/len(papers)*100:.1f}%)")
    print(f"Questions: {total_questions}")
    if failed:
        print(f"\nFailed ({len(failed)}): {', '.join(failed[:10])}")
        if len(failed) > 10:
            print(f"  ... and {len(failed)-10} more")

if __name__ == '__main__':
    main()
