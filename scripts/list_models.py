import requests
import os
from dotenv import load_dotenv

load_dotenv('.env.local')

api_key = os.environ.get("GROQ_API_KEY")
url = "https://api.groq.com/openai/v1/models"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers)
data = response.json()

print("Available Groq Models:")
print("=" * 50)
for m in sorted(data.get('data', []), key=lambda x: x['id']):
    print(f"  - {m['id']}")
