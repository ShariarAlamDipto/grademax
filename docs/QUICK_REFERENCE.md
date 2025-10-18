# Further Pure Mathematics - Quick Reference

## ⚡ Quick Commands

### Setup (Run Once)
```powershell
# 1. Add subject + topics to database
python scripts/setup_further_pure_db.py

# 2. Test classifier (optional)
python scripts/test_classifier.py

# 3. Process all papers
python scripts/batch_process_further_pure.py
```

### Individual Paper
```powershell
python scripts/page_based_ingest.py "data/raw/IGCSE/FurtherPureMaths/2024/May-Jun/Paper 1.pdf" "data/raw/IGCSE/FurtherPureMaths/2024/May-Jun/Paper 1_MS.pdf"
```

### Verify Physics Still Works
```powershell
python scripts/page_based_ingest.py "data/raw/IGCSE/Physics/2024/May-Jun/Paper 2.pdf" "data/raw/IGCSE/Physics/2024/May-Jun/Paper 2_MS.pdf"
```

## 📂 Required Folder Structure

```
data/raw/IGCSE/FurtherPureMaths/
  2024/
    May-Jun/
      Paper 1.pdf
      Paper 1_MS.pdf
  2023/
    Oct-Nov/
      Paper 1.pdf
      Paper 1_MS.pdf
```

## 🎯 10 Topics

| Code | ID | Name |
|------|-----|------|
| "1" | LOGS | Logarithmic functions & indices |
| "2" | QUAD | Quadratic function |
| "3" | IDENT_INEQ | Identities & inequalities |
| "4" | GRAPHS | Graphs & transformations |
| "5" | SERIES | Series (AP/GP) |
| "6" | BINOMIAL | Binomial series |
| "7" | VECTORS | Scalar & vector quantities |
| "8" | COORD | Cartesian coordinates |
| "9" | CALC | Calculus |
| "10" | TRIG | Trigonometry |

## 🔍 Symbol Detection

| Symbol | Normalized | Topic |
|--------|-----------|--------|
| ∫...dx | int...dx | CALC |
| d/dx, dy/dx, f'(x) | d/dx, dy/dx, f'(x) | CALC |
| C(n,r), ₙCᵣ | C(n,r), nCr | BINOMIAL |
| (1±x)ⁿ | (1±x)^n | BINOMIAL |
| Σ, S_n | Sigma, S_n | SERIES |
| sin(A±B) | sin(A±B) | TRIG |
| θ, π | theta, pi | TRIG/COORD |
| \|a\|, a·b | \|a\|, a·b | VECTORS |
| x² | x^2 | (any topic) |

## ⚙️ Classification Flow

```
1. Extract text from question
2. Normalize symbols (θ→theta, x²→x^2)
3. Detect token patterns (∫, d/dx, sin(), etc.)
4. Score topics:
   - Lexical: 35% (keywords)
   - Symbols: 45% (PRIMARY)
   - Layout: 5% (diagrams)
   - Co-tag: 15% (related topics)
5. Apply hard confidence floors
6. If max < 0.62 → Escalate to LLM
7. Return multi-topic result
```

## 📊 Expected Output

### Simple Question (Single Topic)
```python
ClassificationResult(
  topic="9",  # Calculus
  topics=[
    {'id': 'CALC', 'code': '9', 'confidence': 0.86, 
     'evidence': ['∫...dx', 'dy/dx']}
  ],
  confidence=0.86,
  difficulty="medium",
  methods=['chain rule'],
  dominant_ao="Algebra & calculus"
)
```

### Complex Question (Multi-Topic)
```python
ClassificationResult(
  topic="9",  # Primary: Calculus
  topics=[
    {'id': 'CALC', 'code': '9', 'confidence': 0.86, 
     'evidence': ['∫...dx', 'tangent']},
    {'id': 'GRAPHS', 'code': '4', 'confidence': 0.58,
     'evidence': ['axes present', 'y=f(x)']}
  ],
  confidence=0.86,
  difficulty="hard",
  methods=['chain rule', 'tangent equation'],
  dominant_ao="Algebra & calculus"
)
```

## 🔧 Troubleshooting

### "No paper pairs found"
- Check folder structure matches pattern above
- Ensure MS files have `_MS` suffix

### "GEMINI_API_KEY not set"
- Add to `.env.ingest`: `GEMINI_API_KEY=your_key`

### "Topic confidence too low"
- Check if question has distinctive symbols
- LLM should auto-escalate if confidence < 0.62
- Run `python scripts/test_classifier.py` to debug

### "Wrong topic assigned"
- Check question text for negative keywords
- Verify symbol patterns in YAML
- Adjust `scoring.weights` if needed

## 📈 Performance

- **Split**: ~3 sec per paper
- **Classify**: ~4-6 sec per question (with rate limit)
- **Compress**: ~1 sec per PDF (33% savings)
- **Upload**: ~2 sec per PDF
- **Total**: ~50 sec for 8-question paper

## ✅ Verification Checklist

After running setup:

- [ ] Database has subject "9FM0"
- [ ] Database has 10 topics (codes "1"-"10")
- [ ] Test script passes (3/3 tests)
- [ ] Batch processor finds papers
- [ ] UI shows "IGCSE Further Pure Mathematics"
- [ ] UI shows 10 topics in table
- [ ] Physics still works (no regression)

## 🚀 Next Subjects

Use same process for:
1. **Maths A (9MA0)**: Create `config/maths_a_topics.yaml`
2. **Maths B (4MB1)**: Create `config/maths_b_topics.yaml`
3. **Mechanics 1 (WME1)**: Create `config/mechanics_topics.yaml`

All use same classifier, same pipeline, same UI!

## 📚 Documentation

- **Setup Guide**: `docs/FURTHER_PURE_SETUP.md` (detailed)
- **Integration Summary**: `docs/INTEGRATION_SUMMARY.md` (overview)
- **This File**: `docs/QUICK_REFERENCE.md` (commands)

---

**Ready?** Run: `python scripts/setup_further_pure_db.py` 🚀
