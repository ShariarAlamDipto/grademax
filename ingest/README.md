# Ingestion Pipeline

This folder contains scripts to ingest past papers into GradeMax.

## Files

- **parse_pdf.ts** - Extract text from PDFs and split into questions
- **rules.ts** - Difficulty scoring, question normalization, topic keywords
- **embeddings.ts** - Generate embeddings using MiniLM-L6-v2
- **upload_storage.ts** - Upload PDFs to Supabase Storage
- **ingest_papers.ts** - Main orchestration script

## Setup

1. Create `.env.ingest` in project root:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE=your-service-role-key
```

2. Create data directory structure:
```
data/raw/
  IGCSE/
    4PH1/
      2019/Jun/
        4PH1_1P.pdf
        4PH1_1P_MS.pdf
```

3. Run schema SQL in Supabase (see `supabase/seed/schema.sql`)

4. Run topic seed SQL (see `supabase/seed/igcse_physics_topics.sql`)

## Usage

```bash
# Show help
npm run ingest:papers -- --help

# Dry run (parse but don't insert)
npm run ingest:papers -- --dry-run

# Actually ingest
npm run ingest:papers

# Custom data directory
npm run ingest:papers -- --data-dir=C:\path\to\papers
```

## How it works

1. Scans `data/raw/` for papers organized by Level/Subject/Year/Season
2. Uploads PDFs to Supabase Storage (`papers` bucket)
3. Parses questions using regex patterns
4. Determines difficulty (1-3) based on marks and command verbs
5. Generates embeddings for each question
6. Auto-tags topics using cosine similarity + keyword boosting
7. Matches markschemes by question number
8. Inserts everything to Supabase (papers, questions, markschemes, question_topics)

## Accuracy Notes

- Question splitting uses regex for "Question N", "Q N", "(a)", "(i)", etc.
- Difficulty = f(marks, command words) - calculate/explain/derive/evaluate
- Topic tagging = embeddings (semantic) + keyword boost (synonyms)
- Confidence threshold = 0.4 (top 3 topics per question)
- Markscheme matching = exact question number match (e.g., "Q5(b)(ii)")
