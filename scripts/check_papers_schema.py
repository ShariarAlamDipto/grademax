"""Check papers table schema"""
import os
from supabase import create_client

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

supabase = create_client(
    env['NEXT_PUBLIC_SUPABASE_URL'],
    env['SUPABASE_SERVICE_ROLE_KEY']
)

# Get one paper to see structure
response = supabase.table('papers').select('*').limit(1).execute()

if response.data:
    paper = response.data[0]
    print("📋 Papers table columns:")
    for key in paper.keys():
        print(f"   - {key}: {type(paper[key]).__name__}")
else:
    print("❌ No papers found")
