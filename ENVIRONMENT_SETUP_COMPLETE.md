# 🔧 Environment Setup Complete

## ✅ What Was Fixed

### 1. UI Styling - Dark Theme Applied
- ✅ Background: Black gradient (gray-900 → black → gray-900)
- ✅ Text: White/Gray-300
- ✅ Cards: Dark gray-800 with opacity
- ✅ Borders: Gray-600/700
- ✅ Selected topics: Blue glow effect
- ✅ Error messages: Red-900 with red borders
- ✅ Results section: Dark theme throughout

### 2. API Keys Configured
- ✅ **Gemini API Key** added to `.env.ingest`
- ✅ **Supabase credentials** already present
- ✅ **SupabaseClient** updated to use correct env variables

### 3. Supabase Client Fixed
- ✅ Now checks for `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE`
- ✅ Falls back to `NEXT_PUBLIC_*` variables if needed
- ✅ Better error messages

---

## 📁 Environment Files

### `.env.ingest` (For Python Scripts)
```bash
SUPABASE_URL=https://tybaetnvnfgniotdfxze.supabase.co
SUPABASE_SERVICE_ROLE=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
GEMINI_API_KEY=REDACTED
```
✅ **This file is configured correctly!**

### `.env.local` (For Next.js Frontend)
Check if this exists and has:
```bash
NEXT_PUBLIC_SUPABASE_URL=https://tybaetnvnfgniotdfxze.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>
```

---

## 🎯 Understanding the System

### How Classification Works

**Classification happens DURING paper processing, NOT during worksheet generation.**

#### Step 1: Paper Ingestion (Uses Gemini)
```bash
python scripts/page_based_ingest.py "QP.pdf" "MS.pdf"
```
**What happens:**
1. ✂️ Splits QP into individual question pages
2. 🔍 Extracts corresponding MS pages
3. 🤖 **Uses Gemini API** to classify each question by topic
4. 📤 Uploads PDFs to Supabase Storage
5. 💾 Stores metadata in database (with topics array)

**Gemini API is used here for classification!**

#### Step 2: Worksheet Generation (No Gemini)
```
1. User selects topics in UI
2. Frontend calls /api/worksheets/generate-v2
3. API queries database: SELECT * WHERE topics && ARRAY['1','3']
4. Returns pre-classified questions
5. User downloads PDFs
```

**No AI needed - just database queries!**

---

## 🚀 What To Do Now

### Step 1: Run Database Migrations (5 minutes)

**You MUST do this before processing papers!**

1. Go to Supabase Dashboard: https://supabase.com/dashboard
2. Navigate to SQL Editor
3. Run these migrations in order:

**Migration 1: Cleanup**
```sql
-- File: supabase/migrations/01_cleanup_old_data.sql
-- This drops old tables
DROP TABLE IF EXISTS worksheet_items CASCADE;
DROP TABLE IF EXISTS worksheets CASCADE;
-- ... etc
```

**Migration 2: New Schema**
```sql
-- File: supabase/migrations/00_clean_schema.sql
-- This creates new page-based schema
CREATE TABLE subjects (...);
CREATE TABLE topics (...);
-- ... etc
```

### Step 2: Load Environment Variables

**Before running Python scripts:**
```powershell
# Load .env.ingest variables into your session
Get-Content .env.ingest | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
    }
}
```

Or use `python-dotenv` (already in your script):
```python
from dotenv import load_dotenv
load_dotenv('.env.ingest')  # Loads automatically
```

### Step 3: Process Your First Paper

```bash
python scripts/page_based_ingest.py "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf" "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf"
```

**What you'll see:**
```
======================================================================
📋 Processing: 2019_Jun_1P
======================================================================

1️⃣  Creating paper record...
   ✅ Paper UUID: abc-def-123...

2️⃣  Splitting QP into pages...
   ✅ Split into 11 questions

3️⃣  Extracting mark schemes...
   ✅ Q1 MS extracted
   ✅ Q2 MS extracted
   ...

4️⃣  Classifying and uploading pages...
   ✅ [1/11] Q1: Topic 1 (Forces) | medium | conf: 0.92
   ✅ [2/11] Q2: Topic 2 (Electricity) | easy | conf: 0.88
   ...
```

### Step 4: Test Frontend

```bash
npm run dev
```

Visit: http://localhost:3000/generate

**Now with dark theme!** 🌙

---

## 🔍 Troubleshooting

### Error: "Invalid API key"
**Cause:** Environment variables not loaded
**Fix:** 
```powershell
# Load .env.ingest
Get-Content .env.ingest | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
    }
}

# Verify
python -c "import os; print('SUPABASE_URL:', os.getenv('SUPABASE_URL'))"
```

### Error: "Table doesn't exist"
**Cause:** Migrations not run
**Fix:** Run migrations in Supabase SQL Editor

### Error: "No questions found"
**Cause:** Database is empty
**Fix:** Process at least one paper first

---

## 📊 API Key Usage

### Gemini API Key
- **Used for:** Question classification during ingestion
- **Rate limit:** 15 requests per minute (free tier)
- **Cost:** Free up to 1500 requests/day
- **When:** Only during `page_based_ingest.py` execution

### Supabase Keys
- **SUPABASE_SERVICE_ROLE:** Server-side operations (Python scripts)
- **NEXT_PUBLIC_SUPABASE_ANON_KEY:** Client-side operations (Next.js)
- **Cost:** Free tier: 500MB database, 1GB storage

---

## ✅ Pre-Flight Checklist

Before processing papers:

- [ ] Database migrations run in Supabase
- [ ] `.env.ingest` has all 3 keys (✅ Done)
- [ ] Environment variables loaded in terminal
- [ ] `supabase_client.py` updated (✅ Done)
- [ ] Dark theme applied to UI (✅ Done)
- [ ] Test paper PDFs ready

---

## 🎨 UI Changes Summary

### Before (Light Theme)
```
- White background
- Gray text
- Light cards
```

### After (Dark Theme)
```
- Black/gray-900 gradient background
- White/gray-300 text
- Dark gray-800 cards with opacity
- Blue glow on selected topics
- Red-900 error messages
- Dark result cards with borders
```

**Much better for long sessions!** 👁️

---

## 🚀 Quick Start Commands

```powershell
# 1. Load environment
Get-Content .env.ingest | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
    }
}

# 2. Process a paper
python scripts/page_based_ingest.py "data/raw/.../QP.pdf" "data/raw/.../MS.pdf"

# 3. Start frontend
npm run dev

# 4. Visit http://localhost:3000/generate
```

---

## 📚 Key Files Modified

1. ✅ `.env.ingest` - Added GEMINI_API_KEY
2. ✅ `scripts/supabase_client.py` - Updated env variable handling
3. ✅ `src/app/generate/page.tsx` - Applied dark theme

---

**Status**: ✅ **READY TO PROCESS PAPERS**

**Next Step**: Run database migrations, then process your first paper!
