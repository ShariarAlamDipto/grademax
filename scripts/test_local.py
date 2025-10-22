"""
Local Testing Script - Quick validation of all endpoints
Run this before pushing to production
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:3000"

print("=" * 70)
print("🧪 LOCAL TESTING SCRIPT")
print("=" * 70)
print(f"Testing: {BASE_URL}")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

tests_passed = 0
tests_failed = 0

def test_endpoint(name, url, expected_keys=None, should_be_array=False):
    global tests_passed, tests_failed
    print(f"\n🔍 Testing: {name}")
    print(f"   URL: {url}")
    
    try:
        response = requests.get(url, timeout=5)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if should_be_array:
                if isinstance(data, list):
                    print(f"   ✅ PASS - Returned array with {len(data)} items")
                    if len(data) > 0:
                        print(f"   Sample: {json.dumps(data[0], indent=2)[:100]}...")
                    tests_passed += 1
                    return True
                else:
                    print(f"   ❌ FAIL - Expected array, got {type(data)}")
                    tests_failed += 1
                    return False
            
            if expected_keys:
                missing_keys = [k for k in expected_keys if k not in data]
                if missing_keys:
                    print(f"   ❌ FAIL - Missing keys: {missing_keys}")
                    tests_failed += 1
                    return False
            
            print(f"   ✅ PASS - Response: {json.dumps(data, indent=2)[:200]}...")
            tests_passed += 1
            return True
        else:
            print(f"   ❌ FAIL - Status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            tests_failed += 1
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ FAIL - Cannot connect! Is dev server running?")
        print(f"   Run: npm run dev")
        tests_failed += 1
        return False
    except Exception as e:
        print(f"   ❌ FAIL - Error: {str(e)}")
        tests_failed += 1
        return False

# Run tests
print("\n" + "=" * 70)
print("📋 API ENDPOINT TESTS")
print("=" * 70)

# Test 1: Config diagnostic
test_endpoint(
    "Configuration Diagnostic",
    f"{BASE_URL}/api/debug/config",
    expected_keys=['hasSupabaseUrl', 'hasAnonKey', 'supabaseConnected']
)

# Test 2: Subjects API
test_endpoint(
    "Subjects API",
    f"{BASE_URL}/api/subjects",
    should_be_array=True
)

# Test 3: Topics API (using Further Pure Mathematics ID)
test_endpoint(
    "Topics API",
    f"{BASE_URL}/api/topics?subjectId=8dea5d70-f026-4e03-bb45-053f154c6898",
    should_be_array=True
)

# Test 4: Auth Debug
test_endpoint(
    "Auth Debug",
    f"{BASE_URL}/api/debug/auth",
    expected_keys=['hasUser', 'hasSession']
)

# Test 5: Permission Check (may fail if not logged in)
print(f"\n🔍 Testing: Permission Check (may fail if not logged in)")
print(f"   URL: {BASE_URL}/api/worksheets/check-permission")
try:
    response = requests.get(f"{BASE_URL}/api/worksheets/check-permission", timeout=5)
    print(f"   Status: {response.status_code}")
    data = response.json()
    if response.status_code == 200 and data.get('hasPermission'):
        print(f"   ✅ PASS - User has permission")
        print(f"   Quota: {data.get('remainingQuota')}/{data.get('maxPerDay')}")
        tests_passed += 1
    elif response.status_code == 401:
        print(f"   ⚠️  SKIP - Not logged in (this is OK)")
    else:
        print(f"   ℹ️  INFO - Response: {json.dumps(data, indent=2)}")
except Exception as e:
    print(f"   ⚠️  SKIP - {str(e)}")

# Summary
print("\n" + "=" * 70)
print("📊 TEST SUMMARY")
print("=" * 70)
print(f"✅ Passed: {tests_passed}")
print(f"❌ Failed: {tests_failed}")
print(f"Total: {tests_passed + tests_failed}")

if tests_failed == 0:
    print("\n🎉 ALL TESTS PASSED!")
    print("\n✅ Safe to proceed with:")
    print("   1. Test in browser: http://localhost:3000/generate")
    print("   2. Verify subjects dropdown populates")
    print("   3. Verify topics dropdown works")
    print("   4. Test worksheet generation")
    print("   5. If all works, commit and push")
else:
    print("\n⚠️  SOME TESTS FAILED!")
    print("\n❌ Fix issues before committing:")
    print("   1. Check dev server is running: npm run dev")
    print("   2. Check .env.local has correct values")
    print("   3. Check database has data: python scripts/check_current_state.py")
    print("   4. Re-run this script")

print("\n" + "=" * 70)
print("📝 NEXT STEPS")
print("=" * 70)

if tests_failed == 0:
    print("\n1. Open browser and test UI:")
    print("   http://localhost:3000/generate")
    print("\n2. Complete these manual tests:")
    print("   ✓ Login with justarice7@gmail.com")
    print("   ✓ Subject dropdown shows 'Further Pure Mathematics'")
    print("   ✓ Select subject → Topics dropdown populates")
    print("   ✓ Select 2-3 topics, set year range")
    print("   ✓ Click 'Generate Worksheet'")
    print("   ✓ Questions appear (5+ questions)")
    print("   ✓ Download PDF buttons work")
    print("\n3. If all manual tests pass:")
    print("   git add .")
    print('   git commit -m "fix: Description of what was fixed"')
    print("   git push origin main")
else:
    print("\n❌ Cannot proceed until all tests pass")
    print("   Fix the failed tests above first")

print("\n" + "=" * 70)
