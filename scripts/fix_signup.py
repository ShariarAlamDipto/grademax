#!/usr/bin/env python3
"""
Apply the signup trigger fix to database.
This fixes the "Database error saving new user" issue.
"""

import os
import sys
import webbrowser
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(dotenv_path=env_path)

def main():
    print("=" * 70)
    print(" Fix Signup Trigger")
    print("=" * 70)
    print()
    
    supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    
    if not supabase_url:
        print("❌ Missing NEXT_PUBLIC_SUPABASE_URL")
        sys.exit(1)
    
    project_ref = supabase_url.replace('https://', '').replace('.supabase.co', '')
    
    fix_file = Path(__file__).parent.parent / 'supabase' / 'migrations' / 'fix_signup_trigger.sql'
    
    print("📋 Issue: Database error when new users sign up")
    print("📋 Fix: Update handle_new_user() trigger\n")
    
    print("📝 Steps to apply fix:")
    print("-" * 70)
    print("1. Opening Supabase SQL Editor in browser...")
    print("2. Copy the SQL from: supabase/migrations/fix_signup_trigger.sql")
    print("3. Paste and run in SQL Editor")
    print("4. Wait for success message")
    print()
    
    sql_url = f"https://supabase.com/dashboard/project/{project_ref}/sql/new"
    
    print(f"🔗 Opening: {sql_url}\n")
    
    try:
        webbrowser.open(sql_url)
        print("✅ Browser opened!")
    except:
        print(f"⚠️  Couldn't open browser automatically")
        print(f"   Please manually open: {sql_url}")
    
    print()
    print("=" * 70)
    print(" After applying the fix:")
    print("=" * 70)
    print()
    print("1. Clear your browser cache and cookies")
    print("2. Go to: http://localhost:3002/login")
    print("3. Click 'Continue with Google'")
    print("4. Complete sign-in")
    print("5. You should be redirected to dashboard")
    print()
    print("The new user will automatically get:")
    print("  ✅ user_profiles entry")
    print("  ✅ user_permissions (enabled)")
    print("  ✅ profiles entry")
    print("  ✅ Default quota: 30 worksheets/day")
    print()
    
    input("Press Enter to view the SQL fix file...")
    
    print("\n" + "=" * 70)
    print(" SQL Fix Content:")
    print("=" * 70)
    print()
    
    with open(fix_file, 'r') as f:
        print(f.read())

if __name__ == '__main__':
    main()
