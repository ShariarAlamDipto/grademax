"""
Compare environment between test and pipeline
"""
import os
from dotenv import load_dotenv

load_dotenv()

print("Environment variables:")
print(f"URL: {os.getenv('NEXT_PUBLIC_SUPABASE_URL')}")
print(f"ANON_KEY: {os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')[:20]}...{os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')[-20:]}")
print(f"Full key length: {len(os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY') or '')}")

# Check if it's the same as what the client gets
from supabase_client import SupabaseClient
client = SupabaseClient()
print(f"\nClient URL: {client.url}")
print(f"Client key length: {len(client.key)}")
print(f"Keys match: {client.key == os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')}")

# Try an upload
from pathlib import Path
test_file = Path("data/processed/4PH1_2019_Jun_1P/pages/q2.pdf")

if test_file.exists():
    print(f"\n📄 Attempting upload from pipeline context...")
    try:
        result = client.upload_file(
            bucket='question-pdfs',
            file_path=str(test_file),
            destination_path="pipeline_test/q2.pdf"
        )
        print(f"✅ Upload successful: {result}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")
else:
    print(f"\n❌ Test file not found: {test_file}")
