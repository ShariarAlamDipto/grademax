# 🚨 LOGIN & UI ISSUES - DIAGNOSIS & FIX

## Problems Identified

### 1. **Login Loop**
- **Cause**: `profiles` table doesn't exist yet
- **Dashboard query fails**: `SELECT ... FROM profiles WHERE id = ...`
- **Result**: Redirect back to `/login`

### 2. **White Worksheet UI**
- **Likely cause**: JavaScript error or missing data
- **Need to check**: Browser console for errors

### 3. **No Subjects in Dropdown**
- **Cause**: `subjects` table is empty OR doesn't have data
- **Component queries**: `SELECT id, name, level FROM subjects`
- **Result**: Empty dropdown

---

## 🔍 DIAGNOSIS STEPS

### Step 1: Check if you ran the SQL migration
Did you run `FIXED_DATABASE_SCHEMA.sql` in Supabase?

**To verify**:
1. Go to Supabase Dashboard → Table Editor
2. Check if these tables exist:
   - [ ] `profiles`
   - [ ] `subjects`
   - [ ] `topics`
   - [ ] `papers`
   - [ ] `questions`
   - [ ] `question_parts`

If tables DON'T exist → **You need to run the SQL migration first!**

### Step 2: Check if profiles table has RLS trigger
1. Go to Supabase → Database → Triggers
2. Look for trigger: `on_auth_user_created`
3. Should trigger on `auth.users` INSERT
4. Calls function: `handle_new_user()`

If trigger doesn't exist → **Run FIXED_DATABASE_SCHEMA.sql**

### Step 3: Check if subjects table has data
1. Go to Supabase → Table Editor → `subjects`
2. Check if there are rows

If table is EMPTY → **You need to seed data!**

---

## ✅ FIXES

### Fix 1: Run Database Migration (CRITICAL)

**If you haven't run it yet:**

1. Open `FIXED_DATABASE_SCHEMA.sql`
2. Copy ALL 406 lines
3. Go to Supabase → SQL Editor → New Query
4. Paste and click RUN
5. Wait for success message

**Expected output**:
```
✅ Fixed database schema applied successfully!
✅ profiles (with auto-creation trigger) - FIXES LOGIN LOOP
✅ papers (extended with new columns)
...
```

### Fix 2: Seed Subjects Data

The `subjects` table is empty! You need to add subjects. I'll create a seed script.

**Quick fix** - Run this in Supabase SQL Editor:

```sql
-- Insert sample subjects for testing
INSERT INTO subjects (board, level, code, name, color) VALUES
  ('Edexcel', 'IGCSE', '4PH1', 'Physics', '#3b82f6'),
  ('Edexcel', 'IGCSE', '4CH1', 'Chemistry', '#10b981'),
  ('Edexcel', 'IGCSE', '4MA1', 'Mathematics', '#ef4444'),
  ('Edexcel', 'IGCSE', '4BI1', 'Biology', '#8b5cf6'),
  ('Cambridge', 'IGCSE', '0625', 'Physics', '#3b82f6'),
  ('Cambridge', 'IGCSE', '0620', 'Chemistry', '#10b981'),
  ('Cambridge', 'IGCSE', '0580', 'Mathematics', '#ef4444')
ON CONFLICT (board, level, code) DO NOTHING;
```

### Fix 3: Manually Create Your Profile (Temporary)

If login still fails, manually create your profile:

```sql
-- Replace YOUR_USER_ID with your actual auth.users id
-- Find it in: Supabase → Authentication → Users → click your user
INSERT INTO profiles (id, email, full_name, study_level, marks_goal_pct)
VALUES (
  'YOUR_USER_ID',  -- ← Replace this
  'your@email.com', -- ← Replace this
  'Your Name',      -- ← Replace this
  'igcse',
  90
)
ON CONFLICT (id) DO NOTHING;
```

### Fix 4: Check for `user_subjects` Table

The SubjectDropdown component queries `user_subjects` table which doesn't exist in the schema!

**Add this table** - Run in Supabase SQL Editor:

```sql
-- Create user_subjects junction table
CREATE TABLE IF NOT EXISTS user_subjects (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  subject_id UUID REFERENCES subjects(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, subject_id)
);

CREATE INDEX IF NOT EXISTS idx_user_subjects_user ON user_subjects(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subjects_subject ON user_subjects(subject_id);

-- Enable RLS
ALTER TABLE user_subjects ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own subjects" ON user_subjects;
CREATE POLICY "Users can view own subjects" ON user_subjects
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can add own subjects" ON user_subjects;
CREATE POLICY "Users can add own subjects" ON user_subjects
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can remove own subjects" ON user_subjects;
CREATE POLICY "Users can remove own subjects" ON user_subjects
  FOR DELETE USING (auth.uid() = user_id);
```

### Fix 5: Check Worksheet Page

Let me check the worksheets page for errors. But first, check browser console:

1. Go to http://localhost:3001/worksheets
2. Press F12 (open DevTools)
3. Go to Console tab
4. Look for red errors

**Common errors**:
- "Cannot read property..." → Data is null/undefined
- "Failed to fetch" → API endpoint issue
- "relation does not exist" → Table not created

---

## 🎯 COMPLETE FIX SEQUENCE

### Step 1: Run This Complete SQL Script

I'll create a complete SQL script that fixes everything:

```sql
-- ============================================================================
-- COMPLETE FIX: Login + UI Issues
-- Run this entire script in Supabase SQL Editor
-- ============================================================================

-- Part 1: Ensure profiles table exists (fixes login)
-- (Already in FIXED_DATABASE_SCHEMA.sql - run that first!)

-- Part 2: Ensure subjects table has data
INSERT INTO subjects (board, level, code, name, color) VALUES
  ('Edexcel', 'IGCSE', '4PH1', 'Physics', '#3b82f6'),
  ('Edexcel', 'IGCSE', '4CH1', 'Chemistry', '#10b981'),
  ('Edexcel', 'IGCSE', '4MA1', 'Mathematics', '#ef4444'),
  ('Edexcel', 'IGCSE', '4BI1', 'Biology', '#8b5cf6'),
  ('Edexcel', 'IGCSE', '4EN1', 'English Language', '#f59e0b'),
  ('Cambridge', 'IGCSE', '0625', 'Physics', '#3b82f6'),
  ('Cambridge', 'IGCSE', '0620', 'Chemistry', '#10b981'),
  ('Cambridge', 'IGCSE', '0580', 'Mathematics', '#ef4444'),
  ('Cambridge', 'IGCSE', '0610', 'Biology', '#8b5cf6')
ON CONFLICT (board, level, code) DO NOTHING;

-- Part 3: Create user_subjects table (fixes subject dropdown)
CREATE TABLE IF NOT EXISTS user_subjects (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  subject_id UUID REFERENCES subjects(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, subject_id)
);

CREATE INDEX IF NOT EXISTS idx_user_subjects_user ON user_subjects(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subjects_subject ON user_subjects(subject_id);

ALTER TABLE user_subjects ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own subjects" ON user_subjects;
CREATE POLICY "Users can view own subjects" ON user_subjects
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can add own subjects" ON user_subjects;
CREATE POLICY "Users can add own subjects" ON user_subjects
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can remove own subjects" ON user_subjects;
CREATE POLICY "Users can remove own subjects" ON user_subjects
  FOR DELETE USING (auth.uid() = user_id);

-- Success message
DO $$
BEGIN
  RAISE NOTICE '✅ Complete fix applied!';
  RAISE NOTICE '  ✅ Subjects seeded';
  RAISE NOTICE '  ✅ user_subjects table created';
  RAISE NOTICE '';
  RAISE NOTICE '👉 Now:';
  RAISE NOTICE '   1. Logout and login again';
  RAISE NOTICE '   2. Profile should auto-create';
  RAISE NOTICE '   3. Subjects should appear in dropdown';
END $$;
```

### Step 2: Logout and Login Again

1. Go to dashboard (if you can)
2. Click logout
3. Clear browser cache (Ctrl+Shift+Delete)
4. Go to http://localhost:3001/login
5. Login with Google
6. Should work now!

### Step 3: Verify Everything Works

- [ ] Login redirects to /dashboard (not /login)
- [ ] Dashboard shows "Hi, [Your Name] 👋"
- [ ] Subject dropdown shows subjects when you click "Manage"
- [ ] Worksheets page loads (not white screen)
- [ ] No errors in browser console

---

## 🔍 DEBUGGING CHECKLIST

If still not working, check these:

### Check 1: Profiles Table
```sql
-- In Supabase SQL Editor:
SELECT * FROM profiles LIMIT 5;
```
- Should show your profile after login
- If empty → trigger didn't fire

### Check 2: Subjects Table
```sql
-- In Supabase SQL Editor:
SELECT * FROM subjects LIMIT 10;
```
- Should show 9+ subjects
- If empty → seed data didn't run

### Check 3: Triggers
```sql
-- Check if trigger exists:
SELECT trigger_name, event_manipulation, event_object_table
FROM information_schema.triggers
WHERE trigger_name = 'on_auth_user_created';
```
- Should return 1 row
- If empty → run FIXED_DATABASE_SCHEMA.sql

### Check 4: RLS Policies
```sql
-- Check profiles policies:
SELECT policyname, cmd FROM pg_policies
WHERE tablename = 'profiles';
```
- Should show 3 policies: SELECT, UPDATE, INSERT
- If less → run FIXED_DATABASE_SCHEMA.sql

### Check 5: Your User ID
```sql
-- Find your user ID:
SELECT id, email FROM auth.users;
```
- Copy your ID, use it to manually create profile if needed

---

## 🆘 EMERGENCY FIX

If nothing works, run these in order:

```sql
-- 1. Check your user exists
SELECT id, email FROM auth.users WHERE email = 'your@email.com';

-- 2. Manually create profile (replace YOUR_ID)
INSERT INTO profiles (id, email, study_level, marks_goal_pct)
VALUES ('YOUR_ID', 'your@email.com', 'igcse', 90)
ON CONFLICT (id) DO UPDATE SET
  email = EXCLUDED.email,
  study_level = EXCLUDED.study_level;

-- 3. Verify profile exists
SELECT * FROM profiles WHERE email = 'your@email.com';

-- 4. Check subjects exist
SELECT COUNT(*) FROM subjects;
-- Should return 9 or more

-- 5. Check user_subjects table exists
SELECT COUNT(*) FROM user_subjects;
-- Should return 0 (empty is OK)
```

---

## 📋 Quick Action Plan

1. **First**: Run `FIXED_DATABASE_SCHEMA.sql` if you haven't
2. **Second**: Run the "COMPLETE FIX" SQL script above
3. **Third**: Logout, clear cache, login again
4. **Fourth**: Check browser console for errors
5. **Fifth**: Report back what errors you see

---

**Most likely issue**: You haven't run the database migration yet!

Go run `FIXED_DATABASE_SCHEMA.sql` in Supabase SQL Editor now! 🚀
