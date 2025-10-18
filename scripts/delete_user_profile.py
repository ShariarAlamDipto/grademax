"""
Delete a specific user's profile and all related data.
Usage: python delete_user_profile.py email@example.com
"""

import os
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: python delete_user_profile.py <email>")
    print("Example: python delete_user_profile.py shariardipto111@gmail.com")
    sys.exit(1)

email_to_delete = sys.argv[1]

# Load .env.local file
env_file = Path(__file__).parent.parent / '.env.local'

if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
else:
    print(f"❌ Error: .env.local not found at {env_file}")
    sys.exit(1)

from supabase import create_client

url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("❌ Error: Missing Supabase credentials")
    sys.exit(1)

supabase = create_client(url, key)

print("="*80)
print(f"🗑️  DELETING USER PROFILE: {email_to_delete}")
print("="*80 + "\n")

# Find user profile
print("1️⃣ Looking for user profile...")
try:
    profile = supabase.table('user_profiles').select('*').eq('email', email_to_delete).execute()
    
    if not profile.data or len(profile.data) == 0:
        print(f"   ℹ️  No profile found for {email_to_delete}")
        print(f"   The user may have already been deleted or never signed up.")
        sys.exit(0)
    
    user_data = profile.data[0]
    user_id = user_data['user_id']
    
    print(f"   ✅ Found profile:")
    print(f"      Email: {user_data.get('email')}")
    print(f"      Name: {user_data.get('full_name', 'N/A')}")
    print(f"      User ID: {user_id}\n")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Check for related data
print("2️⃣ Checking for related data...")

try:
    # Check permissions
    perms = supabase.table('user_permissions').select('*').eq('user_id', user_id).execute()
    print(f"   📋 Permissions: {len(perms.data)} record(s)")
    
    # Check logs
    logs = supabase.table('worksheet_generation_logs').select('*').eq('user_id', user_id).execute()
    print(f"   📊 Generation logs: {len(logs.data)} record(s)\n")
    
except Exception as e:
    print(f"   ⚠️  Warning: {e}\n")

# Confirm deletion
print("⚠️  WARNING: This will permanently delete:")
print(f"   - User profile for {email_to_delete}")
print(f"   - All permissions")
print(f"   - All generation logs")
print(f"   - This DOES NOT delete the auth.users entry (delete that in Supabase Dashboard)")

response = input("\nAre you sure you want to proceed? (yes/no): ").strip().lower()

if response != 'yes':
    print("❌ Cancelled. No changes made.")
    sys.exit(0)

# Delete data
print("\n3️⃣ Deleting data...")

try:
    # Delete logs first (has foreign key to user_id)
    logs_result = supabase.table('worksheet_generation_logs').delete().eq('user_id', user_id).execute()
    print(f"   ✅ Deleted {len(logs_result.data) if logs_result.data else 0} log(s)")
    
    # Delete permissions
    perms_result = supabase.table('user_permissions').delete().eq('user_id', user_id).execute()
    print(f"   ✅ Deleted {len(perms_result.data) if perms_result.data else 0} permission(s)")
    
    # Delete profile
    profile_result = supabase.table('user_profiles').delete().eq('user_id', user_id).execute()
    print(f"   ✅ Deleted profile")
    
except Exception as e:
    print(f"   ❌ Error during deletion: {e}")
    sys.exit(1)

print("\n✅ User profile deleted successfully!")
print("\n📝 Next steps:")
print("   1. If the user still exists in Supabase Auth, delete them from:")
print("      Dashboard → Authentication → Users")
print("   2. The user can now sign up again with a fresh account")
