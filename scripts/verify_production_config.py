"""
Comprehensive Production Configuration Checker
Verifies Supabase connectivity, environment variables, and deployment readiness.
"""
import os
import sys
from dotenv import load_dotenv
import requests

load_dotenv('.env.local')

print("=" * 70)
print("🔍 PRODUCTION CONFIGURATION VERIFICATION")
print("=" * 70)

all_checks_passed = True

# Check 1: Environment Variables
print("\n📋 CHECK 1: Local Environment Variables")
print("-" * 70)

env_vars = {
    'NEXT_PUBLIC_SUPABASE_URL': os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    'NEXT_PUBLIC_SUPABASE_ANON_KEY': os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY'),
    'SUPABASE_SERVICE_ROLE_KEY': os.getenv('SUPABASE_SERVICE_ROLE_KEY'),
}

for var_name, var_value in env_vars.items():
    if var_value:
        masked = var_value[:20] + '...' if len(var_value) > 20 else var_value
        print(f"✅ {var_name}: {masked}")
    else:
        print(f"❌ {var_name}: MISSING")
        all_checks_passed = False

# Check 2: Supabase Connectivity
print("\n📋 CHECK 2: Supabase Connectivity")
print("-" * 70)

supabase_url = env_vars['NEXT_PUBLIC_SUPABASE_URL']
if supabase_url:
    try:
        response = requests.get(f"{supabase_url}/rest/v1/", timeout=5)
        if response.status_code in [200, 401, 404]:  # Any of these means it's reachable
            print(f"✅ Supabase API reachable: {supabase_url}")
        else:
            print(f"⚠️  Supabase responded with status: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot reach Supabase: {str(e)}")
        all_checks_passed = False
else:
    print("❌ Supabase URL not configured")
    all_checks_passed = False

# Check 3: Supabase Configuration Status
print("\n📋 CHECK 3: Supabase Configuration Requirements")
print("-" * 70)
print("⚠️  MANUAL VERIFICATION REQUIRED:")
print("\n1. Supabase Dashboard Configuration:")
print("   URL: https://supabase.com/dashboard/project/tybaetnvnfgniotdfxze")
print("   → Authentication → URL Configuration")
print()
print("   ✓ Site URL should be: https://www.grademax.me")
print("   ✓ Redirect URLs should include:")
print("      - https://www.grademax.me/auth/callback")
print("      - https://www.grademax.me")
print("      - https://grademax.me/auth/callback")
print("      - https://grademax.me")
print("      - http://localhost:3000/auth/callback")
print("      - http://localhost:3000")

# Check 4: Google OAuth Configuration
print("\n📋 CHECK 4: Google OAuth Configuration")
print("-" * 70)
print("⚠️  MANUAL VERIFICATION REQUIRED:")
print("\n1. Google Cloud Console:")
print("   URL: https://console.cloud.google.com/apis/credentials")
print()
print("   ✓ Authorized redirect URIs should include:")
print("      - https://tybaetnvnfgniotdfxze.supabase.co/auth/v1/callback")
print("      - https://www.grademax.me/auth/callback")
print("      - https://grademax.me/auth/callback")

# Check 5: Vercel Configuration
print("\n📋 CHECK 5: Vercel Environment Variables")
print("-" * 70)
print("⚠️  MANUAL VERIFICATION REQUIRED:")
print("\n1. Vercel Dashboard:")
print("   Go to: https://vercel.com → grademax → Settings → Environment Variables")
print()
print("   ✓ Ensure these variables are set for Production:")
print("      - NEXT_PUBLIC_SUPABASE_URL")
print("      - NEXT_PUBLIC_SUPABASE_ANON_KEY")
print("      - SUPABASE_SERVICE_ROLE_KEY")

# Check 6: Build Readiness
print("\n📋 CHECK 6: Build Readiness")
print("-" * 70)

# Check if there are uncommitted changes
import subprocess
try:
    result = subprocess.run(['git', 'status', '--porcelain'], 
                          capture_output=True, text=True, check=True)
    if result.stdout.strip():
        print("⚠️  Uncommitted changes detected:")
        print(result.stdout)
        print("\n   Run: git add . && git commit -m 'your message'")
    else:
        print("✅ No uncommitted changes - ready to deploy")
except Exception as e:
    print(f"⚠️  Could not check git status: {str(e)}")

# Check 7: Recent Commits
print("\n📋 CHECK 7: Recent Commits")
print("-" * 70)
try:
    result = subprocess.run(['git', 'log', '--oneline', '-5'], 
                          capture_output=True, text=True, check=True)
    print("Recent commits:")
    print(result.stdout)
except Exception as e:
    print(f"⚠️  Could not check git log: {str(e)}")

# Final Summary
print("\n" + "=" * 70)
print("📊 VERIFICATION SUMMARY")
print("=" * 70)

if all_checks_passed:
    print("\n✅ All automated checks PASSED!")
    print("\n⚠️  Before deploying, manually verify:")
    print("   1. Supabase redirect URLs are configured")
    print("   2. Google OAuth redirect URIs are configured")
    print("   3. Vercel environment variables are set")
    print("\n🚀 Ready to deploy!")
    print("\n   Run: git push origin main")
    print("   This will trigger automatic Vercel deployment")
else:
    print("\n❌ Some checks FAILED!")
    print("\n   Fix the issues above before deploying.")
    sys.exit(1)

print("\n" + "=" * 70)
print("📝 POST-DEPLOYMENT TESTING")
print("=" * 70)
print("\nAfter deployment, test these URLs:")
print("   1. https://www.grademax.me")
print("   2. https://www.grademax.me/login")
print("   3. https://www.grademax.me/api/debug/auth")
print("\nTest OAuth flow:")
print("   1. Go to login page")
print("   2. Click 'Continue with Google'")
print("   3. Complete OAuth")
print("   4. Should redirect to /generate")

print("\n" + "=" * 70)
