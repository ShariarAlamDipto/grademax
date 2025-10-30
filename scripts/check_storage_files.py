import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv('.env.local')

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

print("🔍 Checking Supabase storage for FPM PDFs...\n")

# Try to list files in different paths
paths_to_check = [
    "subjects/Further_Pure_Mathematics/Pages",
    "subjects/Further_Pure_Mathematics/pages",
    "subjects/Further_Pure_mathematics/Pages",
    "subjects/Further_Pure_mathematics/pages",
]

for path in paths_to_check:
    print(f"📂 Checking: {path}")
    try:
        folders = supabase.storage.from_('question-pdfs').list(path)
        if folders:
            print(f"   ✅ Found {len(folders)} items")
            for folder in folders[:5]:
                print(f"      - {folder['name']}")
                # Try to list files in first folder
                if len(folders) > 0:
                    try:
                        files = supabase.storage.from_('question-pdfs').list(f"{path}/{folders[0]['name']}")
                        print(f"      📄 First folder has {len(files)} files")
                        for f in files[:3]:
                            print(f"         - {f['name']}")
                    except Exception as e:
                        print(f"      ❌ Error listing files: {e}")
                    break
        else:
            print(f"   ⚠️  Empty or doesn't exist")
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:100]}")
    print()

# Also check root level
print("📂 Checking root level of question-pdfs bucket:")
try:
    root_items = supabase.storage.from_('question-pdfs').list()
    print(f"   Found {len(root_items)} items at root:")
    for item in root_items[:10]:
        print(f"      - {item['name']}")
except Exception as e:
    print(f"   ❌ Error: {e}")
