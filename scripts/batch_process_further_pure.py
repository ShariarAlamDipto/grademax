"""
Batch process Further Pure Mathematics papers
Uses enhanced symbol-aware classifier
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from page_based_ingest import PageBasedPipeline


def find_paper_pairs(raw_dir: Path):
    """Find QP and MS pairs in the raw directory"""
    pairs = []
    
    # Look for papers in structure: data/raw/IGCSE/FurtherPureMaths/YYYY/Session/Paper X.pdf
    for year_dir in sorted(raw_dir.glob('*')):
        if not year_dir.is_dir():
            continue
        
        for session_dir in sorted(year_dir.glob('*')):
            if not session_dir.is_dir():
                continue
            
            # Find all QP files (Paper X.pdf without _MS)
            qp_files = sorted([f for f in session_dir.glob('Paper *.pdf') 
                             if '_MS' not in f.name])
            
            for qp_file in qp_files:
                # Look for matching MS
                ms_file = session_dir / f"{qp_file.stem}_MS.pdf"
                
                if ms_file.exists():
                    pairs.append((qp_file, ms_file))
                    print(f"✅ Found pair: {qp_file.name} + {ms_file.name}")
                else:
                    print(f"⚠️  No MS for: {qp_file.name}")
    
    return pairs


def main():
    """Process all Further Pure Maths papers"""
    
    # Configuration
    RAW_DIR = Path('data/raw/IGCSE/Further Pure Maths')
    CONFIG_PATH = 'config/further_pure_topics.yaml'
    
    if not RAW_DIR.exists():
        print(f"❌ Raw directory not found: {RAW_DIR}")
        print(f"   Expected structure: data/raw/IGCSE/FurtherPureMaths/YYYY/Session/Paper X.pdf")
        return
    
    if not Path(CONFIG_PATH).exists():
        print(f"❌ Config not found: {CONFIG_PATH}")
        return
    
    # Find all paper pairs
    print(f"\n{'='*70}")
    print(f"🔍 Scanning for Further Pure Mathematics papers...")
    print(f"{'='*70}")
    pairs = find_paper_pairs(RAW_DIR)
    
    if not pairs:
        print(f"\n❌ No paper pairs found in {RAW_DIR}")
        return
    
    print(f"\n📊 Found {len(pairs)} paper pair(s)")
    
    # Initialize pipeline with Further Pure config
    print(f"\n{'='*70}")
    print(f"⚙️  Initializing symbol-aware classifier...")
    print(f"{'='*70}")
    pipeline = PageBasedPipeline(config_path=CONFIG_PATH, subject_name='Further Pure Mathematics')
    
    # Process each pair
    success_count = 0
    failed_count = 0
    
    for i, (qp_path, ms_path) in enumerate(pairs, 1):
        print(f"\n{'='*70}")
        print(f"📄 Processing pair {i}/{len(pairs)}")
        print(f"{'='*70}")
        
        try:
            pipeline.process_paper_pair(str(qp_path), str(ms_path))
            success_count += 1
            print(f"\n✅ Successfully processed {qp_path.name}")
        except Exception as e:
            failed_count += 1
            print(f"\n❌ Failed to process {qp_path.name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 BATCH PROCESSING SUMMARY")
    print(f"{'='*70}")
    print(f"✅ Successful: {success_count}/{len(pairs)}")
    print(f"❌ Failed: {failed_count}/{len(pairs)}")
    
    if success_count > 0:
        print(f"\n🎉 Further Pure Mathematics papers are ready!")
        print(f"   Check the database 'pages' table for classified questions.")


if __name__ == '__main__':
    main()
