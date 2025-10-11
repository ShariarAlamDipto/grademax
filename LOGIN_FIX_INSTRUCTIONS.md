# 🔧 LOGIN FIX INSTRUCTIONS

## Issue: Login Loop (keeps redirecting back to /login)

### Root Cause
The `profiles` table doesn't exist or RLS policies are preventing access.

---

## 🎯 SOLUTION: Run the Complete Database Schema

### Step 1: Copy the SQL File
The complete schema is in: `COMPLETE_DATABASE_SCHEMA.sql`

### Step 2: Run in Supabase
1. Go to your Supabase Dashboard: https://supabase.com/dashboard
2. Select your project: `tybaetnvnfgniotdfxze`
3. Click **SQL Editor** in the left sidebar
4. Click **"New Query"**
5. Copy and paste the entire contents of `COMPLETE_DATABASE_SCHEMA.sql`
6. Click **"Run"** (or press Ctrl+Enter)

### Step 3: Verify
You should see output like:
```
✅ Complete database schema created successfully!
Tables created:
  - profiles (with RLS and auto-creation trigger)
  - subjects, topics
  - papers
  - questions
  - question_parts
  - question_tags
  - ingestions
  - worksheets
  - worksheet_items

🔒 All tables have RLS enabled with proper policies
✅ Ready for use!
```

---

## 🔍 What This Does

### Creates Missing Tables
- **profiles**: Stores user data (study level, marks goal)
- **papers**: Exam papers metadata
- **questions**: Question data
- **question_parts**: Individual parts (a, b, c, etc.)
- **question_tags**: Topic tags
- **ingestions**: Tracks PDF ingestions
- **worksheets**: User-created worksheets
- **worksheet_items**: Items in worksheets

### Sets Up Authentication
- **Auto-creates profile** when user signs up
- **RLS policies** so users only see their own data
- **Triggers** to auto-update timestamps

---

## 🧪 Test After Running

### 1. Test Login Flow
```
1. Go to http://localhost:3001/login
2. Click "Continue with Google"
3. Authorize the app
4. Should redirect to /dashboard (NOT back to /login)
```

### 2. Check Profile Created
Go to Supabase Dashboard → Table Editor → profiles
You should see your profile with:
- Your email
- Your name
- Default marks_goal_pct: 90

### 3. Test Dashboard
- Dashboard should show your name
- "Hi, [YourName] 👋" at the top
- Level and goal selector should work

---

## ⚠️ If Still Having Issues

### Check Browser Console
1. Open browser DevTools (F12)
2. Go to Console tab
3. Look for errors

### Common Errors:

**"relation public.profiles does not exist"**
→ Run COMPLETE_DATABASE_SCHEMA.sql

**"new row violates row-level security policy"**
→ Check that RLS policies were created (they're in the schema file)

**"Could not auto-refresh session"**
→ Google OAuth not configured correctly

**Infinite redirect loop**
→ Profile not being created on signup. Check that the trigger exists:
```sql
SELECT * FROM pg_trigger WHERE tgname = 'on_auth_user_created';
```

---

## 📋 Quick Checklist

- [ ] Run COMPLETE_DATABASE_SCHEMA.sql in Supabase
- [ ] Verify profiles table exists
- [ ] Verify trigger `on_auth_user_created` exists
- [ ] Google OAuth configured in Supabase (Authentication → Providers)
- [ ] Redirect URIs include:
  - `https://tybaetnvnfgniotdfxze.supabase.co/auth/v1/callback`
  - `http://localhost:3001/auth/callback`
- [ ] Clear browser cookies for localhost
- [ ] Try logging in again

---

## 🎓 Why This Happens

When you login with Google:
1. Google redirects to `/auth/callback`
2. Callback exchanges code for session
3. Redirects to `/dashboard`
4. Dashboard tries to read from `profiles` table
5. **If table doesn't exist**: Error occurs, redirects to `/login`
6. **If RLS blocks read**: Same redirect loop

The solution is to create the profiles table with proper RLS policies!

---

## 📞 Next Steps After Fix

Once login works:
1. ✅ Test dashboard displays correctly
2. ✅ Test QA dashboard at http://localhost:3001/qa
3. ✅ Run integration test: `npx tsx ingest/test_full_integration.ts`
4. ✅ Start ingesting papers

---

**File to run in Supabase**: `COMPLETE_DATABASE_SCHEMA.sql`  
**Expected time**: 2 minutes  
**Result**: Login should work perfectly!
