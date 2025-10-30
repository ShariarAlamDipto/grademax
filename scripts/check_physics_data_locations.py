"""
Check if Physics data exists and where
"""
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

print("🔍 Checking Physics data locations...")

# Check raw
raw_physics = DATA_DIR / "raw" / "IGCSE" / "Physics"
if raw_physics.exists():
    years = list(raw_physics.iterdir())
    print(f"\n✅ Raw Physics data found: {len(years)} year folders")
    
    # Count total PDFs
    total_pdfs = list(raw_physics.rglob("*.pdf"))
    print(f"   Total PDF files: {len(total_pdfs)}")
    
    # Sample a folder
    if years:
        sample_year = years[0]
        print(f"\n   Sample: {sample_year.name}")
        seasons = list(sample_year.iterdir())
        if seasons:
            sample_season = seasons[0]
            pdfs = list(sample_season.rglob("*.pdf"))
            print(f"   → {sample_season.name}: {len(pdfs)} PDFs")
            for pdf in pdfs[:5]:
                print(f"      • {pdf.name}")
else:
    print("\n❌ No raw Physics data found")

# Check processed
processed_physics = DATA_DIR / "processed" / "Physics Processed"
if processed_physics.exists():
    folders = [f for f in processed_physics.iterdir() if f.is_dir()]
    print(f"\n📁 Processed Physics folders: {len(folders)}")
    
    # Check if they have content
    folders_with_manifest = 0
    folders_with_pages = 0
    total_files = 0
    
    for folder in folders:
        if (folder / "manifest.json").exists():
            folders_with_manifest += 1
        if (folder / "pages").exists():
            pages = list((folder / "pages").glob("*.pdf"))
            if pages:
                folders_with_pages += 1
                total_files += len(pages)
    
    print(f"   Folders with manifest.json: {folders_with_manifest}")
    print(f"   Folders with pages/ PDFs: {folders_with_pages}")
    print(f"   Total page PDFs: {total_files}")
    
    if folders_with_manifest == 0 and folders_with_pages == 0:
        print(f"\n   ⚠️  All {len(folders)} folders are EMPTY!")
        print("   Physics needs to be processed from raw data first.")
else:
    print("\n❌ No processed Physics folder found")

print("\n" + "="*60)
print("RECOMMENDATION:")
print("="*60)

if processed_physics.exists() and folders:
    if folders_with_manifest == 0:
        print("❌ Physics processed folders exist but are EMPTY")
        print("   Need to process from raw data first")
        print(f"\n   Run: python scripts/extract_physics_pages.py")
    else:
        print("✅ Physics data is processed and ready")
        print(f"   Can run: python scripts/process_and_classify_all_physics.py")
else:
    print("❌ No processed data at all")
    print("   Need to process from raw data first")
