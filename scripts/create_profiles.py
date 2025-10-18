#!/usr/bin/env python3
"""
Create profiles table entries for users who don't have them.
The dashboard checks the 'profiles' table for basic user info.
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
    print(" Create Profiles Table Entries")
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
    users_result = supabase.auth.admin.list_users()
    users = users_result.users if hasattr(users_result, 'users') else []
    
    print(f"Found {len(users)} users\n")
    
    for user in users:
        user_id = user.id
        user_email = user.email
        
        print(f"👤 Processing: {user_email}")
        
        # Check if profile exists in 'profiles' table
        profile_result = supabase.table('profiles').select('*').eq('id', user_id).execute()
        
        if not profile_result.data:
            print(f"   Creating profile in 'profiles' table...")
            try:
                supabase.table('profiles').insert({
                    'id': user_id,
                    'study_level': 'ial',  # Default level
                    'marks_goal_pct': 90   # Default goal
                }).execute()
                print(f"   ✅ Created profile")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        else:
            print(f"   ✅ Profile already exists")
        
        print()
    
    print("=" * 70)
    print(" ✅ Complete!")
    print("=" * 70)
    print()

if __name__ == '__main__':
    main()
