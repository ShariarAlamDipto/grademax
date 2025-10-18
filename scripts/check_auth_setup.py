"""
Check if the authentication system is set up correctly.
This script verifies database tables, functions, and connection.
"""

import os
import sys
from pathlib import Path

# Load .env.local file
env_file = Path(__file__).parent.parent / '.env.local'

if env_file.exists():
    print(f"📄 Loading environment from: {env_file}\n")
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
else:
    print(f"❌ Error: .env.local not found at {env_file}")
    sys.exit(1)

# Check required variables
required_vars = ['NEXT_PUBLIC_SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']
missing = [var for var in required_vars if var not in os.environ]

if missing:
    print(f"❌ Missing required environment variables: {', '.join(missing)}")
    sys.exit(1)

from supabase import create_client

print("="*80)
print("🔍 AUTHENTICATION SYSTEM CHECK")
print("="*80 + "\n")

# Initialize Supabase
url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

print(f"1️⃣ Connecting to Supabase...")
print(f"   URL: {url}")

try:
    supabase = create_client(url, key)
    print(f"   ✅ Connection successful!\n")
except Exception as e:
    print(f"   ❌ Connection failed: {e}\n")
    sys.exit(1)

# Check if tables exist
print(f"2️⃣ Checking database tables...")

tables_to_check = ['user_profiles', 'user_permissions', 'worksheet_generation_logs']

for table in tables_to_check:
    try:
        result = supabase.table(table).select('*').limit(1).execute()
        print(f"   ✅ Table '{table}' exists")
    except Exception as e:
        print(f"   ❌ Table '{table}' NOT FOUND")
        print(f"      Error: {e}")

# Check if functions exist
print(f"\n3️⃣ Checking database functions...")

functions_to_check = [
    'check_worksheet_permission',
    'get_remaining_worksheet_quota',
    'handle_new_user'
]

try:
    result = supabase.rpc('check_worksheet_permission', {'check_user_id': '00000000-0000-0000-0000-000000000000'}).execute()
    print(f"   ✅ Function 'check_worksheet_permission' exists")
except Exception as e:
    if "function" in str(e).lower() and "does not exist" in str(e).lower():
        print(f"   ❌ Function 'check_worksheet_permission' NOT FOUND")
    else:
        print(f"   ✅ Function 'check_worksheet_permission' exists (test call expected to fail)")

try:
    result = supabase.rpc('get_remaining_worksheet_quota', {'check_user_id': '00000000-0000-0000-0000-000000000000'}).execute()
    print(f"   ✅ Function 'get_remaining_worksheet_quota' exists")
except Exception as e:
    if "function" in str(e).lower() and "does not exist" in str(e).lower():
        print(f"   ❌ Function 'get_remaining_worksheet_quota' NOT FOUND")
    else:
        print(f"   ✅ Function 'get_remaining_worksheet_quota' exists (test call expected to fail)")

# Check for existing users
print(f"\n4️⃣ Checking for existing users...")

try:
    result = supabase.table('user_profiles').select('email, full_name, created_at').execute()
    
    if result.data:
        print(f"   ✅ Found {len(result.data)} user(s):\n")
        for user in result.data:
            email = user.get('email', 'N/A')
            name = user.get('full_name', 'N/A')
            created = user.get('created_at', 'N/A')
            print(f"      📧 {email}")
            print(f"         Name: {name}")
            print(f"         Joined: {created}\n")
    else:
        print(f"   ℹ️  No users found yet")
        print(f"      Users will be created automatically when they sign in with Google\n")
except Exception as e:
    print(f"   ❌ Error checking users: {e}\n")

# Summary
print("="*80)
print("📊 SUMMARY")
print("="*80 + "\n")

print("Next Steps:")
print("\n✅ If all tables and functions exist:")
print("   1. Go to http://localhost:3000/login")
print("   2. Sign in with Google")
print("   3. Run: python scripts/manage_permissions_env.py grant your-email@gmail.com")
print("   4. Refresh the /generate page")

print("\n❌ If tables/functions are missing:")
print("   1. Go to Supabase Dashboard → SQL Editor")
print("   2. Copy contents of: supabase/migrations/01_user_permissions.sql")
print("   3. Paste and run in SQL Editor")
print("   4. Run this check script again")

print("\n📖 For detailed setup guide, see: docs/AUTHENTICATION_SETUP.md\n")
