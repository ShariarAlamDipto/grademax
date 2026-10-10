#!/usr/bin/env python3
"""
Apply one SQL migration file to the production database (DATABASE_URL in
.env.local) in a single transaction, then print a check for migration 35.

    python scripts/apply_sql_migration.py supabase/migrations/35_questions_mirror_of_pages.sql
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    sql_file = Path(sys.argv[1])
    load_dotenv(ROOT / ".env.local")
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
        cur.execute(sql_file.read_text(encoding="utf-8"))
        conn.commit()
        print(f"applied {sql_file.name}")
        if sql_file.name.startswith("35_"):
            cur.execute("""select count(*) filter (where q.id is null),
                                  count(*) filter (where q.id is not null and
                                    (q.page_pdf_url is distinct from p.qp_page_url
                                     or q.ms_pdf_url is distinct from p.ms_page_url)),
                                  count(*)
                           from pages p left join questions q on q.id = p.id""")
            missing, differ, total = cur.fetchone()
            print(f"pages rows: {total}; without mirror: {missing}; mirror differs: {differ}  (both should be 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
