"""
Test actual storage URLs to find what works
"""
import requests

base_url = "https://tybaetnvnfgniotdfxze.supabase.co/storage/v1/object/public/question-pdfs"

# Test different path formats
test_paths = [
    "papers/2019_Jun_1P/Q3.pdf",
    "papers/2019_Jun_1P/Q4.pdf",
    "papers/2019_Jun_1P/Q5.pdf",
    "2019/Jun/1P/Q2.pdf",
    "2019/Jun/1P/Q3.pdf",
]

print("🧪 Testing actual storage URLs:\n")

for path in test_paths:
    full_url = f"{base_url}/{path}"
    
    try:
        response = requests.head(full_url, timeout=5)
        
        if response.status_code == 200:
            size = int(response.headers.get('Content-Length', 0))
            print(f"✅ {path} ({size/1024:.1f} KB)")
        elif response.status_code == 404:
            print(f"❌ {path} - NOT FOUND")
        else:
            print(f"⚠️  {path} - HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ {path} - Error: {e}")

print("\n📊 Conclusion:")
print("The paths that work (✅) are the ones actually in your storage bucket.")
print("Database needs to match these paths!")
