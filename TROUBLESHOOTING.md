# 🔧 Troubleshooting Guide

## Issues Fixed ✅

### 1. Ingestion Script Error (Module Not Found)
**Error:** `Cannot find module 'C:\Users\shari\grademax\ingest\parse_pdf'`

**Root Cause:** ts-node has issues with ESM imports without `.js` extensions

**Solution:**
- ✅ Installed `tsx` package (better ESM support)
- ✅ Updated all imports in `ingest_papers.ts` to use `.js` extensions
- ✅ Changed `package.json` script to use `tsx` instead of `ts-node`

**Verification:**
```cmd
npm run ingest:papers -- --help
```
Should show help text without errors.

---

### 2. Topics Dropdown Not Showing
**Issue:** Topics section not appearing on /worksheets page

**Root Cause:** Topics API was using `Number(subjectId)` but schema uses UUIDs

**Solution:**
- ✅ Fixed `/api/topics/route.ts` to use UUID directly (removed `Number()` cast)
- ✅ Added debug console logs to worksheets page
- ✅ Changed topics section to show "Loading topics..." when empty
- ✅ Added topic count indicator

**Verification:**
1. Open http://localhost:3000/worksheets
2. Open browser DevTools (F12) → Console tab
3. Select "IGCSE Physics (4PH1)" from dropdown
4. You should see:
   - Console: "Loading topics for subject: {...}"
   - Console: "Topics loaded: [21 topics]"
   - UI: "Topics (optional) - 21 available"
   - 21 checkboxes with topic names

---

## Quick Tests

### Test 1: Check Subjects API
```cmd
curl http://localhost:3000/api/subjects
```
Expected: JSON array with Physics subject (UUID id)

### Test 2: Check Topics API
Get subject ID from Test 1, then:
```cmd
curl "http://localhost:3000/api/topics?subjectId=YOUR-UUID-HERE"
```
Expected: JSON array with 21 Physics topics

### Test 3: Test Ingestion (Dry Run)
```cmd
npm run ingest:papers -- --dry-run --data-dir=./data/raw
```
Expected: 
- "📚 Loading topics..." 
- "✓ Loaded 21 topics"
- Parse simulation without database writes

### Test 4: Check Debug Page
Visit: http://localhost:3000/debug

Should show:
- Subjects array with 1 item (Physics)
- Topics array with 21 items

---

## Common Issues

### Issue: "SUPABASE_URL is not defined"
**Solution:** Check `.env.ingest` file exists and has correct values:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE=your-service-role-key
```

### Issue: "No topics found. Run schema and seed SQL first."
**Solution:**
1. Go to Supabase Dashboard → SQL Editor
2. Run `supabase/seed/schema.sql` (creates tables)
3. Run `supabase/seed/igcse_physics_topics.sql` (seeds topics)
4. Verify: `SELECT COUNT(*) FROM topics;` should return 21

### Issue: Topics show "Loading topics..." forever
**Open browser DevTools (F12) → Console**

Look for errors:
- If "Subject not found for code: 4PH1" → Schema not seeded
- If "Failed to load topics" → Check Supabase connection
- If "NetworkError" → Check dev server running (`npm run dev`)

### Issue: "Cannot find module 'zod'"
**Solution:**
```cmd
npm install
```

### Issue: Embeddings very slow on first run
**This is normal!** The MiniLM model (~100MB) downloads once and caches.
First run: ~2-5 minutes per topic
Subsequent runs: Fast

---

## Step-by-Step Verification

### 1. Environment Setup ✓
```cmd
# Check files exist
dir .env.local
dir .env.ingest

# Should contain SUPABASE_URL and keys
```

### 2. Dependencies ✓
```cmd
npm ls pdf-parse @xenova/transformers zod tsx
```
All should show versions (not missing)

### 3. Database Schema ✓
In Supabase SQL Editor:
```sql
SELECT tablename FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('subjects', 'topics', 'papers', 'questions')
ORDER BY tablename;
```
Should return 4 rows

### 4. Topics Seeded ✓
```sql
SELECT code, name FROM topics 
WHERE subject_id = (
  SELECT id FROM subjects 
  WHERE code='4PH1' AND level='IGCSE'
)
ORDER BY code;
```
Should return 21 rows (1a through 8b)

### 5. Web App Running ✓
```cmd
npm run dev
```
Visit http://localhost:3000/worksheets

### 6. Topics Loading ✓
1. Open DevTools Console (F12)
2. Select "IGCSE Physics (4PH1)"
3. Check console logs
4. Verify 21 checkboxes appear

---

## Next Steps After Fixing

### If Topics Now Show:
Proceed to Step 7 (Ingest Papers):

1. Create directory structure:
```cmd
mkdir data\raw\IGCSE\4PH1\2019\Jun
```

2. Add PDFs:
- `data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf` (question paper)
- `data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf` (markscheme)

3. Dry run:
```cmd
npm run ingest:papers -- --dry-run
```

4. Real ingestion:
```cmd
npm run ingest:papers
```

5. Generate worksheet:
- Visit http://localhost:3000/worksheets
- Select Physics
- Select topics (e.g., "Forces and motion", "Electricity")
- Set difficulty and count
- Click "Generate Worksheet"

---

## Debug Logs Reference

### Good Console Output:
```
Loading topics for subject: {id: "...", code: "4PH1", name: "Physics", level: "IGCSE"}
Topics loaded: [{id: "...", code: "1a", name: "Units"}, ...]
```

### Bad Console Output:
```
Subject not found for code: 4PH1
```
→ Topics SQL not run

```
Failed to load topics: NetworkError
```
→ Check Supabase credentials in .env.local

---

## Contact Points

If still having issues, check:
1. Browser DevTools Console (F12)
2. Terminal running `npm run dev` (server logs)
3. Supabase Dashboard → Logs (database errors)

Common fixes:
- Refresh page (Ctrl+R)
- Restart dev server (Ctrl+C, then `npm run dev`)
- Clear browser cache (Ctrl+Shift+Delete)
- Check Supabase RLS policies (should be open in dev)

---

**All issues should now be resolved!** ✅
