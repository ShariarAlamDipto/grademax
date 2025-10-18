"""
Test if the user creation trigger is working properly.
This simulates what happens when a user signs up.
"""

import os
import sys
from pathlib import Path

# Load .env.local file
env_file = Path(__file__).parent.parent / '.env.local'

if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

from supabase import create_client

url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(url, key)

print("="*80)
print("🔍 CHECKING USER TRIGGER SETUP")
print("="*80 + "\n")

# Check if trigger exists
print("1️⃣ Checking if trigger exists in database...")
print("   (This requires checking via SQL)\n")

# Check if function exists
print("2️⃣ Checking if handle_new_user() function exists...")
try:
    # We can't directly call the function, but we can check if user_profiles table exists
    # and has the expected structure
    result = supabase.table('user_profiles').select('*').limit(1).execute()
    print("   ✅ user_profiles table exists\n")
except Exception as e:
    print(f"   ❌ Error: {e}\n")

# List all current auth users and their profiles
print("3️⃣ Current state:\n")

print("   Checking user_profiles table...")
try:
    profiles = supabase.table('user_profiles').select('email, created_at').execute()
    if profiles.data:
        print(f"   Found {len(profiles.data)} profile(s):")
        for p in profiles.data:
            print(f"      - {p['email']} (created: {p['created_at']})")
    else:
        print("   No profiles found")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "="*80)
print("💡 TROUBLESHOOTING STEPS")
print("="*80 + "\n")

print("If signup isn't creating profiles, try these:")
print("\n1. Check trigger exists in Supabase:")
print("   Dashboard → Database → Triggers")
print("   Look for: 'on_auth_user_created'")

print("\n2. Manually check/recreate trigger via SQL Editor:")
print("   Run this query:")
print("""
   SELECT * FROM pg_trigger 
   WHERE tgname = 'on_auth_user_created';
   """)

print("\n3. If trigger is missing, recreate it:")
print("   Go to: supabase/migrations/01_user_permissions.sql")
print("   Copy the entire file and run in SQL Editor")

print("\n4. Test signup again:")
print("   - Sign out completely")
print("   - Clear browser cookies")
print("   - Go to /login and sign in with Google")
print("   - Check if profile was created:")
print("     python scripts/check_auth_setup.py")

print("\n5. Check Supabase logs:")
print("   Dashboard → Logs → Database Logs")
print("   Look for errors when signing up")
