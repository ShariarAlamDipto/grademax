import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv('.env.local')

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Check a sample folder for mark scheme files
folder = '2014_Jan_2P'
files = supabase.storage.from_('question-pdfs').list(f'subjects/Further_Pure_Mathematics/pages/{folder}')

print(f"📂 Files in {folder}:\n")
for f in files:
    print(f"  - {f['name']}")

# Count QP vs MS files
qp_files = [f for f in files if not '_ms' in f['name']]
ms_files = [f for f in files if '_ms' in f['name']]

print(f"\n📊 Summary:")
print(f"  Question Papers: {len(qp_files)}")
print(f"  Mark Schemes: {len(ms_files)}")
