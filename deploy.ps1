# 🚀 Quick Deploy to Vercel

Write-Host "🚀 GradeMax - Vercel Deployment Script" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Git Status
Write-Host "📊 Checking Git status..." -ForegroundColor Yellow
git status
Write-Host ""

# Step 2: Test Build
Write-Host "🔨 Testing production build locally..." -ForegroundColor Yellow
Write-Host "This ensures the build will succeed on Vercel" -ForegroundColor Gray
npm run build
$buildResult = $LASTEXITCODE

if ($buildResult -ne 0) {
    Write-Host ""
    Write-Host "❌ Build failed! Fix errors before deploying." -ForegroundColor Red
    Write-Host "Check the error messages above and fix them." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Build successful!" -ForegroundColor Green
Write-Host ""

# Step 3: Confirm Deployment
Write-Host "📤 Ready to deploy to Vercel!" -ForegroundColor Cyan
Write-Host ""
Write-Host "Changes to be deployed:" -ForegroundColor Yellow
Write-Host "  ✅ PDF download route refactored (Python → JavaScript)" -ForegroundColor Green
Write-Host "  ✅ PDF preview iframes added" -ForegroundColor Green
Write-Host "  ✅ Using pdf-lib for PDF merging" -ForegroundColor Green
Write-Host ""

$confirm = Read-Host "Do you want to push to GitHub and deploy? (yes/no)"

if ($confirm -eq "yes" -or $confirm -eq "y") {
    Write-Host ""
    Write-Host "🚀 Pushing to GitHub..." -ForegroundColor Yellow
    git push origin main
    
    Write-Host ""
    Write-Host "✅ Pushed to GitHub!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Next Steps:" -ForegroundColor Cyan
    Write-Host "  1. Go to https://vercel.com/dashboard" -ForegroundColor White
    Write-Host "  2. Click on your 'grademax' project" -ForegroundColor White
    Write-Host "  3. Wait for automatic deployment to complete (1-3 minutes)" -ForegroundColor White
    Write-Host "  4. Click the deployment URL to test your live site" -ForegroundColor White
    Write-Host ""
    Write-Host "⚠️  IMPORTANT: Verify Environment Variables" -ForegroundColor Yellow
    Write-Host "  Make sure these are set in Vercel → Settings → Environment Variables:" -ForegroundColor Gray
    Write-Host "    - NEXT_PUBLIC_SUPABASE_URL" -ForegroundColor Gray
    Write-Host "    - NEXT_PUBLIC_SUPABASE_ANON_KEY" -ForegroundColor Gray
    Write-Host ""
    Write-Host "🎉 Deployment initiated! Check Vercel dashboard for progress." -ForegroundColor Green
    
} else {
    Write-Host ""
    Write-Host "❌ Deployment cancelled." -ForegroundColor Red
    Write-Host "Run this script again when you're ready to deploy." -ForegroundColor Gray
}

Write-Host ""
Write-Host "📖 For detailed deployment guide, see: DEPLOYMENT_GUIDE.md" -ForegroundColor Cyan
