# 🔧 Vercel Environment Variables Setup

## Problem
Subjects and topics not showing on production even though database has data.

## Root Cause
Environment variables not configured in Vercel production environment.

## Solution: Set Environment Variables in Vercel

### Step 1: Go to Vercel Dashboard
1. Visit: https://vercel.com
2. Select your **grademax** project
3. Click **Settings** tab
4. Click **Environment Variables** in left sidebar

### Step 2: Add Required Variables

Add these **3 environment variables** for **Production** environment:

#### Variable 1: NEXT_PUBLIC_SUPABASE_URL
```
Name: NEXT_PUBLIC_SUPABASE_URL
Value: https://tybaetnvnfgniotdfxze.supabase.co
Environment: Production (check the box)
```

#### Variable 2: NEXT_PUBLIC_SUPABASE_ANON_KEY
```
Name: NEXT_PUBLIC_SUPABASE_ANON_KEY
Value: [Your anon key from .env.local]
Environment: Production (check the box)
```

To get the value, run locally:
```bash
# Windows PowerShell
Get-Content .env.local | Select-String "NEXT_PUBLIC_SUPABASE_ANON_KEY"

# Or just open .env.local and copy the value
```

#### Variable 3: SUPABASE_SERVICE_ROLE_KEY
```
Name: SUPABASE_SERVICE_ROLE_KEY
Value: [Your service role key from .env.local]
Environment: Production (check the box)
```

To get the value, run locally:
```bash
# Windows PowerShell
Get-Content .env.local | Select-String "SUPABASE_SERVICE_ROLE_KEY"

# Or just open .env.local and copy the value
```

### Step 3: Redeploy

After adding all variables:
1. Go to **Deployments** tab in Vercel
2. Find the latest deployment
3. Click the **⋯** (three dots) menu
4. Click **Redeploy**
5. Select **Use existing Build Cache** (optional)
6. Click **Redeploy**

OR just push a new commit to trigger deployment:
```bash
git commit --allow-empty -m "Trigger redeploy with env vars"
git push origin main
```

### Step 4: Verify Configuration

After redeployment, test these endpoints:

```bash
# Check configuration
curl https://www.grademax.me/api/debug/config

# Check subjects
curl https://www.grademax.me/api/subjects

# Check topics (use actual subject ID)
curl https://www.grademax.me/api/topics?subjectId=8dea5d70-f026-4e03-bb45-053f154c6898
```

Expected results:
- `/api/debug/config` - Should show all env vars as `true`
- `/api/subjects` - Should return array with subjects
- `/api/topics` - Should return array with topics

## Alternative: Use Vercel CLI

If you have Vercel CLI installed:

```bash
# Install Vercel CLI (if not installed)
npm i -g vercel

# Login to Vercel
vercel login

# Link to your project
vercel link

# Add environment variables
vercel env add NEXT_PUBLIC_SUPABASE_URL production
# Paste: https://tybaetnvnfgniotdfxze.supabase.co

vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production
# Paste your anon key

vercel env add SUPABASE_SERVICE_ROLE_KEY production
# Paste your service role key

# Trigger redeploy
vercel --prod
```

## Verification Checklist

After setting environment variables and redeploying:

- [ ] All 3 environment variables added in Vercel
- [ ] Variables set for **Production** environment
- [ ] Redeployment triggered
- [ ] Deployment completed successfully
- [ ] Visit https://www.grademax.me/api/debug/config
  - Should show `hasSupabaseUrl: true`
  - Should show `hasAnonKey: true`
  - Should show `hasServiceKey: true`
  - Should show `supabaseConnected: true`
  - Should show `subjectsTest.success: true`
  - Should show `topicsTest.success: true`
- [ ] Visit https://www.grademax.me/generate
  - Subject dropdown should populate
  - Selecting subject should populate topics
  - No errors in browser console

## Debugging

### Check Vercel Deployment Logs
1. Go to Vercel Dashboard
2. Click on latest deployment
3. Click **View Function Logs**
4. Look for console.log output from APIs

### Check Browser Console
1. Open https://www.grademax.me/generate
2. Press F12 to open DevTools
3. Go to Console tab
4. Look for API errors
5. Check Network tab for failed requests

### Common Issues

**Issue:** "Missing Supabase credentials" in logs
- **Fix:** Environment variables not set or deployment not redeployed

**Issue:** API returns empty arrays
- **Fix:** Wrong Supabase URL or keys

**Issue:** CORS errors
- **Fix:** Check Supabase CORS settings in dashboard

**Issue:** 401 Unauthorized
- **Fix:** Anon key incorrect or expired

## Quick Copy-Paste Values

Your Supabase URL:
```
https://tybaetnvnfgniotdfxze.supabase.co
```

Get your keys from local `.env.local` file:
```bash
# View your .env.local
cat .env.local

# Or on Windows
type .env.local
```

## After Setup

Once environment variables are configured:
1. ✅ Subjects will load in dropdown
2. ✅ Topics will load when subject selected
3. ✅ Worksheet generation will work
4. ✅ No more empty dropdowns

---

**Important:** Never commit `.env.local` to git! These are secrets.
Only add them to Vercel through the dashboard or CLI.
