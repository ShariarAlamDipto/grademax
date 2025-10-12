# GradeMax - Complete Setup & Usage Guide

## 🎯 System Overview

GradeMax processes IGCSE Physics past papers into a searchable database organized by topics:

- **Storage**: `subjects/Physics/topics/1/2019_Jun_1P_Q1.pdf`
- **ONE topic per question** (no ambiguity)
- **Mark schemes linked** to each question
- **Bulk processing** of hundreds of papers
- **Gemini AI classification** with confidence scores

## 📋 Prerequisites

1. **Python 3.13.8** with virtual environment
2. **Supabase account** with project created
3. **Google Gemini API key** (free tier: 15 RPM, 1000 RPD)
4. **Node.js 18+** for Next.js frontend

## 🚀 Quick Start

### 1. Environment Setup

```powershell
# Set environment variables
$env:GEMINI_API_KEY="your-gemini-api-key"
$env:NEXT_PUBLIC_SUPABASE_URL="https://your-project.supabase.co"
$env:NEXT_PUBLIC_SUPABASE_ANON_KEY="your-anon-key"
```

Or create `.env` file:
```env
GEMINI_API_KEY=your-gemini-api-key
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### 2. Database Setup

Run in Supabase SQL Editor:

```sql
-- Run migrations/add_topic_code_and_ms.sql
ALTER TABLE questions 
ADD COLUMN IF NOT EXISTS topic_code TEXT,
ADD COLUMN IF NOT EXISTS ms_pdf_url TEXT,
ADD COLUMN IF NOT EXISTS confidence FLOAT;

CREATE INDEX IF NOT EXISTS idx_questions_topic_code ON questions(topic_code);
```

### 3. Storage Bucket Setup

1. Go to Supabase Dashboard → Storage
2. Create bucket: `question-pdfs`
3. Make it **public**
4. Set RLS policies for anon role

### 4. Install Dependencies

```powershell
# Python dependencies
pip install -r requirements.txt

# Node dependencies
npm install
```

## 📂 Directory Structure

```
grademax/
├── data/
│   ├── raw/              # Your past papers here
│   │   └── IGCSE/
│   │       └── 4PH1/
│   │           ├── 2019/
│   │           │   └── Jun/
│   │           │       ├── 4PH1_Jun19_QP_1P.pdf
│   │           │       └── 4PH1_Jun19_MS_1P.pdf
│   │           └── 2020/
│   │               └── Oct/
│   │                   ├── 4PH1_Oct20_QP_1P.pdf
│   │                   └── 4PH1_Oct20_MS_1P.pdf
│   └── processed/        # Auto-generated
│
├── config/
│   └── physics_topics.yaml    # 8 IGCSE topics
│
├── scripts/
│   ├── complete_pipeline.py   # Process single paper pair
│   ├── bulk_ingest.py          # Process entire directories
│   ├── single_topic_classifier.py
│   ├── split_pages.py
│   └── supabase_client.py
│
└── src/                  # Next.js frontend
    └── app/
        ├── browse/       # Browse by topic
        ├── worksheets/   # Generate worksheets
        └── api/
```

## 🔄 Processing Pipeline

### Process Single Paper

```powershell
python scripts/complete_pipeline.py `
  data/raw/IGCSE/4PH1/2019/Jun/4PH1_Jun19_QP_1P.pdf `
  data/raw/IGCSE/4PH1/2019/Jun/4PH1_Jun19_MS_1P.pdf
```

**What happens:**
1. ✅ Splits QP into individual questions → `data/processed/2019_Jun_1P/pages/q1.pdf`
2. ✅ Extracts mark schemes for each question → `data/processed/2019_Jun_1P/markschemes/q1_ms.pdf`
3. ✅ Classifies each question with Gemini AI → ONE topic per question
4. ✅ Uploads to storage → `subjects/Physics/topics/1/2019_Jun_1P_Q1.pdf`
5. ✅ Links mark scheme → `subjects/Physics/topics/1/2019_Jun_1P_Q1_MS.pdf`
6. ✅ Stores in database with full metadata

**Output:**
```
📋 Processing Paper: 2019_Jun_1P
1️⃣  Splitting QP into questions...
   ✅ Split into 10 questions
2️⃣  Extracting mark schemes...
   ✅ Q1 MS extracted
   ✅ Q2 MS extracted
   ...
3️⃣  Classifying questions with Gemini AI...
   [1/10] Q1 → Topic 1 (medium) [confidence: 0.95]
   [2/10] Q2 → Topic 3 (easy) [confidence: 0.98]
   ...
4️⃣  Uploading to Supabase Storage...
   ✅ Q1 uploaded to Topic 1
   ✅ Q2 uploaded to Topic 3
   ...
5️⃣  Storing in database...
   ✅ Stored 10 questions
✅ COMPLETE: 2019_Jun_1P
   Questions: 10
   Topics: {1, 2, 3, 5, 7}
```

### Bulk Process Multiple Papers

```powershell
# Process all papers in directory
python scripts/bulk_ingest.py data/raw/IGCSE/4PH1/

# Process first 5 papers (for testing)
python scripts/bulk_ingest.py data/raw/IGCSE/4PH1/ 5
```

**Example output:**
```
🚀 BULK INGESTION
📁 Scanning for papers...
✅ Found pair: 4PH1_Jun19_QP_1P.pdf + 4PH1_Jun19_MS_1P.pdf
✅ Found pair: 4PH1_Oct19_QP_1P.pdf + 4PH1_Oct19_MS_1P.pdf
✅ Found pair: 4PH1_Jun20_QP_1P.pdf + 4PH1_Jun20_MS_1P.pdf
...
✅ Found 50 paper pairs

📄 Paper 1/50
📋 Processing Paper: 2019_Jun_1P
...

📊 BULK PROCESSING COMPLETE
✅ Successful papers: 50/50
📝 Total questions: 550
```

**Processing Time:**
- 10 questions = ~2 minutes (1.5 min classification + 0.5 min upload/storage)
- 100 questions = ~15 minutes
- 500 questions = ~75 minutes (1.25 hours)

**Rate Limits:**
- Gemini Free Tier: 15 requests/minute, 1000/day
- Can process ~800 questions per day

## 🌐 Frontend Usage

### Start Development Server

```powershell
npm run dev
```

### Browse Questions by Topic

Navigate to: `http://localhost:3000/browse`

**Features:**
- Select any of 8 topics
- View all questions for that topic
- See metadata: Year, Season, Paper, Difficulty
- View question PDF with diagrams
- Download question PDF
- View mark scheme PDF

### Generate Custom Worksheets

Navigate to: `http://localhost:3000/worksheets`

**Features:**
- Select multiple topics
- Choose difficulty level
- Set number of questions
- Generate worksheet
- Download as single PDF

## 📊 Database Structure

### papers table
```
- id: uuid
- board: "IGCSE"
- level: "4PH1"
- subject: "Physics"
- year: 2019
- season: "Jun"
- paper_number: "1P"
- qp_path: "data/raw/.../QP_1P.pdf"
- ms_path: "data/raw/.../MS_1P.pdf"
- total_questions: 10
```

### questions table
```
- id: uuid
- paper_id: uuid → papers.id
- question_number: "1", "2a", "3"
- topic_code: "1" to "8" (ONE topic only)
- difficulty: "easy", "medium", "hard"
- page_pdf_url: "subjects/Physics/topics/1/2019_Jun_1P_Q1.pdf"
- ms_pdf_url: "subjects/Physics/topics/1/2019_Jun_1P_Q1_MS.pdf"
- has_diagram: boolean
- page_count: integer
- confidence: 0.0 to 1.0
```

## 🔍 Query Examples

### Get all questions for Topic 1 (Forces and motion)
```typescript
const { data } = await supabase
  .from('questions')
  .select('*, papers(*)')
  .eq('topic_code', '1')
  .not('page_pdf_url', 'is', null);
```

### Get medium difficulty questions
```typescript
const { data } = await supabase
  .from('questions')
  .select('*, papers(*)')
  .eq('difficulty', 'medium')
  .in('topic_code', ['1', '2', '3']);
```

### Get questions from specific year
```typescript
const { data } = await supabase
  .from('questions')
  .select('*, papers!inner(*)')
  .eq('papers.year', 2019)
  .eq('topic_code', '5');
```

## 🛠️ Maintenance

### Clear Database and Start Fresh

```sql
-- Delete all questions and papers
DELETE FROM questions;
DELETE FROM papers;
```

Then re-run bulk ingestion.

### Check Storage Usage

Go to Supabase Dashboard → Storage → question-pdfs

Expected structure:
```
subjects/
└── Physics/
    └── topics/
        ├── 1/
        │   ├── 2019_Jun_1P_Q1.pdf
        │   ├── 2019_Jun_1P_Q1_MS.pdf
        │   └── ...
        ├── 2/
        └── ...
```

### Monitor API Usage

- Gemini API: https://aistudio.google.com/apikey
- Check daily quota: 1000 requests/day
- Monitor rate limits: 15 requests/minute

## 📝 Topics Configuration

Edit `config/physics_topics.yaml` to customize:

```yaml
topics:
  - code: "1"
    name: "Forces and motion"
    keywords:
      - force
      - motion
      - acceleration
      - velocity
      - Newton's laws
    formulas:
      - "F = ma"
      - "v = u + at"
      - "s = ut + ½at²"
```

## 🐛 Troubleshooting

### No questions found for topic
- Check database: `SELECT * FROM questions WHERE topic_code = '1';`
- Verify storage: Check `subjects/Physics/topics/1/` folder
- Re-run ingestion if needed

### PDF 404 errors
- Ensure storage bucket is public
- Check RLS policies allow anon access
- Verify `page_pdf_url` column has correct paths

### Classification errors
- Verify Gemini API key is valid
- Check rate limits (15 RPM, 1000 RPD)
- Review `confidence` scores (< 0.7 may need manual review)

### Slow processing
- Normal: 4.5 seconds per question (rate limiting)
- 100 questions = ~7.5 minutes
- Run overnight for large batches

## 📚 Additional Resources

- **Architecture**: See `FINAL_ARCHITECTURE.md`
- **Redesign Notes**: See `REDESIGN_SINGLE_TOPIC.md`
- **Topics Config**: See `config/physics_topics.yaml`
- **Supabase Docs**: https://supabase.com/docs
- **Gemini API**: https://ai.google.dev/docs

## 🎉 Success Criteria

✅ Storage organized by subject/topic  
✅ ONE topic per question  
✅ Mark schemes linked to questions  
✅ Year/season/paper tracked  
✅ Fast topic-based queries  
✅ Bulk processing of hundreds of papers  
✅ Frontend displays PDFs correctly  
✅ Download functionality works  

---

**Ready to process your papers!** 🚀

Start with a single paper to test, then use bulk_ingest.py for your entire collection.
