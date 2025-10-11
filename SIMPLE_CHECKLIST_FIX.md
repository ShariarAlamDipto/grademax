# ✅ SIMPLE CHECKLIST - Do These 2 Things

## Problem Summary

🔴 **Database diagnostics show:**
- ✅ 20 subjects exist (including Physics)
- ❌ 0 topics exist (database is empty!)
- ⚠️ You haven't run the updated COMPLETE_FIX.sql yet

🔴 **Login error:** "requested path is invalid"
- ⚠️ Redirect URLs not configured in Supabase

---

## ☑️ FIX #1: Add Physics Topics (5 minutes)

### ☐ Step 1: Go to Supabase
- Open: https://supabase.com/dashboard
- Click your project: `tybaetnvnfgniotdfxze`

### ☐ Step 2: Open SQL Editor
- Left sidebar → "SQL Editor"
- Click "+ New query"

### ☐ Step 3: Run COMPLETE_FIX.sql
- In VS Code: Open `COMPLETE_FIX.sql`
- Press `Ctrl+A` then `Ctrl+C` (copy all)
- Paste into Supabase SQL Editor
- Click "RUN" button
- Wait for ✅ success message

### ☐ Step 4: Verify
```powershell
npx tsx test_supabase_connection.ts
```
Should show: **"✅ Found 24 Physics topics"**

---

## ☑️ FIX #2: Configure Auth URLs (3 minutes)

### ☐ Step 1: Go to Auth Settings
- In Supabase Dashboard
- Left sidebar → "Authentication"
- Click "URL Configuration"

### ☐ Step 2: Set Site URL
Change to:
```
http://localhost:3001
```

### ☐ Step 3: Add Redirect URLs
Click "Add URL" twice and add:
```
http://localhost:3001/auth/callback
http://localhost:3001/**
```

### ☐ Step 4: Save
- Click "Save" at bottom
- Wait for confirmation

---

## ☑️ TEST Everything (2 minutes)

### ☐ Clear Browser Cache
- Press `Ctrl+Shift+Delete`
- Clear "Cookies" and "Cache"

### ☐ Test Login
- Go to: http://localhost:3001/login
- Click "Continue with Google"
- Should work! No errors!

### ☐ Test Topics
- Go to: http://localhost:3001/worksheets
- Select "Edexcel IGCSE Physics (4PH1)"
- Should see: **"24 available"** topics
- Topics should list: Units, Movement, Forces, Electricity, etc.

---

## 🎯 Done!

When ALL checkboxes above are ✅, both issues are fixed!

**Total time: ~10 minutes**

---

## Still Not Working?

Run this to see what's missing:
```powershell
npx tsx test_supabase_connection.ts
```

It will tell you:
- ✅ or ❌ Subjects (should be 20)
- ✅ or ❌ Physics topics (should be 24)
- ✅ or ❌ Profiles table exists

If topics = 0 → You didn't run Step 1 correctly
If login fails → You didn't do Step 2 correctly
