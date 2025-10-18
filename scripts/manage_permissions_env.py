"""
Load environment variables from .env.local and run the permission management script.
This is a wrapper script that loads env vars before running manage_permissions.py
"""

import os
import sys
from pathlib import Path

# Load .env.local file
env_file = Path(__file__).parent.parent / '.env.local'

if env_file.exists():
    print(f"📄 Loading environment from: {env_file}")
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
                if 'KEY' in key:
                    print(f"✅ Loaded: {key} = ***hidden***")
                else:
                    print(f"✅ Loaded: {key}")
else:
    print(f"❌ Error: .env.local not found at {env_file}")
    sys.exit(1)

# Check required variables
required_vars = ['NEXT_PUBLIC_SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']
missing = [var for var in required_vars if var not in os.environ]

if missing:
    print(f"\n❌ Missing required environment variables: {', '.join(missing)}")
    print("\nPlease add to .env.local:")
    for var in missing:
        print(f"  {var}=your-value-here")
    sys.exit(1)

print("\n✅ All environment variables loaded!\n")

# Now import and run the main script
import manage_permissions

if __name__ == "__main__":
    manage_permissions.main()
