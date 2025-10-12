# 🔧 Frontend "Invalid API Key" Fix

## ❌ Problem

After running `npm run dev` and trying to generate a worksheet, you get:
```
Error: Invalid API key
```

---

## 🔍 Root Cause

The Next.js dev server was started **before** the `.env.local` file was properly configured. Environment variables are only loaded when the server starts, so it's reading old/missing values.

---

## ✅ Solution: Restart the Dev Server

### Step 1: Stop the Current Server

In the terminal running `npm run dev`:
- Press **`Ctrl + C`** to stop the server

### Step 2: Verify Environment File

Check that `.env.local` exists and has the correct values:

```powershell
Get-Content .env.local
```

**Expected output:**
```bash
NEXT_PUBLIC_SUPABASE_URL=https://tybaetnvnfgniotdfxze.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

✅ **These values are already correct in your file!**

### Step 3: Restart the Server

```powershell
npm run dev
```

### Step 4: Test the Frontend

1. Visit: **http://localhost:3000/generate**
2. Select some topics
3. Click "Generate Worksheet"
4. Should work now! ✅

---

## 🔍 Why This Happens

### How Next.js Loads Environment Variables:

```
1. npm run dev starts
2. Next.js reads .env.local (ONE TIME)
3. Injects variables into process.env
4. Server runs with those values
```

**Key Point**: Environment variables are read **only at startup**, not on every request.

### When You Need to Restart:

- ✅ After creating `.env.local`
- ✅ After modifying `.env.local`
- ✅ After changing any `NEXT_PUBLIC_*` variables
- ❌ NOT needed for code changes (hot reload works)

---

## 🧪 Verify the Fix

### Test 1: Check Environment Variables Are Loaded

After restarting, check the terminal output. You should see:
```
✓ Ready in [time]
○ Local: http://localhost:3000
```

No errors about missing environment variables.

### Test 2: Generate a Worksheet

1. Go to http://localhost:3000/generate
2. Select 2-3 topics (e.g., Forces and motion, Electricity)
3. Select difficulty: Medium
4. Click "Generate Worksheet"

**Expected**: Should see list of questions, not an error! ✅

---

## 🔐 What the API Keys Are Used For

### Frontend API Routes Use:

**`.env.local`** (Client-safe keys):
```bash
NEXT_PUBLIC_SUPABASE_URL=https://tybaetnvnfgniotdfxze.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc... (anon key)
```

**Used in**:
- `/api/worksheets/generate-v2` ← Worksheet generation
- `/api/worksheets/[id]/download` ← PDF downloads
- `/api/topics` ← Fetch topics
- `/api/subjects` ← Fetch subjects

### Python Scripts Use:

**`.env.ingest`** (Server-only keys):
```bash
SUPABASE_URL=https://tybaetnvnfgniotdfxze.supabase.co
SUPABASE_SERVICE_ROLE=eyJhbGc... (service role - full access)
GEMINI_API_KEY=AIzaSyB... (AI classification)
DATABASE_URL=postgresql://... (PostgreSQL direct)
```

**Used in**:
- `page_based_ingest.py` ← Paper processing
- `bulk_ingest.py` ← Batch processing
- `complete_pipeline.py` ← Full pipeline

---

## 📋 Quick Checklist

Before using the frontend:

- [x] ✅ `.env.local` exists with correct keys
- [x] ✅ `npm run dev` is running
- [ ] ⏳ **Restart dev server** (do this now!)
- [ ] ⏳ Test worksheet generation

---

## 🆘 If It Still Doesn't Work

### Error: "Invalid API key" after restart

**Check 1**: Verify environment variables are loaded
```powershell
# In a NEW terminal (keep npm run dev running)
node -e "console.log('URL:', process.env.NEXT_PUBLIC_SUPABASE_URL); console.log('Key:', process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.slice(0, 20))"
```

**Check 2**: Look at the browser console (F12) for the exact error message

**Check 3**: Check the terminal running `npm run dev` for error messages

### Error: "Cannot connect to Supabase"

**Solution**: Check that the URL and key match what's in Supabase dashboard:
- Go to: https://supabase.com/dashboard/project/tybaetnvnfgniotdfxze/settings/api
- Copy "Project URL" and "anon public" key
- Update `.env.local` if they don't match

---

## 🎯 Next Steps

### Step 1: Restart Dev Server ⏳
```powershell
# Press Ctrl+C in the terminal running npm run dev
# Then run:
npm run dev
```

### Step 2: Test Worksheet Generation ⏳
1. Visit http://localhost:3000/generate
2. Select topics
3. Click "Generate Worksheet"
4. Should work! ✅

### Step 3: Download PDFs ⏳
1. Click "Download Worksheet PDF"
2. Click "Download Markscheme PDF"
3. Check the PDFs open correctly

---

## 📝 Summary

**The Fix**: Just restart the Next.js dev server!

**Why**: Environment variables are loaded at startup, not on every request.

**How**:
1. Press `Ctrl + C` in terminal
2. Run `npm run dev`
3. Test again

**Status**: Your `.env.local` file is already correct, you just need to restart! 🚀
