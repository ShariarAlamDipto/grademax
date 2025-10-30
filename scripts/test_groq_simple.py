#!/usr/bin/env python3
"""Simple test of Groq API"""
import os
import requests
from dotenv import load_dotenv

load_dotenv('.env.local')

groq_api_key = os.getenv('GROQ_API_KEY')

if not groq_api_key:
    print("❌ GROQ_API_KEY not found")
    exit(1)

print(f"✅ API Key loaded: {groq_api_key[:20]}...")

# Test Groq API
url = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {groq_api_key}",
    "Content-Type": "application/json"
}

payload = {
    "model": "llama-3.1-8b-instant",
    "messages": [
        {"role": "user", "content": "Return only this JSON: {\"test\": \"success\"}"}
    ],
    "temperature": 0.1,
    "max_tokens": 50,
    "response_format": {"type": "json_object"}
}

print("\n🔄 Testing Groq API...")
try:
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    result = response.json()
    message = result['choices'][0]['message']['content']
    print(f"✅ Groq API working!")
    print(f"Response: {message}")
except Exception as e:
    print(f"❌ Error: {e}")
