#!/usr/bin/env python3
"""Check user permissions in detail"""

import os
from dotenv import load_dotenv
from supabase import create_client

# Load from .env.local
load_dotenv('.env.local')

url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not url or not key:
    print("❌ Missing Supabase credentials in .env file")
    exit(1)

supabase = create_client(url, key)

# Get user by email
email = "justarice7@gmail.com"
print(f"Checking permissions for: {email}\n")

# Get user ID from auth
auth_result = supabase.auth.admin.list_users()
users = [u for u in auth_result if u.email == email]

if not users:
    print(f"❌ User {email} not found")
    exit(1)

user = users[0]
user_id = user.id
print(f"✅ Found user: {user.email}")
print(f"   ID: {user_id}\n")

# Check user_permissions
print("📋 Checking user_permissions table...")
perm_result = supabase.table('user_permissions').select('*').eq('user_id', user_id).execute()

if perm_result.data:
    perm = perm_result.data[0]
    print(f"✅ Permissions found:")
    print(f"   can_generate_worksheets: {perm.get('can_generate_worksheets')}")
    print(f"   is_active: {perm.get('is_active')}")
    print(f"   max_worksheets_per_day: {perm.get('max_worksheets_per_day')}")
    print(f"   max_questions_per_worksheet: {perm.get('max_questions_per_worksheet')}")
    print(f"   notes: {perm.get('notes')}")
    print(f"   created_at: {perm.get('created_at')}")
    
    # Calculate hasPermission as dashboard does
    has_permission = perm.get('can_generate_worksheets') and perm.get('is_active')
    print(f"\n🔍 Dashboard hasPermission calculation:")
    print(f"   can_generate_worksheets={perm.get('can_generate_worksheets')} AND is_active={perm.get('is_active')}")
    print(f"   Result: {has_permission}")
    
    if has_permission:
        print(f"\n✅ User SHOULD be able to access dashboard and generate worksheets")
    else:
        print(f"\n❌ User CANNOT generate worksheets")
        if not perm.get('can_generate_worksheets'):
            print(f"   Reason: can_generate_worksheets is False")
        if not perm.get('is_active'):
            print(f"   Reason: is_active is False")
else:
    print(f"❌ No permissions found")

# Check user_profiles
print("\n📋 Checking user_profiles table...")
profile_result = supabase.table('user_profiles').select('*').eq('user_id', user_id).execute()
if profile_result.data:
    profile = profile_result.data[0]
    print(f"✅ Profile found:")
    print(f"   email: {profile.get('email')}")
    print(f"   full_name: {profile.get('full_name')}")
    print(f"   role: {profile.get('role')}")
else:
    print(f"❌ No profile found")

# Check profiles
print("\n📋 Checking profiles table...")
profiles_result = supabase.table('profiles').select('*').eq('id', user_id).execute()
if profiles_result.data:
    p = profiles_result.data[0]
    print(f"✅ Profile found:")
    print(f"   study_level: {p.get('study_level')}")
    print(f"   marks_goal_pct: {p.get('marks_goal_pct')}")
else:
    print(f"❌ No profile found")

print("\n" + "="*60)
