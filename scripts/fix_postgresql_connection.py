"""
PostgreSQL Connection Troubleshooting Script
Tests multiple connection methods to fix the connection issue
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv('.env.ingest')

def test_method_1_basic():
    """Method 1: Basic psycopg2 connection"""
    print("\n" + "=" * 70)
    print("METHOD 1: Basic psycopg2 Connection")
    print("=" * 70)
    
    try:
        import psycopg2
        database_url = os.getenv('DATABASE_URL')
        
        print(f"📡 Connecting with URL: {database_url[:50]}...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ SUCCESS! Database version: {version[:60]}...")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

def test_method_2_components():
    """Method 2: Connection using individual components"""
    print("\n" + "=" * 70)
    print("METHOD 2: Individual Connection Parameters")
    print("=" * 70)
    
    try:
        import psycopg2
        
        # Parse connection details
        host = "db.tybaetnvnfgniotdfxze.supabase.co"
        port = "5432"
        database = "postgres"
        user = "postgres"
        password = "EV/9GwfMdegWSTg"
        
        print(f"📡 Connecting to:")
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print(f"   Database: {database}")
        print(f"   User: {user}")
        print(f"   Password: {password[:3]}***")
        
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        cursor = conn.cursor()
        
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ SUCCESS! Database version: {version[:60]}...")
        
        # Test a query
        cursor.execute("SELECT COUNT(*) FROM subjects;")
        count = cursor.fetchone()[0]
        print(f"✅ Query test: Found {count} subjects")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

def test_method_3_pooler():
    """Method 3: Using Supabase connection pooler (port 6543)"""
    print("\n" + "=" * 70)
    print("METHOD 3: Supabase Connection Pooler (Recommended)")
    print("=" * 70)
    
    try:
        import psycopg2
        
        # Supabase pooler uses port 6543 instead of 5432
        host = "db.tybaetnvnfgniotdfxze.supabase.co"
        port = "6543"  # Connection pooler port
        database = "postgres"
        user = "postgres"
        password = "EV/9GwfMdegWSTg"
        
        print(f"📡 Connecting via pooler:")
        print(f"   Host: {host}")
        print(f"   Port: {port} (pooler)")
        print(f"   Database: {database}")
        
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            connect_timeout=10
        )
        cursor = conn.cursor()
        
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ SUCCESS! Database version: {version[:60]}...")
        
        # Test queries
        cursor.execute("SELECT COUNT(*) FROM subjects;")
        count = cursor.fetchone()[0]
        print(f"✅ Query test: Found {count} subjects")
        
        cursor.execute("SELECT COUNT(*) FROM topics;")
        count = cursor.fetchone()[0]
        print(f"✅ Query test: Found {count} topics")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 CONNECTION POOLER WORKS!")
        print("   This is the recommended method for production use.")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

def test_method_4_dns_check():
    """Method 4: DNS resolution test"""
    print("\n" + "=" * 70)
    print("METHOD 4: DNS Resolution Test")
    print("=" * 70)
    
    try:
        import socket
        
        hostname = "db.tybaetnvnfgniotdfxze.supabase.co"
        print(f"🔍 Resolving: {hostname}")
        
        ip_address = socket.gethostbyname(hostname)
        print(f"✅ Resolved to IP: {ip_address}")
        
        # Try to connect to the socket
        print(f"\n🔌 Testing TCP connection to {ip_address}:5432...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((ip_address, 5432))
        sock.close()
        
        if result == 0:
            print("✅ Port 5432 is open and reachable")
        else:
            print(f"❌ Port 5432 is not reachable (error code: {result})")
            print("   Trying pooler port 6543...")
            
            sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock2.settimeout(5)
            result2 = sock2.connect_ex((ip_address, 6543))
            sock2.close()
            
            if result2 == 0:
                print("✅ Port 6543 (pooler) is open and reachable!")
                return True
            else:
                print(f"❌ Port 6543 also not reachable (error code: {result2})")
        
        return result == 0 or result2 == 0
        
    except socket.gaierror as e:
        print(f"❌ DNS resolution failed: {str(e)}")
        print("   This might be a network/firewall issue")
        return False
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

def test_method_5_sqlalchemy():
    """Method 5: Using SQLAlchemy (alternative library)"""
    print("\n" + "=" * 70)
    print("METHOD 5: SQLAlchemy Connection (Alternative)")
    print("=" * 70)
    
    try:
        from sqlalchemy import create_engine, text
        
        # Try with pooler port
        database_url = "postgresql://postgres:EV%2F9GwfMdegWSTg@db.tybaetnvnfgniotdfxze.supabase.co:6543/postgres"
        
        print(f"📡 Creating SQLAlchemy engine...")
        engine = create_engine(database_url, pool_pre_ping=True, connect_args={"connect_timeout": 10})
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✅ SUCCESS! Database version: {version[:60]}...")
            
            result = conn.execute(text("SELECT COUNT(*) FROM subjects;"))
            count = result.fetchone()[0]
            print(f"✅ Query test: Found {count} subjects")
        
        return True
        
    except ImportError:
        print("⚠️  SQLAlchemy not installed")
        print("   Install with: pip install sqlalchemy")
        return False
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

def main():
    print("=" * 70)
    print("🔧 POSTGRESQL CONNECTION TROUBLESHOOTING")
    print("=" * 70)
    print("\nTesting multiple connection methods to find what works...")
    
    results = {}
    
    # Test Method 4 first (DNS check)
    results['DNS Check'] = test_method_4_dns_check()
    
    # Test Method 1
    results['Basic Connection'] = test_method_1_basic()
    
    # Test Method 2
    results['Component Connection'] = test_method_2_components()
    
    # Test Method 3 (Recommended)
    results['Pooler Connection'] = test_method_3_pooler()
    
    # Test Method 5
    results['SQLAlchemy'] = test_method_5_sqlalchemy()
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 RESULTS SUMMARY")
    print("=" * 70)
    
    for method, success in results.items():
        status = "✅ WORKS" if success else "❌ FAILED"
        print(f"{method:.<40} {status}")
    
    print("=" * 70)
    
    # Recommendations
    print("\n" + "=" * 70)
    print("💡 RECOMMENDATIONS")
    print("=" * 70)
    
    if results.get('Pooler Connection'):
        print("\n✅ SOLUTION FOUND: Use Connection Pooler (Port 6543)")
        print("\nUpdate your DATABASE_URL in .env.ingest to:")
        print("DATABASE_URL=postgresql://postgres:EV%2F9GwfMdegWSTg@db.tybaetnvnfgniotdfxze.supabase.co:6543/postgres")
        print("                                                                                                          ^^^^")
        print("                                                                                                       Port 6543")
        
    elif results.get('Component Connection'):
        print("\n✅ SOLUTION FOUND: Use component-based connection")
        print("\nCreate connection like this:")
        print("""
import psycopg2
conn = psycopg2.connect(
    host="db.tybaetnvnfgniotdfxze.supabase.co",
    port="5432",
    database="postgres",
    user="postgres",
    password="EV/9GwfMdegWSTg"
)
        """)
        
    elif results.get('SQLAlchemy'):
        print("\n✅ SOLUTION FOUND: Use SQLAlchemy")
        print("\nInstall: pip install sqlalchemy")
        
    else:
        print("\n❌ NO WORKING METHOD FOUND")
        print("\nPossible issues:")
        print("1. Firewall blocking PostgreSQL ports (5432 and 6543)")
        print("2. Network restrictions (corporate/school network)")
        print("3. Supabase project might have IP restrictions")
        print("\n💡 Solutions:")
        print("- Check Supabase dashboard for connection settings")
        print("- Try from a different network")
        print("- Use REST API instead (already working!)")
        print("- Check if VPN/proxy is interfering")
    
    print("=" * 70)

if __name__ == "__main__":
    main()
