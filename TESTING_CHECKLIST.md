# 🧪 COMPLETE TESTING CHECKLIST

## Pre-Testing Setup

### ✅ Required: Run Database Migration
```sql
-- In Supabase Dashboard → SQL Editor
-- Copy/paste and run: COMPLETE_DATABASE_SCHEMA.sql
```

**Verify it worked:**
- Go to Supabase → Table Editor
- Should see: profiles, papers, questions, question_parts, etc.

---

## Test 1: Login System ✓

### Steps:
1. Open http://localhost:3001/login
2. Click "Continue with Google"
3. Authorize the app
4. Should redirect to /dashboard

### Expected Results:
- ✅ No redirect loop
- ✅ Dashboard shows "Hi, [Your Name] 👋"
- ✅ Profile created in `profiles` table
- ✅ Can see Level and Goal selector

### If It Fails:
- Check `LOGIN_FIX_INSTRUCTIONS.md`
- Verify profiles table exists
- Check browser console for errors

---

## Test 2: Metadata Detection ✓

### Command:
```bash
npx tsx ingest/test_metadata.ts
```

### Expected Output:
```
✅ 8/8 validation checks passed (100%)
✅ Board: Edexcel
✅ Level: IGCSE
✅ Subject: Physics (4PH1)
✅ Year: 2019 June
✅ Confidence: 55-100%
```

### Status: **READY** (no database required)

---

## Test 3: Features Extraction ✓

### Command:
```bash
npx tsx ingest/test_features.ts
```

### Expected Output:
```
✅ All 12 questions analyzed
✅ Difficulty: 0 easy, 7 medium, 5 hard
✅ Average time: 14.1 minutes
✅ Styles: calculation, explanation, diagram
```

### Status: **READY** (no database required)

---

## Test 4: Persistence ✓

### Command:
```bash
npx tsx ingest/test_persist.ts
```

### Expected Output:
```
✅ SAVE SUCCESSFUL!
Paper ID: [UUID]
Questions: 1
Parts: 2
Tags: 1
```

### Requirements:
- ✅ COMPLETE_DATABASE_SCHEMA.sql run
- ✅ .env.local with Supabase credentials

### If It Fails:
- "Missing Supabase environment variables" → Check .env.local
- "relation does not exist" → Run COMPLETE_DATABASE_SCHEMA.sql
- Check error message for specific table

---

## Test 5: Full Integration ✓

### Command:
```bash
npx tsx ingest/test_full_integration.ts
```

### Expected Output:
```
✅ INTEGRATION TEST COMPLETE

📊 SUMMARY:
  Parsed:     32 pages, 2000+ text items
  Segmented:  12 questions, 61 parts
  Linked:     11 markschemes (92% coverage)
  Tagged:     8 questions
  Features:   12 questions analyzed
  Saved:      12 questions, 61 parts

⏱️  TOTAL:    ~1.3s
```

### Requirements:
- ✅ COMPLETE_DATABASE_SCHEMA.sql run
- ✅ PDFs in `data/raw/IGCSE/4PH1/2019/Jun/`

### If It Fails:
- Check which step fails
- Each step has error messages
- See `TROUBLESHOOTING.md`

---

## Test 6: API Routes ✓

### Test GET /api/papers
```bash
# In browser or curl:
curl http://localhost:3001/api/papers
```

### Expected Response:
```json
{
  "success": true,
  "papers": [...],
  "count": N
}
```

### Test POST /api/ingest
```bash
# This requires authentication
# Use Postman or test through UI
```

### Status: **READY** (requires login)

---

## Test 7: QA Dashboard ✓

### Steps:
1. Login at http://localhost:3001/login
2. Go to http://localhost:3001/qa
3. Should see ingestions table

### Expected Results:
- ✅ Stats cards (questions, parts, tags)
- ✅ Table with ingested papers
- ✅ Click row to see details
- ✅ "View Details" button works

### Status: **READY** (requires login + data)

---

## Test 8: Dashboard Features ✓

### Steps:
1. Login at http://localhost:3001/login
2. Go to http://localhost:3001/dashboard
3. Test all features

### Features to Test:
- [ ] Level selector (IGCSE/IAL)
- [ ] Marks goal slider
- [ ] Subject dropdown
- [ ] Timer (starts/stops)
- [ ] Papers checklist
- [ ] Marks chart
- [ ] Logout button

### Status: **READY** (requires login)

---

## Test 9: Worksheets Page ✓

### Steps:
1. Go to http://localhost:3001/worksheets
2. Should see worksheet list

### Expected:
- ✅ "Create New Worksheet" button
- ✅ List of worksheets (if any exist)
- ✅ Can click to view/edit

### Status: **READY**

---

## 📊 Overall Test Summary

| Test | Status | Requirements | Time |
|------|--------|--------------|------|
| Login | ✅ Ready | Database schema | 1 min |
| Metadata | ✅ Ready | None | 1 min |
| Features | ✅ Ready | None | 1 min |
| Persistence | ✅ Ready | Database + PDFs | 2 min |
| Integration | ✅ Ready | Database + PDFs | 3 min |
| API Routes | ✅ Ready | Database + Login | 2 min |
| QA Dashboard | ✅ Ready | Database + Login + Data | 2 min |
| Dashboard | ✅ Ready | Database + Login | 2 min |
| Worksheets | ✅ Ready | Database + Login | 1 min |

**Total Testing Time**: ~15 minutes

---

## 🎯 Quick Start Testing Sequence

### 1. Setup (One-time)
```bash
# Run in Supabase SQL Editor:
COMPLETE_DATABASE_SCHEMA.sql
```

### 2. Test Without Database
```bash
npx tsx ingest/test_metadata.ts
npx tsx ingest/test_features.ts
```

### 3. Test Login
```
1. Open http://localhost:3001/login
2. Login with Google
3. Verify dashboard loads
```

### 4. Test With Database
```bash
npx tsx ingest/test_persist.ts
npx tsx ingest/test_full_integration.ts
```

### 5. Test UI
```
1. Visit http://localhost:3001/dashboard
2. Visit http://localhost:3001/qa
3. Visit http://localhost:3001/worksheets
```

---

## ⚠️ Common Issues & Fixes

### "Missing Supabase environment variables"
**Fix**: Verify `.env.local` exists with correct values

### "relation does not exist"
**Fix**: Run `COMPLETE_DATABASE_SCHEMA.sql` in Supabase

### Login loop (keeps redirecting to /login)
**Fix**: See `LOGIN_FIX_INSTRUCTIONS.md`

### "No questions found"
**Fix**: Check PDFs are in `data/raw/IGCSE/4PH1/2019/Jun/`

### 401 Unauthorized
**Fix**: Login required. Go to /login first

### TypeScript errors
**Fix**: Run `npm install` to install all dependencies

---

## ✅ Success Criteria

### All tests pass if:
- ✅ Login works (no redirect loop)
- ✅ Dashboard displays user info
- ✅ Metadata detection: 8/8 checks
- ✅ Features extraction: 12/12 questions
- ✅ Persistence: saves to database
- ✅ Integration: full pipeline < 2 seconds
- ✅ API routes return data
- ✅ QA dashboard shows ingestions
- ✅ All pages load without errors

---

## 📝 Report Template

After testing, report results:

```
✅ TESTING COMPLETE

Environment:
- Supabase URL: https://tybaetnvnfgniotdfxze.supabase.co
- Database schema: ✅ Installed
- Environment variables: ✅ Set
- PDFs available: ✅ Yes

Test Results:
1. Login: ✅ Pass / ❌ Fail - [notes]
2. Metadata: ✅ Pass / ❌ Fail - [notes]
3. Features: ✅ Pass / ❌ Fail - [notes]
4. Persistence: ✅ Pass / ❌ Fail - [notes]
5. Integration: ✅ Pass / ❌ Fail - [notes]
6. API Routes: ✅ Pass / ❌ Fail - [notes]
7. QA Dashboard: ✅ Pass / ❌ Fail - [notes]
8. Dashboard: ✅ Pass / ❌ Fail - [notes]
9. Worksheets: ✅ Pass / ❌ Fail - [notes]

Performance:
- Metadata detection: [X]ms
- Features extraction: [X]ms
- Full pipeline: [X]ms

Issues Found:
- [List any issues]

Overall Status: ✅ PASS / ❌ FAIL
```

---

**Start testing now!** Begin with the Quick Start Testing Sequence above.
