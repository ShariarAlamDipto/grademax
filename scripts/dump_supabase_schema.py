#!/usr/bin/env python3
"""
Dump the live Supabase Postgres schema (public schema) to a re-runnable DDL
file: db/schema_snapshot.sql, plus db/schema_manifest.json with row counts.

This is the offline disaster-recovery copy. If the production DB is ever
dropped again (see incidents 2026-06-01 / 2026-06-11), a fresh Supabase
project can be rebuilt with:

    1. Paste db/schema_snapshot.sql into the Supabase SQL editor (runs as
       `postgres`, so default grants for anon/authenticated/service_role
       apply automatically).
    2. Load data:  python scripts/restore_db_from_snapshot.py --data
       (reads the JSON archive written by export_db_to_offline_archive.py)

Read-only: this script only SELECTs from catalogs.

Usage:
    python -X utf8 scripts/dump_supabase_schema.py
    python -X utf8 scripts/dump_supabase_schema.py --output db/schema_snapshot.sql
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env.local")

SCHEMA = "public"


sys.path.append(str(Path(__file__).resolve().parent))
from lib.db_connect import connect_db


def connect():
    return connect_db(readonly=True)


def fetch_all(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchall()


def dump_extensions(cur):
    # Guarded so the snapshot also applies on non-Supabase Postgres where
    # Supabase-only extensions (supabase_vault, vector, ...) are unavailable.
    rows = fetch_all(cur, """
        SELECT extname FROM pg_extension
        WHERE extname NOT IN ('plpgsql')
        ORDER BY extname
    """)
    return [
        (
            "DO $$ BEGIN\n"
            f'  CREATE EXTENSION IF NOT EXISTS "{name}";\n'
            "EXCEPTION WHEN OTHERS THEN\n"
            f"  RAISE NOTICE 'extension {name} unavailable on this server — skipped';\n"
            "END $$;"
        )
        for (name,) in rows
    ]


def dump_functions(cur):
    rows = fetch_all(cur, """
        SELECT p.oid, p.proname
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = %s
          AND NOT EXISTS (SELECT 1 FROM pg_depend d
                          WHERE d.objid = p.oid AND d.deptype = 'e')
        ORDER BY p.proname
    """, (SCHEMA,))
    out = []
    for oid, name in rows:
        (definition,) = fetch_all(cur, "SELECT pg_get_functiondef(%s)", (oid,))[0]
        out.append(f"-- function: {name}\n{definition};")
    return out


def list_tables(cur):
    return [r[0] for r in fetch_all(cur, """
        SELECT c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s AND c.relkind = 'r'
        ORDER BY c.relname
    """, (SCHEMA,))]


def dump_table(cur, table):
    cols = fetch_all(cur, """
        SELECT a.attname,
               format_type(a.atttypid, a.atttypmod),
               a.attnotnull,
               pg_get_expr(d.adbin, d.adrelid)
        FROM pg_attribute a
        LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
        WHERE a.attrelid = format('%%I.%%I', %s, %s)::regclass
          AND a.attnum > 0 AND NOT a.attisdropped
        ORDER BY a.attnum
    """, (SCHEMA, table))

    lines = []
    for name, coltype, notnull, default in cols:
        parts = [f'  "{name}" {coltype}']
        if default:
            parts.append(f"DEFAULT {default}")
        if notnull:
            parts.append("NOT NULL")
        lines.append(" ".join(parts))

    # Non-FK constraints inline (PK, UNIQUE, CHECK); FKs are emitted later so
    # table creation order never matters.
    constraints = fetch_all(cur, """
        SELECT conname, pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conrelid = format('%%I.%%I', %s, %s)::regclass
          AND contype IN ('p', 'u', 'c')
        ORDER BY contype, conname
    """, (SCHEMA, table))
    for conname, condef in constraints:
        lines.append(f'  CONSTRAINT "{conname}" {condef}')

    body = ",\n".join(lines)
    return f'CREATE TABLE IF NOT EXISTS "{table}" (\n{body}\n);'


def dump_foreign_keys(cur, table):
    rows = fetch_all(cur, """
        SELECT conname, pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conrelid = format('%%I.%%I', %s, %s)::regclass
          AND contype = 'f'
        ORDER BY conname
    """, (SCHEMA, table))
    return [
        f'ALTER TABLE "{table}" ADD CONSTRAINT "{conname}" {condef};'
        for conname, condef in rows
    ]


def dump_indexes(cur, table):
    # Skip indexes that back constraints — those are recreated by the
    # constraint definitions above.
    rows = fetch_all(cur, """
        SELECT indexdef
        FROM pg_indexes
        WHERE schemaname = %s AND tablename = %s
          AND indexname NOT IN (
            SELECT conname FROM pg_constraint
            WHERE conrelid = format('%%I.%%I', %s, %s)::regclass
          )
        ORDER BY indexname
    """, (SCHEMA, table, SCHEMA, table))
    return [f"{indexdef};" for (indexdef,) in rows]


def dump_rls(cur, table):
    out = []
    (enabled,) = fetch_all(cur, """
        SELECT relrowsecurity FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s AND c.relname = %s
    """, (SCHEMA, table))[0]
    if enabled:
        out.append(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;')

    policies = fetch_all(cur, """
        SELECT policyname, permissive, roles, cmd, qual, with_check
        FROM pg_policies
        WHERE schemaname = %s AND tablename = %s
        ORDER BY policyname
    """, (SCHEMA, table))
    for name, permissive, roles, cmd, qual, with_check in policies:
        stmt = f'CREATE POLICY "{name}" ON "{table}"'
        if permissive == "RESTRICTIVE":
            stmt += " AS RESTRICTIVE"
        if cmd and cmd != "ALL":
            stmt += f" FOR {cmd}"
        if isinstance(roles, str):
            roles = [r.strip('"') for r in roles.strip("{}").split(",") if r]
        if roles and list(roles) != ["public"]:
            stmt += f" TO {', '.join(roles)}"
        if qual:
            stmt += f" USING ({qual})"
        if with_check:
            stmt += f" WITH CHECK ({with_check})"
        out.append(stmt + ";")
    return out


def dump_triggers(cur, table):
    rows = fetch_all(cur, """
        SELECT pg_get_triggerdef(t.oid)
        FROM pg_trigger t
        WHERE t.tgrelid = format('%%I.%%I', %s, %s)::regclass
          AND NOT t.tgisinternal
        ORDER BY t.tgname
    """, (SCHEMA, table))
    return [f"{trigdef};" for (trigdef,) in rows]


def dump_comments(cur, table):
    out = []
    rows = fetch_all(cur, """
        SELECT a.attname, col_description(a.attrelid, a.attnum)
        FROM pg_attribute a
        WHERE a.attrelid = format('%%I.%%I', %s, %s)::regclass
          AND a.attnum > 0 AND NOT a.attisdropped
          AND col_description(a.attrelid, a.attnum) IS NOT NULL
    """, (SCHEMA, table))
    for col, comment in rows:
        escaped = comment.replace("'", "''")
        out.append(f"COMMENT ON COLUMN \"{table}\".\"{col}\" IS '{escaped}';")
    (table_comment,) = fetch_all(cur, """
        SELECT obj_description(format('%%I.%%I', %s, %s)::regclass, 'pg_class')
    """, (SCHEMA, table))[0]
    if table_comment:
        escaped = table_comment.replace("'", "''")
        out.insert(0, f"COMMENT ON TABLE \"{table}\" IS '{escaped}';")
    return out


def row_counts(cur, tables):
    counts = {}
    for table in tables:
        try:
            (count,) = fetch_all(cur, f'SELECT COUNT(*) FROM "{table}"')[0]
            counts[table] = count
        except psycopg2.Error:
            counts[table] = None
    return counts


def main():
    parser = argparse.ArgumentParser(description="Dump live Supabase schema to DDL")
    parser.add_argument("--output", default=str(REPO_ROOT / "db" / "schema_snapshot.sql"))
    args = parser.parse_args()

    conn = connect()
    cur = conn.cursor()

    tables = list_tables(cur)
    print(f"Found {len(tables)} tables in schema '{SCHEMA}': {', '.join(tables)}")

    generated_at = datetime.now(timezone.utc).isoformat()
    sections = [
        "-- ============================================================================",
        "-- GradeMax — production Supabase schema snapshot (public schema)",
        f"-- Generated: {generated_at} by scripts/dump_supabase_schema.py",
        "--",
        "-- Recreates every table, constraint, index, RLS policy, trigger and",
        "-- function. Apply on a FRESH Supabase project via the SQL editor.",
        "-- Default Supabase grants apply because the editor runs as `postgres`.",
        "-- Data restore: scripts/restore_db_from_snapshot.py --data",
        "-- ============================================================================",
        "",
        "-- ─── Extensions ─────────────────────────────────────────────────────────────",
        *dump_extensions(cur),
        "",
        "-- ─── Functions ──────────────────────────────────────────────────────────────",
        *dump_functions(cur),
        "",
        "-- ─── Tables ─────────────────────────────────────────────────────────────────",
    ]
    for table in tables:
        sections.append(f"-- table: {table}")
        sections.append(dump_table(cur, table))
        sections.append("")

    sections.append("-- ─── Foreign keys ───────────────────────────────────────────────────────────")
    for table in tables:
        sections.extend(dump_foreign_keys(cur, table))

    sections.append("")
    sections.append("-- ─── Indexes ────────────────────────────────────────────────────────────────")
    for table in tables:
        sections.extend(dump_indexes(cur, table))

    sections.append("")
    sections.append("-- ─── Row level security ─────────────────────────────────────────────────────")
    for table in tables:
        sections.extend(dump_rls(cur, table))

    sections.append("")
    sections.append("-- ─── Triggers ───────────────────────────────────────────────────────────────")
    for table in tables:
        sections.extend(dump_triggers(cur, table))

    sections.append("")
    sections.append("-- ─── Comments ───────────────────────────────────────────────────────────────")
    for table in tables:
        sections.extend(dump_comments(cur, table))
    sections.append("")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(sections), encoding="utf-8")
    print(f"Schema DDL written to {output_path}")

    counts = row_counts(cur, tables)
    manifest = {
        "generated_at": generated_at,
        "schema": SCHEMA,
        "tables": len(tables),
        "row_counts": counts,
    }
    manifest_path = output_path.parent / "schema_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Row-count manifest written to {manifest_path}")
    for table, count in sorted(counts.items()):
        print(f"  {table:24s} {count}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
