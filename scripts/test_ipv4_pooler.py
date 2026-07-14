"""
Test PostgreSQL connection with the IPv4-compatible AWS pooler.

Credentials are read from DATABASE_URL (or SUPABASE_DB_* env vars) — nothing
is hardcoded. Set them in .env.ingest.
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv('.env.ingest')


def _pooler_config(port: int) -> dict:
    """Build a psycopg2 config from env. Prefers DATABASE_URL when present."""
    url = os.environ.get("DATABASE_URL")
    if url:
        parsed = urlparse(url)
        if not parsed.hostname or not parsed.password:
            raise RuntimeError("DATABASE_URL is missing host or password")
        return {
            'host': parsed.hostname,
            'port': port,
            'database': (parsed.path or '/postgres').lstrip('/') or 'postgres',
            'user': parsed.username,
            'password': parsed.password,
            'connect_timeout': 10,
        }
    host = os.environ.get("SUPABASE_DB_HOST")
    user = os.environ.get("SUPABASE_DB_USER")
    password = os.environ.get("SUPABASE_DB_PASSWORD")
    if not host or not user or not password:
        raise RuntimeError(
            "No DB credentials in environment. Set DATABASE_URL, or "
            "SUPABASE_DB_HOST + SUPABASE_DB_USER + SUPABASE_DB_PASSWORD, in .env.ingest."
        )
    return {
        'host': host,
        'port': port,
        'database': os.environ.get("SUPABASE_DB_NAME", "postgres"),
        'user': user,
        'password': password,
        'connect_timeout': 10,
    }


def test_transaction_pooler():
    """Test connection using the Transaction Pooler (port 6543, IPv4-compatible)"""
    print("=" * 70)
    print("TESTING POSTGRESQL WITH IPv4 TRANSACTION POOLER")
    print("=" * 70)

    try:
        import psycopg2

        config = _pooler_config(port=6543)

        print("\nConnection Details:")
        print(f"   Host: {config['host']} (IPv4 proxy)")
        print(f"   Port: {config['port']} (transaction pooler)")
        print(f"   User: {config['user']}")
        print(f"   Database: {config['database']}")

        print("\nAttempting connection...")
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()

        print("CONNECTION SUCCESSFUL!")

        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"Version: {version[:80]}...")

        cursor.execute("SELECT code, name FROM subjects ORDER BY code;")
        subjects = cursor.fetchall()
        print(f"Found {len(subjects)} subject(s)")

        cursor.execute("SELECT COUNT(*) FROM papers;")
        print(f"Papers: {cursor.fetchone()[0]}")

        cursor.execute("SELECT COUNT(*) FROM pages;")
        print(f"Pages: {cursor.fetchone()[0]}")

        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"Found {len(tables)} tables")

        cursor.close()
        conn.close()

        print("\nALL TESTS PASSED — Transaction Pooler (IPv4) is working.")
        return True

    except Exception as e:
        print("\nCONNECTION FAILED")
        print(f"   Error: {str(e)}")
        print("\nTroubleshooting:")
        print("   1. Verify DATABASE_URL / SUPABASE_DB_* env vars are set")
        print("   2. Check username format (postgres.<project-ref> for the pooler)")
        print("   3. Ensure port 6543 is not blocked")
        return False


def test_session_pooler():
    """Test connection using the Session Pooler (port 5432)"""
    print("\n" + "=" * 70)
    print("TESTING SESSION POOLER (Alternative)")
    print("=" * 70)

    try:
        import psycopg2

        config = _pooler_config(port=5432)

        print("Testing Session Pooler (port 5432)...")
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()

        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]

        print("Session Pooler also works!")
        print(f"   {version[:70]}...")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"Session pooler test: {str(e)}")
        return False


def main():
    print("\n" + "=" * 70)
    print("POSTGRESQL IPv4 POOLER CONNECTION TEST")
    print("=" * 70)

    try:
        _pooler_config(port=6543)
    except RuntimeError as e:
        print(f"\n{e}")
        sys.exit(1)

    transaction_works = test_transaction_pooler()

    if transaction_works:
        test_session_pooler()
        print("\nPOSTGRESQL CONNECTION WORKING!")
    else:
        print("\nCONNECTION FAILED — continue using the REST API (already working).")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
