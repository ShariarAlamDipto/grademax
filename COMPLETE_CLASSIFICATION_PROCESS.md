# 📚 Complete Classification Process: Further Pure Maths & Physics

## Overview

This document provides an end-to-end guide for the classification pipeline used to process exam papers for **Further Pure Mathematics (4PM1)** and **Physics (4PH1)** in the GradeMax system.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Phase 1: Raw Paper Acquisition](#phase-1-raw-paper-acquisition)
3. [Phase 2: Document Splitting](#phase-2-document-splitting)
4. [Phase 3: Topic Classification](#phase-3-topic-classification)
5. [Phase 4: Database Storage](#phase-4-database-storage)
6. [Phase 5: Quality Validation](#phase-5-quality-validation)
7. [Subject-Specific Details](#subject-specific-details)
8. [Scripts Reference](#scripts-reference)
9. [Configuration Files](#configuration-files)
10. [Version History](#version-history)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    GradeMax Classification Pipeline                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │  Raw PDFs    │───▶│  Document    │───▶│   Topic      │───▶           │
│  │  (QP + MS)   │    │  Splitting   │    │  Classification│              │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│                                                  │                       │
│                                                  ▼                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │  Frontend    │◀───│  API Layer   │◀───│  Database    │               │
│  │  (Worksheets)│    │  (Supabase)  │    │  Storage     │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Core Components

| Component | File | Purpose |
|-----------|------|---------|
| Config Loader | `scripts/splitting_config_loader.py` | Loads YAML configurations |
| Document Splitter | `scripts/reprocess_all_papers_configurable.py` | Splits PDFs into questions |
| Hybrid Classifier v2.3 | `scripts/hybrid_classifier_v23.py` | Multi-pass LLM classification |
| Classification Runner | `scripts/run_hybrid_classification_v23.py` | Bulk classification execution |
| FPM Classifier | `scripts/run_fpm_classification.py` | FPM-specific classification |

---

## Phase 1: Raw Paper Acquisition

### Input Structure

```
data/raw/IGCSE/
├── 4PM1/                          # Further Pure Maths
│   ├── 2011/
│   │   ├── Jan/
│   │   │   ├── 4PM1_1P.pdf       # Question Paper
│   │   │   └── 4PM1_1P_MS.pdf    # Mark Scheme
│   │   └── Jun/
│   │       ├── 4PM1_1P.pdf
│   │       └── 4PM1_1P_MS.pdf
│   └── 2024/
│       └── ...
│
└── 4PH1/                          # Physics
    ├── 2019/
    │   ├── Jun/
    │   │   ├── 4PH1_1P.pdf
    │   │   └── 4PH1_1P_MS.pdf
    │   └── Oct/
    │       └── ...
    └── 2024/
        └── ...
```

### Paper Naming Convention

- **Question Paper**: `{CODE}_{PAPER}.pdf` (e.g., `4PM1_1P.pdf`)
- **Mark Scheme**: `{CODE}_{PAPER}_MS.pdf` (e.g., `4PM1_1P_MS.pdf`)
- **Seasons**: Jan, Jun, Oct, Nov

---

## Phase 2: Document Splitting

### Configuration-Driven Approach

The system uses YAML-based configurations for subject-specific splitting rules.

#### Configuration File: `config/document_splitting_config.yaml`

```yaml
further_pure_maths:
  subject_code: "4PM1"
  subject_name: "Further Pure Mathematics"
  
  question_patterns:
    priority_1:
      - regex: '^\s*(\d+)\s+[A-Z(]'
        description: "Number + space + uppercase"
    priority_2:
      - regex: '^\s*(\d+)\s*$'
        validation:
          keywords: ["diagram", "find", "show", "calculate", "prove"]
          search_range: 15

  validation:
    min_question: 1
    max_question: 11
    expected_range: [9, 11]

physics:
  subject_code: "4PH1"
  subject_name: "Physics"
  # Similar structure...
```

### Splitting Process

1. **Load Configuration**: Subject-specific YAML loaded
2. **Extract Text**: PDF text extracted page-by-page using PyMuPDF
3. **Detect Questions**: Regex patterns identify question starts
4. **Validate Numbers**: Question numbers validated against expected range
5. **Split PDFs**: Individual question PDFs created
6. **Match Markschemes**: MS pages linked to questions
7. **Generate Manifest**: JSON metadata file created

### Output Structure

```
data/processed/
├── Further Pure Maths Processed/
│   ├── 2011_Jun_1P/
│   │   ├── pages/
│   │   │   ├── q1.pdf
│   │   │   ├── q2.pdf
│   │   │   └── ...
│   │   ├── markschemes/
│   │   │   ├── q1.pdf
│   │   │   └── ...
│   │   └── manifest.json
│   └── ... (68 papers total)
│
└── Physics Processed/
    ├── 2019_Jun_1P/
    │   ├── pages/
    │   ├── markschemes/
    │   └── manifest.json
    └── ... (100+ papers)
```

### Running Document Splitting

```powershell
# Process all subjects with configurable splitting
python scripts\reprocess_all_papers_configurable.py --yes
```

---

## Phase 3: Topic Classification

### Classification Pipeline v2.3

The hybrid multi-pass classification system uses three passes:

```
┌────────────────────────────────────────────────────────────────┐
│                     CLASSIFICATION PIPELINE                     │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Pass 1: Groq Llama 3.3 70B (BULK)                             │
│  ├── Batch: 10 questions per request                           │
│  ├── Context: 4000 characters                                  │
│  ├── Confidence: 0.80-1.00                                     │
│  └── If confidence < 0.70 → Pass 2                             │
│                                                                 │
│  Pass 2: Groq Llama 3.3 70B (REFINE)                           │
│  ├── Individual question analysis                              │
│  ├── Enhanced prompts with examples                            │
│  ├── Page context for incomplete questions                     │
│  └── If still low → Pass 3                                     │
│                                                                 │
│  Pass 3: Enhanced Keywords (FALLBACK)                          │
│  ├── Weighted keyword scoring (5=core, 2=support)              │
│  ├── Formula recognition (v=fλ, F=ma, etc.)                    │
│  ├── Negative keyword filtering                                │
│  └── Disambiguation rules applied                              │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### Topic Definitions

#### Physics Topics (8 Topics)

| ID | Code | Name | Key Formulas |
|----|------|------|--------------|
| 1 | FM | Forces and motion | F=ma, p=mv, KE=½mv² |
| 2 | ELEC | Electricity | V=IR, P=IV |
| 3 | WAVE | Waves | v=fλ, Snell's law |
| 4 | ENRG | Energy resources and transfers | Efficiency, E=mcΔθ |
| 5 | SLG | Solids, liquids and gases | ρ=m/V, pV=constant |
| 6 | MAG | Magnetism and electromagnetism | F=BIL, Vp/Vs=Np/Ns |
| 7 | RADIO | Radioactivity and particles | Half-life, α/β/γ |
| 8 | SPACE | Astrophysics | Red shift, Big Bang |

#### Further Pure Maths Topics (10 Topics)

| ID | Code | Name | Key Concepts |
|----|------|------|--------------|
| 1 | LOGS | Logarithmic functions & indices | Laws of logs, change of base |
| 2 | QUAD | Quadratic function | Discriminant, completing square |
| 3 | IDENT | Identities & inequalities | Factor theorem, remainder |
| 4 | GRAPHS | Graphs | Rational functions, asymptotes |
| 5 | SERIES | Series | Arithmetic/geometric sequences |
| 6 | BINOM | Binomial series | (1+x)^n expansion |
| 7 | VECT | Scalar & vector quantities | Position vectors, magnitude |
| 8 | COORD | Rectangular Cartesian coordinates | Distance, gradient, circles |
| 9 | CALC | Calculus | Differentiation, integration |
| 10 | TRIG | Trigonometry | Identities, equations, graphs |

### Running Classification

```powershell
# Physics classification (v2.3)
python scripts\run_hybrid_classification_v23.py

# Further Pure Maths classification
python scripts\run_fpm_classification.py
```

### Classification Output

Each question receives:
- **Topic Code**: 1-8 (Physics) or 1-10 (FPM)
- **Difficulty**: easy, medium, hard
- **Confidence Score**: 0.00-1.00
- **Classification Method**: groq_bulk, groq_refine, keywords

---

## Phase 4: Database Storage

### Supabase Schema

```sql
-- Subjects table
CREATE TABLE subjects (
  id UUID PRIMARY KEY,
  code TEXT NOT NULL,        -- "4PH1" or "4PM1"
  name TEXT NOT NULL,        -- "Physics" or "Further Pure Mathematics"
  board TEXT,                -- "Edexcel"
  level TEXT                 -- "International GCSE"
);

-- Papers table  
CREATE TABLE papers (
  id UUID PRIMARY KEY,
  subject_id UUID REFERENCES subjects(id),
  year INT,
  season TEXT,               -- "Jan", "Jun", "Oct"
  paper_number TEXT,         -- "1P", "2P"
  qp_path TEXT,
  ms_path TEXT
);

-- Pages table (questions)
CREATE TABLE pages (
  id UUID PRIMARY KEY,
  paper_id UUID REFERENCES papers(id),
  page_number INT,
  question_number TEXT,
  topic_id TEXT,             -- "1" to "8" or "1" to "10"
  difficulty TEXT,           -- "easy", "medium", "hard"
  confidence FLOAT,          -- 0.00-1.00
  text_excerpt TEXT,
  pdf_url TEXT,
  ms_pdf_url TEXT
);
```

### Storage Structure

```
question-pdfs/
└── subjects/
    ├── Physics/
    │   └── topics/
    │       ├── 1/                     # Forces and motion
    │       │   ├── 2019_Jun_1P_Q1.pdf
    │       │   └── 2019_Jun_1P_Q1_MS.pdf
    │       ├── 2/                     # Electricity
    │       └── ...
    │
    └── Further Pure Mathematics/
        └── topics/
            ├── 1/                     # LOGS
            ├── 2/                     # QUAD
            └── ...
```

---

## Phase 5: Quality Validation

### Analysis Scripts

```powershell
# Check Physics classifications
python scripts\analyze_classifications.py

# Check FPM classifications
python scripts\check_fpm_classification.py
```

### Quality Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Coverage | 100% | All pages have topic assignments |
| Confidence | >70% at ≥0.70 | Most classifications are confident |
| Difficulty Split | 20/60/20 | Easy/Medium/Hard distribution |
| Topic Balance | <3:1 ratio | No extreme topic imbalance |

### Current Status

**Physics (490 pages)**:
- Coverage: 100%
- Topic Distribution: Balanced (Forces: 30%, Electricity: 19%, etc.)
- Confidence: High (0.70+ average)

**Further Pure Maths (68 papers, ~658 questions)**:
- 10 topics configured
- Classification system operational
- Production-ready

---

## Subject-Specific Details

### Physics Classification Journey

1. **Initial Setup**: Basic keyword matching (low accuracy)
2. **v2.0**: Single-pass LLM (Gemini) - rate limited
3. **v2.2**: Hybrid multi-pass (Gemini + Groq + Keywords)
   - 3x faster processing
   - 5x more accurate
   - Formula recognition added
4. **v2.3**: Groq-only (Llama 3.3 70B)
   - No rate limits
   - 4000 char context
   - Page context for incomplete questions

### Further Pure Maths Configuration

**Unique Challenges**:
- Different paper formats (2011-2015 vs 2016+)
- 10 highly specialized topics
- Mathematical notation parsing

**Solutions**:
- Format-specific detection rules in YAML
- Weighted keywords for mathematical terms
- Precedence rules (CALC over TRIG, QUAD over IDENT)

---

## Scripts Reference

### Document Splitting

| Script | Purpose |
|--------|---------|
| `splitting_config_loader.py` | Loads YAML configurations |
| `reprocess_all_papers_configurable.py` | Main splitting script |

### Classification

| Script | Purpose |
|--------|---------|
| `hybrid_classifier_v23.py` | Core v2.3 classification engine |
| `run_hybrid_classification_v23.py` | Physics classifier runner |
| `run_fpm_classification.py` | FPM classifier runner |
| `mistral_classifier.py` | Generic YAML-based classifier |

### Analysis & Utilities

| Script | Purpose |
|--------|---------|
| `analyze_classifications.py` | Quality metrics |
| `check_fpm_classification.py` | FPM-specific verification |
| `reset_all_classifications.py` | Clear and restart |
| `reclassify_difficulty.py` | Fix difficulty distribution |

---

## Configuration Files

### Topic Definitions

| File | Subject | Topics |
|------|---------|--------|
| `classification/physics_topics.yaml` | Physics | 8 topics |
| `classification/further_pure_maths_topics.yaml` | FPM | 10 topics |

### Splitting Configuration

| File | Purpose |
|------|---------|
| `config/document_splitting_config.yaml` | All subjects' splitting rules |
| `config/TEMPLATE_subject_topics.yaml` | Template for new subjects |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | - | Basic keyword matching |
| v2.0 | - | Single-pass LLM (Gemini) |
| v2.2 | Oct 2025 | Hybrid multi-pass (Gemini + Groq + Keywords) |
| v2.3 | Oct 2025 | Groq-only (Llama 3.3 70B), 4000 char context |

### v2.3 Improvements

- ✅ Replaced Gemini with Groq Llama 3.3 70B (no rate limits)
- ✅ 4000 character context (was 2000)
- ✅ Page context extraction for incomplete questions
- ✅ Disambiguation rules and postprocessing
- ✅ Better keyword matching

---

## Complete Workflow Summary

```
1. ACQUIRE PAPERS
   └── Place PDFs in data/raw/IGCSE/{CODE}/{YEAR}/{SEASON}/

2. SPLIT DOCUMENTS
   └── python scripts\reprocess_all_papers_configurable.py --yes
       └── Creates: data/processed/{Subject} Processed/

3. CLASSIFY QUESTIONS
   ├── Physics: python scripts\run_hybrid_classification_v23.py
   └── FPM: python scripts\run_fpm_classification.py

4. VALIDATE QUALITY
   ├── python scripts\analyze_classifications.py
   └── python scripts\check_fpm_classification.py

5. DEPLOY TO FRONTEND
   └── Questions available via Supabase API for worksheet generation
```

---

## Quick Commands

```powershell
# Complete pipeline for Physics
python scripts\reprocess_all_papers_configurable.py --yes
python scripts\run_hybrid_classification_v23.py
python scripts\analyze_classifications.py

# Complete pipeline for FPM
python scripts\reprocess_all_papers_configurable.py --yes
python scripts\run_fpm_classification.py
python scripts\check_fpm_classification.py

# Reset and reclassify
python scripts\reset_all_classifications.py
python scripts\run_hybrid_classification_v23.py
```

---

**Status**: Production Ready ✅  
**Last Updated**: October 2025  
**Version**: 2.3

