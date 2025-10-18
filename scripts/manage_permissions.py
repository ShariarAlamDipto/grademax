"""
Manage User Permissions for Worksheet Generation
This script allows admins to grant/revoke permissions and manage quotas.
"""

import os
import sys
from supabase import create_client, Client
from datetime import datetime

def get_supabase() -> Client:
    """Initialize Supabase client with service role key."""
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        print("❌ Error: Missing Supabase credentials")
        print("Please set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables")
        sys.exit(1)
    
    return create_client(url, key)

def list_users(supabase: Client):
    """List all users with their permission status."""
    print("\n📋 User Permissions List\n" + "="*80)
    
    # Get all user profiles with permissions
    response = supabase.table('user_profiles')\
        .select('*, user_permissions(*)')\
        .execute()
    
    if not response.data:
        print("No users found.")
        return
    
    for user in response.data:
        email = user.get('email', 'N/A')
        name = user.get('full_name', 'N/A')
        role = user.get('role', 'N/A')
        
        perms = user.get('user_permissions')
        if perms and len(perms) > 0:
            perm = perms[0]
            can_generate = "✅ Yes" if perm.get('can_generate_worksheets') else "❌ No"
            is_active = "✅" if perm.get('is_active') else "⏸️"
            max_per_day = perm.get('max_worksheets_per_day') or "Unlimited"
        else:
            can_generate = "❓ Not configured"
            is_active = "❓"
            max_per_day = "N/A"
        
        print(f"\n{email}")
        print(f"  Name: {name}")
        print(f"  Role: {role}")
        print(f"  Can Generate: {can_generate}")
        print(f"  Active: {is_active}")
        print(f"  Daily Quota: {max_per_day}")

def grant_permission(supabase: Client, email: str, admin_email: str = None):
    """Grant worksheet generation permission to a user."""
    # Find user by email
    try:
        user_response = supabase.table('user_profiles')\
            .select('user_id, email')\
            .eq('email', email)\
            .single()\
            .execute()
        
        if not user_response.data:
            print(f"❌ User not found: {email}")
            print(f"\n💡 This user hasn't signed up yet. They need to:")
            print(f"   1. Go to your app's login page")
            print(f"   2. Sign in with Google using {email}")
            print(f"   3. Then run this command again to grant permission")
            return
    except Exception as e:
        if "0 rows" in str(e) or "PGRST116" in str(e):
            print(f"❌ User not found: {email}")
            print(f"\n💡 This user hasn't signed up yet. They need to:")
            print(f"   1. Go to your app's login page")
            print(f"   2. Sign in with Google using {email}")
            print(f"   3. Then run this command again to grant permission")
        else:
            print(f"❌ Error checking user: {e}")
        return
    
    user_id = user_response.data['user_id']
    
    # Get admin user_id if provided
    admin_id = None
    if admin_email:
        admin_response = supabase.table('user_profiles')\
            .select('user_id')\
            .eq('email', admin_email)\
            .single()\
            .execute()
        
        if admin_response.data:
            admin_id = admin_response.data['user_id']
    
    # Update or insert permission
    permission_data = {
        'user_id': user_id,
        'can_generate_worksheets': True,
        'is_active': True,
        'permission_granted_at': datetime.utcnow().isoformat(),
        'permission_granted_by': admin_id,
        'notes': f'Permission granted via admin script on {datetime.now().strftime("%Y-%m-%d %H:%M")}'
    }
    
    response = supabase.table('user_permissions')\
        .upsert(permission_data, on_conflict='user_id')\
        .execute()
    
    if response.data:
        print(f"✅ Permission granted to {email}")
    else:
        print(f"❌ Failed to grant permission to {email}")

def revoke_permission(supabase: Client, email: str):
    """Revoke worksheet generation permission from a user."""
    # Find user by email
    try:
        user_response = supabase.table('user_profiles')\
            .select('user_id, email')\
            .eq('email', email)\
            .single()\
            .execute()
        
        if not user_response.data:
            print(f"❌ User not found: {email}")
            return
    except Exception as e:
        if "0 rows" in str(e) or "PGRST116" in str(e):
            print(f"❌ User not found: {email}")
            print(f"💡 This user hasn't signed up yet.")
        else:
            print(f"❌ Error checking user: {e}")
        return
    
    user_id = user_response.data['user_id']
    
    # Update permission
    response = supabase.table('user_permissions')\
        .update({
            'can_generate_worksheets': False,
            'is_active': False,
            'notes': f'Permission revoked via admin script on {datetime.now().strftime("%Y-%m-%d %H:%M")}'
        })\
        .eq('user_id', user_id)\
        .execute()
    
    if response.data:
        print(f"✅ Permission revoked from {email}")
    else:
        print(f"❌ Failed to revoke permission from {email}")

def set_quota(supabase: Client, email: str, max_per_day: int):
    """Set daily worksheet quota for a user."""
    # Find user by email
    try:
        user_response = supabase.table('user_profiles')\
            .select('user_id, email')\
            .eq('email', email)\
            .single()\
            .execute()
        
        if not user_response.data:
            print(f"❌ User not found: {email}")
            return
    except Exception as e:
        if "0 rows" in str(e) or "PGRST116" in str(e):
            print(f"❌ User not found: {email}")
            print(f"💡 This user hasn't signed up yet.")
        else:
            print(f"❌ Error checking user: {e}")
        return
    
    user_id = user_response.data['user_id']
    
    # Update quota
    response = supabase.table('user_permissions')\
        .update({
            'max_worksheets_per_day': max_per_day if max_per_day > 0 else None,
            'notes': f'Quota set to {max_per_day} per day via admin script on {datetime.now().strftime("%Y-%m-%d %H:%M")}'
        })\
        .eq('user_id', user_id)\
        .execute()
    
    if response.data:
        print(f"✅ Daily quota set to {max_per_day if max_per_day > 0 else 'unlimited'} for {email}")
    else:
        print(f"❌ Failed to set quota for {email}")

def view_logs(supabase: Client, email: str = None, limit: int = 20):
    """View worksheet generation logs."""
    print(f"\n📊 Worksheet Generation Logs (Last {limit})\n" + "="*80)
    
    query = supabase.table('worksheet_generation_logs')\
        .select('*, user_profiles!inner(email, full_name)')\
        .order('generated_at', desc=True)\
        .limit(limit)
    
    if email:
        query = query.eq('user_profiles.email', email)
    
    response = query.execute()
    
    if not response.data:
        print("No logs found.")
        return
    
    for log in response.data:
        profile = log.get('user_profiles', {})
        user_email = profile.get('email', 'N/A')
        status = log.get('status', 'N/A')
        subject = log.get('subject_code', 'N/A')
        topics = log.get('topics', [])
        questions = log.get('questions_generated', 0)
        timestamp = log.get('generated_at', 'N/A')
        
        status_icon = "✅" if status == "success" else "❌"
        
        print(f"\n{status_icon} {user_email} - {timestamp}")
        print(f"   Subject: {subject} | Topics: {', '.join(topics)}")
        print(f"   Status: {status} | Questions: {questions}")
        
        if log.get('error_message'):
            print(f"   Error: {log.get('error_message')}")

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python manage_permissions.py list                          # List all users")
        print("  python manage_permissions.py grant <email>                 # Grant permission")
        print("  python manage_permissions.py revoke <email>                # Revoke permission")
        print("  python manage_permissions.py quota <email> <max_per_day>  # Set daily quota")
        print("  python manage_permissions.py logs [email] [limit]         # View generation logs")
        sys.exit(1)
    
    supabase = get_supabase()
    command = sys.argv[1].lower()
    
    if command == "list":
        list_users(supabase)
    
    elif command == "grant":
        if len(sys.argv) < 3:
            print("❌ Error: Email required")
            print("Usage: python manage_permissions.py grant <email>")
            sys.exit(1)
        
        email = sys.argv[2]
        admin_email = sys.argv[3] if len(sys.argv) > 3 else None
        grant_permission(supabase, email, admin_email)
    
    elif command == "revoke":
        if len(sys.argv) < 3:
            print("❌ Error: Email required")
            print("Usage: python manage_permissions.py revoke <email>")
            sys.exit(1)
        
        email = sys.argv[2]
        revoke_permission(supabase, email)
    
    elif command == "quota":
        if len(sys.argv) < 4:
            print("❌ Error: Email and quota required")
            print("Usage: python manage_permissions.py quota <email> <max_per_day>")
            sys.exit(1)
        
        email = sys.argv[2]
        try:
            max_per_day = int(sys.argv[3])
        except ValueError:
            print("❌ Error: Quota must be a number")
            sys.exit(1)
        
        set_quota(supabase, email, max_per_day)
    
    elif command == "logs":
        email = sys.argv[2] if len(sys.argv) > 2 else None
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        view_logs(supabase, email, limit)
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Valid commands: list, grant, revoke, quota, logs")
        sys.exit(1)

if __name__ == "__main__":
    main()
