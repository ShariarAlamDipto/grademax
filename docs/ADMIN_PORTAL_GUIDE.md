# 👑 Admin Portal Guide

## Overview
The Admin Portal provides a beautiful, easy-to-use interface for managing user permissions without needing to use command-line scripts.

## Features

### 📊 Dashboard Overview
- **Total Users**: See how many users have signed up
- **Approved Users**: Count of users with worksheet generation permission
- **Pending Approval**: Users waiting for permission

### 👥 User Management Table
View all users with:
- Email and full name
- Institution and role
- Permission status (Granted/Denied/Not Configured)
- Daily quota (if set)
- Join date
- Quick action buttons

### ⚡ Quick Actions
**For each user, you can:**

1. **Grant Permission** ✅
   - Click "Grant" button
   - Optionally add admin notes
   - Instant approval

2. **Revoke Permission** ❌
   - Click "Revoke" button
   - Confirm action
   - User loses access immediately

3. **Set Quota** 📊
   - Click "Set Quota" button
   - Enter max worksheets per day
   - Set 0 for unlimited

4. **View Details** 👁️
   - Click on any user row
   - See complete profile
   - View generation history
   - See all past worksheets generated

## How to Access

### URL
Navigate to: **http://localhost:3000/admin**

Or click the **👑 Admin** link in the navbar.

## Usage Guide

### Approving New Users

1. **User signs up** → They appear in the admin portal with "Pending Approval" status
2. **Click "Grant" button** for their row
3. **Optionally add notes** (e.g., "Approved for school project")
4. **Click "Grant Permission"**
5. **User can now generate worksheets!** ✅

### Setting Quotas

1. **Click "Set Quota"** for any user
2. **Enter limit:**
   - `10` = 10 worksheets per day
   - `0` = Unlimited
3. **Click "Save Quota"**
4. Quota resets daily at midnight

### Revoking Access

1. **Click "Revoke"** for the user
2. **Confirm** in the dialog
3. User loses access immediately
4. Can be re-granted later

### Viewing User Activity

1. **Click on any user row** in the table
2. **See modal with:**
   - Full profile information
   - Complete generation history
   - Success/failure status
   - Topics and subjects used
   - Timestamps

## API Endpoints

The admin portal uses these endpoints:

- `GET /api/admin/users` - List all users
- `POST /api/admin/grant-permission` - Grant access
- `POST /api/admin/revoke-permission` - Revoke access
- `POST /api/admin/set-quota` - Set daily limit
- `GET /api/admin/logs?userId=xxx` - Get user's generation history

## Security

### Who Can Access?
Currently, the admin portal is publicly accessible. You should add authentication:

```typescript
// Add to src/app/admin/page.tsx
useEffect(() => {
  // Check if user is admin
  async function checkAdmin() {
    const response = await fetch('/api/admin/check-auth');
    if (!response.ok) {
      router.push('/login');
    }
  }
  checkAdmin();
}, []);
```

### Protection Recommendations

1. **Add Admin Role Check**
   - Update `user_profiles` to have `role` field
   - Set your account role to "admin"
   - Check role in admin API endpoints

2. **Create Admin Check Middleware**
   ```typescript
   // Only allow users with role === 'admin'
   const profile = await supabase
     .from('user_profiles')
     .select('role')
     .eq('user_id', userId)
     .single();
   
   if (profile.data?.role !== 'admin') {
     return NextResponse.json({ error: 'Unauthorized' }, { status: 403 });
   }
   ```

3. **Add to .env.local**
   ```bash
   ADMIN_EMAILS=your-email@gmail.com,another-admin@gmail.com
   ```

## UI Features

### Color-Coded Status
- 🟢 **Green**: Permission granted
- 🔴 **Red**: Permission denied
- 🟡 **Yellow**: Inactive
- ⚪ **Gray**: Not configured

### Real-time Updates
- All actions update the UI immediately
- No page refresh needed
- Success/error messages show at top

### Responsive Design
- Works on desktop, tablet, and mobile
- Table scrolls horizontally on small screens
- Modals are mobile-friendly

### Keyboard Shortcuts
- `Esc` - Close modals
- Click outside modal - Close

## Comparison: Admin Portal vs CLI Script

| Feature | Admin Portal | CLI Script |
|---------|-------------|------------|
| **Ease of Use** | ✅ Very Easy | ⚠️ Technical |
| **Speed** | ✅ 1 click | ⚠️ Type command |
| **User Search** | ✅ Visual table | ❌ Must know email |
| **History View** | ✅ Built-in | ❌ Separate command |
| **Bulk Actions** | ⚠️ Coming soon | ❌ One at a time |
| **Mobile Friendly** | ✅ Yes | ❌ Desktop only |
| **Real-time** | ✅ Yes | ⚠️ Manual refresh |

## Tips

### Quick Approval Workflow
1. Open admin portal in one tab
2. Tell users to sign up
3. Refresh admin portal
4. Click "Grant" for each new user
5. Done! ✨

### Managing Multiple Users
- Sort by join date to see newest first
- Use browser search (Ctrl+F) to find specific email
- Check "Pending Approval" count for quick triage

### Monitoring Usage
- Click on power users to see their history
- Check for errors in generation logs
- Adjust quotas based on usage patterns

## Troubleshooting

### "Failed to fetch users"
**Cause**: Database connection issue or RLS policy blocking

**Fix**:
1. Check `.env.local` has `SUPABASE_SERVICE_ROLE_KEY`
2. Verify migration was applied
3. Check Supabase logs in dashboard

### Changes not showing
**Cause**: Caching or stale data

**Fix**:
1. Hard refresh (Ctrl + Shift + R)
2. Clear browser cache
3. Check browser console for errors

### Permission granted but user still denied
**Cause**: User needs to refresh their page

**Fix**:
1. Tell user to refresh `/generate` page
2. Or log out and log back in
3. Check RLS policies allow user to read own permissions

## Future Enhancements

### Planned Features
- [ ] Bulk approve multiple users
- [ ] Search and filter users
- [ ] Email notifications when approved
- [ ] Usage analytics dashboard
- [ ] Export user data to CSV
- [ ] Admin activity log
- [ ] Role-based access (super admin, moderator)
- [ ] Custom permission levels
- [ ] Temporary access (expires after X days)

### Want to Add a Feature?
The admin portal code is in:
- Frontend: `src/app/admin/page.tsx`
- API: `src/app/api/admin/*`

## Summary

The Admin Portal makes user management **fast and easy**:

✅ Visual interface - No command line needed  
✅ One-click approval - Grant permission instantly  
✅ Real-time updates - See changes immediately  
✅ User history - Track all activity  
✅ Quota management - Set limits easily  
✅ Mobile friendly - Manage on any device  

**You can now manage your users like a pro!** 👑
