# PostgreSQL Database

## ⚠️ Two databases — never mix them

| | Production (Supabase) | Self-hosted (Docker) |
|---|---|---|
| Schema source | `supabase/migrations/` + `db/schema_snapshot.sql` | `db/migrations/` |
| Used by | grademax.me (Vercel, `main` branch) | `imrul-deploy` Docker stack |
| Has | `subjects`, `papers`, `pages`, RLS, `auth.users` FKs | new redesign tables, no RLS |

**`db/migrations/` must NEVER run against production Supabase.** Doing so
dropped the live tables on 2026-06-01 and again on 2026-06-11 (a
`DATABASE_URL` in `docker.env`/`.env.local` pointed at Supabase). Both
`postgres:migrate` and `postgres:seed` now **refuse Supabase hosts** unless
`ALLOW_SUPABASE_MIGRATIONS=I_UNDERSTAND_THIS_CAN_DESTROY_PRODUCTION` is set.

## Self-hosted target (Docker)

```bash
npm run postgres:migrate   # applies db/migrations/ to DATABASE_URL (Supabase hosts refused)
npm run postgres:seed
```

In Docker:

```bash
docker compose --env-file docker.env up -d postgres
docker compose --env-file docker.env run --rm grademax npm run postgres:migrate
docker compose --env-file docker.env run --rm grademax npm run postgres:seed
```

In `docker.env`, `DATABASE_URL` must point at the compose-internal Postgres
(`postgresql://grademax:...@postgres:5432/grademax`), never at Supabase.

The self-hosted schema intentionally removes Supabase-only constructs:

- no `auth.users` foreign keys
- no RLS policies
- no `storage.objects` or `storage.buckets`

## Production backup & disaster recovery

Offline copies (regenerate after any schema change or big ingest):

```bash
# 1. Schema DDL → db/schema_snapshot.sql + db/schema_manifest.json (committed)
python -X utf8 scripts/dump_supabase_schema.py

# 2. Full data → ~/grademax_offline_archive/ (LOCAL ONLY — contains user PII)
python -X utf8 scripts/export_db_to_offline_archive.py
```

`db/schema_snapshot.sql` recreates all tables, constraints, indexes, RLS
policies, triggers and functions of the live `public` schema. The data
archive is JSON per table (~17 MB, 34k rows) plus the classification YAMLs.

### If production is lost again

1. **Check Supabase Dashboard → Database → Backups first.** NOTE: daily
   backups are a **Pro-plan feature** — after the 2026-06 downgrade to Free
   there are NO dashboard backups, and the offline copies below are the ONLY
   recovery path. Re-run both dump scripts after every schema change/ingest.
2. **From the offline copies (works on a brand-new project):**
   - Create the Supabase project, paste `db/schema_snapshot.sql` into the
     SQL editor.
   - `python scripts/restore_db_from_snapshot.py --target env --data --yes`
     (reads `~/grademax_offline_archive/db_export/`; rows pointing at auth
     users that don't exist yet are skipped and counted, not fatal).
3. **After ANY restore:** redeploy the site **without build cache**
   (papersIndex is baked at build time), then verify with
   `python scripts/check_no_supabase_urls.py` and
   `curl https://grademax.me/api/subjects` (expect 50 subjects).

Note: direct `db.<ref>.supabase.co` hosts are IPv6-only. All backup/restore
scripts automatically fall back to the IPv4 session pooler
(`aws-1-ap-southeast-1.pooler.supabase.com`) via `scripts/lib/db_connect.py`.

### Drill-tested (2026-06-12)

The full path was rehearsed against a scratch Postgres 16 container:
schema snapshot applied cleanly under `ON_ERROR_STOP` (27 tables, 63 RLS
policies, all FKs/indexes/triggers), then the data archive loaded
**34,226 rows with 0 skips** — including `auth.users` (265 accounts with
bcrypt password hashes + Google OAuth identities), so user logins survive a
from-scratch rebuild. Counts verified equal to production for every content
and user table.

Application code still needs to be migrated route-by-route from Supabase
clients to a PostgreSQL data layer before the Docker target can serve
production.
