#!/usr/bin/env python3
"""Test different OpenRouter free models"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv('.env.local')

api_key = os.getenv('OPENROUTER_API_KEY')
url = "https://openrouter.ai/api/v1/chat/completions"

# Free models to test
free_models = [
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "qwen/qwen-2.5-7b-instruct:free",
]

test_prompt = """Classify this physics question: "Calculate the current in a circuit with voltage 12V and resistance 4Ω"

Return JSON: {"topic": "2", "difficulty": "easy", "confidence": 0.95}"""

for model in free_models:
    print(f"\nTesting: {model}")
    print("-" * 50)
    
    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://grademax.com"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "user", "content": test_prompt}
                ],
                "max_tokens": 100
            },
            timeout=15
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"✅ SUCCESS!")
            print(f"Response: {content[:200]}")
        else:
            print(f"❌ FAILED: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

print("\n" + "="*50)
