"""
Test worksheet generation for Math B
"""
import urllib.request
import json

def test_generate():
    base = "http://localhost:3000/api"
    subject_id = "af08fe67-37e2-4e20-9550-30103c4fe91a"  # Math B
    
    # Test generating with topic code "3" (Algebra)
    payload = {
        "subjectCode": subject_id,
        "topics": ["3"],  # Algebra
        "limit": 10,
        "shuffle": False
    }
    
    print("Testing worksheet generation...")
    print(f"  Subject: Math B ({subject_id})")
    print(f"  Topics: {payload['topics']}")
    
    req = urllib.request.Request(
        f"{base}/worksheets/generate-v2",
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req) as r:
            result = json.load(r)
            print(f"\n  Success!")
            print(f"  Worksheet ID: {result.get('worksheet_id')}")
            print(f"  Questions found: {len(result.get('pages', []))}")
            
            if result.get('pages'):
                print("\n  Sample questions:")
                for p in result['pages'][:3]:
                    print(f"    - Q{p['questionNumber']} (Year {p['year']}, {p['season']})")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"  Error {e.code}: {error_body}")
    except Exception as e:
        print(f"  Error: {e}")


if __name__ == "__main__":
    test_generate()
