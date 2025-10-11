# 🚀 Complete Ingestion Pipeline - Upload Papers & Generate Worksheets

## Current Status

✅ **Database Ready:**
- 20 subjects seeded
- 21 Physics topics seeded
- All tables created

❌ **No Questions Yet:**
- Questions table is empty
- That's why worksheet generation returns "No questions found"

**Solution:** You need to ingest past papers (PDFs) to extract questions!

---

## 📋 What You Need

### 1. Past Paper PDFs
Organize your PDFs like this:

```
data/papers/physics/
├── 2023_June_4PH1_1H_QP.pdf
├── 2023_June_4PH1_1H_MS.pdf
├── 2022_June_4PH1_1H_QP.pdf
├── 2022_June_4PH1_1H_MS.pdf
├── 2021_Nov_4PH1_1H_QP.pdf
├── 2021_Nov_4PH1_1H_MS.pdf
└── ... (more papers)
```

**Naming convention:**
- QP = Question Paper
- MS = Mark Scheme  
- Format: `YEAR_SEASON_CODE_PAPERNUMBER_TYPE.pdf`

### 2. Ingestion Modules (Already Built!)

You have 15 ingestion modules ready in `ingest/` folder:
- `01_extract_text.ts` - Extract text from PDF
- `02_parse_metadata.ts` - Get year, season, paper number
- `03_split_questions.ts` - Split into individual questions
- `04_parse_ms.ts` - Parse markscheme
- `05_link_ms_to_questions.ts` - Link markscheme to questions
- `06_tag_topics.ts` - Auto-tag questions with topics
- `07_assess_difficulty.ts` - Calculate difficulty scores
- `08_extract_diagrams.ts` - Extract images/diagrams
- `09_validate_quality.ts` - Quality checks
- `10_persist.ts` - Save to Supabase
- ... (5 more supporting modules)

---

## 🎯 Simple Ingestion Process (3 Options)

### Option A: **Manual Ingestion** (For Testing - 1 paper at a time)

```powershell
# 1. Place your PDF in data/papers/
# Example: data/papers/2023_June_4PH1_1H_QP.pdf

# 2. Run ingestion for that file
npx tsx ingest/run_single_paper.ts data/papers/2023_June_4PH1_1H_QP.pdf

# 3. Check database
npx tsx test_questions_count.ts
```

### Option B: **Batch Ingestion** (Process all papers in a folder)

```powershell
# 1. Place all PDFs in data/papers/physics/

# 2. Run batch ingestion
npx tsx ingest/run_batch.ts data/papers/physics/

# 3. Check progress
# Will show: "Processing 1/10: 2023_June_4PH1_1H_QP.pdf"
```

### Option C: **Web Upload** (Coming Soon - Upload via browser)

We'll create a simple upload page where you can:
1. Drag & drop PDFs
2. Click "Upload"
3. System processes automatically
4. Shows progress bar

---

## 🔧 Quick Setup (Option A - Test with 1 paper)

### Step 1: Create Single Paper Ingestion Script

I'll create this for you: `ingest/run_single_paper.ts`

### Step 2: Download a Test Paper

Get any Physics past paper PDF:
- Example: Edexcel IGCSE Physics 4PH1 June 2023 Paper 1H
- Save to: `data/papers/test_paper.pdf`

### Step 3: Run Ingestion

```powershell
npx tsx ingest/run_single_paper.ts data/papers/test_paper.pdf
```

You'll see output like:
```
📄 Processing: test_paper.pdf
✅ Step 1: Extracted text (1234 characters)
✅ Step 2: Parsed metadata (Year: 2023, Season: June)
✅ Step 3: Found 15 questions
✅ Step 4: Parsed markscheme
✅ Step 5: Linked markscheme to questions (15/15 matched)
✅ Step 6: Tagged topics (45 topic tags created)
✅ Step 7: Assessed difficulty
✅ Step 8: Extracted 23 diagrams
✅ Step 9: Quality validation passed
✅ Step 10: Saved to database (Paper ID: abc-123-def)

🎉 SUCCESS! 15 questions added to database
```

### Step 4: Verify Questions Exist

```powershell
npx tsx test_questions_count.ts
```

Should show:
```
✅ Found 15 questions for Physics 4PH1
```

### Step 5: Generate Worksheet

Now go to: http://localhost:3001/worksheets
- Select Physics 4PH1
- Select topics
- Click "Generate Worksheet"
- Should show questions! ✅

---

## 🏭 Full Production Setup (Option B - Batch)

### Step 1: Organize Your Papers

```
data/
└── papers/
    └── physics/
        ├── 2023_June_4PH1_1H_QP.pdf
        ├── 2023_June_4PH1_1H_MS.pdf
        ├── 2023_June_4PH1_1F_QP.pdf
        ├── 2023_June_4PH1_1F_MS.pdf
        ├── 2022_June_4PH1_1H_QP.pdf
        ├── 2022_June_4PH1_1H_MS.pdf
        └── ... (more papers)
```

**Important:**
- Each QP should have matching MS
- Use consistent naming
- Keep them organized by subject

### Step 2: Run Batch Ingestion

```powershell
npx tsx ingest/run_batch.ts data/papers/physics/
```

Will process all papers one by one:
```
📦 Batch Ingestion Started
Found 20 PDF files (10 QP, 10 MS pairs)

[1/10] Processing: 2023_June_4PH1_1H_QP.pdf
        ✅ 15 questions extracted
[2/10] Processing: 2023_June_4PH1_1F_QP.pdf
        ✅ 12 questions extracted
[3/10] Processing: 2022_June_4PH1_1H_QP.pdf
        ✅ 14 questions extracted
...

🎉 Complete! Processed 10 papers, extracted 141 questions
```

### Step 3: Verify

```powershell
npx tsx test_questions_count.ts
```

Should show:
```
✅ Physics 4PH1: 141 questions across 10 papers
✅ Topics coverage:
   - 1a (Units): 8 questions
   - 1b (Movement): 12 questions
   - 1c (Forces): 15 questions
   - 2a (Electricity): 11 questions
   ... (all topics covered)
```

---

## 🌐 Option C: Web Upload Interface (Recommended)

Let me create a simple upload page for you!

### Features:
- Drag & drop PDFs
- Automatic processing
- Real-time progress
- Error handling
- Shows questions extracted

### Location:
`http://localhost:3001/admin/upload`

### Usage:
1. Go to upload page
2. Drag & drop multiple PDFs
3. Click "Start Processing"
4. Watch progress
5. Done! Questions added to database

---

## 🎯 Which Option Should You Use?

| Option | Best For | Time | Difficulty |
|--------|----------|------|------------|
| **A: Single Paper** | Testing, Learning | 5 min | Easy ⭐ |
| **B: Batch** | Production, Many papers | 30 min | Medium ⭐⭐ |
| **C: Web Upload** | Easiest, User-friendly | 10 min | Easy ⭐ |

**Recommendation:**

1. **Start with Option A** - Test with 1 paper to make sure it works
2. **Then use Option C** - Web upload for regular use
3. **Use Option B** - For bulk processing many papers at once

---

## 📊 Expected Results

After ingesting papers, you should have:

```
Database Status:
├── Subjects: 20 ✅
├── Topics: 21 (Physics) ✅
├── Papers: 10 (or however many you uploaded) ✅
├── Questions: 100+ ✅
├── Question Parts: 300+ ✅
├── Question Topics: 500+ (tags linking questions to topics) ✅
└── Markschemes: 100+ ✅
```

Then worksheet generation will work:
- Select Physics
- Select topics
- Generate worksheet
- **Questions appear!** 🎉

---

## 🚀 Let Me Create The Scripts For You

I'll create:

1. **`ingest/run_single_paper.ts`** - For Option A
2. **`ingest/run_batch.ts`** - For Option B  
3. **`src/app/admin/upload/page.tsx`** - For Option C (web interface)
4. **`test_questions_count.ts`** - To verify questions

These will use your existing 15 ingestion modules.

**Say "yes" and I'll create all these files for you!**

Then you can:
1. Upload 1 test paper → See it work
2. Upload all your papers → Build question bank
3. Generate worksheets → It works! ✨

---

## 💡 Summary

**Problem:** No questions in database → Worksheet generation fails

**Solution:** Ingest past papers to extract questions

**Steps:**
1. Get PDF papers (QP + MS)
2. Run ingestion (I'll create scripts)
3. Questions appear in database
4. Worksheet generation works! ✅

**Ready to create the ingestion scripts?** 🚀
