#!/usr/bin/env python3
"""
Rebuild a (fresh) Supabase/Postgres database from the offline backups:

  schema:  db/schema_snapshot.sql                (made by dump_supabase_schema.py)
  data:    ~/grademax_offline_archive/db_export/ (made by export_db_to_offline_archive.py)

Safety rails — this script is deliberately hard to fire by accident:
  * The target must be passed explicitly with --target (use "--target env" to
    take DATABASE_URL from .env.local; the resolved host is always printed).
  * --yes is required before anything is written.
  * Data loading refuses non-empty target tables unless --allow-non-empty
    (which switches to per-row inserts that skip conflicts).
  * Rows that violate FKs (e.g. profiles for auth users that don't exist on a
    fresh project) are skipped and counted, never fatal.

Typical disaster recovery on a brand-new Supabase project:
    1. Paste db/schema_snapshot.sql into the SQL editor   (or: --schema)
    2. python scripts/restore_db_from_snapshot.py --target env --data --yes

Usage:
    python -X utf8 scripts/restore_db_from_snapshot.py --target env --schema --yes
    python -X utf8 scripts/restore_db_from_snapshot.py --target env --data --yes
    python -X utf8 scripts/restore_db_from_snapshot.py --target env --data --tables subjects,topics --yes
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras

sys.path.append(str(Path(__file__).resolve().parent))
from lib.db_connect import connect_db

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA_FILE = REPO_ROOT / "db" / "schema_snapshot.sql"
DEFAULT_ARCHIVE = Path.home() / "grademax_offline_archive" / "db_export"

# FK-respecting load order; tables not listed load afterwards (alphabetical).
# auth.users must come first — profiles/worksheets/lectures all FK it.
RESTORE_ORDER = [
    "auth_users", "auth_identities",
    "subjects", "topics", "papers", "pages", "questions", "question_tags",
    "user_profiles", "profiles", "user_permissions",
    "lectures", "worksheets", "worksheet_items", "tests", "test_items",
    "usage_events", "suggestions", "audit_log",
]

# Archive stem → (schema, table). Everything else lives in public.
SCHEMA_QUALIFIED = {
    "auth_users": ("auth", "users"),
    "auth_identities": ("auth", "identities"),
}

# GoTrue cannot scan NULLs in these auth.users token columns — restore them
# as empty strings (matches Supabase's own project-migration guidance).
AUTH_USERS_TEXT_NOT_NULL = {
    "confirmation_token", "recovery_token", "email_change",
    "email_change_token_new", "email_change_token_current",
    "phone_change", "phone_change_token", "reauthentication_token",
}

BATCH_SIZE = 500


def column_types(cur, schema: str, table: str) -> dict:
    cur.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        """,
        (schema, table),
    )
    return dict(cur.fetchall())


def adapt_value(value, data_type: str):
    if value is None:
        return None
    if data_type in ("json", "jsonb"):
        return psycopg2.extras.Json(value)
    if data_type == "ARRAY":
        return value if isinstance(value, list) else [value]
    return value


def load_table(conn, stem: str, rows: list[dict], allow_non_empty: bool) -> tuple[int, int]:
    """Returns (inserted, skipped)."""
    schema, table = SCHEMA_QUALIFIED.get(stem, ("public", stem))
    qualified = f'"{schema}"."{table}"'
    cur = conn.cursor()
    types = column_types(cur, schema, table)
    if not types:
        print("    SKIP — table missing on target")
        return (0, 0)

    cur.execute(f"SELECT COUNT(*) FROM {qualified}")
    (existing_count,) = cur.fetchone()
    if existing_count > 0 and not allow_non_empty:
        print(f"    REFUSED — target already has {existing_count} rows "
              "(re-run with --allow-non-empty to merge with conflict-skip)")
        return (0, 0)

    # Only restore columns that still exist on the target schema.
    columns = [c for c in rows[0].keys() if c in types]
    col_sql = ", ".join(f'"{c}"' for c in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    insert_sql = (
        f"INSERT INTO {qualified} ({col_sql}) VALUES ({placeholders}) "
        "ON CONFLICT DO NOTHING"
    )

    def fixup(column: str, value):
        if stem == "auth_users" and column in AUTH_USERS_TEXT_NOT_NULL and value is None:
            return ""
        return value

    inserted = skipped = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        values = [
            tuple(adapt_value(fixup(c, row.get(c)), types[c]) for c in columns)
            for row in batch
        ]
        try:
            cur.executemany(insert_sql, values)
            conn.commit()
            inserted += len(batch)
        except psycopg2.Error:
            conn.rollback()
            # Batch failed (usually an FK to auth.users) — retry row by row.
            for value_row in values:
                try:
                    cur.execute(insert_sql, value_row)
                    conn.commit()
                    inserted += 1
                except psycopg2.Error:
                    conn.rollback()
                    skipped += 1
    cur.close()
    return (inserted, skipped)


def main():
    parser = argparse.ArgumentParser(description="Restore GradeMax DB from offline snapshot")
    parser.add_argument("--target", required=True,
                        help='Target DATABASE_URL, or "env" to use .env.local')
    parser.add_argument("--schema", action="store_true", help="Apply db/schema_snapshot.sql")
    parser.add_argument("--schema-file", default=str(DEFAULT_SCHEMA_FILE))
    parser.add_argument("--data", action="store_true", help="Load JSON archive data")
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE))
    parser.add_argument("--tables", help="Comma-separated subset of tables to load")
    parser.add_argument("--allow-non-empty", action="store_true",
                        help="Merge into non-empty tables (ON CONFLICT DO NOTHING)")
    parser.add_argument("--yes", action="store_true", help="Required: confirm writes")
    args = parser.parse_args()

    if not args.schema and not args.data:
        parser.error("nothing to do — pass --schema and/or --data")
    if not args.yes:
        parser.error("refusing to write without --yes")

    url = None if args.target == "env" else args.target
    conn = connect_db(readonly=False, url=url)
    conn.autocommit = False
    host = "(env)" if args.target == "env" else (urlparse(args.target).hostname or "?")
    print(f"TARGET: {host} — writes ENABLED\n")

    if args.schema:
        schema_path = Path(args.schema_file)
        if not schema_path.exists():
            print(f"ERROR: schema file not found: {schema_path}")
            sys.exit(2)
        print(f"Applying schema from {schema_path} ...")
        cur = conn.cursor()
        cur.execute(schema_path.read_text(encoding="utf-8"))
        conn.commit()
        cur.close()
        print("  schema applied.\n")

    if args.data:
        archive = Path(args.archive)
        if not archive.exists():
            print(f"ERROR: archive dir not found: {archive}")
            sys.exit(2)

        available = {p.stem: p for p in archive.glob("*.json")}
        wanted = (
            [t.strip() for t in args.tables.split(",")] if args.tables
            else RESTORE_ORDER + sorted(set(available) - set(RESTORE_ORDER))
        )

        total_inserted = total_skipped = 0
        for table in wanted:
            path = available.get(table)
            if not path:
                continue
            rows = json.loads(path.read_text(encoding="utf-8"))
            if not rows:
                print(f"  {table}: 0 rows in archive — skipped")
                continue
            print(f"  {table}: loading {len(rows):,} rows ...")
            inserted, skipped = load_table(conn, table, rows, args.allow_non_empty)
            total_inserted += inserted
            total_skipped += skipped
            print(f"    inserted {inserted:,}, skipped {skipped:,}")

        print(f"\nDone. Inserted {total_inserted:,} rows, skipped {total_skipped:,}.")
        print("Reminder: after any restore, redeploy the site without build cache")
        print("(papersIndex is baked at build time) and run scripts/check_no_supabase_urls.py.")

    conn.close()


if __name__ == "__main__":
    main()
