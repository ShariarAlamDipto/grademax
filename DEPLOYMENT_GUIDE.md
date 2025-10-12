# 🚀 Vercel Deployment Guide for GradeMax

## 📋 Pre-Deployment Checklist

### ✅ Changes Ready
- [x] PDF download route refactored (Python → JavaScript with pdf-lib)
- [x] PDF preview iframes added
- [x] Environment variables configured
- [x] Database connected (Supabase PostgreSQL)
- [x] Git committed (1 commit ahead of origin/main)

---

## 🔧 Step-by-Step Deployment

### Step 1: Push to GitHub

```powershell
# Push your committed changes to GitHub
git push origin main
```

This will push your latest changes (including the PDF download fix) to GitHub.

---

### Step 2: Deploy to Vercel

#### Option A: **Automatic Deployment** (Recommended)
If you already have Vercel connected to this GitHub repo:

1. **Vercel will automatically detect the push** and start deploying
2. Go to your Vercel dashboard: https://vercel.com/dashboard
3. Click on your **grademax** project
4. You'll see the deployment in progress
5. Wait for it to complete (usually 1-3 minutes)

#### Option B: **Manual Deployment via CLI**

If you have Vercel CLI installed:

```powershell
# Install Vercel CLI (if not installed)
npm i -g vercel

# Deploy to production
vercel --prod
```

#### Option C: **Manual Deployment via Dashboard**

1. Go to https://vercel.com/dashboard
2. Click on your **grademax** project
3. Click **"Deployments"** tab
4. Click **"Redeploy"** on the latest deployment
5. Or click **"Deploy"** → Connect to GitHub (if not connected)

---

### Step 3: Configure Environment Variables in Vercel

⚠️ **CRITICAL**: Vercel needs the same environment variables as your local `.env.local`

#### How to Add Environment Variables:

1. Go to your Vercel dashboard: https://vercel.com/dashboard
2. Click on your **grademax** project
3. Click **"Settings"** tab
4. Click **"Environment Variables"** in the sidebar
5. Add these variables:

**Required Environment Variables:**

| Variable Name | Value | Environment |
|---------------|-------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://tybaetnvnfgniotdfxze.supabase.co` | Production, Preview, Development |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `eyJhbGc...BAYes` (from your .env.local) | Production, Preview, Development |

**How to Add Each Variable:**

```
1. Click "Add New"
2. Name: NEXT_PUBLIC_SUPABASE_URL
3. Value: https://tybaetnvnfgniotdfxze.supabase.co
4. Select: Production, Preview, Development (all three)
5. Click "Save"

Repeat for NEXT_PUBLIC_SUPABASE_ANON_KEY
```

⚠️ **Note**: After adding environment variables, you MUST redeploy:
- Click **"Deployments"** tab
- Click **"..."** menu on latest deployment
- Click **"Redeploy"**

---

### Step 4: Verify Deployment

Once deployment completes:

1. **Check Deployment URL**:
   - Vercel will show you the deployment URL (e.g., `https://grademax-xyz.vercel.app`)
   - Click on it to open your live site

2. **Test the Application**:
   - ✅ Homepage loads
   - ✅ Navigate to `/generate`
   - ✅ Select topics and generate worksheet
   - ✅ Click "Download PDFs" button
   - ✅ Verify PDFs download correctly
   - ✅ Check PDF previews display

3. **Check Vercel Logs** (if issues):
   - Go to Vercel dashboard → Your project
   - Click **"Deployments"** → Click the deployment
   - Click **"Functions"** tab to see logs
   - Check for any errors

---

## 🔍 Common Issues & Solutions

### Issue 1: "Build Failed"

**Cause**: TypeScript errors or missing dependencies

**Solution**:
```powershell
# Test build locally first
npm run build

# If it works locally, check Vercel build logs
```

### Issue 2: Environment Variables Not Working

**Symptoms**: 
- "Invalid API key" errors
- Database connection fails
- Supabase errors

**Solution**:
1. Verify variables are set in Vercel settings
2. Make sure they're enabled for "Production"
3. Redeploy after adding variables
4. Check variable names match EXACTLY (including `NEXT_PUBLIC_` prefix)

### Issue 3: PDF Download Fails in Production

**Cause**: Supabase Storage bucket not publicly accessible

**Solution**:
1. Go to Supabase dashboard: https://supabase.com/dashboard
2. Navigate to **Storage** → `question-pdfs` bucket
3. Click bucket settings (gear icon)
4. Ensure **"Public bucket"** is enabled
5. Check bucket policies allow public read access

### Issue 4: Pages Not Found (404)

**Cause**: Next.js routing configuration

**Solution**:
- Vercel should auto-detect Next.js configuration
- Check `next.config.ts` is committed to Git
- Verify all page files are in `src/app/` directory

---

## 📦 What Gets Deployed

### Included in Deployment:
✅ All frontend code (`src/app/`, `src/components/`)
✅ API routes (`src/app/api/`)
✅ Public assets (`public/`)
✅ Configuration files (`next.config.ts`, `tsconfig.json`, etc.)
✅ Dependencies from `package.json`

### NOT Included in Deployment:
❌ `.env.local` (must be set in Vercel dashboard)
❌ `.env.ingest` (only needed for local Python scripts)
❌ `scripts/` folder (Python scripts run locally only)
❌ `data/` folder (raw PDF files)
❌ `node_modules/` (rebuilt by Vercel)

---

## 🎯 Deployment Architecture

```
GitHub Repo (origin/main)
    ↓
Vercel Auto-Deploy
    ↓
Build Next.js App
    ↓
Deploy to Vercel Edge Network
    ↓
Your Live App (https://grademax-xyz.vercel.app)
    ↓
Connects to Supabase (database + storage)
```

---

## ⚡ Quick Deploy Commands

```powershell
# 1. Push to GitHub (triggers auto-deploy)
git push origin main

# 2. Or use Vercel CLI for immediate deploy
vercel --prod

# 3. Check deployment status
vercel ls
```

---

## 🔐 Security Checklist

Before deploying, ensure:

- ✅ `.env.local` is NOT committed to Git (it's in `.gitignore`)
- ✅ `.env.ingest` is NOT committed to Git (contains service role key)
- ✅ Only `NEXT_PUBLIC_*` variables are accessible to frontend
- ✅ Supabase service role key is NOT exposed (only used in local Python scripts)
- ✅ Database connection uses connection pooler (IPv4 compatible)

---

## 📊 Post-Deployment Monitoring

### Check These After Deploy:

1. **Vercel Analytics** (if enabled):
   - Go to Vercel dashboard → Your project → "Analytics"
   - Check page load times
   - Monitor user traffic

2. **Vercel Logs**:
   - Dashboard → Deployments → Click deployment → "Functions"
   - Check for API route errors
   - Look for PDF generation issues

3. **Supabase Metrics**:
   - Supabase dashboard → "Database" → "Logs"
   - Check query performance
   - Monitor storage usage

---

## 🎉 Success Criteria

Your deployment is successful when:

✅ Vercel build completes without errors
✅ Site loads at your Vercel URL
✅ You can navigate to `/generate`
✅ Topics load from database
✅ Worksheet generation works
✅ PDF download works
✅ PDF preview displays
✅ No console errors in browser

---

## 🆘 Need Help?

### Vercel Support:
- Documentation: https://vercel.com/docs
- Support: https://vercel.com/help

### Supabase Support:
- Documentation: https://supabase.com/docs
- Discord: https://discord.supabase.com

### Check Your Deployment:
```powershell
# View deployment details
vercel ls

# View logs in real-time
vercel logs [deployment-url]
```

---

## 📝 Deployment History

Keep track of your deployments:

| Date | Changes | URL | Status |
|------|---------|-----|--------|
| Oct 12, 2025 | PDF download fix, Preview iframes | TBD | Pending |

---

## 🔄 Future Deployments

For future updates:

```powershell
# 1. Make changes locally
# 2. Test locally (npm run dev)
# 3. Commit changes
git add .
git commit -m "Your change description"

# 4. Push to GitHub (triggers auto-deploy)
git push origin main

# 5. Monitor deployment in Vercel dashboard
```

That's it! Vercel handles the rest automatically! 🚀
