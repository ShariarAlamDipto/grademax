# Mathematics B (4MB1) - Setup Guide

## Overview

This guide explains how to set up Mathematics B (Edexcel IGCSE 4MB1) for the GradeMax worksheet generator.

## Files Created

| File | Purpose |
|------|---------|
| `classification/maths_b_topics.yaml` | Topic definitions for LLM classification |
| `config/document_splitting_config.yaml` | Question detection patterns (updated) |
| `scripts/add_subject.py` | Subject database setup (updated) |
| `scripts/segment_maths_b_papers.py` | PDF segmentation script |
| `scripts/process_and_classify_all_maths_b.py` | Classification script |

## Topics Structure

Mathematics B has **8 topics**:

| # | Code | Topic Name | Description |
|---|------|------------|-------------|
| 1 | NUM | Number | Integers, fractions, decimals, indices, surds, estimation |
| 2 | ALG | Algebra | Expressions, equations, inequalities, formulae, functions |
| 3 | COORD | Coordinate Geometry and Graphs | Gradients, lines, curves, transformations |
| 4 | GEOM | Geometry | Angles, polygons, circle theorems, proofs |
| 5 | MENS | Measures and Mensuration | Area, volume, similar shapes |
| 6 | TRIG | Trigonometry | Sin/cos/tan, sine/cosine rules |
| 7 | TRANS | Transformations and Vectors | Transformations, vectors |
| 8 | STAT | Statistics and Probability | Data, averages, probability |

## Step-by-Step Setup

### Step 1: Download Past Papers

Download papers from Physics and Maths Tutor:
- Paper 1: https://www.physicsandmathstutor.com/past-papers/gcse-maths/edexcel-igcse-b-paper-1/
- Paper 2: https://www.physicsandmathstutor.com/past-papers/gcse-maths/edexcel-igcse-b-paper-2/

### Step 2: Organize Raw Papers

Place PDF files in this structure:
```
data/raw/IGCSE/Maths B/
├── 2017/
│   └── May-Jun/
│       ├── Paper 1.pdf
│       ├── Paper 1_MS.pdf
│       ├── Paper 2.pdf
│       └── Paper 2_MS.pdf
├── 2018/
│   └── May-Jun/
│       └── ...
└── 2024/
    └── May-Jun/
        └── ...
```

### Step 3: Add Subject to Database

```powershell
cd c:\Users\shari\grademax
.\.venv\Scripts\activate
python scripts/add_subject.py maths_b
```

This creates:
- Subject record (code: 4MB1)
- 8 topic records

### Step 4: Segment Papers

```powershell
# Dry run first to check detection
python scripts/segment_maths_b_papers.py --dry-run

# Run actual segmentation
python scripts/segment_maths_b_papers.py

# Or segment specific year
python scripts/segment_maths_b_papers.py --year 2019
```

### Step 5: Process and Classify

```powershell
python scripts/process_and_classify_all_maths_b.py
```

This:
- Creates paper records in database
- Creates page records for each question
- Classifies each question by topic using Groq LLM
- Stores confidence scores and difficulty levels

### Step 6: Verify

```powershell
# Check database
python scripts/check_all_subjects.py
```

## Troubleshooting

### No Questions Detected
Check the splitting config patterns in `config/document_splitting_config.yaml`. 
Math B papers typically have 15-25 questions per paper.

### Classification Errors
- Ensure `GROQ_API_KEY` is set in `.env.local` or `.env.ingest`
- Check rate limits (script has built-in delays)

### Missing Mark Schemes
The script automatically links QP questions to their MS. If MS linking fails:
- Check MS file naming: `Paper 1_MS.pdf` or `Paper 1 MS.pdf`
- Verify MS format matches expected patterns

## Expected Results

After processing all available papers:
- ~30+ papers (Paper 1 + Paper 2 for ~8 years of sessions)
- ~400-600 questions total
- ~350-500 linked mark schemes (80%+ linking rate expected)

## Next Steps After Setup

1. Open the web app: `npm run dev`
2. Go to http://localhost:3000/generate
3. Select "Mathematics B" from subjects
4. Select topics and generate worksheets!

## Reference: Edexcel IGCSE Mathematics B Specification

The specification document is available at:
https://qualifications.pearson.com/content/dam/pdf/International%20GCSE/Mathematics%20B/2016/Specification%20and%20sample%20assessments/international-gcse-in-mathematics-spec-b.pdf

Key features of Math B:
- **Two papers**: Paper 1 (non-calculator) and Paper 2 (calculator)
- **Higher tier only** (no foundation tier)
- **More challenging** than Mathematics A
- Includes additional content like surds, circle theorems, vectors
