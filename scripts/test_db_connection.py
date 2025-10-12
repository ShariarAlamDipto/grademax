"""
Database Connection Test Script
Tests both REST API and PostgreSQL connections to Supabase
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv('.env.ingest')

def test_environment_variables():
    """Check if all required environment variables are set"""
    print("=" * 70)
    print("🔍 CHECKING ENVIRONMENT VARIABLES")
    print("=" * 70)
    
    required_vars = {
        'SUPABASE_URL': os.getenv('SUPABASE_URL'),
        'SUPABASE_SERVICE_ROLE': os.getenv('SUPABASE_SERVICE_ROLE'),
        'DATABASE_URL': os.getenv('DATABASE_URL'),
        'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY')
    }
    
    all_present = True
    for key, value in required_vars.items():
        if value:
            # Mask sensitive values
            if 'KEY' in key or 'ROLE' in key or 'URL' in key:
                masked = value[:20] + '...' if len(value) > 20 else value
                print(f"✅ {key}: {masked}")
            else:
                print(f"✅ {key}: Set")
        else:
            print(f"❌ {key}: MISSING")
            all_present = False
    
    print()
    return all_present

def test_rest_api_connection():
    """Test Supabase REST API connection"""
    print("=" * 70)
    print("🌐 TESTING SUPABASE REST API CONNECTION")
    print("=" * 70)
    
    try:
        from scripts.supabase_client import SupabaseClient
        
        print("📡 Initializing SupabaseClient...")
        client = SupabaseClient()
        
        print("✅ Client initialized successfully")
        print(f"   URL: {client.url}")
        print(f"   Key: {client.key[:20]}...")
        
        # Test a simple query
        print("\n🔍 Testing database query (fetching subjects)...")
        result = client.select('subjects', '*')
        
        if result:
            print(f"✅ Query successful! Found {len(result)} subjects:")
            for subject in result:
                print(f"   - {subject.get('code')}: {subject.get('name')}")
        else:
            print("⚠️  Query returned no results (database might be empty)")
        
        print("\n✅ REST API CONNECTION SUCCESSFUL")
        return True
        
    except Exception as e:
        print(f"\n❌ REST API CONNECTION FAILED")
        print(f"   Error: {str(e)}")
        return False

def test_postgresql_connection():
    """Test direct PostgreSQL connection"""
    print("\n" + "=" * 70)
    print("🐘 TESTING POSTGRESQL DIRECT CONNECTION")
    print("=" * 70)
    
    try:
        import psycopg2
        print("✅ psycopg2 library found")
    except ImportError:
        print("❌ psycopg2 not installed")
        print("   Install with: pip install psycopg2-binary")
        return False
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set")
        return False
    
    try:
        # Check if using IPv4 pooler
        if 'pooler.supabase.com' in database_url:
            print(f"📡 Connecting via IPv4 pooler...")
            print(f"   Using: aws-1-ap-southeast-1.pooler.supabase.com")
        else:
            print(f"📡 Connecting to: {database_url.split('@')[1].split('/')[0]}...")
        
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("✅ PostgreSQL connection established")
        
        # Test query
        print("\n🔍 Testing query (checking database version)...")
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Database version: {version[:50]}...")
        
        # Check tables
        print("\n🔍 Checking existing tables...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        if tables:
            print(f"✅ Found {len(tables)} tables:")
            for table in tables[:10]:
                print(f"   - {table[0]}")
            if len(tables) > 10:
                print(f"   ... and {len(tables) - 10} more")
        else:
            print("⚠️  No tables found (migrations need to be run)")
        
        # Check data
        print("\n🔍 Checking subjects...")
        cursor.execute("SELECT code, name FROM subjects;")
        subjects = cursor.fetchall()
        if subjects:
            print(f"✅ Found {len(subjects)} subject(s):")
            for code, name in subjects:
                print(f"   - {code}: {name}")
        else:
            print("⚠️  No subjects found")
        
        cursor.close()
        conn.close()
        
        print("\n✅ POSTGRESQL CONNECTION SUCCESSFUL")
        return True
        
    except Exception as e:
        print(f"\n⚠️  POSTGRESQL CONNECTION ISSUE")
        print(f"   Error: {str(e)}")
        
        if 'IPv6' in str(e) or 'getaddrinfo' in str(e) or 'translate host' in str(e):
            print("\n💡 TIP: Update DATABASE_URL to use IPv4 pooler:")
            print("   postgresql://postgres.tybaetnvnfgniotdfxze:PASSWORD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres")
        
        return False

def main():
    """Run all connection tests"""
    print("\n" + "=" * 70)
    print("🚀 GRADEMAX DATABASE CONNECTION TEST")
    print("=" * 70)
    print()
    
    # Test 1: Environment Variables
    env_ok = test_environment_variables()
    if not env_ok:
        print("\n❌ CRITICAL: Missing environment variables")
        print("   Please check your .env.ingest file")
        sys.exit(1)
    
    # Test 2: REST API
    print()
    rest_ok = test_rest_api_connection()
    
    # Test 3: PostgreSQL
    print()
    pg_ok = test_postgresql_connection()
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    print(f"Environment Variables: {'✅ PASS' if env_ok else '❌ FAIL'}")
    print(f"REST API Connection:   {'✅ PASS' if rest_ok else '❌ FAIL'}")
    print(f"PostgreSQL Connection: {'✅ PASS' if pg_ok else '❌ FAIL'}")
    print("=" * 70)
    
    if env_ok and rest_ok:
        print("\n✅ ALL CRITICAL TESTS PASSED!")
        print("   You can now process papers with page_based_ingest.py")
        if not pg_ok:
            print("\n⚠️  Note: PostgreSQL connection failed (optional)")
            print("   REST API is sufficient for paper processing")
    else:
        print("\n❌ SOME TESTS FAILED")
        print("   Please fix the issues above before proceeding")
        sys.exit(1)

if __name__ == "__main__":
    main()
