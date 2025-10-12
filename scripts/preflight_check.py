#!/usr/bin/env python3
"""
Pre-flight check - Verify system is ready
"""

import os
import sys
from pathlib import Path

print("🔍 GradeMax Pre-Flight Check")
print("="*70)

# Check 1: Environment variables
print("\n1️⃣  Environment Variables")
checks = {
    'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY'),
    'NEXT_PUBLIC_SUPABASE_URL': os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    'NEXT_PUBLIC_SUPABASE_ANON_KEY': os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY'),
}

all_env_ok = True
for key, value in checks.items():
    if value:
        masked = value[:10] + "..." if len(value) > 10 else value
        print(f"   ✅ {key}: {masked}")
    else:
        print(f"   ❌ {key}: NOT SET")
        all_env_ok = False

# Check 2: Python packages
print("\n2️⃣  Python Packages")
required_packages = [
    'fitz',  # PyMuPDF
    'google.generativeai',
    'yaml',
    'dotenv',
]

all_packages_ok = True
for package in required_packages:
    try:
        if package == 'fitz':
            import fitz
            print(f"   ✅ PyMuPDF: {fitz.version}")
        elif package == 'google.generativeai':
            import google.generativeai as genai
            print(f"   ✅ google-generativeai: installed")
        elif package == 'yaml':
            import yaml
            print(f"   ✅ PyYAML: installed")
        elif package == 'dotenv':
            from dotenv import load_dotenv
            print(f"   ✅ python-dotenv: installed")
    except ImportError:
        print(f"   ❌ {package}: NOT INSTALLED")
        all_packages_ok = False

# Check 3: Required files
print("\n3️⃣  Required Files")
required_files = [
    'config/physics_topics.yaml',
    'scripts/split_pages.py',
    'scripts/single_topic_classifier.py',
    'scripts/supabase_client.py',
    'scripts/complete_pipeline.py',
    'scripts/bulk_ingest.py',
]

all_files_ok = True
for filepath in required_files:
    path = Path(filepath)
    if path.exists():
        print(f"   ✅ {filepath}")
    else:
        print(f"   ❌ {filepath}: NOT FOUND")
        all_files_ok = False

# Check 4: Data directory
print("\n4️⃣  Directory Structure")
data_dir = Path('data/raw/IGCSE/4PH1')
if data_dir.exists():
    pdf_files = list(data_dir.rglob("*.pdf"))
    print(f"   ✅ data/raw/IGCSE/4PH1: {len(pdf_files)} PDF files found")
    
    # Count QP and MS pairs
    qp_count = len([f for f in pdf_files if 'QP' in f.name or '_1P' in f.name])
    ms_count = len([f for f in pdf_files if 'MS' in f.name])
    print(f"   📄 Question Papers: ~{qp_count}")
    print(f"   📝 Mark Schemes: ~{ms_count}")
else:
    print(f"   ⚠️  data/raw/IGCSE/4PH1: Directory not found")
    print(f"      Create this directory and add your past papers")

# Check 5: Supabase connection
print("\n5️⃣  Supabase Connection")
try:
    sys.path.insert(0, 'scripts')
    from supabase_client import SupabaseClient
    
    db = SupabaseClient()
    
    # Test query
    topics = db.select('topics', '*', limit=1)
    if topics:
        print(f"   ✅ Connection successful")
        print(f"   ✅ Can query topics table")
    else:
        print(f"   ⚠️  Connection OK but no topics found")
        print(f"      Run: python create_topics.py")
        
except Exception as e:
    print(f"   ❌ Connection failed: {e}")
    all_env_ok = False

# Check 6: Gemini API
print("\n6️⃣  Gemini API")
if os.getenv('GEMINI_API_KEY'):
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        
        # Test with simple prompt
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content("Say 'OK' if you can read this.")
        
        if response and response.text:
            print(f"   ✅ API key valid")
            print(f"   ✅ Model responding")
        else:
            print(f"   ⚠️  API key valid but no response")
    except Exception as e:
        print(f"   ❌ API test failed: {e}")
        all_env_ok = False
else:
    print(f"   ❌ GEMINI_API_KEY not set")

# Summary
print("\n" + "="*70)
print("📊 Summary")
print("="*70)

if all_env_ok and all_packages_ok and all_files_ok:
    print("✅ ALL CHECKS PASSED")
    print("\n🚀 Ready to process papers!")
    print("\nNext steps:")
    print("  1. Add PDF files to: data/raw/IGCSE/4PH1/YYYY/Season/")
    print("  2. Run: python scripts/complete_pipeline.py <qp_path> <ms_path>")
    print("  3. Or bulk: python scripts/bulk_ingest.py data/raw/IGCSE/4PH1/")
else:
    print("❌ SOME CHECKS FAILED")
    print("\nPlease fix the issues above before proceeding.")
    
    if not all_env_ok:
        print("\n⚠️  Set environment variables:")
        print("  $env:GEMINI_API_KEY='your-key'")
        print("  $env:NEXT_PUBLIC_SUPABASE_URL='https://...'")
        print("  $env:NEXT_PUBLIC_SUPABASE_ANON_KEY='your-key'")
    
    if not all_packages_ok:
        print("\n⚠️  Install Python packages:")
        print("  pip install -r requirements.txt")

print("\n" + "="*70)
