"""Upload all FPM PDFs to Supabase storage"""
import os
from supabase import create_client
from pathlib import Path

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

# Get FPM subject
fpm_response = supabase.table('subjects').select('*').eq('code', '9FM0').execute()
fpm = fpm_response.data[0]
print(f"✅ FPM Subject: {fpm['name']}")

# Base path for processed papers
base_path = Path("data/processed/Further Pure Maths Processed")

if not base_path.exists():
    print(f"❌ Path not found: {base_path}")
    exit(1)

# Get all paper folders
paper_folders = [f for f in base_path.iterdir() if f.is_dir()]
print(f"📂 Found {len(paper_folders)} paper folders")

total_uploaded = 0
total_skipped = 0
total_errors = 0

for folder in sorted(paper_folders):
    folder_name = folder.name  # e.g., "2011_Jun_1P"
    pages_dir = folder / "pages"
    
    if not pages_dir.exists():
        continue
    
    # Get all PDFs in pages folder
    pdf_files = list(pages_dir.glob("*.pdf"))
    
    if not pdf_files:
        continue
    
    print(f"\n📄 {folder_name} ({len(pdf_files)} PDFs)")
    
    for pdf_file in pdf_files:
        # Construct storage path  
        # Looking at the sample URL: /subjects/Further_Pure_Mathematics/pages/{folder}/q{num}.pdf
        # But the bucket is actually 'question-pdfs' or might be different
        # Let's check what bucket actually exists first
        storage_path = f"subjects/Further_Pure_Mathematics/pages/{folder_name}/{pdf_file.name}"
        
        try:
            # Upload file (don't pre-check existence, let the upload fail if it exists)
            with open(pdf_file, 'rb') as f:
                file_data = f.read()
                
            supabase.storage.from_('question-pdfs').upload(
                storage_path,
                file_data,
                file_options={"content-type": "application/pdf", "upsert": "false"}
            )
            
            total_uploaded += 1
            if total_uploaded % 50 == 0:
                print(f"   Uploaded {total_uploaded} files...")
                
        except Exception as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower() or 'resource already exists' in error_msg.lower():
                total_skipped += 1
            else:
                total_errors += 1
                print(f"   ❌ Error uploading {pdf_file.name}: {error_msg[:80]}")

print(f"\n✅ Upload complete!")
print(f"   Uploaded: {total_uploaded}")
print(f"   Skipped (already exists): {total_skipped}")
print(f"   Errors: {total_errors}")
