# GradeMax Worksheet Generator - Setup Guide

## 1. Install Dependencies

### Fix PowerShell Execution Policy (if needed)
Run PowerShell as **Administrator** and execute:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then install dependencies:
```bash
npm install
```

This will install:
- `pdf-parse` - PDF text extraction
- `@xenova/transformers` - Semantic embeddings (MiniLM-L6-v2)
- `yaml` - Synonym config parser
- `ts-node` - TypeScript execution for ingestion scripts
- `recharts` - Dashboard charts

---

## 2. Create Supabase Tables

Go to your Supabase project → SQL Editor → New query, and run this:

```sql
-- Create subjects table
CREATE TABLE IF NOT EXISTS subjects (
  id BIGSERIAL PRIMARY KEY,
  board TEXT NOT NULL,
  level TEXT NOT NULL,
  code TEXT NOT NULL,
  name TEXT NOT NULL,
  color TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(board, level, code)
);

-- Create topics table
CREATE TABLE IF NOT EXISTS topics (
  id BIGSERIAL PRIMARY KEY,
  subject_id BIGINT REFERENCES subjects(id) ON DELETE CASCADE,
  code TEXT NOT NULL,
  name TEXT NOT NULL,
  spec_ref TEXT,
  content TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(subject_id, code)
);

-- Create papers table
CREATE TABLE IF NOT EXISTS papers (
  id BIGSERIAL PRIMARY KEY,
  subject_id BIGINT REFERENCES subjects(id) ON DELETE CASCADE,
  paper_number TEXT NOT NULL,
  year INT NOT NULL,
  season TEXT NOT NULL,
  pdf_url TEXT,
  markscheme_pdf_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(subject_id, year, season, paper_number)
);

-- Create questions table
CREATE TABLE IF NOT EXISTS questions (
  id BIGSERIAL PRIMARY KEY,
  paper_id BIGINT REFERENCES papers(id) ON DELETE CASCADE,
  question_number TEXT NOT NULL,
  text TEXT NOT NULL,
  diagram_urls TEXT[],
  marks INT,
  difficulty INT CHECK (difficulty >= 1 AND difficulty <= 3),
  embedding VECTOR(384), -- for MiniLM-L6-v2
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create markschemes table
CREATE TABLE IF NOT EXISTS markschemes (
  id BIGSERIAL PRIMARY KEY,
  question_id BIGINT REFERENCES questions(id) ON DELETE CASCADE,
  text TEXT NOT NULL,
  marks_breakdown JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(question_id)
);

-- Create question_topics junction table (many-to-many)
CREATE TABLE IF NOT EXISTS question_topics (
  id BIGSERIAL PRIMARY KEY,
  question_id BIGINT REFERENCES questions(id) ON DELETE CASCADE,
  topic_id BIGINT REFERENCES topics(id) ON DELETE CASCADE,
  confidence REAL DEFAULT 1.0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(question_id, topic_id)
);

-- Enable RLS (if you want row-level security)
ALTER TABLE subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE papers ENABLE ROW LEVEL SECURITY;
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE markschemes ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_topics ENABLE ROW LEVEL SECURITY;

-- Create policies (allow all for now - adjust later)
CREATE POLICY "Allow all operations" ON subjects FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations" ON topics FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations" ON papers FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations" ON questions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations" ON markschemes FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations" ON question_topics FOR ALL USING (true) WITH CHECK (true);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_questions_paper_id ON questions(paper_id);
CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions(difficulty);
CREATE INDEX IF NOT EXISTS idx_markschemes_question_id ON markschemes(question_id);
CREATE INDEX IF NOT EXISTS idx_question_topics_question_id ON question_topics(question_id);
CREATE INDEX IF NOT EXISTS idx_question_topics_topic_id ON question_topics(topic_id);
CREATE INDEX IF NOT EXISTS idx_topics_subject_id ON topics(subject_id);
CREATE INDEX IF NOT EXISTS idx_papers_subject_id ON papers(subject_id);

-- Create vector similarity index (for semantic search)
CREATE INDEX IF NOT EXISTS idx_questions_embedding ON questions 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

---

## 3. Seed Physics Topics

Run the SQL in `ingest/seed_physics_topics.sql` in Supabase SQL Editor:

```bash
# Or from command line (if you have psql)
psql "postgres://[user]:[password]@[host]:5432/postgres" < ingest/seed_physics_topics.sql
```

This will insert 26 Physics topics across 8 main areas:
- Forces and motion
- Electricity
- Waves
- Energy resources
- Solids, liquids, gases
- Magnetism and electromagnetism
- Radioactivity
- Astrophysics

---

## 4. Test the App

Start the dev server:
```bash
npm run dev
```

Visit http://localhost:3000 and check:
- ✅ Authentication (Google OAuth via Supabase)
- ✅ Dashboard loads with your name
- ✅ Worksheets page shows subject/topic dropdowns

---

## 5. Ingest Sample Paper

### Step 1: Build topic embeddings
```bash
npm run ingest:topics
```
This creates `topic_index.json` with embeddings for all topics.

### Step 2: Extract questions from a PDF
Place a past paper PDF in `ingest/data/papers/` (e.g., `4PH1_1P_2023_Jun.pdf`)

Run:
```bash
npx ts-node ingest/extract_questions.ts ingest/data/papers/4PH1_1P_2023_Jun.pdf
```

This creates `4PH1_1P_2023_Jun_questions.json`.

### Step 3: Extract markscheme
Place the markscheme PDF in `ingest/data/markschemes/` (e.g., `4PH1_1P_2023_Jun_MS.pdf`)

Run:
```bash
npx ts-node ingest/extract_markschemes.ts ingest/data/markschemes/4PH1_1P_2023_Jun_MS.pdf
```

This creates `4PH1_1P_2023_Jun_MS_markschemes.json`.

### Step 4: Ingest to Supabase (auto-tag topics)
```bash
npx ts-node ingest/ingest_to_supabase.ts \
  --subject-id=1 \
  --paper=1P \
  --year=2023 \
  --season=Jun \
  --questions=4PH1_1P_2023_Jun_questions.json \
  --markschemes=4PH1_1P_2023_Jun_MS_markschemes.json
```

This will:
- Insert the paper into `papers` table
- Insert questions into `questions` table
- Match markschemes by question number
- **Auto-tag topics** using embeddings + synonyms
- Store confidence scores in `question_topics`

---

## 6. Generate a Worksheet

1. Go to http://localhost:3000/worksheets
2. Select **Physics (4PH1)**
3. Choose topics (e.g., "Forces and motion", "Electricity")
4. Set difficulty (1=easy, 2=medium, 3=hard)
5. Set number of questions (e.g., 10)
6. Click **Generate Worksheet**

The API will:
- Filter questions by topics and difficulty
- Balance questions across selected topics
- Return questions with markschemes

---

## 7. Review Auto-Tagged Questions (Admin)

Go to http://localhost:3000/admin/tagger

This page lets you:
- See all questions with their **predicted topics** (auto-tagged)
- **Confidence scores** for each topic (0-1)
- Manually **correct** tags by adding/removing topics
- Save changes to `question_topics` table

---

## 8. Environment Variables

Make sure your `.env.local` has:
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

---

## Troubleshooting

### "Cannot find module 'pdf-parse'"
Run `npm install` (fix execution policy first if needed)

### "No topics found for subject"
Check that Physics topics were seeded correctly in Supabase

### "No questions generated"
Check that you've ingested at least one paper with auto-tagging

### Embeddings too slow
First run creates the model cache (~100MB download). Subsequent runs are fast.

### Wrong topic predictions
Adjust `ingest/synonyms.yml` to boost keywords for each topic, then re-run ingestion

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (Next.js 15 + React 19)                       │
│  - src/app/worksheets/page.tsx  (generator UI)          │
│  - src/app/admin/tagger/page.tsx  (QA tool)             │
└──────────────────┬──────────────────────────────────────┘
                   │
                   v
┌─────────────────────────────────────────────────────────┐
│  API Routes                                              │
│  - /api/generate-worksheet  (filter + balance)          │
│  - /api/subjects            (list subjects)             │
│  - /api/topics              (list topics by subject)    │
└──────────────────┬──────────────────────────────────────┘
                   │
                   v
┌─────────────────────────────────────────────────────────┐
│  Supabase (PostgreSQL + pgvector)                       │
│  - subjects, topics, papers, questions, markschemes     │
│  - question_topics (many-to-many with confidence)       │
│  - Vector similarity search on question embeddings      │
└─────────────────────────────────────────────────────────┘
                   ^
                   │
┌─────────────────────────────────────────────────────────┐
│  Ingestion Pipeline (TypeScript + Node)                 │
│  1. build_topic_index.ts      → topic_index.json        │
│  2. extract_questions.ts      → questions.json          │
│  3. extract_markschemes.ts    → markschemes.json        │
│  4. ingest_to_supabase.ts     → auto-tag + insert       │
│                                                          │
│  Auto-Tagging:                                           │
│  - Semantic: cosine_similarity(question, topic)         │
│  - Keyword: boost if synonyms match                     │
│  - Threshold: confidence > 0.5 → tag applied            │
└─────────────────────────────────────────────────────────┘
```

---

## Next Steps

1. ✅ Fix PowerShell policy and run `npm install`
2. ✅ Create Supabase tables (SQL above)
3. ✅ Seed Physics topics
4. ✅ Test app at http://localhost:3000
5. ✅ Ingest a sample paper (follow Step 5)
6. ✅ Generate a worksheet
7. ✅ Review/correct tags in admin tagger
8. 🚀 Deploy to Vercel (connect Supabase, add env vars)

**All code is ready to run!** Just need to install deps, create DB tables, and seed topics.
