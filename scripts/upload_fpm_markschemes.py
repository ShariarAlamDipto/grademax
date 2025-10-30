"""Upload all FPM mark scheme PDFs to Supabase storage"""
import os
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

from supabase import create_client

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
print(f"📂 Found {len(paper_folders)} paper folders\n")

total_uploaded = 0
total_skipped = 0
total_errors = 0

for folder in sorted(paper_folders):
    folder_name = folder.name  # e.g., "2014_Jan_2P" (already without "Paper" prefix)
    markschemes_dir = folder / "markschemes"
    
    if not markschemes_dir.exists():
        continue
    
    # Get all PDFs in markschemes folder
    pdf_files = list(markschemes_dir.glob("*.pdf"))
    
    if not pdf_files:
        continue
    
    print(f"📄 {folder_name} ({len(pdf_files)} mark schemes)")
    
    for pdf_file in pdf_files:
        # Construct storage path
        # Database expects: q1_ms.pdf, q2_ms.pdf, etc.
        # Local files are: q1.pdf, q2.pdf in markschemes folder
        filename = pdf_file.stem + "_ms.pdf"  # q1.pdf -> q1_ms.pdf
        storage_path = f"subjects/Further_Pure_Mathematics/pages/{folder_name}/{filename}"
        
        try:
            # Upload file
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
                print(f"   ❌ Error uploading {filename}: {error_msg[:80]}")

print(f"\n✅ Upload complete!")
print(f"   Uploaded: {total_uploaded}")
print(f"   Skipped (already exists): {total_skipped}")
print(f"   Errors: {total_errors}")
