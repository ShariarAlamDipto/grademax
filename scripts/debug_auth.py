#!/usr/bin/env python3
"""
Debug authentication and check database state.
This script helps diagnose login and dashboard issues.
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
    print(" GradeMax Authentication Debug")
    print("=" * 70)
    print()
    
    supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials in .env.local")
        sys.exit(1)
    
    print(f"✅ Connected to: {supabase_url}\n")
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # Check if Phase 1 migration is applied
    print("📋 Checking Phase 1 Migration Status...")
    print("-" * 70)
    
    try:
        # Check for Phase 1 tables
        tables_to_check = ['user_sessions', 'trusted_devices', 'audit_log', 'usage_meters']
        
        for table in tables_to_check:
            try:
                result = supabase.table(table).select('id').limit(1).execute()
                print(f"✅ Table '{table}' exists")
            except Exception as e:
                if 'does not exist' in str(e).lower() or 'relation' in str(e).lower():
                    print(f"❌ Table '{table}' NOT FOUND")
                else:
                    print(f"⚠️  Table '{table}' - Unknown error: {e}")
        
        print()
        
        # Check if RPC functions exist
        print("📋 Checking Phase 1 Functions...")
        print("-" * 70)
        
        try:
            # Try calling get_current_month_usage
            result = supabase.rpc('get_current_month_usage', {
                'check_user_id': '00000000-0000-0000-0000-000000000000'
            }).execute()
            print("✅ Function 'get_current_month_usage' exists")
        except Exception as e:
            if 'does not exist' in str(e).lower() or 'function' in str(e).lower():
                print("❌ Function 'get_current_month_usage' NOT FOUND")
                print("\n⚠️  PHASE 1 MIGRATION NOT APPLIED!")
                print("   Run: python scripts/apply_migration_helper.py")
            else:
                print(f"⚠️  Function check error: {e}")
        
        print()
        
    except Exception as e:
        print(f"❌ Error checking migration: {e}")
    
    # Check user profiles
    print("📋 Checking User Profiles...")
    print("-" * 70)
    
    try:
        # Get all users
        users_result = supabase.auth.admin.list_users()
        users = users_result if hasattr(users_result, '__iter__') else []
        
        if hasattr(users_result, 'users'):
            users = users_result.users
        
        print(f"Total users in auth: {len(users) if users else 0}")
        
        if users:
            for user in users[:5]:  # Show first 5
                user_id = user.id
                user_email = user.email
                
                print(f"\n👤 User: {user_email}")
                print(f"   ID: {user_id}")
                
                # Check if profile exists
                try:
                    profile_result = supabase.table('profiles').select('*').eq('id', user_id).execute()
                    if profile_result.data:
                        print(f"   ✅ Profile exists in 'profiles' table")
                    else:
                        print(f"   ❌ NO profile in 'profiles' table")
                except Exception as e:
                    print(f"   ⚠️  Error checking profiles: {e}")
                
                # Check if user_profile exists (Phase 1)
                try:
                    user_profile_result = supabase.table('user_profiles').select('*').eq('user_id', user_id).execute()
                    if user_profile_result.data:
                        print(f"   ✅ Profile exists in 'user_profiles' table")
                        profile = user_profile_result.data[0]
                        print(f"      Role: {profile.get('role_type', 'N/A')}")
                    else:
                        print(f"   ❌ NO profile in 'user_profiles' table")
                except Exception as e:
                    if 'does not exist' in str(e).lower():
                        print(f"   ⚠️  'user_profiles' table doesn't exist (Phase 1 not applied)")
                    else:
                        print(f"   ⚠️  Error checking user_profiles: {e}")
                
                # Check permissions
                try:
                    perm_result = supabase.table('user_permissions').select('*').eq('user_id', user_id).execute()
                    if perm_result.data:
                        perm = perm_result.data[0]
                        print(f"   ✅ Permissions: has_permission={perm.get('has_permission', False)}")
                    else:
                        print(f"   ⚠️  No permissions set")
                except Exception as e:
                    if 'does not exist' in str(e).lower():
                        print(f"   ⚠️  'user_permissions' table doesn't exist")
                    else:
                        print(f"   ⚠️  Error checking permissions: {e}")
        
        print()
        
    except Exception as e:
        print(f"❌ Error checking users: {e}")
    
    # Check database tables
    print("\n📋 Checking Database Tables...")
    print("-" * 70)
    
    critical_tables = ['profiles', 'subjects', 'topics', 'papers', 'pages', 'worksheets']
    
    for table in critical_tables:
        try:
            result = supabase.table(table).select('id').limit(1).execute()
            count = len(result.data) if result.data else 0
            print(f"✅ Table '{table}' exists (sample count: {count})")
        except Exception as e:
            if 'does not exist' in str(e).lower():
                print(f"❌ Table '{table}' NOT FOUND")
            else:
                print(f"⚠️  Table '{table}' - Error: {e}")
    
    print()
    print("=" * 70)
    print(" Summary")
    print("=" * 70)
    print()
    print("If you see errors above:")
    print("1. Phase 1 tables missing → Apply migration: python scripts/apply_migration_helper.py")
    print("2. Profile missing → User needs to complete signup/trigger profile creation")
    print("3. Permissions missing → Grant permission via admin portal")
    print()

if __name__ == '__main__':
    main()
