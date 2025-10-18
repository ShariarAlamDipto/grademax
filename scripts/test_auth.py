"""Test authentication and permissions for justarice7@gmail.com"""
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv(".env.local")

supabase = create_client(
    os.getenv("NEXT_PUBLIC_SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

email = "justarice7@gmail.com"

print("🔍 Testing authentication setup\n")

# Check user exists
users = supabase.table('user_profiles').select('*').eq('email', email).execute()
if users.data:
    user = users.data[0]
    print(f"✅ User found: {user['full_name']}")
    print(f"   Email: {user['email']}")
    print(f"   User ID: {user['user_id']}")
    print(f"   Role: {user.get('role', 'N/A')}")
    
    # Check permissions
    perms = supabase.table('user_permissions').select('*').eq('user_id', user['user_id']).execute()
    if perms.data:
        perm = perms.data[0]
        print(f"\n📋 Permissions:")
        print(f"   ✅ Can generate worksheets: {perm['can_generate_worksheets']}")
        print(f"   ✅ Is active: {perm['is_active']}")
        print(f"   ✅ Max worksheets/day: {perm['max_worksheets_per_day']}")
        print(f"   Notes: {perm.get('notes', 'N/A')}")
    else:
        print(f"\n❌ No permissions found")
    
    # Check if admin
    admin_emails = os.getenv('ADMIN_EMAILS', '').split(',')
    is_admin = email in [e.strip() for e in admin_emails]
    print(f"\n🔐 Admin status: {'✅ Yes' if is_admin else '❌ No'}")
    
    print(f"\n✅ User should be able to access /generate")
    print(f"   Visit: http://localhost:3000/generate")
    
else:
    print(f"❌ User not found: {email}")
