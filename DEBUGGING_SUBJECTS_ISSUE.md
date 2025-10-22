# 🐛 Debugging Subjects Not Showing Issue

## Problem
- Access is granted (shows "Access Granted" message)
- But subjects and topics dropdowns are empty
- Database has subjects (confirmed via /api/debug/config)
- API works (subjects test returns 2 subjects)

## Changes Made for Debugging

### 1. Added Debug Panel (Always Visible)
Location: `/generate` page

Shows:
- Subjects count
- Loading state
- Selected subject
- Permission status
- List of subject names

**Why:** Need to see if subjects are being fetched but not displayed

### 2. Enhanced Console Logging

**Frontend (`generate/page.tsx`):**
- Logs when fetch starts
- Logs response status
- Logs data received
- Logs array validation
- Logs default selection

**Backend (`check-permission/route.ts`):**
- Logs authentication status
- Logs user email
- Logs permission record
- Logs quota check
- Logs final decision

**Why:** Track the entire flow from API to UI

### 3. API Logging (`subjects/route.ts`)

Added:
- Environment variable checks
- Detailed error logging
- Success count logging

**Why:** Confirm API is actually fetching data

## How to Diagnose

### Step 1: Check Browser Console
1. Go to https://www.grademax.me/generate
2. Open DevTools (F12) → Console tab
3. Look for `[Generate]` log messages
4. Check if subjects are being fetched

Expected logs:
```
[Generate] Fetching subjects...
[Generate] Subjects response status: 200
[Generate] Subjects data: Array(2)
[Generate] Setting subjects: 2 subjects found
[Generate] Setting default subject: [id]
```

### Step 2: Check Debug Panel
On the page, you should now see a blue debug box showing:
- Subjects count
- Loading state
- Permission status

If it shows:
- `Subjects count: 0` → API returning empty array
- `Subjects count: 2+` → Subjects loaded but not rendering
- `Loading subjects: Yes` → Still fetching
- `Has permission: No` → Permission check failing

### Step 3: Check Vercel Logs
1. Go to Vercel Dashboard → grademax → Deployments
2. Click latest deployment → View Function Logs
3. Look for console.log output:
   - `[check-permission]` logs
   - `Subjects API:` logs

### Step 4: Test APIs Directly

```bash
# Test config
curl https://www.grademax.me/api/debug/config

# Test subjects (should return array)
curl https://www.grademax.me/api/subjects

# Test permission (with your session)
curl https://www.grademax.me/api/worksheets/check-permission \
  -H "Cookie: your-session-cookie"
```

## Possible Issues & Solutions

### Issue 1: Subjects Fetched But Not Displayed
**Symptoms:** Console shows subjects loaded, but UI is empty
**Solution:** Check if conditional rendering is hiding the component

### Issue 2: Permission Check Failing Silently
**Symptoms:** Shows "Access Granted" but hasPermission is false
**Solution:** Check permission API response in Network tab

### Issue 3: Frontend State Not Updating
**Symptoms:** Logs show data, but state doesn't update
**Solution:** React state update issue - check for conflicts

### Issue 4: API Returning Empty Array
**Symptoms:** API call succeeds but returns `[]`
**Solution:** Database query issue - check environment variables

### Issue 5: CORS or Cookie Issue
**Symptoms:** API calls fail with network errors
**Solution:** Check CORS settings and cookie domain

## Next Steps

After deployment completes (2-3 minutes):

1. **Visit the page with debugging enabled**
   - Go to: https://www.grademax.me/generate
   - Should see blue debug panel

2. **Check the debug panel values**
   - If subjects count > 0: UI rendering issue
   - If subjects count = 0: API/database issue
   - If loading stuck: API timeout issue

3. **Check browser console**
   - Look for [Generate] logs
   - Check for any errors
   - Verify fetch sequence

4. **Check Network tab**
   - Filter for `/api/subjects`
   - Check response payload
   - Verify it's an array

5. **Report findings**
   - Screenshot of debug panel
   - Copy console logs
   - Copy API response

## Quick Test Commands

Once deployed, you can ask the user to:

```bash
# Check what the API returns
curl https://www.grademax.me/api/subjects

# Expected response:
[
  {
    "id": "...",
    "name": "Physics",
    "code": "4PH1",
    ...
  },
  {
    "id": "...",
    "name": "Further Pure Mathematics",
    "code": "9FM0",
    ...
  }
]
```

## Files Modified

- ✅ `src/app/generate/page.tsx` - Added debug panel + logging
- ✅ `src/app/api/worksheets/check-permission/route.ts` - Added logging
- ✅ Committed and ready to push

## Deployment

```bash
git push origin main
```

Wait 2-3 minutes, then check:
- https://www.grademax.me/generate
- Should see debug info
- Should see detailed console logs

---

**Status:** Ready for deployment and diagnosis
**Time:** Just now
**Commit:** 2361f05
