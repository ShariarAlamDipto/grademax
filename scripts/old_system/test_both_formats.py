"""
Test both path formats
"""
import requests
from supabase_client import SupabaseClient
from dotenv import load_dotenv

load_dotenv()
db = SupabaseClient()

paths_to_test = [
    "2019/Jun/1P/Q2.pdf",
    "papers/2019_Jun_1P/Q3.pdf",
    "papers/2019_Jun_1P/Q12.pdf"
]

print("Testing accessibility of different path formats:\n")

for path in paths_to_test:
    url = db.get_public_url('question-pdfs', path)
    
    try:
        response = requests.head(url, timeout=5)
        size = response.headers.get('Content-Length', '?')
        
        if response.status_code == 200:
            print(f"✅ {path}")
            print(f"   Size: {int(size)/1024:.1f} KB" if size != '?' else "   Size: unknown")
            print(f"   URL: {url}\n")
        else:
            print(f"❌ {path} - HTTP {response.status_code}\n")
    except Exception as e:
        print(f"❌ {path} - Error: {e}\n")
