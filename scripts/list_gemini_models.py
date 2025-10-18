"""
List available Gemini models
"""
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv('.env.ingest')

api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)

print("\n" + "="*70)
print("Available Gemini Models")
print("="*70)

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"\n📦 {model.name}")
        print(f"   Display name: {model.display_name}")
        print(f"   Description: {model.description}")
        print(f"   Input token limit: {model.input_token_limit:,}")
        print(f"   Output token limit: {model.output_token_limit:,}")
