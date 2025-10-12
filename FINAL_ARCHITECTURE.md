# GradeMax - Final Architecture Specification

## Storage Hierarchy

```
question-pdfs/
├── subjects/
│   └── Physics/
│       └── topics/
│           ├── 1/  (Forces and motion)
│           │   ├── 2019_Jun_1P_Q1.pdf
│           │   ├── 2019_Jun_1P_Q1_MS.pdf
│           │   ├── 2020_Oct_2P_Q3.pdf
│           │   └── 2020_Oct_2P_Q3_MS.pdf
│           ├── 2/  (Electricity)
│           │   ├── 2019_Jun_1P_Q5.pdf
│           │   └── 2019_Jun_1P_Q5_MS.pdf
│           ├── 3/  (Waves)
│           ├── 4/  (Energy resources)
│           ├── 5/  (Solids, liquids and gases)
│           ├── 6/  (Magnetism and electromagnetism)
│           ├── 7/  (Radioactivity and particles)
│           └── 8/  (Astrophysics)
```

## Database Schema

### papers
```sql
- id (uuid, PK)
- board (text) - "IGCSE"
- level (text) - "4PH1"
- subject (text) - "Physics"
- year (int) - 2019
- season (text) - "Jun"
- paper_number (text) - "1P"
- qp_path (text) - Original QP file path
- ms_path (text) - Original MS file path
- total_questions (int)
- processed_at (timestamp)
```

### questions
```sql
- id (uuid, PK)
- paper_id (uuid, FK → papers)
- question_number (text) - "1", "2a", "3"
- topic_code (text) - "1" to "8" (ONE topic only)
- difficulty (text) - "easy", "medium", "hard"
- page_pdf_url (text) - "subjects/Physics/topics/1/2019_Jun_1P_Q1.pdf"
- ms_pdf_url (text) - "subjects/Physics/topics/1/2019_Jun_1P_Q1_MS.pdf"
- has_diagram (bool)
- page_count (int)
- confidence (float) - LLM classification confidence
- created_at (timestamp)
```

### topics (existing - no changes needed)
```sql
- id (uuid, PK)
- code (text) - "1" to "8"
- name (text) - "Forces and motion"
- subject (text) - "Physics"
```

## Processing Pipeline

### 1. Split Phase
```python
Input: data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf
Output: 
  - data/processed/2019_Jun_1P/pages/q1.pdf
  - data/processed/2019_Jun_1P/pages/q2.pdf
  - data/processed/2019_Jun_1P/pages/q3.pdf
  - manifest.json (metadata)
```

### 2. Classification Phase
```python
For each question PDF:
  - Send to Gemini API with text extract
  - Get ONE topic code (1-8)
  - Get difficulty level
  - Get confidence score
```

### 3. Mark Scheme Matching Phase
```python
For each question:
  - Find corresponding MS pages
  - Extract MS for same question number
  - Save as separate MS PDF
```

### 4. Upload Phase
```python
For each question:
  - Upload QP: subjects/Physics/topics/{code}/2019_Jun_1P_Q{num}.pdf
  - Upload MS: subjects/Physics/topics/{code}/2019_Jun_1P_Q{num}_MS.pdf
  - Get public URLs
```

### 5. Database Storage Phase
```python
For each question:
  - Insert/update paper record
  - Insert question record with:
    - paper_id
    - question_number
    - topic_code (single value)
    - page_pdf_url
    - ms_pdf_url
    - metadata
```

## Frontend Workflow

### Topic Selection
```typescript
1. User selects "Topic 1: Forces and motion"
2. API query: GET /api/questions?topic_code=1
3. Returns all questions with topic_code="1"
4. Each question has:
   - page_pdf_url: "subjects/Physics/topics/1/2019_Jun_1P_Q3.pdf"
   - ms_pdf_url: "subjects/Physics/topics/1/2019_Jun_1P_Q3_MS.pdf"
   - year: 2019
   - season: "Jun"
   - paper: "1P"
```

### Display
```typescript
<iframe src={`${supabaseUrl}/storage/v1/object/public/question-pdfs/${question.page_pdf_url}`} />
<button onClick={() => window.open(`${supabaseUrl}/storage/v1/object/public/question-pdfs/${question.ms_pdf_url}`)}>
  View Mark Scheme
</button>
```

### Worksheet Generation
```typescript
1. User selects multiple topics: [1, 3, 5]
2. API fetches random questions from each topic
3. Merge PDFs from storage URLs
4. Return combined worksheet PDF
```

## Bulk Processing

### Command
```bash
python scripts/bulk_ingest.py data/raw/IGCSE/4PH1/
```

### Process
```
For each year/season folder:
  ├── Find QP and MS files
  ├── Split QP into questions
  ├── Split MS into corresponding answers
  ├── Classify each question (ONE topic)
  ├── Upload QP + MS to subject/topic folders
  └── Store in database with full metadata
```

### Example
```
Input:
  data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf (10 questions)
  data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf (10 answers)

Output (Storage):
  subjects/Physics/topics/1/2019_Jun_1P_Q1.pdf
  subjects/Physics/topics/1/2019_Jun_1P_Q1_MS.pdf
  subjects/Physics/topics/2/2019_Jun_1P_Q5.pdf
  subjects/Physics/topics/2/2019_Jun_1P_Q5_MS.pdf
  ...

Output (Database):
  - 1 paper record
  - 10 question records (each with topic_code, page_pdf_url, ms_pdf_url)
```

## Benefits

1. **Clear Organization**: Easy to browse by subject → topic
2. **Fast Queries**: `SELECT * FROM questions WHERE topic_code = '1'`
3. **MS Integration**: Every question linked to its mark scheme
4. **Scalability**: Hundreds of papers, thousands of questions
5. **Metadata Rich**: Year, season, paper tracked for each question
6. **Single Topic**: ONE topic per question (no ambiguity)
7. **Frontend Simple**: Direct URL to PDF, no complex lookups

## Migration Path

1. Clear existing storage bucket (or create new one)
2. Clear questions and papers tables
3. Run bulk ingestion on all papers
4. Update frontend to use new URL format
5. Test with Topic 1, verify PDFs load
6. Process remaining papers

## Rate Limiting

- Gemini API: 15 RPM (4.5s delay between calls)
- For 100 questions: ~7.5 minutes classification time
- Can process ~800 questions per day (free tier: 1000 RPD)
