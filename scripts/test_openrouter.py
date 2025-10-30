#!/usr/bin/env python3
"""Test OpenRouter API connection"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv('.env.local')

api_key = os.getenv('OPENROUTER_API_KEY')
print(f"API Key: {api_key[:20]}...")

url = "https://openrouter.ai/api/v1/chat/completions"

test_prompt = """Classify this IGCSE Physics question: "Calculate the current in a circuit with voltage 12V and resistance 4Ω"

Return JSON only:
{"topic": "2", "difficulty": "easy", "confidence": 0.95}"""

try:
    print("\nSending request...")
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://grademax.com",
            "X-Title": "GradeMax Test"
        },
        json={
            "model": "google/gemini-2.0-flash-exp:free",
            "messages": [
                {"role": "system", "content": "You are a physics expert. Output JSON only."},
                {"role": "user", "content": test_prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 200
        },
        timeout=30
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    
    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content']
        print(f"\nContent: {content}")
        parsed = json.loads(content.strip().strip('```json').strip('```'))
        print(f"Parsed: {parsed}")
        print("\n✅ API Test PASSED!")
    else:
        print(f"\n❌ API Test FAILED: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
