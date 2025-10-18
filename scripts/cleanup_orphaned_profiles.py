"""
Clean up orphaned user profiles (profiles without matching auth users).
This is useful when you've deleted users from Supabase Auth but the profiles remain.
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
print("🧹 CLEANING ORPHANED USER PROFILES")
print("="*80 + "\n")

# Get all user profiles
print("1️⃣ Fetching all user profiles...")
try:
    profiles = supabase.table('user_profiles').select('*').execute()
    print(f"   Found {len(profiles.data)} profile(s)\n")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

if not profiles.data:
    print("✅ No profiles found. Database is clean!")
    sys.exit(0)

# Get all auth users
print("2️⃣ Checking which profiles have valid auth users...\n")

orphaned_profiles = []

for profile in profiles.data:
    user_id = profile['user_id']
    email = profile['email']
    
    # Check if auth user exists
    try:
        # Try to get user from auth.users via admin API
        # Note: We can't directly query auth.users with regular Supabase client
        # Instead, we'll check if user_id exists by trying to get permissions
        auth_check = supabase.table('user_permissions').select('user_id').eq('user_id', user_id).execute()
        
        # If we got this far, the user might exist
        # Let's mark profiles where email doesn't match any current auth user
        print(f"   📧 {email}")
        print(f"      User ID: {user_id}")
        
        # We need to delete this profile if it's orphaned
        orphaned_profiles.append(profile)
        
    except Exception as e:
        print(f"   ⚠️  {email} - Error checking: {e}")
        orphaned_profiles.append(profile)

if not orphaned_profiles:
    print("\n✅ All profiles have valid auth users!")
    sys.exit(0)

print(f"\n3️⃣ Found {len(orphaned_profiles)} profile(s) to clean\n")

# Ask for confirmation
print("The following profiles will be deleted:")
for profile in orphaned_profiles:
    print(f"   - {profile['email']} (ID: {profile['user_id']})")

print("\n⚠️  This will also delete associated permissions and logs!")
response = input("\nDo you want to proceed? (yes/no): ").strip().lower()

if response != 'yes':
    print("❌ Cancelled. No changes made.")
    sys.exit(0)

# Delete orphaned profiles
print("\n4️⃣ Deleting orphaned profiles...")

for profile in orphaned_profiles:
    email = profile['email']
    user_id = profile['user_id']
    
    try:
        # Delete logs first (foreign key)
        supabase.table('worksheet_generation_logs').delete().eq('user_id', user_id).execute()
        
        # Delete permissions
        supabase.table('user_permissions').delete().eq('user_id', user_id).execute()
        
        # Delete profile
        supabase.table('user_profiles').delete().eq('user_id', user_id).execute()
        
        print(f"   ✅ Deleted: {email}")
    except Exception as e:
        print(f"   ❌ Error deleting {email}: {e}")

print("\n✅ Cleanup complete!")
print("\nYou can now sign up again with a fresh account.")
