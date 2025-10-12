"""
Create Supabase Storage bucket for question PDFs
Run this once before running ingestion
"""
import os
import requests

# Get credentials from environment
SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
SUPABASE_KEY = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY")
    exit(1)

# Create bucket
bucket_name = 'question-pdfs'
storage_url = f"{SUPABASE_URL}/storage/v1/bucket"

headers = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json'
}

# Create bucket with public access
bucket_config = {
    'id': bucket_name,
    'name': bucket_name,
    'public': True,  # Make publicly accessible
    'file_size_limit': 52428800,  # 50MB
    'allowed_mime_types': ['application/pdf']
}

print(f"Creating storage bucket: {bucket_name}...")

response = requests.post(storage_url, json=bucket_config, headers=headers)

if response.status_code == 200:
    print(f"✅ Bucket '{bucket_name}' created successfully!")
elif response.status_code == 409:
    print(f"✅ Bucket '{bucket_name}' already exists")
else:
    print(f"❌ Failed to create bucket: {response.status_code}")
    print(f"   Response: {response.text}")
    
    # Try to list existing buckets
    print("\n📦 Existing buckets:")
    list_response = requests.get(storage_url, headers=headers)
    if list_response.status_code == 200:
        buckets = list_response.json()
        for bucket in buckets:
            print(f"   - {bucket['name']} (public: {bucket.get('public', False)})")
    
    exit(1)

print(f"\n✅ Ready to upload PDFs to storage!")
print(f"   Bucket: {bucket_name}")
print(f"   Access: Public")
print(f"   Max size: 50MB per file")
