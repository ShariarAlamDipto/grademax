"""Re-process all Physics papers and add them to the database"""
import os
from supabase import create_client
from pathlib import Path
import json

# Read from .env.local
def load_env():
    env_vars = {}
    with open('.env.local', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
    return env_vars

env = load_env()

supabase = create_client(
    env['NEXT_PUBLIC_SUPABASE_URL'],
    env['SUPABASE_SERVICE_ROLE_KEY']
)

# Get Physics subject
physics_response = supabase.table('subjects').select('*').eq('code', '4PH1').execute()
if not physics_response.data:
    print("❌ Physics subject not found!")
    exit(1)

physics = physics_response.data[0]
print(f"✅ Physics Subject: {physics['name']} (ID: {physics['id']})")

# Base path for processed papers
base_path = Path("data/processed/Physics Processed")

if not base_path.exists():
    print(f"❌ Path not found: {base_path}")
    exit(1)

# Get all paper folders
paper_folders = [f for f in base_path.iterdir() if f.is_dir()]
print(f"📂 Found {len(paper_folders)} Physics paper folders\n")

papers_created = 0
pages_created = 0
errors = 0

for folder in sorted(paper_folders):
    folder_name = folder.name
    manifest_path = folder / "manifest.json"
    
    if not manifest_path.exists():
        print(f"⚠️  Skipping {folder_name}: No manifest.json")
        continue
    
    try:
        # Read manifest
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Parse folder name: e.g., "2018_Jun_1" or "2018_Jun_1H"
        parts = folder_name.split('_')
        if len(parts) < 3:
            print(f"⚠️  Skipping {folder_name}: Invalid folder name format")
            continue
        
        year = int(parts[0])
        season = parts[1]
        paper_number = parts[2]
        
        # Check if paper already exists
        existing = supabase.table('papers').select('id').eq('subject_id', physics['id']).eq('year', year).eq('season', season).eq('paper_number', paper_number).execute()
        
        if existing.data:
            print(f"   Skipping {folder_name}: Already exists")
            continue
        
        # Create paper
        paper_data = {
            'subject_id': physics['id'],
            'year': year,
            'season': season,
            'paper_number': paper_number,
            'total_pages': len(manifest.get('pages', [])),
        }
        
        paper_response = supabase.table('papers').insert(paper_data).execute()
        paper_id = paper_response.data[0]['id']
        papers_created += 1
        
        print(f"📄 Created paper: {folder_name} (ID: {paper_id[:8]}...)")
        
        # Create pages
        pages_dir = folder / "pages"
        if pages_dir.exists():
            pdf_files = list(pages_dir.glob("*.pdf"))
            for pdf_file in pdf_files:
                # Extract question number from filename (e.g., q1.pdf -> 1)
                q_num = pdf_file.stem.replace('q', '')
                if not q_num.isdigit():
                    continue
                
                # Create page
                page_data = {
                    'paper_id': paper_id,
                    'question_number': q_num,
                    'qp_page_url': f"https://{env['NEXT_PUBLIC_SUPABASE_URL']}/storage/v1/object/public/question-pdfs/subjects/Physics/pages/{folder_name}/q{q_num}.pdf",
                    'ms_page_url': f"https://{env['NEXT_PUBLIC_SUPABASE_URL']}/storage/v1/object/public/question-pdfs/subjects/Physics/pages/{folder_name}/q{q_num}_ms.pdf",
                    'topics': []  # Will be classified later
                }
                
                supabase.table('pages').insert(page_data).execute()
                pages_created += 1
        
        if papers_created % 10 == 0:
            print(f"   Progress: {papers_created} papers, {pages_created} pages created...")
            
    except Exception as e:
        errors += 1
        print(f"   ❌ Error processing {folder_name}: {str(e)[:100]}")

print(f"\n✅ Processing complete!")
print(f"   Papers created: {papers_created}")
print(f"   Pages created: {pages_created}")
print(f"   Errors: {errors}")
