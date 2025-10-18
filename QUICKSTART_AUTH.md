# Quick Start: Authentication Setup

## ⚡ Fast Track (15 minutes)

### Step 1: Apply Migration (2 minutes)
```powershell
# Option A: Using Supabase Dashboard
# 1. Go to Supabase Dashboard → SQL Editor
# 2. Copy contents of: supabase/migrations/01_user_permissions.sql
# 3. Paste and Run

# Option B: Using CLI (if installed)
supabase db push
```

### Step 2: Install Python Package (1 minute)
```powershell
pip install supabase
```

### Step 3: Set Environment Variables (1 minute)
```powershell
# Check your .env.local file has these:
NEXT_PUBLIC_SUPABASE_URL=your-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### Step 4: Test the System (5 minutes)

#### 4.1 Start Dev Server
```powershell
npm run dev
```

#### 4.2 Sign In
1. Go to http://localhost:3000/login
2. Sign in with Google
3. Go to http://localhost:3000/generate
4. You should see: 🔒 **"Access Restricted"** (Good!)

#### 4.3 Grant Yourself Permission
```powershell
# Replace with your email
python scripts/manage_permissions.py grant your-email@gmail.com
```

#### 4.4 Verify Access
1. Refresh http://localhost:3000/generate
2. You should see: ✅ **"Access Granted"** (Perfect!)
3. Generate button should be enabled
4. Try generating a worksheet

### Step 5: Manage Users (2 minutes)

#### List all users
```powershell
python scripts/manage_permissions.py list
```

#### Grant permission to someone
```powershell
python scripts/manage_permissions.py grant their-email@gmail.com
```

#### Set daily quota
```powershell
# Limit to 10 worksheets per day
python scripts/manage_permissions.py quota their-email@gmail.com 10

# Unlimited
python scripts/manage_permissions.py quota their-email@gmail.com 0
```

#### View generation logs
```powershell
python scripts/manage_permissions.py logs
```

## ✅ Verification Checklist

After setup, verify these work:

- [ ] Migration applied (tables exist in Supabase)
- [ ] Sign up creates profile automatically
- [ ] New users see "Access Restricted" by default
- [ ] Admin can grant permission via script
- [ ] Granted users see "Access Granted"
- [ ] Generate button enabled only with permission
- [ ] Worksheet generation works for approved users
- [ ] Logs appear in database

## 🆘 Quick Troubleshooting

### "User not found" when granting permission
**Problem:** User hasn't signed up yet

**Solution:** Have them sign in first at `/login`

### "Access Restricted" even after granting
**Solution:** Hard refresh (Ctrl + Shift + R) or clear cookies

### Script says "Missing Supabase credentials"
**Solution:** 
```powershell
$env:NEXT_PUBLIC_SUPABASE_URL = "your-url"
$env:SUPABASE_SERVICE_ROLE_KEY = "your-key"
```

### Tables not found
**Problem:** Migration not applied

**Solution:** Run the migration SQL manually in Supabase Dashboard

## 📚 Full Documentation

For detailed info, see:
- `docs/AUTHENTICATION_SETUP.md` - Complete setup guide
- `docs/AUTHENTICATION_SUMMARY.md` - System overview

## 🎯 What You Built

✅ **Database Layer**
- 3 tables: permissions, profiles, logs
- 3 functions: check permission, get quota, handle new user
- RLS policies for security
- Automatic triggers

✅ **API Layer**
- Permission check endpoint
- Returns quota info
- Error handling

✅ **Frontend Layer**
- Permission check on page load
- Access denied UI
- Access granted UI with quota
- Conditional rendering

✅ **Admin Tools**
- Command-line management script
- Grant/revoke permissions
- Set quotas
- View logs

## 🚀 You're Done!

The authentication system is ready. Users must now:
1. Sign up with Google
2. Wait for admin approval
3. Get permission granted by you
4. Generate worksheets

You can manage permissions with the Python script. Enjoy! 🎉
