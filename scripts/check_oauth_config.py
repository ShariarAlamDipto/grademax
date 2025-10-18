"""
Check and display current Supabase OAuth configuration.
Run this to see what redirect URLs are configured.
"""
import os
from dotenv import load_dotenv

load_dotenv('.env.local')

print("=" * 60)
print("🔍 Current Supabase Configuration")
print("=" * 60)

print("\n📋 Environment Variables:")
print(f"   NEXT_PUBLIC_SUPABASE_URL: {os.getenv('NEXT_PUBLIC_SUPABASE_URL')}")
print(f"   Has ANON_KEY: {'✅' if os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY') else '❌'}")
print(f"   Has SERVICE_KEY: {'✅' if os.getenv('SUPABASE_SERVICE_ROLE_KEY') else '❌'}")

print("\n" + "=" * 60)
print("🔧 Required Supabase Dashboard Settings")
print("=" * 60)

print("\n1️⃣  Go to: https://supabase.com/dashboard/project/tybaetnvnfgniotdfxze")
print("2️⃣  Navigate to: Authentication → URL Configuration")
print("3️⃣  Set the following:")

print("\n📍 Site URL:")
print("   http://localhost:3000")

print("\n📍 Redirect URLs (add all of these):")
urls = [
    "http://localhost:3000/auth/callback",
    "http://localhost:3000",
    "https://grademax.vercel.app/auth/callback",
    "https://grademax.vercel.app",
    "https://*.vercel.app/auth/callback"
]
for url in urls:
    print(f"   ✅ {url}")

print("\n" + "=" * 60)
print("⚠️  IMPORTANT: After updating Supabase settings")
print("=" * 60)
print("   1. Clear browser cookies for localhost")
print("   2. Restart dev server: npm run dev")
print("   3. Try OAuth login again")
print("\n" + "=" * 60)
