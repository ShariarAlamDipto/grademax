"""
Test PostgreSQL connection with different approaches
Specifically testing IPv6 and connection pooler.

Credentials are read from the environment (DATABASE_URL, or the individual
PG* / SUPABASE_DB_* vars) — never hardcoded. Set them in .env.ingest.
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv('.env.ingest')


def _db_config(port: int) -> dict:
    """Build a psycopg2 config from env. Prefers DATABASE_URL when present."""
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        parsed = urlparse(database_url)
        return {
            'host': parsed.hostname,
            'port': parsed.port or port,
            'database': (parsed.path or '/postgres').lstrip('/') or 'postgres',
            'user': parsed.username,
            'password': parsed.password,
            'connect_timeout': 10,
        }
    host = os.environ.get("SUPABASE_DB_HOST") or os.environ.get("PGHOST")
    password = os.environ.get("SUPABASE_DB_PASSWORD") or os.environ.get("PGPASSWORD")
    if not host or not password:
        raise RuntimeError(
            "No DB credentials in environment. Set DATABASE_URL, or "
            "SUPABASE_DB_HOST + SUPABASE_DB_PASSWORD, in .env.ingest."
        )
    return {
        'host': host,
        'port': port,
        'database': os.environ.get("SUPABASE_DB_NAME", "postgres"),
        'user': os.environ.get("SUPABASE_DB_USER", "postgres"),
        'password': password,
        'connect_timeout': 10,
    }


def test_with_pooler():
    """Test connection using Supabase connection pooler (port 6543)"""
    print("=" * 70)
    print("TESTING POSTGRESQL WITH CONNECTION POOLER (Port 6543)")
    print("=" * 70)

    try:
        import psycopg2

        config = _db_config(port=6543)

        print("\nAttempting connection...")
        print(f"   Host: {config['host']}")
        print(f"   Port: {config['port']} (connection pooler)")
        print(f"   Database: {config['database']}")

        conn = psycopg2.connect(**config)
        cursor = conn.cursor()

        print("\nCONNECTION SUCCESSFUL!")

        print("\nTest 1: Database version")
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"   {version[:70]}...")

        print("\nTest 2: Query subjects table")
        cursor.execute("SELECT code, name FROM subjects;")
        subjects = cursor.fetchall()
        print(f"   Found {len(subjects)} subject(s):")
        for code, name in subjects:
            print(f"      - {code}: {name}")

        print("\nTest 3: Query topics table")
        cursor.execute("SELECT COUNT(*) FROM topics;")
        count = cursor.fetchone()[0]
        print(f"   Found {count} topics")

        print("\nTest 4: List all tables")
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"   Found {len(tables)} tables:")
        for table in tables:
            print(f"      - {table[0]}")

        cursor.close()
        conn.close()

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED!")
        print("=" * 70)
        return True

    except Exception as e:
        print("\nCONNECTION FAILED")
        print(f"   Error: {str(e)}")
        print("\nTroubleshooting steps:")
        print("   1. Check if port 6543 is blocked by firewall")
        print("   2. Try from a different network")
        print("   3. Verify DATABASE_URL / SUPABASE_DB_* env vars are set correctly")
        print("   4. Check Supabase dashboard for connection settings")
        return False


def test_direct_ipv6():
    """Test direct connection with an explicit IPv6 host from env."""
    print("\n" + "=" * 70)
    print("TESTING WITH IPv6 ADDRESS")
    print("=" * 70)

    ipv6_host = os.environ.get("SUPABASE_DB_IPV6")
    if not ipv6_host:
        print("\nSkipped: set SUPABASE_DB_IPV6 to test a direct IPv6 connection.")
        return False

    try:
        import psycopg2

        config = _db_config(port=6543)
        config['host'] = ipv6_host

        print("\nAttempting IPv6 connection...")
        print(f"   IPv6: {ipv6_host}")
        print("   Port: 6543")

        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]

        print("\nIPv6 CONNECTION SUCCESSFUL!")
        print(f"   {version[:70]}...")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"\nIPv6 connection failed: {str(e)}")
        return False


def main():
    print("\n" + "=" * 70)
    print("POSTGRESQL CONNECTION TEST")
    print("=" * 70)

    pooler_works = test_with_pooler()

    if not pooler_works:
        ipv6_works = test_direct_ipv6()

        if not ipv6_works:
            print("\n" + "=" * 70)
            print("POSTGRESQL CONNECTION NOT WORKING")
            print("=" * 70)
            print("\nRECOMMENDATION:")
            print("   Continue using REST API (already working)")
            print("   Run migrations in Supabase dashboard")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
