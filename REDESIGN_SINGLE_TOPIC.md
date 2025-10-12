# 🔄 SYSTEM REDESIGN: Single Topic Per Question

## Changes Made

### 1. Classification System
**OLD**: Multiple topics per question
**NEW**: ONE primary topic per question

**Files:**
- ✅ `scripts/single_topic_classifier.py` - New simple classifier
- ❌ `scripts/classify_with_gemini.py` - Old multi-topic (deprecated)

### 2. Storage Organization
**OLD**: PDFs stored by paper: `2019/Jun/1P/Q2.pdf`
**NEW**: PDFs stored by topic: `topics/1/Q2.pdf`, `topics/5/Q7.pdf`

**Benefits:**
- Easy to find all questions for a topic
- Simpler download: "Give me all Topic 1 questions"
- Clear organization by subject matter

### 3. Database Structure
**Current** (to keep):
```sql
questions (
  id uuid PRIMARY KEY,
  question_number text,
  paper_id uuid,
  page_pdf_url text,  -- Now: "topics/1/Q2.pdf"
  difficulty int,
  has_diagram boolean,
  classification_confidence float
)

question_topics (
  question_id uuid,
  topic_id uuid,
  confidence float
)
```

**Change**: Each question will have ONLY ONE entry in `question_topics`

### 4. Simplified Pipeline
**File**: `scripts/simple_ingest.py`

**Steps:**
1. Split PDF by question
2. Classify with ONE topic (using Gemini)
3. Upload to `topics/{code}/Q{num}.pdf`
4. Store in database with single topic link

### 5. Frontend Display
Questions will show:
- PDF from: `https://.../storage/v1/object/public/question-pdfs/topics/1/Q2.pdf`
- Single topic badge
- Difficulty level

### 6. Worksheet Generation
**OLD**: Complex topic filtering with multiple topics per question
**NEW**: Simple - select questions WHERE topic_id = X

## How to Use

### Re-ingest a Paper:
```powershell
$env:GEMINI_API_KEY="..."
$env:NEXT_PUBLIC_SUPABASE_URL="..."
$env:NEXT_PUBLIC_SUPABASE_ANON_KEY="..."

python scripts/simple_ingest.py data/raw/IGCSE/4PH1/2019/Jun/4PH1_Jun19_QP_1P.pdf
```

### What Happens:
1. Splits PDF → `data/processed/4PH1_2019_Jun_1P/pages/q2.pdf`
2. Classifies each → "Topic 1: Forces"
3. Uploads → `topics/1/Q2.pdf` in storage
4. Stores → Database with single topic link

### Generate Worksheet:
1. User selects "Topic 1: Forces"
2. Query: `SELECT * FROM questions WHERE id IN (SELECT question_id FROM question_topics WHERE topic_id = '...')`
3. Returns all Topic 1 questions
4. Frontend displays PDFs from `topics/1/` folder

## Files Cleaned Up

Removed redundant files:
- ❌ All test_*.py files
- ❌ All check_*.py files  
- ❌ All verify_*.py files
- ❌ All debug_*.py files
- ❌ All *_FIX.md files
- ❌ All *_GUIDE.md files
- ❌ All *_STATUS.md files
- ❌ Many duplicate documentation files

Kept essential files:
- ✅ README.md
- ✅ config/physics_topics.yaml
- ✅ scripts/split_pages.py
- ✅ scripts/single_topic_classifier.py (NEW)
- ✅ scripts/simple_ingest.py (NEW)
- ✅ scripts/supabase_client.py
- ✅ Frontend code (src/)

## Next Steps

1. **Clear old data** (optional):
   ```sql
   DELETE FROM question_topics;
   DELETE FROM questions;
   DELETE FROM papers;
   ```

2. **Re-ingest with new system**:
   ```powershell
   python scripts/simple_ingest.py data/raw/IGCSE/4PH1/2019/Jun/4PH1_Jun19_QP_1P.pdf
   ```

3. **Test worksheet generation**:
   - Go to http://localhost:3000/worksheets
   - Select one topic
   - Generate worksheet
   - Should see questions from that topic only

## Benefits

✅ **Simpler**: ONE topic per question (not multiple)
✅ **Clearer**: PDFs organized by topic folder
✅ **Faster**: Direct query by topic
✅ **Cleaner**: Less redundant code/files
✅ **Better UX**: "All Forces questions" → instant results

## Questions Storage Example

```
question-pdfs/
├── topics/
│   ├── 1/           # Forces and motion
│   │   ├── Q2.pdf
│   │   ├── Q7.pdf
│   │   └── Q11.pdf
│   ├── 2/           # Electricity
│   │   ├── Q3.pdf
│   │   └── Q9.pdf
│   ├── 5/           # Solids, liquids, gases
│   │   ├── Q4.pdf
│   │   ├── Q6.pdf
│   │   └── Q12.pdf
│   └── ...
```

Each PDF is a complete question page with diagrams!
