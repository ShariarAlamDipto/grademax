"""Test Maths B Topic Questions API"""
import urllib.request
import json

SUBJECT_ID = "af08fe67-37e2-4e20-9550-30103c4fe91a"  # Maths B

# Test 1: Get all subjects
print("=" * 60)
print("TEST 1: Get All Subjects")
print("=" * 60)
try:
    res = urllib.request.urlopen('http://localhost:3000/api/subjects')
    subjects = json.loads(res.read().decode())
    print(f"Found {len(subjects)} subjects:")
    for s in subjects:
        print(f"  - {s['name']} (ID: {s['id']})")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Get Maths B topics
print("\n" + "=" * 60)
print("TEST 2: Get Maths B Topics")
print("=" * 60)
try:
    res = urllib.request.urlopen(f'http://localhost:3000/api/topics?subjectId={SUBJECT_ID}')
    topics = json.loads(res.read().decode())
    print(f"Found {len(topics)} topics for Maths B:")
    for t in topics:
        print(f"  - [{t['code']}] {t['name']}: {t.get('description', 'N/A')}")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Get questions for topic 1 (Number)
print("\n" + "=" * 60)
print("TEST 3: Get Questions for Topic 1 (Number)")
print("=" * 60)
try:
    data = {
        'subjectCode': SUBJECT_ID,
        'topics': ['1'],  # Topic code for "Number"
        'limit': 10
    }
    req = urllib.request.Request(
        'http://localhost:3000/api/worksheets/generate-v2',
        data=json.dumps(data).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    res = urllib.request.urlopen(req)
    result = json.loads(res.read().decode())
    
    if 'pages' in result:
        print(f"Found {len(result['pages'])} questions:")
        for p in result['pages'][:5]:  # Show first 5
            paper = p.get('papers', {})
            print(f"  - Q{p['question_number']} from {paper.get('year', '?')} {paper.get('season', '?')} Paper {paper.get('paper_number', '?')}")
            print(f"    Topics: {p.get('topics', [])}, Difficulty: {p.get('difficulty', 'N/A')}")
    else:
        print(f"Result: {json.dumps(result, indent=2)}")
except Exception as e:
    print(f"Error: {e}")

# Test 4: Get questions for topic 3 (Algebra)
print("\n" + "=" * 60)
print("TEST 4: Get Questions for Topic 3 (Algebra)")
print("=" * 60)
try:
    data = {
        'subjectCode': SUBJECT_ID,
        'topics': ['3'],  # Topic code for "Algebra"
        'limit': 10
    }
    req = urllib.request.Request(
        'http://localhost:3000/api/worksheets/generate-v2',
        data=json.dumps(data).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    res = urllib.request.urlopen(req)
    result = json.loads(res.read().decode())
    
    if 'pages' in result:
        print(f"Found {len(result['pages'])} questions:")
        for p in result['pages'][:5]:  # Show first 5
            paper = p.get('papers', {})
            print(f"  - Q{p['question_number']} from {paper.get('year', '?')} {paper.get('season', '?')} Paper {paper.get('paper_number', '?')}")
            print(f"    Topics: {p.get('topics', [])}, Difficulty: {p.get('difficulty', 'N/A')}")
    else:
        print(f"Result: {json.dumps(result, indent=2)}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("Test Complete!")
print("=" * 60)
