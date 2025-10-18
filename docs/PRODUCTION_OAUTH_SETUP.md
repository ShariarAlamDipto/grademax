# Production OAuth Setup for www.grademax.me

## Problem
Getting "Application error: a client-side exception has occurred" when trying to authenticate on production (www.grademax.me).

## Solution

### 1. Update Supabase Project Settings for Production

Go to your Supabase Dashboard:
1. Navigate to: https://supabase.com/dashboard/project/tybaetnvnfgniotdfxze
2. Go to **Authentication** → **URL Configuration**
3. Update the following fields:

#### Site URL (Primary):
```
https://www.grademax.me
```

#### Redirect URLs (Add ALL of these):
```
https://www.grademax.me/auth/callback
https://www.grademax.me
https://grademax.me/auth/callback
https://grademax.me
http://localhost:3000/auth/callback
http://localhost:3000
https://*.vercel.app/auth/callback
https://grademax-*.vercel.app/auth/callback
```

### 2. Update Vercel Environment Variables

Go to Vercel Dashboard:
1. Navigate to: https://vercel.com/your-team/grademax/settings/environment-variables
2. Make sure these are set:

```bash
NEXT_PUBLIC_SUPABASE_URL=https://tybaetnvnfgniotdfxze.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

3. **Redeploy** after adding environment variables

### 3. Configure Custom Domain in Supabase

If using custom domain (www.grademax.me):

1. In Supabase Dashboard → **Settings** → **API**
2. Under "API URL", verify it matches your production domain
3. Add custom domain to allowed origins

### 4. Google OAuth Configuration

You also need to update Google Cloud Console:

1. Go to: https://console.cloud.google.com/apis/credentials
2. Find your OAuth 2.0 Client ID
3. Under **Authorized redirect URIs**, add:
   ```
   https://tybaetnvnfgniotdfxze.supabase.co/auth/v1/callback
   https://www.grademax.me/auth/callback
   https://grademax.me/auth/callback
   ```

### 5. Verify DNS and SSL

Make sure:
- ✅ DNS A/CNAME records point to Vercel
- ✅ SSL certificate is active
- ✅ Both `grademax.me` and `www.grademax.me` work
- ✅ HTTPS is enforced

### 6. Test the Flow

After configuration:
1. Go to https://www.grademax.me/login
2. Click "Continue with Google"
3. Should redirect to Google OAuth
4. After authorization, returns to https://www.grademax.me/auth/callback
5. Then redirects to https://www.grademax.me/generate

## Common Issues

### Issue: "Application error: a client-side exception"
**Cause:** Missing environment variables or incorrect Supabase URL
**Fix:** 
- Check Vercel environment variables are set
- Redeploy after adding env vars
- Check browser console for specific error

### Issue: "Invalid redirect URI"
**Cause:** Redirect URL not whitelisted in Supabase
**Fix:** Add ALL production URLs to Supabase redirect URLs list

### Issue: "CORS error"
**Cause:** Domain not in Supabase allowed origins
**Fix:** Add production domain to Supabase CORS settings

### Issue: "Session not persisting"
**Cause:** Cookie domain mismatch
**Fix:** Ensure Site URL in Supabase matches your production domain exactly

## Debugging Steps

1. **Check Browser Console:**
   ```
   Open DevTools → Console tab
   Look for specific error messages
   ```

2. **Check Network Tab:**
   ```
   Filter for "supabase" or "auth"
   Look for failed requests
   Check response status codes
   ```

3. **Verify Environment Variables:**
   ```bash
   # In Vercel Dashboard
   Settings → Environment Variables
   Make sure all SUPABASE_* variables are set
   ```

4. **Test API Connectivity:**
   ```bash
   curl https://www.grademax.me/api/debug/auth
   # Should return auth status
   ```

## Quick Checklist

- [ ] Supabase Site URL = `https://www.grademax.me`
- [ ] All redirect URLs added to Supabase
- [ ] Environment variables set in Vercel
- [ ] Redeployed after env var changes
- [ ] Google OAuth redirect URIs updated
- [ ] DNS pointing to Vercel correctly
- [ ] SSL certificate active
- [ ] Tested login flow end-to-end

## Production URLs to Configure

Copy-paste these into Supabase Redirect URLs:

```
https://www.grademax.me/auth/callback
https://www.grademax.me
https://grademax.me/auth/callback
https://grademax.me
```

## After Setup

Once configured:
1. Clear browser cache
2. Try login again
3. Check that session persists after redirect
4. Test on different browsers
5. Test on mobile devices

## Support

If issues persist:
1. Check Supabase logs: Dashboard → Logs → Auth logs
2. Check Vercel deployment logs
3. Verify all URLs match exactly (no trailing slashes)
4. Ensure HTTPS is used everywhere
