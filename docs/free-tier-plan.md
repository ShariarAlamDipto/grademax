# Running GradeMax on free tiers (Vercel Hobby + Supabase Free)

Assessment date: 2026-06-11; re-verified live 2026-06-12 immediately before
the Pro → Free downgrade. Verdict up front: **both services fit comfortably
in their free tiers today.**

## Pre-downgrade verification (2026-06-12, all live-checked)

| Check | Result |
|---|---|
| Database size | **45 MB** of 500 MB limit (9%) |
| Supabase Storage | 2 buckets, **0 objects, 0 bytes** |
| URL-leak guard (`check_no_supabase_urls.py`) | **PASS** — every PDF URL on R2 |
| Auth users | 264 (limit 50 000 MAU) |
| Realtime usage | none in codebase |
| Keep-alive | 2 daily GitHub Action crons query the DB (04:00 + 06:00 UTC) |
| Live site | `grademax.me/api/subjects` returns 50 subjects ✓ |
| Offline schema snapshot | `db/schema_snapshot.sql` regenerated same day |
| Offline data archive | 34 494 rows / 29 tables / 17.6 MB incl. `auth.users` + identities |
| Restore drill | Schema + data restored into scratch Postgres: **0 skips**, counts match prod |

**What you LOSE on Free: daily backups.** There is no dashboard restore any
more — the offline snapshot + archive (`db/README.md` playbook) are the only
recovery path. Re-run both dump scripts after every schema change or ingest.

**Action required around the downgrade — custom SMTP.** The login page uses
email/password `signUp`, whose confirmation emails go through Supabase's
built-in sender — on Free that's ~2 emails/hour, so signups will silently
break under any real traffic. Configure custom SMTP (Resend key already in
`.env.local`) under Dashboard → Auth → SMTP. Available on Free. The architecture already does the two things that matter —
PDF bytes live on Cloudflare R2 (free egress), and past-paper pages are
fully static (`dynamicParams = false`, no ISR writes). The items below are
the remaining checks and the few habits that keep it that way.

---

## Supabase Free tier

| Limit (Free) | GradeMax usage today | Headroom |
|---|---|---|
| 500 MB database | ~6.5k `pages`, 2.5k `papers`, 11k `worksheet_items`, 264 `profiles` — low tens of MB incl. indexes | Huge |
| 1 GB file storage | 0 MB (Phase D emptied all buckets; everything is on R2) | Full |
| 5 GB egress / month | Metadata JSON only — the heavy bytes (PDFs) never touch Supabase | Huge |
| 50k monthly active users | 264 registered profiles | Huge |
| 2 projects | 1 | OK |

Row counts (2026-06-11): papers 2 530 · pages 6 477 · questions 4 932 ·
question_tags 4 919 · subjects 50 · topics 106 · worksheets 1 017 ·
worksheet_items 11 181 · tests 46 · usage_events 1 492 · profiles 264.

### Required actions

1. **Auth email rate limit.** Free tier's built-in SMTP sends only ~2
   emails/hour — fine for trickle signups, fatal for bulk sends. The
   announcement script (`scripts/send_announcement_email*`) must use an
   external SMTP provider (e.g. Resend free tier, 100/day) configured under
   Auth → SMTP settings, never Supabase's built-in sender.
2. **Free projects pause after ~7 days of inactivity.** The daily
   `storage-leak-check.yml` GitHub Action queries the DB and keeps the
   project warm — but GitHub disables cron workflows after 60 days without
   repo activity. Keep committing, or re-enable the workflow if a pause
   email arrives.
3. **Apply migration 11** (drops `questions` + `question_tags`, ~10k rows)
   — not needed for quota, but shrinks the DB and removes a stale write
   target.

### Growth watch-items (none urgent)

- `usage_events` is the only unbounded table. At the current rate (~1.5k
  rows total) it's irrelevant; if tracking volume grows 100×, add a monthly
  cron that deletes rows older than 12 months.
- `worksheet_items` grows ~10 rows per generated worksheet. 500 MB ≈ tens of
  millions of rows — not a realistic concern.

## Vercel Hobby tier

| Limit (Hobby) | GradeMax behaviour | Risk |
|---|---|---|
| 100 GB bandwidth / month | HTML/JS only; every PDF is served by R2 | Low |
| ISR reads/writes | Past-paper routes are fully static (`revalidate = false`, `dynamicParams = false`, build-time `papersIndex`) — the ISR bleed was fixed in commit `fdc7a5ef` | Low |
| Image optimization (~1k source images) | `next/image` used in exactly one place (profile avatar) | Low |
| Function invocations / GB-hours | Thin Supabase-proxy API routes; worksheet PDFs are assembled **in the browser** via pdf-lib, costing Vercel nothing | Low |
| Cron jobs (limited on Hobby) | All crons already run in GitHub Actions, not Vercel | None |
| Middleware | None exists | None |

### Required actions

1. **Commercial-use clause.** Vercel Hobby is licensed for personal,
   non-commercial projects. GradeMax is free today, so this is fine — but
   any monetisation (ads, paid tiers) breaks the Hobby ToS. The escape
   hatch is the self-hosted Docker VM that `.github/workflows/deploy.yml`
   already targets (push to `imrul-deploy` → SSH → `docker compose up`):
   it can take over production traffic with a DNS change, at which point
   Vercel can be deleted entirely rather than downgraded.
2. **Keep new dynamic routes off the hot path.** The free-tier fit depends
   on the static-paper-pages design. Any new high-traffic route should
   follow the same pattern: `generateStaticParams` from `papersIndex`, not
   per-request Supabase queries.
3. **Don't add Vercel crons or middleware** — both are metered/limited on
   Hobby and GitHub Actions covers the need for free.

### Sitemap note

`src/app/sitemap.ts` queries Supabase but runs at **build time** (it uses no
dynamic APIs), so it costs zero function invocations at serve time. Keep it
that way — don't add `force-dynamic` to it.

## Cost-relevant invariants (the checklist)

- [ ] All PDFs served from R2, never proxied through Vercel or Supabase.
- [ ] Past-paper routes static; new content appears via redeploy (build
      hook), not ISR.
- [ ] Bulk email goes through external SMTP, not Supabase auth sender.
- [ ] Crons live in GitHub Actions.
- [ ] Migration 11 applied (questions/question_tags dropped).
- [ ] R2 stays on its own (Cloudflare) free tier: 10 GB storage / free
      egress — current corpus ~3 GB, monitor at 8 GB.
