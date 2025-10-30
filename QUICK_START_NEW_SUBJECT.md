# 🚀 Quick Start: Adding a New Subject

This guide walks you through adding a new subject to GradeMax in ~30 minutes.

## Prerequisites

- [ ] Subject exists in Supabase `subjects` table
- [ ] Papers uploaded and linked to subject
- [ ] Pages created for all papers
- [ ] API keys configured (Gemini + Groq)

---

## Step 1: Copy Configuration Template (5 minutes)

```bash
# Copy template
cp config/TEMPLATE_subject_topics.yaml config/mathematics_topics.yaml

# Edit the file
code config/mathematics_topics.yaml
```

**Update these sections:**
1. **Subject metadata** - name, code, board, Supabase ID
2. **Topics** - Define 4-12 topics with clear descriptions
3. **Core keywords** - 5-10 highly specific terms per topic
4. **Support keywords** - 3-5 general terms per topic
5. **Negative keywords** - Common false positive patterns

**Example:**
```yaml
subject:
  code: "4MA1"
  name: "Mathematics"
  id: "your-uuid-here"

topics:
  - id: "1"
    code: "NUMBER"
    name: "Number"
    description: "Integers, fractions, HCF, LCM, prime factorization"
    
keywords:
  core:
    topic_1:
      - text: "hcf"
        weight: 5
      - text: "prime factorization"
        weight: 5
```

---

## Step 2: Create Classifier (10 minutes)

```bash
# Copy template
cp scripts/physics_classifier.py scripts/mathematics_classifier.py

# Edit the file
code scripts/mathematics_classifier.py
```

**Update these variables:**
```python
SUBJECT_NAME = "Mathematics"
SUBJECT_ID = "your-uuid-here"  # From Supabase
CONFIG_PATH = Path(__file__).parent.parent / 'config' / 'mathematics_topics.yaml'
```

**Test it:**
```bash
python scripts/mathematics_classifier.py
```

Expected output:
```
✅ Mathematics classifier initialized
📚 8 topics loaded
🔑 45 keywords loaded

Test: Topic 2, medium, 0.45
```

---

## Step 3: Create Runner (5 minutes)

```bash
# Copy template
cp scripts/run_hybrid_classification.py scripts/run_mathematics_classification.py

# Edit the file
code scripts/run_mathematics_classification.py
```

**Update imports and constants:**
```python
from mathematics_classifier import MathematicsClassifier, SUBJECT_ID

# Update VALID_TOPICS if you have more/fewer topics
VALID_TOPICS = ['1', '2', '3', '4', '5', '6', '7', '8']
```

---

## Step 4: Create Analysis Tool (5 minutes)

```bash
# Copy template
cp scripts/analyze_classifications.py scripts/analyze_mathematics_classifications.py

# Edit the file
code scripts/analyze_mathematics_classifications.py
```

**Update subject ID:**
```python
SUBJECT_ID = "your-uuid-here"  # Mathematics UUID

# Update topic names for display
topic_names = {
    "1": "Number",
    "2": "Algebra",
    "3": "Geometry",
    # ... your topics
}
```

---

## Step 5: Test Classification (5 minutes)

### Test on Sample Questions

Create `test_mathematics.py`:
```python
from mathematics_classifier import MathematicsClassifier
import os
from dotenv import load_dotenv

load_dotenv('.env.local')

classifier = MathematicsClassifier(
    os.getenv('GEMINI_API_KEY'),
    os.getenv('GROQ_API_KEY')
)

# Test questions
questions = [
    {"number": "1", "text": "Find the HCF of 24 and 36"},
    {"number": "2", "text": "Solve the quadratic equation x² + 5x + 6 = 0"},
    {"number": "3", "text": "Calculate the area of a circle with radius 5cm"}
]

for q in questions:
    result = classifier.classify_keyword_fallback(q)
    print(f"Q{q['number']}: Topic {result.topic} ({result.difficulty}, {result.confidence:.2f})")
```

Run:
```bash
python test_mathematics.py
```

Expected:
```
Q1: Topic 1 (medium, 0.45)  # Number
Q2: Topic 2 (medium, 0.50)  # Algebra
Q3: Topic 3 (medium, 0.40)  # Geometry
```

### Adjust Keywords if Needed

If classifications are wrong:
1. Check which keywords matched
2. Add more specific keywords
3. Increase weights on unique terms
4. Add negative keywords for false positives

---

## Step 6: Run Full Classification (Variable time)

```bash
# Classify all pages
python scripts/run_mathematics_classification.py
```

**What happens:**
1. Loads all Mathematics pages from Supabase
2. Downloads and extracts text from PDFs
3. Classifies in batches using hybrid system
4. Updates database with topics and difficulty
5. Reports statistics

**Expected time:** 10-20 minutes for ~500 pages

---

## Step 7: Analyze Results

```bash
python scripts/analyze_mathematics_classifications.py
```

**Look for:**
- ✅ 100% coverage (all pages have topics)
- ✅ Reasonable topic distribution (not 80% one topic)
- ✅ Difficulty distribution not >80% medium
- ✅ No invalid topic IDs

**Red flags:**
- ⚠️ >80% pages in one topic → Keywords too broad
- ⚠️ >90% medium difficulty → Improve difficulty detection
- ⚠️ Topic ratio >5:1 → Missing keywords for underrepresented topics

---

## Step 8: Fine-Tune (If Needed)

### If One Topic is Over-Represented

**Problem:** 60% of questions tagged as "Algebra"

**Solution:**
1. Check if those questions are actually Algebra (might be correct!)
2. If not, add negative keywords:
```yaml
negatives:
  - "solve for x"  # Too generic, appears in many topics
```
3. Add more specific core keywords for other topics

### If Difficulty is All Medium

**Problem:** 95% questions marked as "medium"

**Solution:**
1. Run difficulty re-classification:
```bash
cp scripts/reclassify_difficulty.py scripts/reclassify_mathematics_difficulty.py
# Update SUBJECT_ID in the file
python scripts/reclassify_mathematics_difficulty.py
```

### If Confidence is Low (<0.50 average)

**Problem:** Most classifications have confidence 0.30-0.40

**Solution:**
1. Add more core keywords (weight 5)
2. Add formulas specific to each topic
3. Check if negative keywords are too aggressive

---

## Step 9: Update Frontend (5 minutes)

The frontend should automatically pick up the new subject if:
- Subject exists in `subjects` table
- Subject has classified pages
- API endpoint recognizes subject_id

**Test:**
1. Go to http://localhost:3000/generate
2. Select your new subject from dropdown
3. Select a topic
4. Generate worksheet
5. Verify questions are relevant

---

## Step 10: Validate Quality

Create validation script:

```python
# scripts/validate_mathematics.py
def validate():
    # Load pages
    pages = load_pages_from_supabase(SUBJECT_ID)
    
    print(f"Total pages: {len(pages)}")
    
    # Check coverage
    missing_topics = [p for p in pages if not p.get('topics')]
    print(f"Missing topics: {len(missing_topics)}")
    assert len(missing_topics) == 0, "Some pages missing topics!"
    
    # Check difficulty distribution
    from collections import Counter
    diff_counts = Counter(p['difficulty'] for p in pages)
    for diff, count in diff_counts.items():
        pct = count / len(pages) * 100
        print(f"{diff}: {count} ({pct:.1f}%)")
    
    max_pct = max(diff_counts.values()) / len(pages)
    assert max_pct < 0.80, f"Difficulty too concentrated: {max_pct:.1%}"
    
    # Check topic balance
    topic_counts = Counter()
    for p in pages:
        topic_counts.update(p['topics'])
    
    print("\nTopic distribution:")
    for topic, count in sorted(topic_counts.items()):
        pct = count / len(pages) * 100
        print(f"Topic {topic}: {count} ({pct:.1f}%)")
    
    ratio = max(topic_counts.values()) / min(topic_counts.values())
    if ratio > 5:
        print(f"⚠️ Warning: Topic imbalance {ratio:.1f}:1")
    
    print("\n✅ Validation complete!")

if __name__ == '__main__':
    validate()
```

---

## Troubleshooting

### API Rate Limits

**Error:** `429 Rate limit exceeded`

**Solution:**
- Gemini free tier: 1500 RPM (should be fine)
- Groq free tier: 30 RPM (may hit limits)
- Add delays between requests
- Use larger batch sizes for Gemini

### Database Connection Errors

**Error:** `Connection timeout`

**Solution:**
- Check `.env.local` has correct Supabase URL and keys
- Verify subject_id exists in subjects table
- Check internet connection

### PDF Download Failures

**Error:** `Error downloading PDF`

**Solution:**
- Check URLs are valid
- Verify PDFs are publicly accessible
- Check storage bucket permissions

### Low Classification Quality

**Problem:** Random/incorrect topic assignments

**Solution:**
1. Add more specific keywords
2. Test on 20-30 sample questions manually
3. Check if topics are too similar (may need to merge)
4. Review and improve negative keywords

---

## Checklist

Before marking the subject as "done":

- [ ] Config file created with all topics
- [ ] 5+ core keywords per topic (weight 4-5)
- [ ] 3+ support keywords per topic (weight 2-3)
- [ ] Negative keywords added
- [ ] Classifier runs without errors
- [ ] Runner script completes successfully
- [ ] 100% page coverage achieved
- [ ] Topic distribution is reasonable
- [ ] Difficulty distribution not >80% one level
- [ ] Sample worksheets generate correctly
- [ ] Frontend displays subject correctly
- [ ] Validation script passes

---

## Time Estimate

| Step | Time | Cumulative |
|------|------|------------|
| 1. Config | 5 min | 5 min |
| 2. Classifier | 10 min | 15 min |
| 3. Runner | 5 min | 20 min |
| 4. Analysis | 5 min | 25 min |
| 5. Test | 5 min | 30 min |
| 6. Classify all | 15 min | 45 min |
| 7. Analyze | 2 min | 47 min |
| 8. Fine-tune | 10 min | 57 min |
| 9. Frontend | 5 min | 62 min |
| 10. Validate | 3 min | 65 min |

**Total: ~1 hour** (30 min without full classification)

---

## Need Help?

1. **Check existing implementation:**
   - `config/physics_topics.yaml` - Reference configuration
   - `scripts/hybrid_classifier.py` - Base classifier
   - `scripts/run_hybrid_classification.py` - Reference runner

2. **Read the rulebook:**
   - `CLASSIFICATION_RULEBOOK.md` - Complete specification

3. **Common patterns:**
   - Physics uses formulas heavily → Weight formulas at 5
   - Mathematics uses operation words → Weight "solve", "calculate" at 3-4
   - Biology uses process names → Weight specific processes at 5

---

**Good luck! 🚀**
