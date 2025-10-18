"""Delete all pages from database"""
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv(".env.local")

supabase = create_client(
    os.getenv("NEXT_PUBLIC_SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

print("🗑️ Deleting all pages...")
result = supabase.table('pages').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
print(f"✅ Deleted {len(result.data)} pages")
