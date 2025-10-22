# 🧪 Local Testing Protocol - Before Production Deployment

## Overview
Test everything locally on http://localhost:3000 before pushing to production.

## Pre-Testing Setup

### 1. Ensure Dev Server is Running
```bash
npm run dev
```
Expected: Server starts on http://localhost:3000

### 2. Verify Database State
```bash
python scripts/check_current_state.py
```
Expected output:
- ✅ Subject: Further Pure Mathematics (ID: 8dea5d70...)
- ✅ Topics: 10 topics listed
- ✅ Sample pages: 5+ questions

### 3. Verify Environment Variables
```bash
python scripts/show_env_vars.py
```
Expected:
- ✅ NEXT_PUBLIC_SUPABASE_URL set
- ✅ NEXT_PUBLIC_SUPABASE_ANON_KEY set
- ✅ SUPABASE_SERVICE_ROLE_KEY set

---

## Test Checklist (Execute in Order)

### Phase 1: API Endpoints ✅

#### Test 1.1: Configuration Diagnostic
```bash
# Should show all environment variables as true
curl http://localhost:3000/api/debug/config
```
✅ Expected:
```json
{
  "hasSupabaseUrl": true,
  "hasAnonKey": true,
  "hasServiceKey": true,
  "supabaseConnected": true,
  "subjectsTest": { "success": true, "count": 2+ },
  "topicsTest": { "success": true, "count": 5+ }
}
```

#### Test 1.2: Subjects API
```bash
curl http://localhost:3000/api/subjects
```
✅ Expected: Array of subjects with Further Pure Mathematics

#### Test 1.3: Topics API
```bash
# Replace with actual subject ID from check_current_state.py
curl "http://localhost:3000/api/topics?subjectId=8dea5d70-f026-4e03-bb45-053f154c6898"
```
✅ Expected: Array of 10 topics

#### Test 1.4: Auth Debug
```bash
curl http://localhost:3000/api/debug/auth
```
✅ Expected: Returns session info (even if not logged in)

---

### Phase 2: Authentication Flow ✅

#### Test 2.1: Login Page
1. Visit: http://localhost:3000/login
2. ✅ Page loads without errors
3. ✅ "Continue with Google" button visible
4. ✅ No console errors (F12)

#### Test 2.2: OAuth Flow
1. Click "Continue with Google"
2. ✅ Redirects to Google OAuth
3. ✅ Complete Google sign-in
4. ✅ Redirects back to localhost:3000/auth/callback
5. ✅ Then redirects to /generate
6. ✅ User stays logged in (check navbar)

#### Test 2.3: Permission Check
```bash
# After logging in, check permission API
curl http://localhost:3000/api/worksheets/check-permission
```
✅ Expected for authorized user (justarice7@gmail.com):
```json
{
  "hasPermission": true,
  "remainingQuota": 50,
  "maxPerDay": 50
}
```

---

### Phase 3: Generate Page UI ✅

#### Test 3.1: Page Load
1. Visit: http://localhost:3000/generate
2. ✅ Page loads without errors
3. ✅ Permission check shows "Access Granted"
4. ✅ Debug panel shows subject/topic counts
5. ✅ No red errors in browser console

#### Test 3.2: Subject Dropdown
1. Locate subject dropdown
2. ✅ Dropdown is populated (not empty)
3. ✅ Can see "Further Pure Mathematics"
4. ✅ Can select a subject
5. ✅ Console logs show: "Fetched X subjects"

#### Test 3.3: Topics Dropdown
1. Select "Further Pure Mathematics" from subject dropdown
2. ✅ Topics dropdown becomes enabled
3. ✅ Topics dropdown is populated with 10 topics
4. ✅ Can see topics like "Calculus", "Trigonometry", etc.
5. ✅ Console logs show: "Fetched X topics"
6. ✅ Can select multiple topics

#### Test 3.4: Year Selection
1. ✅ Year start dropdown shows years 2011-2025
2. ✅ Year end dropdown shows years 2011-2025
3. ✅ Can select year range
4. ✅ Start year ≤ End year validation works

#### Test 3.5: Filters
1. ✅ Difficulty dropdown has options
2. ✅ Question limit slider works (1-50)
3. ✅ Shuffle checkbox toggles
4. ✅ All inputs are functional

---

### Phase 4: Worksheet Generation ✅

#### Test 4.1: Generate Questions
1. Select subject: "Further Pure Mathematics"
2. Select topics: At least 2 topics
3. Set year range: 2012-2012
4. Set limit: 5 questions
5. Click "Generate Worksheet"
6. ✅ Loading spinner appears
7. ✅ Questions appear in preview (5 questions)
8. ✅ Each question shows:
   - Question number
   - Topics
   - Difficulty
   - Year/Season/Paper
9. ✅ No errors in console

#### Test 4.2: Download PDFs
1. After generating questions
2. Click "Download Worksheet PDF"
3. ✅ PDF downloads successfully
4. ✅ Opens in PDF viewer
5. ✅ Contains selected questions
6. Click "Download Markscheme PDF"
7. ✅ MS PDF downloads successfully
8. ✅ Contains corresponding answers

---

### Phase 5: Database Operations ✅

#### Test 5.1: Check Topics Sync
```bash
python scripts/check_current_state.py
```
✅ Verify topics match YAML:
1. Logarithmic functions & indices
2. Quadratic function
3. Identities & inequalities
4. Graphs
5. Series (AP/GP, sums, limits)
6. Binomial series
7. Scalar & vector quantities
8. Rectangular Cartesian coordinates
9. Calculus
10. Trigonometry

#### Test 5.2: Check Pages Data
```bash
python scripts/check_pages.py
```
✅ Expected:
- Q1-Q11 all have topics assigned
- Q1-Q11 all have QP PDFs
- Q1-Q11 all have MS PDFs

---

### Phase 6: Admin Portal ✅

#### Test 6.1: Admin Access
1. Visit: http://localhost:3000/admin
2. ✅ Login required (if not logged in)
3. ✅ Admin check passes (for admin users)
4. ✅ Dashboard loads

#### Test 6.2: User Management
1. ✅ Can see list of users
2. ✅ Can grant worksheet access
3. ✅ Can revoke access
4. ✅ Can set quotas

---

## Common Issues & Fixes

### Issue: Subjects dropdown empty
**Check:**
- Browser console for errors
- `/api/subjects` returns data
- Debug panel shows `subjects.length > 0`

**Fix:**
- Check Supabase connection
- Verify subjects exist in database
- Check for API errors in terminal

### Issue: Topics not loading
**Check:**
- Subject is selected
- `/api/topics?subjectId=...` returns data
- Console shows "Fetching topics for subject..."

**Fix:**
- Ensure subject ID is valid
- Check topics exist for that subject
- Verify subjectId is being passed correctly

### Issue: "Not authenticated" error
**Check:**
- `/api/debug/auth` shows session
- Cookies are set (F12 → Application → Cookies)
- User is logged in (check navbar)

**Fix:**
- Clear cookies and re-login
- Check Supabase auth configuration
- Verify middleware is running

### Issue: Permission denied
**Check:**
- `/api/worksheets/check-permission` shows hasPermission: true
- User email is in permissions table

**Fix:**
```bash
python scripts/grant_access.py
# Enter email: justarice7@gmail.com
```

---

## Success Criteria

Before pushing to production, ALL of these must pass:

- [ ] ✅ All API endpoints return expected data
- [ ] ✅ OAuth login works completely
- [ ] ✅ Subjects dropdown populates
- [ ] ✅ Topics dropdown populates when subject selected
- [ ] ✅ Can generate worksheet with 5+ questions
- [ ] ✅ Can download QP PDF
- [ ] ✅ Can download MS PDF
- [ ] ✅ No errors in browser console
- [ ] ✅ No errors in server terminal
- [ ] ✅ Database has 10 topics for Further Pure Maths
- [ ] ✅ All 11 questions have PDFs
- [ ] ✅ Authorized user (justarice7@gmail.com) has access

---

## After Successful Local Testing

### 1. Commit Changes
```bash
git add .
git commit -m "fix: Detailed description of what was fixed"
```

### 2. Push to GitHub (triggers production deployment)
```bash
git push origin main
```

### 3. Monitor Vercel Deployment
- Visit: https://vercel.com/dashboard
- Wait for deployment to complete (~2-3 minutes)
- Check deployment logs for errors

### 4. Test Production
Repeat key tests on production:
- https://www.grademax.me/api/debug/config
- https://www.grademax.me/generate
- Complete worksheet generation flow

### 5. Document Issues
If production differs from local:
- Check Vercel environment variables
- Check Vercel deployment logs
- Check browser console on production
- Update this document with findings

---

## Quick Test Commands

```bash
# Terminal 1: Run dev server
npm run dev

# Terminal 2: Run tests
curl http://localhost:3000/api/debug/config
curl http://localhost:3000/api/subjects
python scripts/check_current_state.py

# Open browser
start http://localhost:3000/generate
```

---

## Debugging Tools

### Browser DevTools (F12)
- **Console:** JavaScript errors, API calls, debug logs
- **Network:** API requests/responses, status codes
- **Application:** Cookies, localStorage, session

### Terminal Logs
- Watch for API errors
- Check Supabase query logs
- Monitor authentication flows

### Python Scripts
- `check_current_state.py` - Database state
- `verify_production_config.py` - Config check
- `show_env_vars.py` - Environment variables
- `check_pages.py` - Question data validation

---

**Remember:** Only push to production after ALL local tests pass! 🚀
