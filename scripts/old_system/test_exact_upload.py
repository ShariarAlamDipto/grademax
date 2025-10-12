"""
Test upload with exact pipeline parameters
"""
import os
from pathlib import Path
from supabase_client import SupabaseClient
from dotenv import load_dotenv

load_dotenv()

# Initialize like pipeline does
db_client = SupabaseClient()

# Use exact file and path from pipeline
bucket_name = 'question-pdfs'
base_path = "2019/Jun/1P"
q_num = 2
pdf_path = "data\\processed\\4PH1_2019_Jun_1P\\pages\\q2.pdf"
dest_path = f"{base_path}/Q{q_num}.pdf"

print(f"📄 File: {pdf_path}")
print(f"📍 Destination: {dest_path}")
print(f"🪣 Bucket: {bucket_name}")

if not os.path.exists(pdf_path):
    print(f"❌ File not found!")
    exit(1)

print(f"\n⬆️  Uploading...")

try:
    result = db_client.upload_file(
        bucket=bucket_name,
        file_path=pdf_path,
        destination_path=dest_path
    )
    print(f"✅ Success: {result}")
    
    url = db_client.get_public_url(bucket_name, dest_path)
    print(f"📎 URL: {url}")
    
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
