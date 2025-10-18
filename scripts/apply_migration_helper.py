#!/usr/bin/env python3
"""
Quick helper to open Supabase Dashboard and show migration instructions.
This script provides a convenient way to apply the Phase 1 migration.
"""

import webbrowser
import sys
from pathlib import Path

def main():
    print("=" * 70)
    print(" Phase 1 Security Migration - Quick Start")
    print("=" * 70)
    print()
    
    migration_file = Path(__file__).parent.parent / 'supabase' / 'migrations' / '02_phase1_security.sql'
    
    print("📋 STEP 1: Open Supabase Dashboard")
    print("-" * 70)
    print("Opening https://supabase.com/dashboard in your browser...")
    print()
    
    try:
        webbrowser.open('https://supabase.com/dashboard/project/tybaetnvnfgniotdfxze/sql/new')
        print("✅ Browser opened successfully!")
    except Exception as e:
        print(f"⚠️  Could not open browser automatically: {e}")
        print("\n🔗 Please manually open:")
        print("   https://supabase.com/dashboard/project/tybaetnvnfgniotdfxze/sql/new")
    
    print()
    print("📋 STEP 2: Copy Migration SQL")
    print("-" * 70)
    print(f"Migration file location:")
    print(f"   {migration_file}")
    print()
    print("Instructions:")
    print("   1. Open the file above in VS Code or your text editor")
    print("   2. Select all (Ctrl+A)")
    print("   3. Copy (Ctrl+C)")
    print()
    
    print("📋 STEP 3: Paste and Run")
    print("-" * 70)
    print("In the Supabase SQL Editor (that just opened):")
    print("   1. Paste the migration SQL (Ctrl+V)")
    print("   2. Click 'Run' button (bottom right)")
    print("   3. Wait for 'Success' message")
    print()
    
    print("📋 STEP 4: Verify")
    print("-" * 70)
    print("Run this query to verify tables were created:")
    print()
    print("   SELECT table_name FROM information_schema.tables")
    print("   WHERE table_schema = 'public'")
    print("   AND table_name IN ('user_sessions', 'trusted_devices', 'audit_log', 'usage_meters');")
    print()
    print("Expected: 4 rows returned")
    print()
    
    print("=" * 70)
    print(" ✨ After migration is applied:")
    print("=" * 70)
    print("• Visit http://localhost:3002/dashboard to see usage stats")
    print("• Generate a worksheet to test quota tracking")
    print("• Check admin portal for audit logs")
    print()
    print("📖 Full guide: PHASE1_MIGRATION_GUIDE.md")
    print()
    
    input("Press Enter to exit...")

if __name__ == '__main__':
    main()
