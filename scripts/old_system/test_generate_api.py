"""
Test the generate API to see what it returns
"""
import requests
import json

url = "http://localhost:3000/api/worksheets/generate"

payload = {
    "subjectCode": "4PH1",
    "topicCodes": ["1", "5"],
    "difficulties": [1, 2, 3],
    "count": 3,
    "includeMarkscheme": False,
    "shuffle": True
}

print("📤 Generating worksheet...")
print(f"Payload: {json.dumps(payload, indent=2)}\n")

response = requests.post(url, json=payload)

print(f"Status: {response.status_code}\n")

if response.status_code == 200:
    data = response.json()
    
    print(f"✅ Worksheet generated!")
    print(f"Worksheet ID: {data.get('worksheetId')}")
    print(f"Items: {len(data.get('items', []))}\n")
    
    if data.get('items'):
        print("First item:")
        item = data['items'][0]
        print(f"  Question: {item.get('questionNumber')}")
        print(f"  Text: {item.get('text', 'N/A')[:100]}...")
        print(f"  pagePdfUrl: {item.get('pagePdfUrl', 'N/A')}")
        print(f"  msPdfUrl: {item.get('msPdfUrl', 'N/A')}")
        print(f"  hasDiagram: {item.get('hasDiagram', 'N/A')}")
        print(f"  confidence: {item.get('confidence', 'N/A')}")
        
        if item.get('pagePdfUrl'):
            full_url = f"https://tybaetnvnfgniotdfxze.supabase.co/storage/v1/object/public/question-pdfs/{item['pagePdfUrl']}"
            print(f"\n  Full URL: {full_url}")
            
            # Test if accessible
            test = requests.head(full_url, timeout=5)
            print(f"  Accessible: {'✅ YES' if test.status_code == 200 else f'❌ NO ({test.status_code})'}")
else:
    print(f"❌ Error: {response.text}")
