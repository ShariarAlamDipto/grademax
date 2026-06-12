#!/usr/bin/env python3
"""
Shared direct-Postgres connector for GradeMax scripts.

Supabase's direct host (db.<ref>.supabase.co) publishes only an AAAA record —
from IPv4-only networks it is unreachable ("could not translate host name").
This connector falls back to the IPv4 session pooler
(aws-N-<region>.pooler.supabase.com:5432, user postgres.<ref>) automatically.

Usage:
    from lib.db_connect import connect_db
    conn = connect_db(readonly=True)
"""

import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import psycopg2
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(REPO_ROOT / ".env.local")

POOLER_REGIONS = [
    "ap-southeast-1",  # this project's region (AAAA prefix 2406:da18 = Singapore)
    "ap-south-1", "us-east-1", "us-east-2", "us-west-1",
    "eu-central-1", "eu-west-1", "eu-west-2", "ap-northeast-1", "sa-east-1",
]


def _pooler_candidates(url: str) -> list[dict]:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if not host.endswith(".supabase.co") or not host.startswith("db."):
        return []
    ref = host.split(".")[1]
    password = unquote(parsed.password or "")
    dbname = (parsed.path or "/postgres").lstrip("/") or "postgres"
    return [
        {
            "host": f"{cluster}-{region}.pooler.supabase.com",
            "port": 5432,
            "user": f"postgres.{ref}",
            "password": password,
            "dbname": dbname,
        }
        for region in POOLER_REGIONS
        for cluster in ("aws-1", "aws-0")
    ]


def connect_db(readonly: bool = True, url: str | None = None):
    """Connect to DATABASE_URL, falling back to the Supabase session pooler."""
    url = url or os.getenv("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL not set in .env.local "
              "(Supabase Dashboard -> Settings -> Database -> Connection string)")
        sys.exit(2)

    host = urlparse(url).hostname or "?"
    print(f"Connecting to {host}...")
    conn = None
    try:
        conn = psycopg2.connect(url, connect_timeout=10)
    except psycopg2.OperationalError as direct_error:
        print(f"  direct connection failed ({str(direct_error).strip()}); trying session pooler...")
        for cand in _pooler_candidates(url):
            try:
                conn = psycopg2.connect(connect_timeout=8, **cand)
                print(f"  connected via pooler: {cand['host']}")
                break
            except psycopg2.OperationalError:
                continue
    if conn is None:
        print("ERROR: could not reach the database directly or via any pooler region.")
        sys.exit(2)

    conn.set_session(readonly=readonly, autocommit=readonly)
    return conn
