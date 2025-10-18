"""
Display environment variable values to copy to Vercel.
"""
import os
from dotenv import load_dotenv

load_dotenv('.env.local')

print("=" * 70)
print("📋 ENVIRONMENT VARIABLES FOR VERCEL")
print("=" * 70)
print("\nCopy these values to Vercel Dashboard:")
print("Go to: https://vercel.com → grademax → Settings → Environment Variables")
print("\n" + "=" * 70)

print("\n1️⃣  NEXT_PUBLIC_SUPABASE_URL")
print("-" * 70)
url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
if url:
    print(f"Value: {url}")
else:
    print("❌ NOT FOUND in .env.local")

print("\n2️⃣  NEXT_PUBLIC_SUPABASE_ANON_KEY")
print("-" * 70)
anon_key = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
if anon_key:
    print(f"Value: {anon_key}")
    print(f"\nFirst 20 chars: {anon_key[:20]}...")
    print(f"Length: {len(anon_key)} characters")
else:
    print("❌ NOT FOUND in .env.local")

print("\n3️⃣  SUPABASE_SERVICE_ROLE_KEY")
print("-" * 70)
service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
if service_key:
    print(f"Value: {service_key}")
    print(f"\nFirst 20 chars: {service_key[:20]}...")
    print(f"Length: {len(service_key)} characters")
else:
    print("❌ NOT FOUND in .env.local")

print("\n" + "=" * 70)
print("📝 INSTRUCTIONS")
print("=" * 70)
print("\n1. Go to: https://vercel.com → Select 'grademax' project")
print("2. Click: Settings → Environment Variables")
print("3. For EACH variable above:")
print("   - Click 'Add New'")
print("   - Enter Name (e.g., NEXT_PUBLIC_SUPABASE_URL)")
print("   - Paste Value from above")
print("   - Select Environment: Production")
print("   - Click 'Save'")
print("\n4. After adding all 3 variables:")
print("   - Go to Deployments tab")
print("   - Click ⋯ on latest deployment")
print("   - Click 'Redeploy'")
print("\n5. Wait 2-3 minutes for deployment")
print("\n6. Test: https://www.grademax.me/api/debug/config")
print("   Should show all values as 'true'")

print("\n" + "=" * 70)
print("🧪 AFTER SETUP - TEST THESE URLS")
print("=" * 70)
print("\n✓ https://www.grademax.me/api/debug/config")
print("  Should show: hasSupabaseUrl: true, hasAnonKey: true, etc.")
print("\n✓ https://www.grademax.me/api/subjects")
print("  Should return: Array of subjects")
print("\n✓ https://www.grademax.me/generate")
print("  Should show: Subject and topic dropdowns populated")

print("\n" + "=" * 70)
