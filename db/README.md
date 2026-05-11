# PostgreSQL Database

`db/migrations` contains plain PostgreSQL migrations for the non-Supabase target.

Run from the project root:

```bash
npm run postgres:migrate
npm run postgres:seed
```

In Docker:

```bash
docker compose --env-file docker.env up -d postgres
docker compose --env-file docker.env run --rm grademax npm run postgres:migrate
docker compose --env-file docker.env run --rm grademax npm run postgres:seed
```

The schema intentionally removes Supabase-only constructs:

- no `auth.users` foreign keys
- no RLS policies
- no `storage.objects` or `storage.buckets`

Application code still needs to be migrated route-by-route from Supabase clients to a PostgreSQL data layer.
