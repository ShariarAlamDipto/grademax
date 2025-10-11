# GradeMax Setup Guide

## Prerequisites
- Node.js 18+ installed
- Supabase account created
- Google Cloud Console project (for OAuth)

## Step 1: Clone and Install

```bash
git clone <repository-url>
cd grademax
npm install
```

## Step 2: Supabase Setup

### 2.1 Create Supabase Project
1. Go to https://supabase.com
2. Create a new project
3. Note your project URL and anon key

### 2.2 Run Database Migrations

Go to your Supabase dashboard → SQL Editor, and run these migrations in order:

**Migration 001: Initial Schema**
```bash
supabase/migrations/001_initial_schema.sql
```

**Migration 002: Profiles Table**
```bash
supabase/migrations/002_profiles.sql
```

**Migration 003: Papers and Sessions**
```bash
supabase/migrations/003_papers_sessions.sql
```

**Migration 004: Ingestion Schema** (REQUIRED for ingestion pipeline)
```bash
supabase/migrations/004_ingestion_schema.sql
```

Or run via Supabase CLI:
```bash
supabase db push
```

### 2.3 Configure Google OAuth

1. Go to Supabase Dashboard → Authentication → Providers
2. Enable Google provider
3. Add your Google OAuth credentials:
   - Client ID from Google Cloud Console
   - Client Secret from Google Cloud Console
4. Add authorized redirect URIs:
   - `https://<your-project-id>.supabase.co/auth/v1/callback`
   - `http://localhost:3000/auth/callback` (for local dev)

## Step 3: Environment Variables

Create `.env.local` in the project root:

```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

**Where to find these values:**
- Go to Supabase Dashboard → Settings → API
- Copy "Project URL" → `NEXT_PUBLIC_SUPABASE_URL`
- Copy "anon public" key → `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## Step 4: Google Cloud Console Setup

### 4.1 Create OAuth Credentials
1. Go to https://console.cloud.google.com
2. Create a new project or select existing
3. Enable Google+ API
4. Go to Credentials → Create Credentials → OAuth 2.0 Client ID
5. Application type: Web application
6. Add authorized redirect URIs:
   - `https://<your-project-id>.supabase.co/auth/v1/callback`
   - `http://localhost:3000/auth/callback`
7. Copy Client ID and Client Secret

### 4.2 Add Credentials to Supabase
1. Go to Supabase Dashboard → Authentication → Providers → Google
2. Enable Google
3. Paste Client ID and Client Secret
4. Save

## Step 5: Run Development Server

```bash
npm run dev
```

Visit http://localhost:3000

## Step 6: Test Login

1. Go to http://localhost:3000/login
2. Click "Continue with Google"
3. Authorize the app
4. You should be redirected to /dashboard

## Step 7: Verify Database

Check that the profile was created:
```sql
SELECT * FROM profiles;
```

## Troubleshooting

### Login redirects to /login with error
- Check Google OAuth credentials are correct
- Verify redirect URIs match exactly (no trailing slashes)
- Check Supabase Auth settings allow Google provider

### "Missing Supabase environment variables"
- Verify `.env.local` exists in project root
- Restart dev server after adding env variables
- Check spelling of environment variable names

### Database errors
- Verify all migrations have been run
- Check RLS policies are enabled
- Ensure user has proper permissions

### Dashboard shows empty state
- Check if profile was created (look in Supabase table editor)
- Verify RLS policies allow authenticated users to read their own data

## Current Status

✅ Environment variables configured (`.env.local` exists)
✅ Supabase URL: `https://tybaetnvnfgniotdfxze.supabase.co`
✅ Login page: `/login` (Google OAuth)
✅ Auth callback: `/auth/callback`
✅ Dashboard: `/dashboard` (protected route)

⚠️ **ACTION REQUIRED**: Run migration 004 for ingestion pipeline
⚠️ **ACTION REQUIRED**: Configure Google OAuth in Supabase dashboard

## Testing Ingestion Pipeline

After running migration 004, test with:

```bash
# Test metadata detection
npx tsx ingest/test_metadata.ts

# Test persistence (requires migration 004)
npx tsx ingest/test_persist.ts

# Full pipeline test
npx tsx ingest/test_features.ts
```

## File Structure

```
grademax/
├── .env.local                 # Environment variables
├── supabase/
│   └── migrations/            # Database migrations
│       ├── 001_initial_schema.sql
│       ├── 002_profiles.sql
│       ├── 003_papers_sessions.sql
│       └── 004_ingestion_schema.sql
├── src/
│   ├── app/
│   │   ├── login/page.tsx     # Login page
│   │   ├── dashboard/page.tsx # Main dashboard
│   │   └── auth/callback/     # OAuth callback
│   ├── lib/
│   │   ├── supabaseClient.ts  # Client-side Supabase
│   │   └── supabaseServer.ts  # Server-side Supabase
│   └── components/            # React components
├── ingest/                    # Ingestion pipeline
│   ├── parse_pdf_v2.ts
│   ├── segment.ts
│   ├── ms_parse_link.ts
│   ├── tagging.ts
│   ├── features.ts
│   ├── metadata.ts
│   └── persist.ts
└── types/
    └── ingestion.ts           # TypeScript types
```

## Next Steps

1. ✅ Configure Google OAuth
2. ✅ Run migration 004
3. ✅ Test login flow
4. ⏳ Build API routes for ingestion
5. ⏳ Build QA dashboard for ingestion validation
6. ⏳ Create admin interface for paper management
