"""Grant worksheet generation access to user"""
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv(".env.local")

supabase = create_client(
    os.getenv("NEXT_PUBLIC_SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

email = "justarice7@gmail.com"

print(f"🔍 Finding user: {email}")

# Get user by email
users = supabase.table('user_profiles').select('*').eq('email', email).execute()

if not users.data:
    print(f"❌ User not found: {email}")
    exit(1)

user = users.data[0]
user_id = user['user_id']
print(f"✅ Found user: {user['full_name']} (ID: {user_id})")

# Check current permissions
perms = supabase.table('user_permissions').select('*').eq('user_id', user_id).execute()

if perms.data:
    current_perms = perms.data[0]
    print(f"\n📋 Current permissions:")
    print(f"   Can generate worksheets: {current_perms.get('can_generate_worksheets')}")
    print(f"   Is active: {current_perms.get('is_active')}")
    print(f"   Max worksheets/day: {current_perms.get('max_worksheets_per_day')}")
    
    # Update permissions
    update_data = {
        'can_generate_worksheets': True,
        'is_active': True,
        'max_worksheets_per_day': 50,
        'notes': 'Access granted for testing - ' + str(current_perms.get('notes', ''))
    }
    
    result = supabase.table('user_permissions').update(update_data).eq('user_id', user_id).execute()
    print(f"\n✅ Updated permissions!")
    
else:
    # Create permissions
    insert_data = {
        'user_id': user_id,
        'can_generate_worksheets': True,
        'is_active': True,
        'max_worksheets_per_day': 50,
        'notes': 'Access granted for testing'
    }
    
    result = supabase.table('user_permissions').insert(insert_data).execute()
    print(f"\n✅ Created permissions!")

# Verify
final_perms = supabase.table('user_permissions').select('*').eq('user_id', user_id).execute()
print(f"\n📊 Final permissions:")
print(f"   ✅ Can generate worksheets: {final_perms.data[0]['can_generate_worksheets']}")
print(f"   ✅ Is active: {final_perms.data[0]['is_active']}")
print(f"   ✅ Max worksheets/day: {final_perms.data[0]['max_worksheets_per_day']}")

print(f"\n🎉 User {email} can now generate worksheets!")
