# Phase 1 Security Migration Guide

## 🎯 Overview

Phase 1 essential security upgrades have been implemented. This document guides you through applying the database migration and testing the new features.

## ✅ What's Been Completed

### 1. Database Migration Created
- **File:** `supabase/migrations/02_phase1_security.sql` (413 lines)
- **Creates:**
  - `user_sessions` - Session tracking with device info
  - `trusted_devices` - Device fingerprinting and management
  - `audit_log` - Tamper-evident event logging with hash chain
  - `usage_meters` - Quota tracking (worksheets/pages/questions)
  - `role_type` column added to `user_profiles`
  - 5 helper functions for session/usage/audit operations
  - RLS policies for secure access

### 2. Services Created
- **AuditLogger** (`src/lib/auditLogger.ts`) - Complete audit logging with convenience methods
- **UsageMeterService** (`src/lib/usageMeter.ts`) - Quota tracking and enforcement

### 3. Dashboard Improvements
- **File:** `src/app/dashboard/page.tsx`
- **Added:**
  - Usage stats banner showing worksheets/pages/questions this month
  - Progress bars for quota usage
  - Permission status alerts
  - Dynamic display based on user role

### 4. Audit Logging Integration
Updated admin APIs:
- `src/app/api/admin/grant-permission/route.ts` - Logs permission grants
- `src/app/api/admin/revoke-permission/route.ts` - Logs permission revocations
- `src/app/api/admin/set-quota/route.ts` - Logs quota changes

### 5. Usage Meter Integration
- **File:** `src/app/api/worksheets/generate-v2/route.ts`
- **Features:**
  - Quota checking before worksheet generation
  - Automatic usage tracking after successful generation
  - Audit logging of worksheet creation events
  - 429 Too Many Requests response when quota exceeded

## 📋 Migration Steps

### Step 1: Apply Database Migration (REQUIRED)

**Option A: Supabase Dashboard (Recommended)**
1. Go to https://supabase.com/dashboard
2. Select your project
3. Navigate to: **SQL Editor**
4. Click: **New Query**
5. Open file: `supabase/migrations/02_phase1_security.sql`
6. Copy the entire contents
7. Paste into the SQL Editor
8. Click: **Run** (bottom right)

**Expected Output:**
```
Success. 4 rows returned.
```

**Option B: Using psql (Advanced)**
```bash
# Get your database password from Supabase Dashboard → Settings → Database
psql -h tybaetnvnfgniotdfxze.supabase.co -p 5432 -d postgres -U postgres -f supabase/migrations/02_phase1_security.sql
```

### Step 2: Verify Migration Success

Run this query in SQL Editor:
```sql
-- Check if new tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('user_sessions', 'trusted_devices', 'audit_log', 'usage_meters');
```

**Expected:** Should return 4 rows

Check if functions exist:
```sql
SELECT routine_name 
FROM information_schema.routines 
WHERE routine_schema = 'public' 
  AND routine_name IN (
    'get_active_sessions_count',
    'get_current_month_usage',
    'increment_usage_meter',
    'create_audit_log_entry',
    'cleanup_expired_sessions'
  );
```

**Expected:** Should return 5 rows

### Step 3: Test New Features

#### Test 1: Dashboard Usage Stats
1. Navigate to: http://localhost:3002/dashboard
2. **Expected:**
   - If you've generated worksheets, you'll see a usage stats banner
   - Shows worksheets/pages/questions generated this month
   - Progress bar if quota is set

#### Test 2: Generate Worksheet with Usage Tracking
1. Navigate to: http://localhost:3002/generate
2. Generate a worksheet
3. **Expected:**
   - Worksheet generates successfully
   - Dashboard updates with new usage stats
   - Audit log entry created

#### Test 3: Verify Audit Logging

Run in SQL Editor:
```sql
SELECT 
  event_type,
  event_category,
  actor_email,
  target_resource_type,
  status,
  created_at
FROM audit_log
ORDER BY created_at DESC
LIMIT 10;
```

**Expected:** See recent events:
- `worksheet.generated` - When you generate worksheets
- `permission.granted` - When admin grants permission
- `permission.revoked` - When admin revokes permission
- `permission.quota_updated` - When admin sets quotas

#### Test 4: Usage Meters

Run in SQL Editor:
```sql
SELECT * FROM get_current_month_usage('YOUR_USER_ID_HERE');
```

**Expected:** Returns current month's usage:
```
worksheets_generated | pages_generated | questions_generated
---------------------|-----------------|--------------------
                  3 |              45 |                  45
```

#### Test 5: Quota Enforcement

1. Go to Admin Portal: http://localhost:3002/admin
2. Set your quota to 1 worksheet per day
3. Try generating 2 worksheets
4. **Expected:**
   - First generates successfully
   - Second returns error: "Monthly worksheet limit reached (30/30)"
   - Audit log shows quota_exceeded event

### Step 4: Set Up Admin Roles (Optional)

If you want to assign roles to users:

```sql
-- Set a user as teacher
UPDATE user_profiles
SET role_type = 'teacher'
WHERE user_id = 'USER_ID_HERE';

-- Set a user as org_admin
UPDATE user_profiles
SET role_type = 'org_admin'
WHERE user_id = 'USER_ID_HERE';
```

Available roles:
- `student` (default)
- `teacher`
- `org_admin`
- `org_owner`
- `support`
- `billing_admin`

## 🔍 Monitoring & Verification

### Check Audit Log Integrity

Run this to verify the hash chain is intact:
```sql
WITH RECURSIVE chain AS (
  SELECT 
    id,
    event_type,
    previous_hash,
    current_hash,
    created_at,
    ROW_NUMBER() OVER (ORDER BY created_at) as rn
  FROM audit_log
  ORDER BY created_at
)
SELECT 
  c1.id,
  c1.event_type,
  c1.previous_hash,
  c1.current_hash,
  c2.current_hash as expected_previous_hash,
  CASE 
    WHEN c1.previous_hash = c2.current_hash OR c1.rn = 1 
    THEN 'OK' 
    ELSE 'BROKEN' 
  END as chain_status
FROM chain c1
LEFT JOIN chain c2 ON c2.rn = c1.rn - 1
ORDER BY c1.created_at;
```

All rows should show `chain_status = 'OK'`.

### Monitor Usage Across All Users

```sql
SELECT 
  up.user_id,
  up.role_type,
  um.worksheets_generated,
  um.pages_generated,
  um.questions_generated,
  perm.max_worksheets_per_day,
  (perm.max_worksheets_per_day * 30) as max_per_month,
  ROUND((um.worksheets_generated::numeric / NULLIF(perm.max_worksheets_per_day * 30, 0)) * 100, 2) as usage_pct
FROM user_profiles up
LEFT JOIN usage_meters um ON up.user_id = um.user_id 
  AND um.period_start = DATE_TRUNC('month', CURRENT_DATE)::DATE
LEFT JOIN user_permissions perm ON up.user_id = perm.user_id
WHERE um.worksheets_generated > 0
ORDER BY um.worksheets_generated DESC;
```

## 🚨 Troubleshooting

### Issue: Migration fails with "relation already exists"
**Solution:** Tables were already created. Run:
```sql
DROP TABLE IF EXISTS user_sessions, trusted_devices, audit_log, usage_meters CASCADE;
```
Then re-run the migration.

### Issue: Dashboard doesn't show usage stats
**Possible causes:**
1. Migration not applied (tables don't exist)
2. No worksheets generated yet (normal)
3. User not authenticated

**Debug:**
```sql
-- Check if function exists
SELECT get_current_month_usage('YOUR_USER_ID');

-- Check if usage_meters table has data
SELECT * FROM usage_meters WHERE user_id = 'YOUR_USER_ID';
```

### Issue: Quota check fails
**Error:** `Could not find the table 'public.usage_meters'`

**Solution:** Migration not applied. Follow Step 1 above.

### Issue: Audit log not recording events
**Debug:**
```sql
-- Check if audit_log table exists
SELECT COUNT(*) FROM audit_log;

-- Check if create_audit_log_entry function exists
SELECT create_audit_log_entry(
  'test.event',
  'test',
  NULL,
  NULL,
  NULL,
  NULL,
  NULL,
  NULL,
  '127.0.0.1',
  NULL,
  NULL,
  '{}',
  'success',
  NULL
);
```

If function doesn't exist, re-run migration.

## 📊 What's Next

Phase 1 is now complete! Here's what you can do:

### Immediate Actions:
1. ✅ Apply the migration (Step 1)
2. ✅ Test all features (Step 3)
3. ✅ Set up user roles if needed (Step 4)

### Future Enhancements (Phase 2+):
- Session management UI (view/revoke active sessions)
- Trusted devices UI
- Admin audit log viewer
- WebAuthn/Passkeys authentication
- Multi-tenant organizations
- Role-based access control (ReBAC)

## 📝 Summary of Changes

**Database:**
- 4 new tables (sessions, devices, audit_log, usage_meters)
- 5 new functions
- RLS policies for security
- role_type column added to user_profiles

**Backend:**
- AuditLogger service (237 lines)
- UsageMeterService (179 lines)
- Audit logging in all admin APIs
- Usage tracking in worksheet generation
- Quota enforcement

**Frontend:**
- Dashboard improvements with usage stats
- Permission status alerts
- Progress bars for quota usage

**Files Modified:**
- `src/app/dashboard/page.tsx` - Usage stats display
- `src/app/api/admin/grant-permission/route.ts` - Audit logging
- `src/app/api/admin/revoke-permission/route.ts` - Audit logging
- `src/app/api/admin/set-quota/route.ts` - Audit logging
- `src/app/api/worksheets/generate-v2/route.ts` - Usage tracking + quota checks

**Files Created:**
- `supabase/migrations/02_phase1_security.sql` - Migration
- `src/lib/auditLogger.ts` - Audit logging service
- `src/lib/usageMeter.ts` - Usage tracking service

## ✨ Features Summary

### Session Tracking
- Track active user sessions with device info
- IP address, user agent, platform detection
- Session expiry management
- Remember me functionality

### Device Management
- Device fingerprinting
- Trusted device tracking
- Platform/browser/OS detection
- Trust management

### Audit Logging
- Tamper-evident hash chain
- Event categories: auth, permission, worksheet, admin, security
- Comprehensive event types (login, logout, permission changes, etc.)
- IP address tracking
- Integrity verification

### Usage Meters
- Track worksheets/pages/questions per month
- Automatic quota enforcement
- Percentage calculations
- Days remaining in month

### Roles
- Student (default)
- Teacher
- Org Admin
- Org Owner
- Support
- Billing Admin

---

**Need Help?**
Check the troubleshooting section above or examine the migration file comments for detailed documentation.

**Status:** ✅ Code complete, awaiting database migration
