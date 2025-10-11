# 🚀 GradeMax Setup Guide

Complete guide to set up the worksheet generator with UUID schema.

---

## ✅ Prerequisites

- Node.js 18+ installed
- npm working (check execution policy on Windows)
- Supabase project created
- Git installed

---

## 📦 Step 1: Install Dependencies

```cmd
npm install
```

This installs:
- `pdf-parse` - PDF text extraction
- `@xenova/transformers` - Embeddings (MiniLM-L6-v2)
- `zod` - Request validation
- `@supabase/ssr` - Supabase client for Next.js
- `ts-node` - TypeScript execution

Self-check:
```cmd
npm ls pdf-parse @xenova/transformers zod
```

---

## 🔑 Step 2: Environment Variables

Create `.env.local` (for Next.js app):
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
```

Create `.env.ingest` (for ingestion scripts):
```env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE=your-service-role-key-here
```

> **Important:** Get service role key from Supabase Dashboard → Settings → API

---

## 🗄️ Step 3: Create Database Schema

1. Open Supabase Dashboard → SQL Editor
2. Copy contents of `supabase/seed/schema.sql`
3. Run the entire script
4. Verify tables exist:

```sql
SELECT tablename FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;
```

You should see:
- subjects
- topics
- papers
- questions
- markschemes
- question_topics
- worksheets
- worksheet_items

---

## 🌱 Step 4: Seed Physics Topics

1. Open Supabase Dashboard → SQL Editor
2. Copy contents of `supabase/seed/igcse_physics_topics.sql`
3. Run the script
4. Verify:

```sql
SELECT code, name FROM topics 
WHERE subject_id = (
  SELECT id FROM subjects 
  WHERE code='4PH1' AND level='IGCSE'
)
ORDER BY code;
```

Should return 21 topics (1a-8b).

---

## 🧪 Step 5: Test the App

Start dev server:
```cmd
npm run dev
```

Visit http://localhost:3000/worksheets

You should see:
- ✅ Subject dropdown (IGCSE Physics)
- ✅ Topics checkboxes (21 topics)
- ✅ Difficulty, count, markscheme toggles
- ❌ Generate won't work yet (no questions ingested)

---

## 📂 Step 6: Prepare PDFs

Create this structure in your project:

```
data/
  raw/
    IGCSE/
      4PH1/
        2019/
          Jun/
            4PH1_1P.pdf        ← Question paper
            4PH1_1P_MS.pdf     ← Markscheme
        2020/
          Nov/
            4PH1_1P.pdf
            4PH1_1P_MS.pdf
```

**Rules:**
- Name format: `{paper_code}.pdf` and `{paper_code}_MS.pdf`
- Paper codes: `4PH1_1P`, `4PH1_2P`, etc.
- Both files must be in same folder

---

## 🔄 Step 7: Ingest Papers

### Dry Run (Test Parsing)
```cmd
npm run ingest:papers -- --dry-run
```

This will:
- ✅ Load topics and generate embeddings
- ✅ Parse PDFs
- ✅ Extract questions
- ✅ Show what would be inserted
- ❌ NOT insert to database

### Real Ingestion
```cmd
npm run ingest:papers
```

This will:
1. Upload PDFs to Supabase Storage (`papers` bucket)
2. Parse questions from paper PDF
3. Parse markschemes from MS PDF
4. Compute difficulty (1-3) based on marks + command verbs
5. Generate embeddings for each question
6. Auto-tag topics using cosine similarity + keyword boosting
7. Match markschemes by question number
8. Insert everything to database

**Expected output:**
```
🚀 GradeMax Paper Ingestion

Data directory: ./data/raw
Dry run: false

📚 Loading topics...
  ✓ 1a - Units
  ✓ 1b - Movement and position
  ...
✓ Loaded 21 topics

📄 Processing IGCSE/4PH1/2019/Jun/4PH1_1P
  📤 Uploading PDFs...
    ✓ Paper: https://...supabase.co/storage/v1/object/public/papers/...
    ✓ MS: https://...supabase.co/storage/v1/object/public/papers/...
  📖 Parsing questions...
    ✓ Found 25 questions
  📖 Parsing markscheme...
    ✓ Found 25 markscheme entries
  💾 Inserting questions...
    ✓ Q1(a): 2 topic(s) tagged
    ✓ Q1(a): markscheme linked
    ...
  ✅ Completed 4PH1_1P

✅ Ingestion complete!
```

---

## 🎯 Step 8: Generate Worksheets

1. Refresh http://localhost:3000/worksheets
2. Select **IGCSE Physics (4PH1)**
3. Select topics (e.g., "Forces and motion", "Electricity")
4. Choose difficulties (1=easy, 2=medium, 3=hard)
5. Set question count (5-50)
6. Toggle "Include markscheme" if needed
7. Click **Generate Worksheet**

You should see:
- Questions with source (e.g., "2019 Jun Paper 1P")
- Difficulty badges (Easy/Medium/Hard)
- Marks for each question
- Markschemes (if toggled)
- Print button

---

## 🔍 Troubleshooting

### "Cannot find module 'zod'"
Run `npm install` again. Check that `zod` is in `package.json`.

### "Subject not found"
Make sure you ran `igcse_physics_topics.sql` in Supabase.

### "No questions found"
You need to ingest at least one paper. Check Step 7.

### Embeddings slow on first run
The model (~100MB) downloads once and caches. Subsequent runs are fast.

### Wrong topic predictions
Edit `ingest/rules.ts` → `topicKeywords` to boost keywords for topics.
Then re-run ingestion:
```cmd
npm run ingest:papers
```

### PowerShell execution policy error
Run PowerShell as **Administrator**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│  Next.js 15 App (Browser)               │
│  - /worksheets (generator UI)           │
│  - Tailwind CSS styling                 │
└──────────────┬──────────────────────────┘
               │ fetch()
               v
┌─────────────────────────────────────────┐
│  API Routes (Server)                    │
│  - /api/subjects                        │
│  - /api/topics?subjectId=...            │
│  - /api/worksheets/generate (POST)      │
└──────────────┬──────────────────────────┘
               │ @supabase/ssr
               v
┌─────────────────────────────────────────┐
│  Supabase (PostgreSQL + pgvector)       │
│  - subjects, topics, papers             │
│  - questions (with embeddings)          │
│  - markschemes, question_topics         │
│  - worksheets, worksheet_items          │
│  - Storage: papers bucket (PDFs)        │
└─────────────────────────────────────────┘
               ^
               │ @supabase/supabase-js
               │ (service role)
┌─────────────────────────────────────────┐
│  Ingestion Scripts (Node.js)            │
│  - parse_pdf.ts (extract text)          │
│  - rules.ts (difficulty, keywords)      │
│  - embeddings.ts (MiniLM-L6-v2)         │
│  - upload_storage.ts (upload PDFs)      │
│  - ingest_papers.ts (orchestrator)      │
│                                          │
│  Auto-Tagging Pipeline:                 │
│  1. Embed question text                 │
│  2. Compute cosine similarity to topics │
│  3. Boost with keyword matches          │
│  4. Tag top 3 with confidence > 0.4     │
└─────────────────────────────────────────┘
```

---

## 📝 Next Steps

1. ✅ Ingest more papers (2019-2024, Jun/Nov)
2. ✅ Test worksheet generation with different filters
3. ✅ Add Chemistry/Maths subjects (create topics SQL)
4. ✅ Implement PDF export (using jsPDF or similar)
5. ✅ Add user authentication (Supabase Auth)
6. ✅ Track worksheet history per user
7. 🚀 Deploy to Vercel

---

## 🎓 Tips

- **Accuracy:** The more papers you ingest, the better the variety
- **Topic Tagging:** Adjust keyword synonyms in `ingest/rules.ts`
- **Performance:** First embedding generation is slow (model download), then fast
- **Storage:** PDFs are public in Supabase Storage (change policies for private)
- **RLS:** Currently open for dev - tighten policies before production

---

## 📚 Reference

- Supabase Dashboard: https://app.supabase.com
- Next.js Docs: https://nextjs.org/docs
- @xenova/transformers: https://huggingface.co/docs/transformers.js
- pdf-parse: https://www.npmjs.com/package/pdf-parse

---

**All code is ready!** Just follow these steps and you'll have a working worksheet generator. 🎉
