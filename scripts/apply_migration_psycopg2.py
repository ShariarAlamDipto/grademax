#!/usr/bin/env python3
"""
Apply Phase 1 security migration using psycopg2.
This connects directly to PostgreSQL and executes the SQL.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(dotenv_path=env_path)

def apply_migration():
    """Apply migration using psycopg2."""
    try:
        import psycopg2
    except ImportError:
        print("❌ psycopg2 not installed.")
        print("\n📦 Installing psycopg2-binary...")
        import subprocess
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'psycopg2-binary'])
        import psycopg2
        print("✅ psycopg2-binary installed successfully\n")
    
    print("📦 Loading configuration...")
    
    # Connection parameters
    # For Supabase, we need to extract the connection details
    supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url:
        print("❌ Missing NEXT_PUBLIC_SUPABASE_URL in .env.local")
        sys.exit(1)
    
    # Extract project ref from URL: https://PROJECT_REF.supabase.co
    project_ref = supabase_url.replace('https://', '').replace('.supabase.co', '')
    
    # Supabase PostgreSQL connection details
    db_host = f"{project_ref}.supabase.co"
    db_port = 5432
    db_name = "postgres"
    db_user = "postgres"
    
    print(f"🔌 Connecting to: {db_host}")
    print("\n⚠️  You will be prompted for the database password.")
    print("   Get it from: Supabase Dashboard → Settings → Database → Connection string")
    print("   (It's different from the service role key)\n")
    
    # Prompt for password
    import getpass
    db_password = getpass.getpass("Enter PostgreSQL password: ")
    
    # Read migration
    migration_path = Path(__file__).parent.parent / 'supabase' / 'migrations' / '02_phase1_security.sql'
    print(f"\n📄 Reading migration: {migration_path.name}")
    
    with open(migration_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    print("\n🚀 Applying migration...")
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        )
        
        cursor = conn.cursor()
        
        # Execute migration
        cursor.execute(sql)
        conn.commit()
        
        print("✅ Migration applied successfully!\n")
        print("📊 New tables created:")
        print("   - user_sessions")
        print("   - trusted_devices")
        print("   - audit_log")
        print("   - usage_meters\n")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == '__main__':
    success = apply_migration()
    sys.exit(0 if success else 1)
