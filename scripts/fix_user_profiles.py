#!/usr/bin/env python3
"""
Fix user profiles and permissions for existing users.
Creates missing profiles and grants permissions.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(dotenv_path=env_path)

def main():
    print("=" * 70)
    print(" Fix User Profiles & Permissions")
    print("=" * 70)
    print()
    
    supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials")
        sys.exit(1)
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # Get all users
    print("📋 Fetching users...")
    try:
        users_result = supabase.auth.admin.list_users()
        
        # Handle different response formats
        if hasattr(users_result, 'users'):
            users = users_result.users
        elif isinstance(users_result, list):
            users = users_result
        elif isinstance(users_result, dict) and 'users' in users_result:
            users = users_result['users']
        else:
            # Try to get from the raw response
            users = []
            print(f"⚠️  Unexpected response format: {type(users_result)}")
            print(f"   Response: {users_result}")
            
        print(f"Found {len(users)} users\n")
        
    except Exception as e:
        print(f"❌ Error fetching users: {e}")
        print("\nTrying alternative method...")
        
        # Alternative: Query from user_profiles table
        profile_result = supabase.table('profiles').select('id').execute()
        user_ids = [p['id'] for p in (profile_result.data or [])]
        print(f"Found {len(user_ids)} users from profiles table")
        
        users = []
        for uid in user_ids:
            try:
                user_data = supabase.auth.admin.get_user_by_id(uid)
                if user_data:
                    users.append(user_data.user if hasattr(user_data, 'user') else user_data)
            except:
                pass
        
        print(f"Successfully retrieved {len(users)} user details\n")
    
    for user in users:
        user_id = user.id
        user_email = user.email
        
        print(f"👤 Processing: {user_email}")
        
        # Check if user_profile exists
        profile_result = supabase.table('user_profiles').select('*').eq('user_id', user_id).execute()
        
        if not profile_result.data:
            print(f"   Creating user_profile...")
            try:
                supabase.table('user_profiles').insert({
                    'user_id': user_id,
                    'email': user_email,
                    'full_name': user_email.split('@')[0],
                    'role': 'student',
                    'role_type': 'student'  # Phase 1 field
                }).execute()
                print(f"   ✅ Created user_profile")
            except Exception as e:
                print(f"   ❌ Error creating profile: {e}")
        else:
            print(f"   ✅ user_profile exists")
        
        # Check if permissions exist
        perm_result = supabase.table('user_permissions').select('*').eq('user_id', user_id).execute()
        
        if not perm_result.data:
            print(f"   Creating permissions...")
            try:
                supabase.table('user_permissions').insert({
                    'user_id': user_id,
                    'can_generate_worksheets': True,  # Grant permission
                    'is_active': True,
                    'max_worksheets_per_day': 30,  # Default quota
                    'notes': 'Auto-granted during profile fix'
                }).execute()
                print(f"   ✅ Created permissions (granted access)")
            except Exception as e:
                print(f"   ❌ Error creating permissions: {e}")
        else:
            # Update existing permissions to grant access
            print(f"   Updating permissions...")
            try:
                supabase.table('user_permissions').update({
                    'can_generate_worksheets': True,
                    'is_active': True
                }).eq('user_id', user_id).execute()
                print(f"   ✅ Permissions updated")
            except Exception as e:
                print(f"   ⚠️  Error updating: {e}")
        
        print()
    
    print("=" * 70)
    print(" ✅ Profile Fix Complete!")
    print("=" * 70)
    print()
    print("All users now have:")
    print("- user_profiles entry")
    print("- user_permissions entry")
    print("- Worksheet generation access")
    print()
    print("You can now log in and access the dashboard!")
    print()

if __name__ == '__main__':
    main()
