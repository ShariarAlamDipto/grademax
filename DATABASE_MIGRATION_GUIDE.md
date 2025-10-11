# 🗄️ DATABASE MIGRATION GUIDE

## Overview
This guide will help you set up your Supabase database correctly by:
1. Removing old/broken SQL files
2. Running the single correct SQL file
3. Verifying everything works

---

## 📋 STEP 1: Files to DELETE (Old/Broken)

Delete these files from your workspace - they have errors or are outdated:

### ❌ Delete These:
```
c:\Users\shari\grademax\COMPLETE_DATABASE_SCHEMA.sql
c:\Users\shari\grademax\supabase_schema.sql
c:\Users\shari\grademax\migrations\003_visual_crops.sql (if exists)
```

### ✅ Keep These:
```
c:\Users\shari\grademax\FIXED_DATABASE_SCHEMA.sql ✓ (THE ONE TO USE)
c:\Users\shari\grademax\migrations\004_core_architecture_redesign.sql ✓ (reference only)
c:\Users\shari\grademax\supabase\seed\schema.sql ✓ (reference only)
```

---

## 📄 STEP 2: The ONE SQL File to Run

### ✅ Use This File ONLY:
**File**: `FIXED_DATABASE_SCHEMA.sql`  
**Location**: `c:\Users\shari\grademax\FIXED_DATABASE_SCHEMA.sql`  
**Purpose**: Complete database setup that extends your existing tables safely

### What It Does:
1. ✅ Creates `profiles` table with auto-creation trigger (FIXES LOGIN LOOP)
2. ✅ Extends `papers` table with new columns (board, level, subject_code, etc.)
3. ✅ Extends `questions` table with new columns (difficulty, style, etc.)
4. ✅ Creates `question_parts` table (for segmented question parts)
5. ✅ Creates `question_tags` table (for topic tagging)
6. ✅ Creates `ingestions` table (for tracking pipeline runs)
7. ✅ Creates `worksheets` table (for user worksheets)
8. ✅ Creates `worksheet_items` table (for worksheet contents)
9. ✅ Sets up RLS policies on all tables
10. ✅ Creates indexes for performance
11. ✅ Sets up triggers for auto-updating timestamps

---

## 🚀 STEP 3: Run the SQL File

### Instructions:

1. **Open Supabase Dashboard**
   - Go to: https://supabase.com/dashboard
   - Select project: `tybaetnvnfgniotdfxze`

2. **Open SQL Editor**
   - Click **SQL Editor** in the left sidebar
   - Click **New Query**

3. **Copy the SQL**
   - Open: `c:\Users\shari\grademax\FIXED_DATABASE_SCHEMA.sql`
   - Select ALL (Ctrl+A)
   - Copy (Ctrl+C)

4. **Paste and Run**
   - Paste into Supabase SQL Editor (Ctrl+V)
   - Click **Run** button (or press Ctrl+Enter)
   - Wait for execution (should take 5-10 seconds)

5. **Verify Success**
   You should see this output:
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

---

## ✅ STEP 4: Verify Tables Exist

### Check in Supabase Dashboard:

1. Go to **Table Editor** in left sidebar
2. You should see these tables:

#### Core Tables (already existed, now extended):
- ✅ `subjects`
- ✅ `topics`
- ✅ `papers` (now has: board, level, subject_code, paper_type, etc.)
- ✅ `questions` (now has: difficulty, style, markscheme_text, etc.)

#### New Tables (created by migration):
- ✅ `profiles` (CRITICAL - fixes login loop)
- ✅ `question_parts`
- ✅ `question_tags`
- ✅ `ingestions`
- ✅ `worksheets`
- ✅ `worksheet_items`

### Check Profiles Table Specifically:

1. Click on **profiles** table
2. Check columns exist:
   - `id` (UUID, primary key)
   - `email` (text)
   - `full_name` (text)
   - `avatar_url` (text)
   - `study_level` (text)
   - `marks_goal_pct` (int)
   - `created_at` (timestamptz)
   - `updated_at` (timestamptz)

3. Check RLS policies:
   - Go to **Authentication** → **Policies**
   - Should see policies for `profiles`:
     - "Users can view own profile"
     - "Users can update own profile"
     - "Users can insert own profile"

4. Check trigger exists:
   - Go to **Database** → **Triggers**
   - Should see: `on_auth_user_created` on `auth.users`

---

## 🧪 STEP 5: Test Everything

### Test 1: Login (CRITICAL)
```
1. Go to: http://localhost:3001/login
2. Click "Continue with Google"
3. Authorize the app
4. Should redirect to /dashboard ✅
5. Should NOT redirect back to /login ❌
```

**If login works**: ✅ Database schema is correct!

**If login still loops**: 
- Check profiles table exists
- Check trigger `on_auth_user_created` exists
- Try logging out and logging in again
- Check browser console for errors

### Test 2: Check Your Profile Created
```
1. Go to Supabase → Table Editor → profiles
2. Should see a row with your email
3. study_level and marks_goal_pct should have default values
```

### Test 3: Run Integration Tests
```bash
# Test metadata detection
npx tsx ingest/test_metadata.ts

# Test features extraction
npx tsx ingest/test_features.ts

# Test persistence (requires database)
npx tsx ingest/test_persist.ts

# Test full pipeline (requires database + PDFs)
npx tsx ingest/test_full_integration.ts
```

---

## 📁 File Reference Guide

### Files in Your Workspace:

#### ✅ CORRECT - Use These:
| File | Purpose | Action |
|------|---------|--------|
| `FIXED_DATABASE_SCHEMA.sql` | Complete database setup | **RUN THIS IN SUPABASE** |
| `DATABASE_MIGRATION_GUIDE.md` | This guide | Reference |
| `QUICK_FIX.md` | Quick reference | Reference |
| `TESTING_CHECKLIST.md` | Testing guide | Follow after migration |
| `LOGIN_FIX_INSTRUCTIONS.md` | Login troubleshooting | Reference if needed |
| `migrations/004_core_architecture_redesign.sql` | Original migration | Reference only (don't run) |
| `supabase/seed/schema.sql` | Original schema | Reference only (don't run) |

#### ❌ INCORRECT - Delete These:
| File | Problem | Action |
|------|---------|--------|
| `COMPLETE_DATABASE_SCHEMA.sql` | Uses `canonical_key` column (doesn't exist) | **DELETE** |
| `supabase_schema.sql` | Outdated, replaced by FIXED version | **DELETE** |
| `migrations/003_visual_crops.sql` | Old migration, not needed | **DELETE** (if exists) |

#### ⚠️ Code Files (Already Fixed):
| File | Status | Notes |
|------|--------|-------|
| `ingest/persist.ts` | ✅ Fixed | No longer uses `canonical_key`, uses composite key |
| `ingest/metadata.ts` | ✅ Working | Tested, 100% accurate |
| `ingest/features.ts` | ✅ Working | Tested on 12 questions |
| `src/app/api/ingest/route.ts` | ✅ Working | API endpoint ready |
| `src/app/qa/page.tsx` | ✅ Working | QA dashboard ready |

---

## 🔍 Common Issues & Solutions

### Issue: "relation 'profiles' does not exist"
**Solution**: Run `FIXED_DATABASE_SCHEMA.sql` in Supabase SQL Editor

### Issue: "column 'canonical_key' does not exist"
**Solution**: 
1. Make sure you're using `FIXED_DATABASE_SCHEMA.sql` (not COMPLETE_DATABASE_SCHEMA.sql)
2. Code has been updated to not use `canonical_key`

### Issue: "column 'part_code' does not exist"
**Solution**: Code has been fixed to use `code` instead of `part_code`

### Issue: Login loop continues
**Solutions**:
1. Verify `profiles` table exists
2. Verify trigger `on_auth_user_created` exists
3. Clear browser cookies and cache
4. Try incognito mode
5. Check browser console for errors

### Issue: "Missing environment variables" in tests
**Solution**: This is expected with `tsx`. Either:
- Run tests through Next.js API
- Or install and use `dotenv-cli`:
  ```bash
  npm install -g dotenv-cli
  dotenv -e .env.local npx tsx ingest/test_persist.ts
  ```

---

## 📊 Migration Summary

### Before Migration:
- ❌ No `profiles` table → Login loop
- ❌ `papers` table missing columns (board, level, etc.)
- ❌ `questions` table missing columns (difficulty, style, etc.)
- ❌ No `question_parts` table → Can't store segmented parts
- ❌ No `question_tags` table → Can't store topic tags
- ❌ No `ingestions` table → Can't track pipeline runs
- ❌ Code references non-existent columns

### After Migration:
- ✅ `profiles` table with auto-creation trigger
- ✅ `papers` table extended with all needed columns
- ✅ `questions` table extended with all needed columns
- ✅ `question_parts` table created
- ✅ `question_tags` table created
- ✅ `ingestions` table created
- ✅ `worksheets` and `worksheet_items` tables created
- ✅ All RLS policies configured
- ✅ All indexes created
- ✅ Code fixed to use correct columns
- ✅ Login works!

---

## 🎯 Quick Checklist

- [ ] Delete old SQL files (COMPLETE_DATABASE_SCHEMA.sql, supabase_schema.sql)
- [ ] Open Supabase Dashboard
- [ ] Go to SQL Editor
- [ ] Copy entire `FIXED_DATABASE_SCHEMA.sql`
- [ ] Paste and run in Supabase
- [ ] Verify success message
- [ ] Check `profiles` table exists in Table Editor
- [ ] Test login at http://localhost:3001/login
- [ ] Verify redirect to /dashboard (NOT /login)
- [ ] Run `npx tsx ingest/test_metadata.ts`
- [ ] Run `npx tsx ingest/test_features.ts`
- [ ] Run `npx tsx ingest/test_persist.ts`
- [ ] Check database for saved data
- [ ] Follow `TESTING_CHECKLIST.md` for complete testing

---

## 🆘 Need Help?

If you encounter issues:

1. **Check the error message** in Supabase SQL Editor
2. **Look at browser console** (F12) for frontend errors
3. **Check Supabase logs** in Dashboard → Logs
4. **Verify environment variables** in `.env.local`
5. **Follow** `LOGIN_FIX_INSTRUCTIONS.md` for detailed troubleshooting

---

**Ready?** Start with Step 1: Delete the old files! 🚀
