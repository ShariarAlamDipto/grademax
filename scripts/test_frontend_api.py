"""
Quick test of the frontend API endpoints
"""
import urllib.request
import json

def test_api():
    base = "http://localhost:3000/api"
    
    # Test subjects
    print("Testing /api/subjects...")
    try:
        with urllib.request.urlopen(f"{base}/subjects") as r:
            subjects = json.load(r)
            print(f"  Found {len(subjects)} subjects:")
            for s in subjects:
                print(f"    - {s['name']} ({s['code']})")
            
            # Get Maths B subject ID
            maths_b = next((s for s in subjects if s['code'] == '4MB1'), None)
            if maths_b:
                print(f"\n  Math B ID: {maths_b['id']}")
                
                # Test topics for Math B
                print(f"\nTesting /api/topics?subjectId={maths_b['id']}...")
                with urllib.request.urlopen(f"{base}/topics?subjectId={maths_b['id']}") as r2:
                    topics = json.load(r2)
                    print(f"  Found {len(topics)} topics:")
                    for t in topics:
                        print(f"    - {t['code']}: {t['name']}")
            else:
                print("  Math B not found!")
                
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_api()
