#!/usr/bin/env python3
"""
Check and fix authentication for a specific user.
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
    if len(sys.argv) < 2:
        print("Usage: python check_user.py EMAIL")
        print("Example: python check_user.py justrice7@gmail.com")
        sys.exit(1)
    
    target_email = sys.argv[1]
    
    print("=" * 70)
    print(f" Checking User: {target_email}")
    print("=" * 70)
    print()
    
    supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials")
        sys.exit(1)
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # Get all users
    print("📋 Fetching all users from auth...")
    try:
        users_result = supabase.auth.admin.list_users()
        
        # Handle different response formats
        users = []
        if hasattr(users_result, 'users'):
            users = users_result.users
        elif isinstance(users_result, list):
            users = users_result
        elif isinstance(users_result, dict) and 'users' in users_result:
            users = users_result['users']
        
        print(f"Found {len(users)} total users in auth system\n")
        
        # Find target user
        target_user = None
        for user in users:
            if user.email == target_email:
                target_user = user
                break
        
        if not target_user:
            print(f"❌ User {target_email} NOT FOUND in auth system")
            print("\nPossible reasons:")
            print("1. User hasn't completed Google OAuth signup")
            print("2. Email is different (check spelling)")
            print("3. User signed up but verification pending")
            print("\nAll users in system:")
            for u in users:
                print(f"  - {u.email}")
            sys.exit(1)
        
        user_id = target_user.id
        print(f"✅ Found user in auth system")
        print(f"   Email: {target_user.email}")
        print(f"   ID: {user_id}")
        print()
        
        # Check profiles table
        print("📋 Checking profiles table...")
        profile_result = supabase.table('profiles').select('*').eq('id', user_id).execute()
        
        if not profile_result.data:
            print("❌ NO profile in 'profiles' table")
            print("   Creating profile...")
            try:
                supabase.table('profiles').insert({
                    'id': user_id,
                    'study_level': 'ial',
                    'marks_goal_pct': 90
                }).execute()
                print("✅ Profile created")
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print("✅ Profile exists in 'profiles' table")
        
        # Check user_profiles table
        print("\n📋 Checking user_profiles table...")
        user_profile_result = supabase.table('user_profiles').select('*').eq('user_id', user_id).execute()
        
        if not user_profile_result.data:
            print("❌ NO profile in 'user_profiles' table")
            print("   Creating user_profile...")
            try:
                supabase.table('user_profiles').insert({
                    'user_id': user_id,
                    'email': target_email,
                    'full_name': target_email.split('@')[0],
                    'role': 'student',
                    'role_type': 'student'
                }).execute()
                print("✅ user_profile created")
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print("✅ user_profile exists")
            print(f"   Role: {user_profile_result.data[0].get('role_type', 'N/A')}")
        
        # Check permissions
        print("\n📋 Checking user_permissions table...")
        perm_result = supabase.table('user_permissions').select('*').eq('user_id', user_id).execute()
        
        if not perm_result.data:
            print("❌ NO permissions set")
            print("   Creating permissions...")
            try:
                supabase.table('user_permissions').insert({
                    'user_id': user_id,
                    'can_generate_worksheets': True,
                    'is_active': True,
                    'max_worksheets_per_day': 30,
                    'notes': 'Auto-granted'
                }).execute()
                print("✅ Permissions created (access granted)")
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            perm = perm_result.data[0]
            can_generate = perm.get('can_generate_worksheets', False)
            is_active = perm.get('is_active', False)
            print(f"✅ Permissions exist")
            print(f"   can_generate_worksheets: {can_generate}")
            print(f"   is_active: {is_active}")
            
            if not can_generate or not is_active:
                print("\n⚠️  Permission not active, fixing...")
                try:
                    supabase.table('user_permissions').update({
                        'can_generate_worksheets': True,
                        'is_active': True
                    }).eq('user_id', user_id).execute()
                    print("✅ Permissions activated")
                except Exception as e:
                    print(f"❌ Error: {e}")
        
        print()
        print("=" * 70)
        print(" ✅ User Setup Complete!")
        print("=" * 70)
        print()
        print(f"User {target_email} is now ready to:")
        print("1. Log in at http://localhost:3002/login")
        print("2. View dashboard at http://localhost:3002/dashboard")
        print("3. Generate worksheets (quota: 30/day)")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
