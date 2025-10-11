# 🚨 QUICK FIX FOR LOGIN LOOP

## The Problem
**Error**: `column "canonical_key" does not exist`  
**Cause**: The database schema didn't match the SQL script, and the code referenced columns that don't exist

## ✅ The Solution (2 minutes)

### Step 1: Run the Fixed Schema
1. Open **Supabase Dashboard**: https://supabase.com/dashboard
2. Select your project: `tybaetnvnfgniotdfxze`
3. Click **SQL Editor** in left sidebar
4. Click **New Query**
5. Copy **ALL contents** from: `FIXED_DATABASE_SCHEMA.sql`
6. Paste into SQL Editor
7. Click **Run** (or press Ctrl+Enter)

### Step 2: Verify Success
You should see:
```
✅ Fixed database schema applied successfully!

Tables created/updated:
  ✅ profiles (with auto-creation trigger) - FIXES LOGIN LOOP
  ✅ papers (extended with new columns)
  ✅ questions (extended with new columns)
  ✅ question_parts
  ✅ question_tags
  ✅ ingestions
  ✅ worksheets
  ✅ worksheet_items

🔒 All tables have RLS enabled with proper policies
✅ Ready to use!

👉 Next: Test login at http://localhost:3001/login
```

### Step 3: Test Login
1. Go to: http://localhost:3001/login
2. Click **"Continue with Google"**
3. Authorize the app
4. Should redirect to `/dashboard` ✅ (NOT back to `/login`)

---

## What Changed?

### ❌ Old Files (Had Errors)
- COMPLETE_DATABASE_SCHEMA.sql - Used `canonical_key` column that doesn't exist
- ingest/persist.ts - Referenced `canonical_key` and `part_code`

### ✅ Fixed Files (Now Work)
- **FIXED_DATABASE_SCHEMA.sql** - Extends existing tables safely, no `canonical_key`
- **ingest/persist.ts** - Uses correct column names (`code` instead of `part_code`, composite key instead of `canonical_key`)

---

## What Gets Fixed?

1. ✅ **Login Loop**: profiles table created with auto-creation trigger
2. ✅ **Missing Columns**: papers and questions get all required columns (board, level, difficulty, etc.)
3. ✅ **New Tables**: question_parts, question_tags, ingestions, worksheets created
4. ✅ **RLS Policies**: All tables secured with row-level security
5. ✅ **Indexes**: Performance indexes created
6. ✅ **Code Fixed**: persist.ts now uses correct column names

---

## After Running Schema

### Test the Pipeline
```bash
# Test 1: Metadata detection (no database needed)
npx tsx ingest/test_metadata.ts

# Test 2: Features extraction (no database needed)
npx tsx ingest/test_features.ts

# Test 3: Persistence (requires database)
npx tsx ingest/test_persist.ts

# Test 4: Full integration (requires database + PDFs)
npx tsx ingest/test_full_integration.ts
```

### Check Database Tables
Go to **Supabase → Table Editor** and verify these tables exist:
- ✅ profiles
- ✅ papers (with new columns: board, level, subject_code, etc.)
- ✅ questions (with new columns: difficulty, style, etc.)
- ✅ question_parts
- ✅ question_tags
- ✅ ingestions
- ✅ worksheets
- ✅ worksheet_items

---

## Troubleshooting

### "relation already exists"
**This is OK!** The script uses `IF NOT EXISTS` so it won't break existing tables.

### "column already exists"
**This is OK!** The script uses `ADD COLUMN IF NOT EXISTS` so it's safe.

### Still getting login loop?
1. Check profiles table exists: Supabase → Table Editor → profiles
2. Check trigger exists: Look for `on_auth_user_created` in triggers
3. Test manually:
   ```sql
   SELECT * FROM profiles WHERE id = auth.uid();
   ```
4. If no profile, create manually:
   ```sql
   INSERT INTO profiles (id, email) 
   VALUES (auth.uid(), 'your@email.com');
   ```

### "Missing environment variables" when running tests
**This is expected** with `tsx` command. Environment variables are loaded by Next.js, not `tsx`.

To run tests with env vars:
```bash
# Option 1: Load .env.local manually
npx dotenv -e .env.local tsx ingest/test_persist.ts

# Option 2: Install dotenv-cli first
npm install -g dotenv-cli
dotenv -e .env.local npx tsx ingest/test_persist.ts
```

---

## Next Steps

After the schema is applied:

1. ✅ **Login**: Test at http://localhost:3001/login
2. ✅ **Dashboard**: Should see your profile at /dashboard
3. ✅ **QA Page**: Check ingestions at /qa
4. ✅ **Run Tests**: Follow TESTING_CHECKLIST.md
5. ✅ **Ingest PDFs**: Use POST /api/ingest to process papers

---

## Files to Use

- ✅ **FIXED_DATABASE_SCHEMA.sql** ← Run this one!
- ❌ COMPLETE_DATABASE_SCHEMA.sql ← Don't use (has errors)
- ✅ LOGIN_FIX_INSTRUCTIONS.md ← Detailed instructions
- ✅ TESTING_CHECKLIST.md ← Testing guide

---

**Ready?** Run `FIXED_DATABASE_SCHEMA.sql` in Supabase now! 🚀
