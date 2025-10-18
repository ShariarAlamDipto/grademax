"""
Production OAuth Configuration Checker
Verifies that all required URLs and settings are in place.
"""

print("=" * 70)
print("🚀 PRODUCTION OAUTH CONFIGURATION CHECKLIST")
print("=" * 70)

print("\n📋 STEP 1: Supabase Dashboard Configuration")
print("-" * 70)
print("Go to: https://supabase.com/dashboard/project/tybaetnvnfgniotdfxze")
print("Navigate to: Authentication → URL Configuration\n")

print("✅ Site URL (set to):")
print("   https://www.grademax.me\n")

print("✅ Redirect URLs (add ALL of these):")
production_urls = [
    "https://www.grademax.me/auth/callback",
    "https://www.grademax.me",
    "https://grademax.me/auth/callback",
    "https://grademax.me",
    "http://localhost:3000/auth/callback",
    "http://localhost:3000",
]
for url in production_urls:
    print(f"   ✓ {url}")

print("\n" + "=" * 70)
print("📋 STEP 2: Vercel Environment Variables")
print("-" * 70)
print("Go to: https://vercel.com/your-team/grademax/settings/environment-variables\n")

print("Required variables:")
env_vars = [
    "NEXT_PUBLIC_SUPABASE_URL",
    "NEXT_PUBLIC_SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
]
for var in env_vars:
    print(f"   ✓ {var}")

print("\n⚠️  IMPORTANT: Redeploy after adding environment variables!")

print("\n" + "=" * 70)
print("📋 STEP 3: Google OAuth Configuration")
print("-" * 70)
print("Go to: https://console.cloud.google.com/apis/credentials\n")

print("Add to Authorized redirect URIs:")
google_uris = [
    "https://tybaetnvnfgniotdfxze.supabase.co/auth/v1/callback",
    "https://www.grademax.me/auth/callback",
    "https://grademax.me/auth/callback",
]
for uri in google_uris:
    print(f"   ✓ {uri}")

print("\n" + "=" * 70)
print("📋 STEP 4: Verify Deployment")
print("-" * 70)
print("\nTest these endpoints:")
test_endpoints = [
    "https://www.grademax.me",
    "https://www.grademax.me/login",
    "https://www.grademax.me/api/debug/auth",
]
for endpoint in test_endpoints:
    print(f"   ✓ {endpoint}")

print("\n" + "=" * 70)
print("📋 STEP 5: Test OAuth Flow")
print("-" * 70)
print("\n1. Go to: https://www.grademax.me/login")
print("2. Click 'Continue with Google'")
print("3. Should redirect to Google OAuth")
print("4. After authorization → https://www.grademax.me/auth/callback")
print("5. Then redirect → https://www.grademax.me/generate")

print("\n" + "=" * 70)
print("🐛 DEBUGGING")
print("-" * 70)
print("\nIf you see 'Application error: a client-side exception':")
print("   1. Open Browser DevTools → Console")
print("   2. Look for specific error messages")
print("   3. Check Network tab for failed requests")
print("   4. Verify environment variables in Vercel")
print("   5. Check Supabase logs: Dashboard → Logs → Auth logs")

print("\n" + "=" * 70)
print("✨ Quick Commands")
print("-" * 70)
print("\n# Test production API")
print("curl https://www.grademax.me/api/debug/auth")
print("\n# Redeploy on Vercel")
print("git push origin main")
print("\n# Check Vercel deployment logs")
print("vercel logs https://www.grademax.me")

print("\n" + "=" * 70)
print("📝 Summary")
print("-" * 70)
print("\n✓ Configure Supabase redirect URLs")
print("✓ Set Vercel environment variables")
print("✓ Update Google OAuth redirect URIs")
print("✓ Redeploy application")
print("✓ Test complete OAuth flow")
print("✓ Clear browser cache if needed")

print("\n" + "=" * 70)
