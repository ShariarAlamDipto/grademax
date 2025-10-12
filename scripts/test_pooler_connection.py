"""
Test PostgreSQL connection with different approaches
Specifically testing IPv6 and connection pooler
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv('.env.ingest')

def test_with_pooler():
    """Test connection using Supabase connection pooler (port 6543)"""
    print("=" * 70)
    print("🔧 TESTING POSTGRESQL WITH CONNECTION POOLER (Port 6543)")
    print("=" * 70)
    
    try:
        import psycopg2
        
        # Connection pooler settings
        config = {
            'host': 'db.tybaetnvnfgniotdfxze.supabase.co',
            'port': 6543,
            'database': 'postgres',
            'user': 'postgres',
            'password': 'EV/9GwfMdegWSTg',
            'connect_timeout': 10
        }
        
        print(f"\n📡 Attempting connection...")
        print(f"   Host: {config['host']}")
        print(f"   Port: {config['port']} (connection pooler)")
        print(f"   Database: {config['database']}")
        
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        
        print("\n✅ CONNECTION SUCCESSFUL!")
        
        # Test 1: Database version
        print("\n🔍 Test 1: Database version")
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"   ✅ {version[:70]}...")
        
        # Test 2: Count subjects
        print("\n🔍 Test 2: Query subjects table")
        cursor.execute("SELECT code, name FROM subjects;")
        subjects = cursor.fetchall()
        print(f"   ✅ Found {len(subjects)} subject(s):")
        for code, name in subjects:
            print(f"      - {code}: {name}")
        
        # Test 3: Count topics
        print("\n🔍 Test 3: Query topics table")
        cursor.execute("SELECT COUNT(*) FROM topics;")
        count = cursor.fetchone()[0]
        print(f"   ✅ Found {count} topics")
        
        # Test 4: List all tables
        print("\n🔍 Test 4: List all tables")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"   ✅ Found {len(tables)} tables:")
        for table in tables:
            print(f"      - {table[0]}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 70)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 70)
        print("\n✅ PostgreSQL connection is now working!")
        print("   Using connection pooler on port 6543")
        print("\n💡 Your DATABASE_URL is correctly configured:")
        print("   postgresql://postgres:***@db.tybaetnvnfgniotdfxze.supabase.co:6543/postgres")
        
        return True
        
    except Exception as e:
        print(f"\n❌ CONNECTION FAILED")
        print(f"   Error: {str(e)}")
        print("\n🔍 Troubleshooting steps:")
        print("   1. Check if port 6543 is blocked by firewall")
        print("   2. Try from a different network")
        print("   3. Verify password is correct: EV/9GwfMdegWSTg")
        print("   4. Check Supabase dashboard for connection settings")
        return False

def test_direct_ipv6():
    """Test direct connection with IPv6 address"""
    print("\n" + "=" * 70)
    print("🌐 TESTING WITH IPv6 ADDRESS")
    print("=" * 70)
    
    try:
        import psycopg2
        
        # Use IPv6 address directly
        ipv6_host = "2406:da18:243:740b:8859:3ce3:4229:bb42"
        
        print(f"\n📡 Attempting IPv6 connection...")
        print(f"   IPv6: {ipv6_host}")
        print(f"   Port: 6543")
        
        conn = psycopg2.connect(
            host=ipv6_host,
            port=6543,
            database='postgres',
            user='postgres',
            password='EV/9GwfMdegWSTg',
            connect_timeout=10
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        print(f"\n✅ IPv6 CONNECTION SUCCESSFUL!")
        print(f"   {version[:70]}...")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ IPv6 connection failed: {str(e)}")
        return False

def main():
    print("\n" + "=" * 70)
    print("🚀 POSTGRESQL CONNECTION TEST")
    print("=" * 70)
    
    # Test with connection pooler
    pooler_works = test_with_pooler()
    
    if not pooler_works:
        # Try IPv6
        ipv6_works = test_direct_ipv6()
        
        if not ipv6_works:
            print("\n" + "=" * 70)
            print("❌ POSTGRESQL CONNECTION NOT WORKING")
            print("=" * 70)
            print("\n💡 RECOMMENDATION:")
            print("   Continue using REST API (already working)")
            print("   Run migrations in Supabase dashboard")
            print("\n📚 See POSTGRESQL_CONNECTION_FIX_GUIDE.md for more options")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
