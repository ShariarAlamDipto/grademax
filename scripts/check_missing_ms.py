import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv('.env.local')

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Check folders that had missing mark schemes
folders = ['2012_Jan_1P', '2011_Jun_2P', '2012_Jun_2P', '2015_Jan_2P']

for folder in folders:
    print(f"\n📂 {folder}:")
    try:
        files = supabase.storage.from_('question-pdfs').list(f'subjects/Further_Pure_Mathematics/pages/{folder}')
        qp_files = [f['name'] for f in files if not '_ms' in f['name']]
        ms_files = [f['name'] for f in files if '_ms' in f['name']]
        
        print(f"   QP files: {len(qp_files)}")
        print(f"   MS files: {len(ms_files)}")
        
        if len(ms_files) < len(qp_files):
            print(f"   ⚠️  Missing {len(qp_files) - len(ms_files)} mark schemes!")
            # Show which ones are missing
            for qp in qp_files:
                ms = qp.replace('.pdf', '_ms.pdf')
                if ms not in ms_files:
                    print(f"      Missing: {ms}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
