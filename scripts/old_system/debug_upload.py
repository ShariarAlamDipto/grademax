"""
Debug storage upload issue
"""
import os
from pathlib import Path
from supabase_client import SupabaseClient

# Load environment
from dotenv import load_dotenv
load_dotenv()

print("🔍 Debugging storage upload...")
print(f"SUPABASE_URL: {os.getenv('NEXT_PUBLIC_SUPABASE_URL')}")
print(f"ANON_KEY length: {len(os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY') or '')}")

# Initialize client
db = SupabaseClient()

# Find a test file (relative to project root)
test_file = Path("..") / "data" / "processed" / "4PH1_2019_Jun_1P" / "pages" / "q2.pdf"

if not test_file.exists():
    print(f"❌ Test file not found: {test_file}")
    exit(1)

print(f"\n📄 Test file: {test_file}")

# Try upload
try:
    dest_path = "debug/test_q2.pdf"
    print(f"⬆️  Uploading to: {dest_path}")
    
    result = db.upload_file(
        bucket='question-pdfs',
        file_path=str(test_file),
        destination_path=dest_path
    )
    
    print(f"✅ Success: {result}")
    
    url = db.get_public_url('question-pdfs', dest_path)
    print(f"📎 Public URL: {url}")
    
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
