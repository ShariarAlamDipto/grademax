# Further Pure Mathematics Integration

This document explains how to add Further Pure Mathematics papers to the GradeMax system using the enhanced symbol-aware classifier.

## Overview

The system now supports **two classification modes**:

1. **Simple Mode** (Physics): Keyword-based classification
2. **Symbol-Aware Mode** (Further Pure): Advanced pattern matching with mathematical symbols

Both modes work seamlessly with the same pipeline code.

## Files Created

### 1. Configuration
- `config/further_pure_topics.yaml` - Complete topic definitions with symbol grammar

### 2. Classifier
- `scripts/symbol_aware_classifier.py` - Enhanced classifier supporting both modes
  - Automatically detects mode from YAML structure
  - Symbol normalization (θ → theta, x² → x^2)
  - Pattern matching with regex
  - Multi-topic support with confidence scores
  - LLM fallback for ambiguous cases
  - Backward compatible with Physics classifier

### 3. Database Setup
- `scripts/setup_further_pure_db.py` - Adds subject + 10 topics to database

### 4. Batch Processing
- `scripts/batch_process_further_pure.py` - Process all Further Pure papers

### 5. Testing
- `scripts/test_classifier.py` - Test both Physics and Further Pure modes

## Setup Instructions

### Step 1: Verify Configuration

Ensure your Further Pure papers are organized:
```
data/raw/IGCSE/FurtherPureMaths/
  2024/
    May-Jun/
      Paper 1.pdf
      Paper 1_MS.pdf
      Paper 2.pdf
      Paper 2_MS.pdf
  2023/
    Oct-Nov/
      Paper 1.pdf
      Paper 1_MS.pdf
```

### Step 2: Add Subject to Database

Run the database setup script **once**:

```powershell
python scripts/setup_further_pure_db.py
```

This will:
- Add subject "9FM0 - Further Pure Mathematics" to `subjects` table
- Add 10 topics to `topics` table:
  1. Logarithmic functions & indices
  2. Quadratic function
  3. Identities & inequalities
  4. Graphs
  5. Series (AP/GP)
  6. Binomial series
  7. Scalar & vector quantities
  8. Rectangular Cartesian coordinates
  9. Calculus
  10. Trigonometry

### Step 3: Test Classifier (Optional but Recommended)

Verify the classifier works correctly:

```powershell
python scripts/test_classifier.py
```

This tests:
- Physics mode (simple keywords)
- Further Pure mode with calculus question
- Further Pure mode with binomial question

Expected output:
```
✅ Physics classifier test PASSED
✅ Further Pure (Calculus) classifier test PASSED
✅ Further Pure (Binomial) classifier test PASSED
```

### Step 4: Process Papers

Run the batch processor:

```powershell
python scripts/batch_process_further_pure.py
```

This will:
1. Scan `data/raw/IGCSE/FurtherPureMaths/` for paper pairs
2. Split each paper into questions
3. Classify each question using symbol-aware mode
4. Compress PDFs (~33% size reduction)
5. Upload to Supabase Storage
6. Store metadata in database

**Processing time**: ~30-45 seconds per question (includes 4.5s rate limit)

### Step 5: Verify in UI

Open `/generate` page in the app:
1. Select "IGCSE Further Pure Mathematics" from subject dropdown
2. Topics should show: LOGS, QUAD, IDENT_INEQ, GRAPHS, SERIES, BINOMIAL, VECTORS, COORD, CALC, TRIG
3. Select years (2011-2025)
4. Generate worksheet

## Classification Details

### Symbol Grammar

The classifier normalizes and detects mathematical symbols:

**Normalization Rules:**
- Superscripts: x² → x^2
- Greek letters: θ → theta, π → pi
- Operators: × → *, ÷ → /

**Token Patterns:**
```yaml
derivatives: [\b(d/dx|dy/dx|f'\(x\))]
integrals: [(∫|\bint\b)]
trig_funcs: [\b(sin|cos|tan)\s*\(]
vectors: [\b(vector|[ij]\s*-?\s*component|\|\s*[a-z]\s*\|)]
choose_binom: [(C\([^)]+\)|nCr|\binom)]
```

### Scoring System

Topics are scored using weighted criteria:

- **Lexical (35%)**: Keyword matches
- **Symbols (45%)**: Mathematical symbol detection (PRIMARY)
- **Layout (5%)**: Visual elements (axes, diagrams)
- **Co-tag Prior (15%)**: Related topic boosting

**Hard Confidence Floors:**

If certain symbols are detected, minimum confidence is enforced:

- CALC: If `∫` or `d/dx` present → min 0.62
- BINOMIAL: If `C(n,r)` or `(1±x)^k` present → min 0.60
- TRIG: If `sin(A±B)` or R-formula present → min 0.58

### Multi-Topic Support

Further Pure questions can have **multiple topics** (unlike Physics):

Example output:
```python
result.topics = [
  {'id': 'CALC', 'code': '9', 'confidence': 0.86, 'evidence': ['∫...dx', 'dy/dx']},
  {'id': 'GRAPHS', 'code': '4', 'confidence': 0.58, 'evidence': ['tangent', 'axes']}
]
```

For backward compatibility, `result.topic` returns the **primary topic** (highest confidence).

### LLM Fallback

If rule-based confidence < 0.62, the classifier escalates to Gemini LLM with a specialized prompt that includes:
- Full taxonomy
- Symbol-first priority instructions
- JSON output schema
- Evidence requirement

## Backward Compatibility

### Physics Classification Still Works

The enhanced classifier **automatically detects** config type:

```python
# If config has 'symbol_grammar' section → Symbol-aware mode
# Otherwise → Simple mode (Physics)

classifier = SymbolAwareClassifier('config/physics_topics.yaml', api_key)
# Uses simple keyword matching

classifier = SymbolAwareClassifier('config/further_pure_topics.yaml', api_key)
# Uses symbol-first classification
```

### No Changes to Existing Code

The ingestion pipeline (`page_based_ingest.py`) works with both modes without modification:

```python
result = classifier.classify(text)
# Returns same ClassificationResult structure for both modes
```

## Troubleshooting

### Issue: "No paper pairs found"

**Cause**: Papers not in expected structure

**Solution**: Ensure papers follow naming:
```
data/raw/IGCSE/FurtherPureMaths/YYYY/Session/Paper X.pdf
data/raw/IGCSE/FurtherPureMaths/YYYY/Session/Paper X_MS.pdf
```

### Issue: "GEMINI_API_KEY not set"

**Cause**: Missing API key in `.env.ingest`

**Solution**: Add to `.env.ingest`:
```
GEMINI_API_KEY=your_key_here
```

### Issue: Classifier confidence too low

**Cause**: Question lacks distinctive symbols

**Solution**: 
1. Check if LLM fallback triggered (should auto-escalate)
2. Verify symbols are detected: Run `test_classifier.py`
3. Add more patterns to `config/further_pure_topics.yaml`

### Issue: Wrong topic assigned

**Cause**: Symbol patterns overlap or negative keywords present

**Solution**:
1. Check `postprocess.negatives_global` in YAML
2. Adjust `scoring.weights` to prioritize symbols more
3. Add `co_tag_prior` boosts to related topics

## Performance

### Processing Times (per paper)

- **Split into questions**: ~3 seconds
- **Classification**: ~4-6 seconds per question (with rate limit)
- **Compression**: ~1 second per PDF
- **Upload**: ~2 seconds per PDF
- **Database insert**: <1 second

**Example**: Paper with 8 questions = ~50 seconds total

### Storage Savings

PDF compression (JPEG quality 85):
- Original: ~500 KB per page
- Compressed: ~330 KB per page
- Savings: **~33%**

## Next Steps

After Further Pure is working:

1. **Add More Subjects**: Create YAML configs for:
   - Maths A (9MA0)
   - Maths B (4MB1)
   - Mechanics 1 (WME1)

2. **Enhance Classification**: Add more:
   - Symbol patterns
   - Methods detection
   - Structural patterns

3. **Multi-Tag Worksheets**: Update worksheet generator to:
   - Support multi-topic questions
   - Show confidence scores
   - Filter by methods used

## References

- **YAML Config**: `config/further_pure_topics.yaml`
- **Classifier**: `scripts/symbol_aware_classifier.py`
- **Pipeline**: `scripts/page_based_ingest.py`
- **Topics**: See Edexcel 9FM0 specification
