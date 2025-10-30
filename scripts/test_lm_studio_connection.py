#!/usr/bin/env python3
"""
Simple test to check LM Studio server connection
"""
import requests
import json

base_url = "http://127.0.0.1:1234"

print("=" * 70)
print("🔍 Testing LM Studio Server Connection")
print("=" * 70)
print()

# Try different endpoints
endpoints = [
    "/v1/models",
    "/models",
    "/v1/chat/completions",
    "/chat/completions",
    "/",
]

for endpoint in endpoints:
    url = base_url + endpoint
    print(f"Testing: {url}")
    
    try:
        if "chat/completions" in endpoint:
            # Try POST for chat endpoints
            response = requests.post(
                url,
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 10
                },
                timeout=5
            )
        else:
            # Try GET for other endpoints
            response = requests.get(url, timeout=5)
        
        print(f"  ✅ Status: {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  📄 Response: {json.dumps(data, indent=2)[:200]}")
            except:
                print(f"  📄 Response: {response.text[:200]}")
        else:
            print(f"  ❌ Error: {response.text[:200]}")
    except requests.exceptions.ConnectionError:
        print(f"  ❌ Connection refused - server not running?")
    except requests.exceptions.Timeout:
        print(f"  ⏱️  Timeout")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print()

print("=" * 70)
print("💡 Check LM Studio:")
print("   1. Is the server running? (Check 'Local Server' tab)")
print("   2. Is a model loaded?")
print("   3. What port is it using? (Default: 1234)")
print("=" * 70)
