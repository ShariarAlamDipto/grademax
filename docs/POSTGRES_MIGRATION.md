# Supabase to PostgreSQL Migration

## Current Coupling

The project can move to plain PostgreSQL, but Supabase is currently used for three different things:

1. Database access through `@supabase/supabase-js` in server pages, API routes, React context, and ingestion scripts.
2. Authentication through Supabase Auth cookies, bearer tokens, Google OAuth, email/password signup, password updates, and admin user listing.
3. Storage through Supabase Storage for `question-pdfs`, `lectures`, and older ingestion scripts. Newer paper admin upload paths already use Cloudflare R2.

The migration should not try to fake Supabase with a drop-in wrapper. The existing query chains are convenient, but they encode RLS, auth, and storage assumptions. A proper migration should introduce explicit app services and then move each route onto those services.

## Recommended Target

- PostgreSQL 16 as the application database.
- Server-side database access through a typed SQL layer, preferably Drizzle or Kysely.
- Auth.js/NextAuth or a small first-party auth module backed by PostgreSQL.
- Cloudflare R2 for object storage, including lectures and worksheet/question PDFs.
- Application-level authorization checks instead of Supabase RLS.

## Tables Seen In App Code

Core content:

- `subjects`
- `topics`
- `papers`
- `pages`
- `questions`
- `question_tags`
- `question_topics`
- `worksheets`
- `worksheet_items`
- `tests`
- `test_items`

User/admin:

- `profiles`
- `lectures`
- `usage_events`
- `admin_audit_log`
- `scraper_runs`
- `user_subjects`

Supabase-specific references that must be rewritten:

- `auth.users` foreign keys in old migrations.
- RLS policies and `auth.uid()` checks.
- Supabase Auth admin calls such as `admin.auth.admin.listUsers`.
- Supabase Storage calls such as `storage.from(...).upload/download/remove/list`.

## Migration Phases

### Phase 1: Local PostgreSQL Foundation

Docker Compose includes an internal PostgreSQL service at `postgres:5432` and persists data in `../postgres_data`. It is not exposed on a host port.

The app still runs on the current Supabase code until the data layer is migrated.

### Phase 2: Normalize Schema

Create a clean PostgreSQL schema that removes Supabase-only constructs:

- Replace `auth.users(id)` references with `users(id)`.
- Keep `profiles` only if it remains separate from `users`; otherwise merge role/name/avatar fields into `users`.
- Remove RLS policies from app migrations.
- Keep PostgreSQL-native features used by the project: UUIDs, JSONB, arrays, GIN indexes, and full-text indexes.
- Decide whether `vector` is required in production; if yes, use a PostgreSQL image/package with `pgvector`.

### Phase 3: Replace Server Database Access

Start with read-only public routes because they are easiest to verify:

- `/api/subjects`
- `/api/topics`
- `/past-papers/*`
- `/qp/*`
- sitemap generation

Then migrate authenticated routes:

- worksheet generation/download
- test builder
- dashboard/profile
- admin content management
- analytics/audit routes

### Phase 4: Replace Auth

Current Supabase Auth features in use:

- Google OAuth
- email/password signup and signin
- session cookies in middleware/proxy
- bearer token auth for mobile/API
- password update
- admin user listing and role promotion

Recommended replacement:

- Auth.js with PostgreSQL adapter if third-party OAuth is still needed.
- Credentials/password auth with bcrypt/argon2 if email/password must remain first-party.
- Store role, name, avatar, and email in `users` or `profiles`.
- Replace `requireAuth`, `requireTeacher`, and `requireAdmin` with local session checks.

### Phase 5: Replace Storage

Current Supabase Storage usage:

- `question-pdfs` for worksheet PDF generation and old processing scripts.
- `lectures` for lecture uploads/deletes.
- Several older ingestion scripts list or upload Supabase buckets.

Recommended replacement:

- Move all bucket behavior to R2.
- Store object keys in PostgreSQL, not Supabase paths.
- Update scripts to use `src/lib/r2Client.ts` or a shared Python-compatible S3 config.

## Practical Order Of Work

1. Add PostgreSQL schema and migration runner.
2. Add typed database client.
3. Convert public read routes.
4. Convert admin paper routes that already use R2 for storage.
5. Convert auth and protected user routes.
6. Convert lecture and worksheet storage.
7. Remove Supabase dependencies and environment variables.

Stopping after only the database client swap would leave auth and storage broken, so the migration should be treated as a staged rewrite.
