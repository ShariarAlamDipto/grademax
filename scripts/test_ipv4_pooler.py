"""
Test PostgreSQL connection with IPv4-compatible AWS pooler
This should work since the pooler uses IPv4 proxy
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv('.env.ingest')

def test_transaction_pooler():
    """Test connection using Supabase Transaction Pooler (IPv4-compatible)"""
    print("=" * 70)
    print("🌐 TESTING POSTGRESQL WITH IPv4 TRANSACTION POOLER")
    print("=" * 70)
    
    try:
        import psycopg2
        
        # Transaction pooler settings (IPv4-compatible)
        config = {
            'host': 'aws-1-ap-southeast-1.pooler.supabase.com',
            'port': 6543,
            'database': 'postgres',
            'user': 'postgres.tybaetnvnfgniotdfxze',
            'password': 'EV/9GwfMdegWSTg',
            'connect_timeout': 10
        }
        
        print(f"\n📡 Connection Details:")
        print(f"   Host: {config['host']} (IPv4 proxy)")
        print(f"   Port: {config['port']} (transaction pooler)")
        print(f"   User: {config['user']}")
        print(f"   Database: {config['database']}")
        
        print(f"\n🔌 Attempting connection...")
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        
        print("✅ CONNECTION SUCCESSFUL!")
        
        # Test 1: Database version
        print("\n" + "=" * 70)
        print("🔍 TEST 1: Database Version")
        print("=" * 70)
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ {version[:80]}...")
        
        # Test 2: Count subjects
        print("\n" + "=" * 70)
        print("🔍 TEST 2: Query Subjects Table")
        print("=" * 70)
        cursor.execute("SELECT code, name FROM subjects ORDER BY code;")
        subjects = cursor.fetchall()
        if subjects:
            print(f"✅ Found {len(subjects)} subject(s):")
            for code, name in subjects:
                print(f"   - {code}: {name}")
        else:
            print("⚠️  No subjects found")
        
        # Test 3: Count topics
        print("\n" + "=" * 70)
        print("🔍 TEST 3: Query Topics Table")
        print("=" * 70)
        cursor.execute("SELECT code, name FROM topics ORDER BY code;")
        topics = cursor.fetchall()
        if topics:
            print(f"✅ Found {len(topics)} topics:")
            for code, name in topics[:8]:
                print(f"   - Topic {code}: {name}")
        else:
            print("⚠️  No topics found")
        
        # Test 4: Check papers
        print("\n" + "=" * 70)
        print("🔍 TEST 4: Check Papers Table")
        print("=" * 70)
        cursor.execute("SELECT COUNT(*) FROM papers;")
        count = cursor.fetchone()[0]
        print(f"✅ Papers table exists")
        print(f"   Current count: {count} papers")
        if count == 0:
            print("   📝 Ready for paper ingestion!")
        
        # Test 5: Check pages
        print("\n" + "=" * 70)
        print("🔍 TEST 5: Check Pages Table")
        print("=" * 70)
        cursor.execute("SELECT COUNT(*) FROM pages;")
        count = cursor.fetchone()[0]
        print(f"✅ Pages table exists")
        print(f"   Current count: {count} pages")
        if count == 0:
            print("   📝 Ready for paper ingestion!")
        
        # Test 6: List all tables
        print("\n" + "=" * 70)
        print("🔍 TEST 6: Database Schema")
        print("=" * 70)
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"✅ Found {len(tables)} tables:")
        for table in tables:
            print(f"   - {table[0]}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 70)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 70)
        
        print("\n✅ PostgreSQL connection is now WORKING!")
        print(f"   Using: Transaction Pooler (IPv4-compatible)")
        print(f"   Host: aws-1-ap-southeast-1.pooler.supabase.com")
        print(f"   Port: 6543")
        
        print("\n💡 Connection Details:")
        print("   - IPv4 proxy: Enabled")
        print("   - Serverless-friendly: Yes")
        print("   - Transaction pooler: Ideal for brief connections")
        print("   - Note: PREPARE statements not supported")
        
        print("\n📝 Your DATABASE_URL in .env.ingest:")
        print("   postgresql://postgres.tybaetnvnfgniotdfxze:***@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres")
        
        return True
        
    except Exception as e:
        print(f"\n❌ CONNECTION FAILED")
        print(f"   Error: {str(e)}")
        print("\n🔍 Troubleshooting:")
        print("   1. Verify password: EV/9GwfMdegWSTg")
        print("   2. Check username format: postgres.tybaetnvnfgniotdfxze")
        print("   3. Ensure port 6543 is not blocked")
        return False

def test_session_pooler():
    """Test connection using Session Pooler (alternative, port 5432)"""
    print("\n" + "=" * 70)
    print("🌐 TESTING SESSION POOLER (Alternative)")
    print("=" * 70)
    
    try:
        import psycopg2
        
        config = {
            'host': 'aws-1-ap-southeast-1.pooler.supabase.com',
            'port': 5432,
            'database': 'postgres',
            'user': 'postgres.tybaetnvnfgniotdfxze',
            'password': 'EV/9GwfMdegWSTg',
            'connect_timeout': 10
        }
        
        print(f"📡 Testing Session Pooler (port 5432)...")
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        print(f"✅ Session Pooler also works!")
        print(f"   {version[:70]}...")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"⚠️  Session pooler test: {str(e)}")
        return False

def main():
    print("\n" + "=" * 70)
    print("🚀 POSTGRESQL IPv4 POOLER CONNECTION TEST")
    print("=" * 70)
    print("\nTesting Supabase's IPv4-compatible connection poolers...")
    
    # Test Transaction Pooler (recommended)
    transaction_works = test_transaction_pooler()
    
    if transaction_works:
        # Also test Session Pooler
        test_session_pooler()
        
        print("\n" + "=" * 70)
        print("✅ POSTGRESQL CONNECTION WORKING!")
        print("=" * 70)
        print("\n🎉 You can now use PostgreSQL directly!")
        print("\nRecommended for:")
        print("   - Database migrations")
        print("   - Complex SQL queries")
        print("   - Direct database access")
        
        print("\n💡 Choose between:")
        print("   1. Transaction Pooler (port 6543) - For serverless/brief connections")
        print("   2. Session Pooler (port 5432) - For longer sessions")
        print("   3. REST API - Still works great for most operations")
        
    else:
        print("\n" + "=" * 70)
        print("❌ CONNECTION FAILED")
        print("=" * 70)
        print("\n💡 Continue using REST API (already working)")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
