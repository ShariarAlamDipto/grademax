import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv('.env.local')

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# List all folders in storage
folders = supabase.storage.from_('question-pdfs').list('subjects/Further_Pure_Mathematics/pages')

print(f"📂 Found {len(folders)} folders in storage:\n")

# Show folders from 2014 and 2019
print("2014 folders:")
for f in [folder for folder in folders if '2014' in folder['name']]:
    print(f"  - {f['name']}")

print("\n2019 folders:")
for f in [folder for folder in folders if '2019' in folder['name']]:
    print(f"  - {f['name']}")

print("\nAll folder names (first 20):")
for f in folders[:20]:
    print(f"  - {f['name']}")
