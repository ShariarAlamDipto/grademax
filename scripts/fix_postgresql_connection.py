"""
PostgreSQL Connection Troubleshooting Script
Tests multiple connection methods to diagnose connection issues.

All credentials come from the environment (DATABASE_URL, or the individual
SUPABASE_DB_* vars) — nothing is hardcoded. Set them in .env.ingest.
"""

import os
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv('.env.ingest')


def _database_url(port: int | None = None) -> str:
    """Return the DATABASE_URL, or synthesize one from SUPABASE_DB_* env vars.

    Raises if no credentials are configured — we never fall back to a
    hardcoded password.
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        if port:
            parsed = urlparse(url)
            netloc = parsed.netloc.rsplit(":", 1)[0] + f":{port}"
            url = parsed._replace(netloc=netloc).geturl()
        return url

    host = os.environ.get("SUPABASE_DB_HOST")
    password = os.environ.get("SUPABASE_DB_PASSWORD")
    if not host or not password:
        raise RuntimeError(
            "No DB credentials in environment. Set DATABASE_URL, or "
            "SUPABASE_DB_HOST + SUPABASE_DB_PASSWORD, in .env.ingest."
        )
    user = os.environ.get("SUPABASE_DB_USER", "postgres")
    name = os.environ.get("SUPABASE_DB_NAME", "postgres")
    return f"postgresql://{user}:{password}@{host}:{port or 5432}/{name}"


def _db_host() -> str:
    parsed = urlparse(_database_url())
    if not parsed.hostname:
        raise RuntimeError("Could not determine DB host from DATABASE_URL")
    return parsed.hostname


def test_method_1_basic():
    """Method 1: Basic psycopg2 connection from DATABASE_URL"""
    print("\n" + "=" * 70)
    print("METHOD 1: Basic psycopg2 Connection")
    print("=" * 70)

    try:
        import psycopg2
        database_url = _database_url()

        print(f"Connecting with URL host: {urlparse(database_url).hostname}")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"SUCCESS! Database version: {version[:60]}...")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"FAILED: {str(e)}")
        return False


def test_method_3_pooler():
    """Method 3: Using Supabase connection pooler (port 6543)"""
    print("\n" + "=" * 70)
    print("METHOD 3: Supabase Connection Pooler (Recommended)")
    print("=" * 70)

    try:
        import psycopg2

        database_url = _database_url(port=6543)
        print(f"Connecting via pooler host: {urlparse(database_url).hostname}:6543")

        conn = psycopg2.connect(database_url, connect_timeout=10)
        cursor = conn.cursor()

        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"SUCCESS! Database version: {version[:60]}...")

        cursor.execute("SELECT COUNT(*) FROM subjects;")
        count = cursor.fetchone()[0]
        print(f"Query test: Found {count} subjects")

        cursor.close()
        conn.close()

        print("\nCONNECTION POOLER WORKS!")
        return True

    except Exception as e:
        print(f"FAILED: {str(e)}")
        return False


def test_method_4_dns_check():
    """Method 4: DNS resolution + port reachability test"""
    print("\n" + "=" * 70)
    print("METHOD 4: DNS Resolution Test")
    print("=" * 70)

    result = result2 = 1
    try:
        hostname = _db_host()
        print(f"Resolving: {hostname}")

        ip_address = socket.gethostbyname(hostname)
        print(f"Resolved to IP: {ip_address}")

        print(f"\nTesting TCP connection to {ip_address}:5432...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((ip_address, 5432))
        sock.close()

        if result == 0:
            print("Port 5432 is open and reachable")
        else:
            print(f"Port 5432 is not reachable (error code: {result}); trying 6543...")
            sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock2.settimeout(5)
            result2 = sock2.connect_ex((ip_address, 6543))
            sock2.close()
            if result2 == 0:
                print("Port 6543 (pooler) is open and reachable!")
            else:
                print(f"Port 6543 also not reachable (error code: {result2})")

        return result == 0 or result2 == 0

    except socket.gaierror as e:
        print(f"DNS resolution failed: {str(e)}")
        return False
    except Exception as e:
        print(f"FAILED: {str(e)}")
        return False


def test_method_5_sqlalchemy():
    """Method 5: Using SQLAlchemy (alternative library)"""
    print("\n" + "=" * 70)
    print("METHOD 5: SQLAlchemy Connection (Alternative)")
    print("=" * 70)

    try:
        from sqlalchemy import create_engine, text

        database_url = _database_url(port=6543)
        print("Creating SQLAlchemy engine...")
        engine = create_engine(database_url, pool_pre_ping=True, connect_args={"connect_timeout": 10})

        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"SUCCESS! Database version: {version[:60]}...")

            result = conn.execute(text("SELECT COUNT(*) FROM subjects;"))
            count = result.fetchone()[0]
            print(f"Query test: Found {count} subjects")

        return True

    except ImportError:
        print("SQLAlchemy not installed. Install with: pip install sqlalchemy")
        return False
    except Exception as e:
        print(f"FAILED: {str(e)}")
        return False


def main():
    print("=" * 70)
    print("POSTGRESQL CONNECTION TROUBLESHOOTING")
    print("=" * 70)
    print("\nTesting multiple connection methods to find what works...")

    try:
        _database_url()
    except RuntimeError as e:
        print(f"\n{e}")
        sys.exit(1)

    results = {
        'DNS Check': test_method_4_dns_check(),
        'Basic Connection': test_method_1_basic(),
        'Pooler Connection': test_method_3_pooler(),
        'SQLAlchemy': test_method_5_sqlalchemy(),
    }

    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    for method, success in results.items():
        status = "WORKS" if success else "FAILED"
        print(f"{method:.<40} {status}")
    print("=" * 70)

    if results.get('Pooler Connection'):
        print("\nSOLUTION: Use the connection pooler (port 6543).")
        print("Set DATABASE_URL in .env.ingest to your pooler URL on port 6543.")
    elif results.get('Basic Connection'):
        print("\nSOLUTION: Direct connection works — keep your current DATABASE_URL.")
    elif results.get('SQLAlchemy'):
        print("\nSOLUTION: SQLAlchemy works. Install: pip install sqlalchemy")
    else:
        print("\nNO WORKING METHOD FOUND. Check firewall/network and Supabase settings.")

    print("=" * 70)


if __name__ == "__main__":
    main()
