#!/usr/bin/env python3
"""
Quick setup script for LM Studio integration
Run this after installing LM Studio to verify everything works
"""

import os
import sys
from pathlib import Path

def check_lmstudio():
    """Check if LM Studio is running"""
    try:
        import requests
        response = requests.get("http://127.0.0.1:1234/v1/models", timeout=5)
        if response.status_code == 200:
            models = response.json().get('data', [])
            print(f"✅ LM Studio is running with {len(models)} model(s) loaded")
            for model in models:
                print(f"   - {model.get('id', 'unknown')}")
            return True
        else:
            print(f"⚠️ LM Studio responded with status {response.status_code}")
            return False
    except ImportError:
        print("❌ 'requests' library not installed")
        print("   Install with: pip install requests")
        return False
    except Exception as e:
        print(f"❌ Could not connect to LM Studio at http://127.0.0.1:1234")
        print(f"   Error: {e}")
        print("\n💡 Make sure LM Studio is running:")
        print("   1. Open LM Studio application")
        print("   2. Go to 'Local Server' tab")
        print("   3. Load a model (qwen2.5-7b-instruct-1m recommended)")
        print("   4. Click 'Start Server'")
        return False

def check_dependencies():
    """Check if required Python packages are installed"""
    required = ['requests', 'yaml']
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
            print(f"✅ {pkg} is installed")
        except ImportError:
            print(f"❌ {pkg} is NOT installed")
            missing.append(pkg)
    
    if missing:
        print(f"\n📦 Install missing packages with:")
        print(f"   pip install {' '.join(missing)}")
        if 'yaml' in missing:
            print(f"   (Note: yaml package is 'PyYAML' on pip)")
        return False
    return True

def check_config():
    """Check if config file exists"""
    config_path = Path(__file__).parent / "config" / "llm.yaml"
    if config_path.exists():
        print(f"✅ Configuration file found: {config_path}")
        return True
    else:
        print(f"❌ Configuration file not found: {config_path}")
        return False

def check_gemini_removed():
    """Check if Gemini API key is removed"""
    gemini_key = os.getenv('GEMINI_API_KEY')
    google_key = os.getenv('GOOGLE_API_KEY')
    
    if gemini_key or google_key:
        print("⚠️ Found Gemini/Google API key in environment:")
        if gemini_key:
            print("   - GEMINI_API_KEY is set")
        if google_key:
            print("   - GOOGLE_API_KEY is set")
        print("\n   These are no longer needed. Remove them with:")
        print("   unset GEMINI_API_KEY (Unix/Mac)")
        print("   $env:GEMINI_API_KEY='' (Windows PowerShell)")
        return False
    else:
        print("✅ No Gemini API keys found in environment")
        return True

def check_lmstudio_env():
    """Check if LM Studio URL is configured"""
    lmstudio_url = os.getenv('LMSTUDIO_BASE_URL')
    if lmstudio_url:
        print(f"✅ LMSTUDIO_BASE_URL is set: {lmstudio_url}")
        return True
    else:
        print("⚠️ LMSTUDIO_BASE_URL is not set")
        print("   Add to .env.local:")
        print("   LMSTUDIO_BASE_URL=http://127.0.0.1:1234")
        return False

def run_quick_test():
    """Run a quick inference test"""
    try:
        sys.path.insert(0, str(Path(__file__).parent / "scripts"))
        from integrate_llm import get_llm
        
        print("\n🧪 Running quick inference test...")
        llm = get_llm()
        
        test_question = "A ball is thrown upward with velocity 10 m/s. Calculate the maximum height."
        result = llm.classify_question(test_question, "Physics")
        
        print(f"✅ Classification successful!")
        print(f"   Topics: {result.get('topics', [])}")
        print(f"   Difficulty: {result.get('difficulty', 'unknown')}")
        return True
    except Exception as e:
        print(f"❌ Inference test failed: {e}")
        return False

def main():
    """Run all checks"""
    print("="*70)
    print("🔧 LM STUDIO INTEGRATION SETUP CHECK")
    print("="*70)
    print()
    
    checks = [
        ("Python Dependencies", check_dependencies),
        ("Configuration File", check_config),
        ("Gemini Removal", check_gemini_removed),
        ("Environment Variables", check_lmstudio_env),
        ("LM Studio Connection", check_lmstudio),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n📋 Checking: {name}")
        print("-" * 70)
        results.append(check_func())
    
    # Run inference test if all checks pass
    all_passed = all(results)
    if all_passed:
        print("\n" + "="*70)
        results.append(run_quick_test())
    
    # Summary
    print("\n" + "="*70)
    print("📊 SETUP SUMMARY")
    print("="*70)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All checks passed ({passed}/{total})")
        print("\n🎉 LM Studio integration is ready to use!")
        print("\nNext steps:")
        print("1. Run full test suite: python scripts/test_llm_integration.py")
        print("2. Integrate into your codebase")
        print("3. Check README_LMStudio.md for usage examples")
    else:
        print(f"⚠️ {total - passed} check(s) failed")
        print("\n📖 Follow the instructions above to fix issues")
        print("   Then run this script again")
    
    print("="*70)
    
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
