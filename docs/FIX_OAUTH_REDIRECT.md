# Fix Supabase OAuth Redirect URL Configuration

## Problem
OAuth callback is redirecting to `localhost:3001` instead of `localhost:3000`.

## Solution

### 1. Update Supabase Project Settings

Go to your Supabase Dashboard:
1. Navigate to: https://supabase.com/dashboard/project/tybaetnvnfgniotdfxze
2. Go to **Authentication** → **URL Configuration**
3. Update the following fields:

**Site URL:**
```
http://localhost:3000
```

**Redirect URLs:** (Add all these)
```
http://localhost:3000/auth/callback
http://localhost:3000
https://grademax.vercel.app/auth/callback
https://grademax.vercel.app
https://*.vercel.app/auth/callback
```

### 2. Check Environment Variables

Make sure your `.env.local` has the correct URL:
```bash
NEXT_PUBLIC_SUPABASE_URL=https://tybaetnvnfgniotdfxze.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### 3. Clear Browser Cache

After updating Supabase settings:
1. Clear your browser cookies for localhost
2. Restart your dev server: `npm run dev`
3. Try signing in again

## Why This Happens

- Supabase caches redirect URLs based on project settings
- If you previously had localhost:3001 configured, it remembers that
- The OAuth provider (Google) also caches the redirect URI
- Must update in Supabase dashboard for changes to take effect

## Testing

After fixing:
1. Go to http://localhost:3000/login
2. Click "Continue with Google"
3. Should redirect to Google OAuth
4. After authorization, should return to http://localhost:3000/auth/callback
5. Then redirect to http://localhost:3000/generate
