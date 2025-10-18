# Authentication Setup Guide

## Overview
This guide will help you set up the authentication and permission system for worksheet generation.

## Step 1: Apply Database Migration

### Option A: Using Supabase CLI (Recommended)
```powershell
# Navigate to project root
cd c:\Users\shari\grademax

# Push migration to Supabase
supabase db push
```

### Option B: Manual Application via Supabase Dashboard
1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Open the file `supabase/migrations/01_user_permissions.sql`
4. Copy the entire contents
5. Paste into the SQL Editor
6. Click **Run** to execute the migration

### Verify Migration Success
After running the migration, verify the tables were created:

```sql
-- Run this in Supabase SQL Editor
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('user_permissions', 'user_profiles', 'worksheet_generation_logs');
```

You should see all 3 tables listed.

## Step 2: Install Python Dependencies

The permission management script requires the Supabase Python client:

```powershell
pip install supabase
```

## Step 3: Test Authentication Flow

### 3.1 Sign Up a Test User
1. Start your Next.js dev server (if not running):
   ```powershell
   npm run dev
   ```

2. Navigate to http://localhost:3000/login

3. Click "Sign in with Google"

4. Complete the Google OAuth flow

5. After signing in, you'll be redirected to the app

### 3.2 Verify User Profile Created
Check in Supabase dashboard:

```sql
SELECT * FROM user_profiles ORDER BY created_at DESC LIMIT 5;
SELECT * FROM user_permissions ORDER BY created_at DESC LIMIT 5;
```

You should see:
- Your email in `user_profiles`
- A matching entry in `user_permissions` with `can_generate_worksheets = FALSE`

### 3.3 Try Accessing Generate Page
1. Navigate to http://localhost:3000/generate

2. You should see a red **"Access Restricted"** banner

3. The generate button should be disabled

This confirms the permission check is working! ✅

## Step 4: Grant Permission to User

### Using the Management Script

```powershell
# List all users
python scripts/manage_permissions.py list

# Grant permission to a specific user
python scripts/manage_permissions.py grant your-email@gmail.com

# Set a daily quota (optional)
python scripts/manage_permissions.py quota your-email@gmail.com 10

# View logs
python scripts/manage_permissions.py logs
```

### Manual via SQL (Alternative)

```sql
-- Grant permission to a user
UPDATE user_permissions
SET can_generate_worksheets = TRUE,
    is_active = TRUE,
    permission_granted_at = NOW(),
    notes = 'Manual approval'
WHERE user_id = (
  SELECT user_id FROM user_profiles WHERE email = 'your-email@gmail.com'
);
```

## Step 5: Verify Permission Granted

1. Refresh the `/generate` page

2. You should now see a green **"Access Granted"** banner

3. The generate button should be enabled

4. You can now generate worksheets! 🎉

## Management Script Usage

### List All Users
```powershell
python scripts/manage_permissions.py list
```

Output:
```
📋 User Permissions List
================================================================================

user1@gmail.com
  Name: John Doe
  Role: student
  Can Generate: ✅ Yes
  Active: ✅
  Daily Quota: 10

user2@gmail.com
  Name: Jane Smith
  Role: teacher
  Can Generate: ❌ No
  Active: ✅
  Daily Quota: N/A
```

### Grant Permission
```powershell
# Basic grant
python scripts/manage_permissions.py grant user@email.com

# Grant with admin tracking
python scripts/manage_permissions.py grant user@email.com admin@email.com
```

### Revoke Permission
```powershell
python scripts/manage_permissions.py revoke user@email.com
```

### Set Daily Quota
```powershell
# Set quota to 10 worksheets per day
python scripts/manage_permissions.py quota user@email.com 10

# Set unlimited (0 = no limit)
python scripts/manage_permissions.py quota user@email.com 0
```

### View Generation Logs
```powershell
# View last 20 logs for all users
python scripts/manage_permissions.py logs

# View last 50 logs for specific user
python scripts/manage_permissions.py logs user@email.com 50
```

## Database Schema Overview

### `user_profiles`
Stores extended user information:
- `user_id`: References `auth.users(id)`
- `email`: User's email
- `full_name`: Display name
- `institution`: School/organization
- `role`: "student", "teacher", "admin"

### `user_permissions`
Controls worksheet generation access:
- `user_id`: References `auth.users(id)`
- `can_generate_worksheets`: Boolean flag (default: FALSE)
- `is_active`: Can temporarily disable without revoking
- `max_worksheets_per_day`: Daily quota (NULL = unlimited)
- `max_questions_per_worksheet`: Max questions per worksheet
- `permission_granted_by`: Admin who granted permission
- `notes`: Admin notes

### `worksheet_generation_logs`
Audit trail of all generation attempts:
- `user_id`: Who generated
- `worksheet_id`: Reference to worksheet
- `subject_code`: Which subject
- `topics`: Selected topics
- `status`: "success", "error", "permission_denied"
- `questions_generated`: Number of questions
- `generated_at`: Timestamp

## Security Features

### Row Level Security (RLS)
- ✅ Users can only view their own permissions and profile
- ✅ Only service_role can grant/revoke permissions
- ✅ All tables have RLS enabled
- ✅ Audit logs are read-only for users

### Automatic Triggers
- ✅ New users automatically get profile created
- ✅ Default permission is DENIED (must be manually approved)
- ✅ Timestamps auto-update on changes

### API Protection
- ✅ Permission check before worksheet generation
- ✅ Quota enforcement (daily limit)
- ✅ All attempts logged for audit

## Troubleshooting

### "No users found" after sign up
**Problem:** User profile not created automatically

**Solution:**
1. Check if trigger exists:
   ```sql
   SELECT * FROM pg_trigger WHERE tgname = 'on_auth_user_created';
   ```

2. Manually create profile:
   ```sql
   INSERT INTO user_profiles (user_id, email, full_name)
   SELECT id, email, raw_user_meta_data->>'full_name'
   FROM auth.users
   WHERE email = 'your-email@gmail.com'
   ON CONFLICT (user_id) DO NOTHING;
   
   INSERT INTO user_permissions (user_id, can_generate_worksheets)
   SELECT id, FALSE
   FROM auth.users
   WHERE email = 'your-email@gmail.com'
   ON CONFLICT (user_id) DO NOTHING;
   ```

### "Permission denied" even after granting
**Problem:** Cache or session issue

**Solutions:**
1. Hard refresh the page (Ctrl + Shift + R)
2. Clear browser cookies for localhost
3. Sign out and sign back in
4. Check in database:
   ```sql
   SELECT can_generate_worksheets, is_active
   FROM user_permissions
   WHERE user_id = (SELECT user_id FROM user_profiles WHERE email = 'your-email@gmail.com');
   ```

### Quota not updating
**Problem:** Daily quota stays at 0

**Solution:**
The quota resets automatically at midnight. To manually reset:
```sql
-- Quota is checked by counting logs from today
-- Just wait until next day, or clear old logs (not recommended)
```

### Script errors about missing Supabase credentials
**Problem:** Environment variables not set

**Solution:**
```powershell
# Set environment variables
$env:NEXT_PUBLIC_SUPABASE_URL = "your-supabase-url"
$env:SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"

# Or add to .env.local and load them
```

## Next Steps

### Implement Worksheet Generation Logging
Update `/api/worksheets/generate-v2` to log all generation attempts:

```typescript
// After successful generation
await supabase.from('worksheet_generation_logs').insert({
  user_id: userId,
  worksheet_id: worksheetId,
  subject_code: subjectCode,
  topics: selectedTopics,
  status: 'success',
  questions_generated: questions.length,
  generated_at: new Date().toISOString()
});
```

### Create Admin Dashboard
Build a UI at `/admin/permissions` for easier permission management (instead of using the script).

### Email Notifications
Send email when permission is granted:
- Use Supabase Edge Functions
- Trigger on `user_permissions` update
- Send welcome email with instructions

## Support

If you encounter issues:
1. Check Supabase logs in dashboard
2. Check browser console for errors
3. Verify environment variables are set
4. Ensure migration was applied successfully
5. Check RLS policies aren't blocking queries
