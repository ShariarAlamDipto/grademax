#!/usr/bin/env python3
"""
Apply Phase 1 security migration to Supabase database.
This script executes the SQL migration using the Supabase REST API.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env.local
env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(dotenv_path=env_path)

def apply_migration():
    """Apply the Phase 1 security migration."""
    print("📦 Loading Supabase credentials...")
    
    supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Error: Missing Supabase credentials in .env.local")
        sys.exit(1)
    
    print(f"✅ Connected to: {supabase_url}\n")
    
    # Create Supabase client
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # Read migration file
    migration_path = Path(__file__).parent.parent / 'supabase' / 'migrations' / '02_phase1_security.sql'
    print(f"📄 Reading migration: {migration_path.name}")
    
    with open(migration_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    print("\n🚀 Applying Phase 1 migration to database...")
    print("   This will create:")
    print("   - user_sessions table (session tracking)")
    print("   - trusted_devices table (device management)")
    print("   - audit_log table (tamper-evident logging)")
    print("   - usage_meters table (quota tracking)")
    print("   - Helper functions and RLS policies\n")
    
    try:
        # Execute SQL via Supabase PostgREST
        # Note: Supabase Python client doesn't support direct SQL execution
        # We need to use the SQL Editor in dashboard or use psycopg2
        
        print("⚠️  Note: Supabase Python client doesn't support direct SQL execution.")
        print("\n📝 Please apply the migration manually using one of these methods:\n")
        
        print("METHOD 1: Supabase Dashboard (Recommended)")
        print("=" * 60)
        print("1. Go to: https://supabase.com/dashboard")
        print("2. Select your project")
        print("3. Navigate to: SQL Editor")
        print("4. Click: New Query")
        print("5. Copy and paste the contents of:")
        print(f"   {migration_path}")
        print("6. Click: Run\n")
        
        print("METHOD 2: psql Command Line")
        print("=" * 60)
        print("If you have PostgreSQL client installed:")
        print(f"psql -h tybaetnvnfgniotdfxze.supabase.co -p 5432 -d postgres -U postgres -f {migration_path}")
        print("(You'll be prompted for the database password)\n")
        
        print("METHOD 3: Using psycopg2 (Install first)")
        print("=" * 60)
        print("pip install psycopg2-binary")
        print("Then run: python scripts/apply_migration_psycopg2.py\n")
        
        # Try to verify if tables already exist
        print("🔍 Checking if migration already applied...")
        try:
            # Check if user_sessions table exists
            result = supabase.table('user_sessions').select('id').limit(1).execute()
            print("✅ Migration appears to be already applied (user_sessions table exists)")
            return True
        except Exception as check_error:
            if 'relation' in str(check_error).lower() or 'does not exist' in str(check_error).lower():
                print("❌ Migration not yet applied (tables don't exist)")
                print("\n👉 Please use METHOD 1 (Dashboard) above to apply the migration.")
                return False
            else:
                print(f"⚠️  Could not verify: {check_error}")
                return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    success = apply_migration()
    sys.exit(0 if success else 1)
