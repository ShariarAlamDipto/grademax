"""
⚠️  THIS SCRIPT IS NOW OBSOLETE ⚠️

The data structure has been updated to match the scraper format directly.
Papers should be manually copied to the new structure:

NEW STRUCTURE:
  data/raw/IGCSE/Physics/2024/May-Jun/
  ├── Paper 1.pdf
  └── Paper 1_MS.pdf

The ingestion script (page_based_ingest.py) now:
1. Extracts metadata from PDF watermarks ("PMT\nPhysics · 2024 · May/Jun · Paper 1 · QP")
2. Auto-detects subject from folder name (Physics → 4PH1)
3. Normalizes season names (May-Jun → Jun)

No file renaming needed anymore!

---

ORIGINAL PURPOSE (Deprecated):
Import Physics papers from scraper folder to GradeMax structure
Handles file renaming and folder structure conversion

FROM: C:/Users/shari/grademax scraper/grademax-scraper/data/raw/Physics/
TO:   C:/Users/shari/grademax/data/raw/IGCSE/4PH1/
"""

import os
import shutil
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Source and destination paths
SCRAPER_ROOT = Path(r"C:\Users\shari\grademax scraper\grademax-scraper\data\raw\Physics")
GRADEMAX_ROOT = Path(r"C:\Users\shari\grademax\data\raw\IGCSE\4PH1")

# Season name mapping
SEASON_MAP = {
    'May-Jun': 'Jun',
    'Oct-Nov': 'Jan',  # Assuming Oct-Nov corresponds to Jan sitting
    'Jan': 'Jan',
    'Jun': 'Jun',
    'May': 'Jun',
    'October': 'Jan',
    'November': 'Jan'
}


def normalize_season(season_str: str) -> str:
    """Convert scraper season name to GradeMax format"""
    for key, value in SEASON_MAP.items():
        if key.lower() in season_str.lower():
            return value
    
    # Default fallback
    print(f"   ⚠️  Unknown season format: {season_str}, defaulting to Jun")
    return 'Jun'


def parse_paper_number(filename: str) -> Tuple[str, bool]:
    """
    Extract paper number from filename
    Returns: (paper_number, is_markscheme)
    
    Examples:
      "Paper 1.pdf" -> ("1", False)
      "Paper 2_MS.pdf" -> ("2", True)
      "Paper 1 MS.pdf" -> ("1", True)
    """
    is_ms = '_MS' in filename or ' MS' in filename or '_ms' in filename
    
    # Try to extract paper number
    match = re.search(r'Paper\s*(\d+)', filename, re.IGNORECASE)
    if match:
        paper_num = match.group(1)
        return (paper_num, is_ms)
    
    return (None, is_ms)


def convert_filename(original_name: str) -> str:
    """
    Convert scraper filename to GradeMax format
    
    Examples:
      "Paper 1.pdf" -> "4PH1_1P.pdf"
      "Paper 2_MS.pdf" -> "4PH1_2P_MS.pdf"
      "Paper 1 MS.pdf" -> "4PH1_1P_MS.pdf"
    """
    paper_num, is_ms = parse_paper_number(original_name)
    
    if not paper_num:
        return None  # Can't convert
    
    base_name = f"4PH1_{paper_num}P"
    if is_ms:
        return f"{base_name}_MS.pdf"
    else:
        return f"{base_name}.pdf"


def scan_scraper_folder() -> List[Dict]:
    """Scan scraper folder and return list of files with metadata"""
    papers = []
    
    if not SCRAPER_ROOT.exists():
        print(f"❌ Scraper folder not found: {SCRAPER_ROOT}")
        return []
    
    # Walk through year folders
    for year_dir in sorted(SCRAPER_ROOT.iterdir()):
        if not year_dir.is_dir():
            continue
        
        year = year_dir.name
        
        # Walk through season folders
        for season_dir in year_dir.iterdir():
            if not season_dir.is_dir():
                continue
            
            original_season = season_dir.name
            mapped_season = normalize_season(original_season)
            
            # Process PDF files
            for pdf_file in season_dir.glob("*.pdf"):
                new_filename = convert_filename(pdf_file.name)
                
                if new_filename:
                    papers.append({
                        'source_path': pdf_file,
                        'source_name': pdf_file.name,
                        'year': year,
                        'original_season': original_season,
                        'mapped_season': mapped_season,
                        'new_filename': new_filename,
                        'dest_folder': GRADEMAX_ROOT / year / mapped_season,
                        'dest_path': GRADEMAX_ROOT / year / mapped_season / new_filename
                    })
    
    return papers


def group_papers_by_pair(papers: List[Dict]) -> List[Tuple[Dict, Dict]]:
    """Group QP and MS pairs together"""
    pairs = []
    processed = set()
    
    for paper in papers:
        if paper['source_path'] in processed:
            continue
        
        if '_MS' not in paper['new_filename']:
            # This is a question paper, find its mark scheme
            qp = paper
            ms = None
            
            # Look for matching mark scheme
            for other in papers:
                if (other['year'] == qp['year'] and 
                    other['mapped_season'] == qp['mapped_season'] and
                    other['new_filename'] == qp['new_filename'].replace('.pdf', '_MS.pdf')):
                    ms = other
                    break
            
            if ms:
                pairs.append((qp, ms))
                processed.add(qp['source_path'])
                processed.add(ms['source_path'])
            else:
                print(f"   ⚠️  Mark scheme not found for: {qp['source_name']}")
    
    return pairs


def copy_papers(papers: List[Dict], dry_run: bool = False) -> int:
    """Copy and rename papers to GradeMax structure"""
    copied = 0
    
    for paper in papers:
        dest_folder = paper['dest_folder']
        dest_path = paper['dest_path']
        
        if dry_run:
            print(f"   [DRY RUN] Would copy:")
            print(f"      FROM: {paper['source_path']}")
            print(f"      TO:   {dest_path}")
        else:
            # Create destination folder
            dest_folder.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            try:
                shutil.copy2(paper['source_path'], dest_path)
                copied += 1
            except Exception as e:
                print(f"   ❌ Error copying {paper['source_name']}: {e}")
    
    return copied


def generate_ingestion_script(pairs: List[Tuple[Dict, Dict]], output_file: str = "process_all_papers.ps1"):
    """Generate PowerShell script to process all papers"""
    script_lines = [
        "# Auto-generated script to process all Physics papers",
        "# Generated by import_from_scraper.py",
        "",
        "$ErrorActionPreference = 'Continue'",
        "$processed = 0",
        "$failed = 0",
        "",
        "Write-Host '=' * 70 -ForegroundColor Cyan",
        "Write-Host 'Processing All Physics Papers' -ForegroundColor Green",
        "Write-Host '=' * 70 -ForegroundColor Cyan",
        "Write-Host ''",
        ""
    ]
    
    for i, (qp, ms) in enumerate(pairs, 1):
        qp_path = str(qp['dest_path']).replace('\\', '/')
        ms_path = str(ms['dest_path']).replace('\\', '/')
        
        script_lines.extend([
            f"# Paper {i}/{len(pairs)}: {qp['year']} {qp['mapped_season']}",
            f"Write-Host 'Processing {qp['year']} {qp['mapped_season']} Paper {qp['new_filename'][5]}...' -ForegroundColor Yellow",
            f"python scripts/page_based_ingest.py \"{qp_path}\" \"{ms_path}\"",
            "if ($LASTEXITCODE -eq 0) {",
            "    $processed++",
            f"    Write-Host '✅ {qp['year']} {qp['mapped_season']} complete' -ForegroundColor Green",
            "} else {",
            "    $failed++",
            f"    Write-Host '❌ {qp['year']} {qp['mapped_season']} failed' -ForegroundColor Red",
            "}",
            "Write-Host ''",
            ""
        ])
    
    script_lines.extend([
        "Write-Host '=' * 70 -ForegroundColor Cyan",
        "Write-Host 'Processing Complete!' -ForegroundColor Green",
        "Write-Host \"Processed: $processed\" -ForegroundColor Green",
        "Write-Host \"Failed: $failed\" -ForegroundColor Red",
        "Write-Host '=' * 70 -ForegroundColor Cyan"
    ])
    
    output_path = Path(__file__).parent.parent / output_file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(script_lines))
    
    print(f"   ✅ Generated batch script: {output_file}")


def main():
    print("=" * 70)
    print("📁 Physics Papers Import Tool")
    print("=" * 70)
    print(f"\nSource: {SCRAPER_ROOT}")
    print(f"Dest:   {GRADEMAX_ROOT}")
    print()
    
    # Step 1: Scan scraper folder
    print("1️⃣  Scanning scraper folder...")
    papers = scan_scraper_folder()
    
    if not papers:
        print("   ❌ No papers found!")
        return
    
    print(f"   ✅ Found {len(papers)} files")
    
    # Step 2: Group into pairs
    print("\n2️⃣  Grouping into QP/MS pairs...")
    pairs = group_papers_by_pair(papers)
    print(f"   ✅ Found {len(pairs)} complete paper pairs")
    
    # Step 3: Show summary
    print("\n3️⃣  Summary by year:")
    year_counts = {}
    for qp, ms in pairs:
        year = qp['year']
        year_counts[year] = year_counts.get(year, 0) + 1
    
    for year in sorted(year_counts.keys()):
        print(f"   {year}: {year_counts[year]} papers")
    
    # Step 4: Confirm
    print("\n4️⃣  Ready to copy files")
    print(f"   Total files to copy: {len(papers)}")
    print(f"   Destination: {GRADEMAX_ROOT}")
    
    response = input("\n   Proceed with copy? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("\n   ❌ Cancelled by user")
        return
    
    # Step 5: Copy files
    print("\n5️⃣  Copying files...")
    copied = copy_papers(papers, dry_run=False)
    print(f"   ✅ Copied {copied} files")
    
    # Step 6: Generate processing script
    print("\n6️⃣  Generating batch processing script...")
    generate_ingestion_script(pairs)
    
    # Step 7: Summary
    print("\n" + "=" * 70)
    print("✅ Import Complete!")
    print("=" * 70)
    print(f"\n📊 Statistics:")
    print(f"   Files copied: {copied}")
    print(f"   Paper pairs: {len(pairs)}")
    print(f"   Years covered: {len(year_counts)}")
    print(f"\n📋 Next Steps:")
    print(f"   1. Verify files: Get-ChildItem 'data\\raw\\IGCSE\\4PH1' -Recurse")
    print(f"   2. Process all papers: .\\process_all_papers.ps1")
    print(f"   3. Or process individually with page_based_ingest.py")
    print(f"\n⏱️  Estimated processing time: ~{len(pairs) * 2} minutes")
    print()


if __name__ == '__main__':
    main()
