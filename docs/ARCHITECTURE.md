# System Architecture - Further Pure Mathematics Integration

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE (Next.js)                     │
│  /generate page with multi-subject selector + topic table + preview  │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      BACKEND API (Next.js)                           │
│  - /api/worksheets/generate-v2 (creates worksheet)                  │
│  - /api/worksheets/[id]/download (downloads PDF)                    │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DATABASE (Supabase)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   subjects   │  │    papers    │  │    pages     │              │
│  │──────────────│  │──────────────│  │──────────────│              │
│  │ 4PH1 Physics │→ │ 2024 May-Jun │→ │ Q1: CALC     │              │
│  │ 9FM0 Further │  │ 2023 Oct-Nov │  │ Q2: GRAPHS   │              │
│  │ 9MA0 Maths A │  │ Paper 1, 2   │  │ topics[]     │              │
│  │ 4MB1 Maths B │  │ QP + MS      │  │ confidence   │              │
│  │ WME1 Mech 1  │  │              │  │ difficulty   │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘

                         ▲
                         │ (ingestion pipeline)
                         │
┌─────────────────────────────────────────────────────────────────────┐
│                 INGESTION PIPELINE (Python)                          │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  page_based_ingest.py (Main Pipeline)                        │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐             │   │
│  │  │ 1. SPLIT   │→ │ 2. CLASSIFY│→ │ 3. UPLOAD  │→ Database   │   │
│  │  │ split_pages│  │ classifier │  │ compress + │             │   │
│  │  └────────────┘  └────────────┘  └────────────┘             │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  Batch Processors:                                                   │
│  - batch_process_physics.py                                          │
│  - batch_process_further_pure.py                                     │
│  - [future: batch_process_maths_a.py, etc.]                          │
└─────────────────────────────────────────────────────────────────────┘

                         ▲
                         │
┌─────────────────────────────────────────────────────────────────────┐
│               CLASSIFICATION ENGINE (Python)                         │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  symbol_aware_classifier.py                                  │   │
│  │                                                               │   │
│  │  ┌─────────────────────┐    ┌──────────────────────┐        │   │
│  │  │   SIMPLE MODE       │    │  SYMBOL-AWARE MODE   │        │   │
│  │  │  (Physics)          │    │  (Further Pure)      │        │   │
│  │  │─────────────────────│    │──────────────────────│        │   │
│  │  │ • Keyword matching  │    │ • Symbol grammar     │        │   │
│  │  │ • Single topic      │    │ • Pattern matching   │        │   │
│  │  │ • Confidence score  │    │ • Hard floors        │        │   │
│  │  │                     │    │ • Multi-topic        │        │   │
│  │  │ Config:             │    │ • Methods detection  │        │   │
│  │  │ physics_topics.yaml │    │ • LLM fallback       │        │   │
│  │  │                     │    │                      │        │   │
│  │  │ 8 topics            │    │ Config:              │        │   │
│  │  │                     │    │ further_pure.yaml    │        │   │
│  │  │                     │    │                      │        │   │
│  │  │                     │    │ 10 topics            │        │   │
│  │  └─────────────────────┘    └──────────────────────┘        │   │
│  │           ▲                             ▲                    │   │
│  │           └─────────────┬───────────────┘                    │   │
│  │                         │                                    │   │
│  │                   Auto-detects mode                          │   │
│  │                   from YAML structure                        │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  LLM Fallback: Gemini 1.5 Flash (if confidence < 0.62)              │
└─────────────────────────────────────────────────────────────────────┘

                         ▲
                         │
┌─────────────────────────────────────────────────────────────────────┐
│                  RAW DATA (File System)                              │
│                                                                       │
│  data/raw/IGCSE/                                                     │
│    ├── Physics/                                                      │
│    │   ├── 2024/May-Jun/Paper 1.pdf, Paper 1_MS.pdf                 │
│    │   └── 2023/Oct-Nov/Paper 2.pdf, Paper 2_MS.pdf                 │
│    │                                                                  │
│    ├── FurtherPureMaths/                                             │
│    │   ├── 2024/May-Jun/Paper 1.pdf, Paper 1_MS.pdf                 │
│    │   └── 2023/Oct-Nov/Paper 1.pdf, Paper 1_MS.pdf                 │
│    │                                                                  │
│    └── [Future: MathsA/, MathsB/, Mechanics1/]                       │
│                                                                       │
│  Watermark format: "PMT\nPhysics · 2024 · May/Jun · Paper 1 · QP"   │
└─────────────────────────────────────────────────────────────────────┘
```

## 🔄 Data Flow - Question Processing

```
RAW PDF
   │
   ▼
┌─────────────────────────────────────┐
│ 1. WATERMARK EXTRACTION             │
│ Extract: Subject, Year, Season      │
│ Normalize: May-Jun → Jun            │
│ Map: Physics → 4PH1                 │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│ 2. PAGE SPLITTING                   │
│ - Detect question starts            │
│ - Extract QP pages                  │
│ - Find matching MS pages            │
│ Output: q1.pdf, q2.pdf, ...         │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│ 3. TEXT EXTRACTION                  │
│ PyMuPDF (fitz) extracts text        │
│ First 3000 chars for classification │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│ 4. CLASSIFICATION                   │
│                                     │
│ Is symbol_grammar in config?        │
│      ↓YES            ↓NO            │
│ Symbol-Aware     Simple Mode        │
│      │               │              │
│      ▼               ▼              │
│ ┌─────────┐   ┌──────────┐         │
│ │ Normalize│   │ Keywords │         │
│ │ Symbols  │   │ Matching │         │
│ └────┬────┘   └────┬─────┘         │
│      ▼             ▼                │
│ ┌─────────┐   ┌──────────┐         │
│ │ Detect  │   │ Score    │         │
│ │ Patterns│   │ Topics   │         │
│ └────┬────┘   └────┬─────┘         │
│      ▼             ▼                │
│ ┌─────────┐   ┌──────────┐         │
│ │ Score   │   │ Return   │         │
│ │ Topics  │   │ Primary  │         │
│ └────┬────┘   └────┬─────┘         │
│      ▼             ▼                │
│ ┌─────────────────────┐            │
│ │ Apply Hard Floors   │            │
│ └────────┬────────────┘            │
│          ▼                          │
│ Confidence < 0.62?                  │
│          ↓YES   ↓NO                 │
│     ┌─────┐   ┌────────┐           │
│     │ LLM │   │ Return │           │
│     │ API │   │ Result │           │
│     └──┬──┘   └────────┘           │
│        ▼                            │
│   Return Result                     │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│ 5. PDF COMPRESSION                  │
│ JPEG quality 85                     │
│ ~33% size reduction                 │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│ 6. UPLOAD TO STORAGE                │
│ Bucket: question-pdfs               │
│ Path: subjects/{name}/pages/...     │
│ QP + MS uploaded                    │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│ 7. DATABASE INSERT                  │
│ pages table:                        │
│ - question_number                   │
│ - topics[] (array)                  │
│ - difficulty                        │
│ - confidence                        │
│ - qp_page_url                       │
│ - ms_page_url                       │
└─────────────────────────────────────┘
```

## 🎯 Classification Decision Tree

```
Question Text
     │
     ▼
Load YAML config
     │
     ▼
Has 'symbol_grammar'?
     ├─YES────────────────────────────┐
     │                                 ▼
     │                       SYMBOL-AWARE MODE
     │                                 │
     │                                 ▼
     │                       1. Normalize text
     │                          θ → theta
     │                          x² → x^2
     │                          × → *
     │                                 │
     │                                 ▼
     │                       2. Extract symbols
     │                          ∫ → integrals
     │                          d/dx → derivatives
     │                          sin() → trig_funcs
     │                                 │
     │                                 ▼
     │                       3. Score each topic
     │                          Lexical: 35%
     │                          Symbols: 45% ⭐
     │                          Layout: 5%
     │                          Co-tag: 15%
     │                                 │
     │                                 ▼
     │                       4. Apply hard floors
     │                          If ∫ present
     │                          → CALC min 0.62
     │                                 │
     │                                 ▼
     │                       5. Check confidence
     │                          Max < 0.62?
     │                          ↓YES    ↓NO
     │                        LLM    Return
     │                                 │
     │                                 ▼
     │                       6. Return multi-topic
     │                          [{id, conf, evidence},
     │                           {id, conf, evidence}]
     │
     └─NO─────────────────────────────┐
                                      ▼
                              SIMPLE MODE
                                      │
                                      ▼
                           1. Extract keywords
                              "velocity"
                              "acceleration"
                              "motion"
                                      │
                                      ▼
                           2. Match to topics
                              Kinematics: 3/5 ✅
                              Forces: 1/5 ❌
                                      │
                                      ▼
                           3. Score topics
                              matches/total
                                      │
                                      ▼
                           4. Return primary
                              {topic: "1",
                               confidence: 0.82,
                               difficulty: "medium"}
```

## 📊 Topic Coverage Matrix

```
┌──────────┬────────────────────┬────────────────┬──────────────┐
│ Subject  │ Code               │ Topics         │ Mode         │
├──────────┼────────────────────┼────────────────┼──────────────┤
│ Physics  │ 4PH1               │ 8              │ Simple       │
│          │                    │ Kinematics     │ Keywords     │
│          │                    │ Forces         │              │
│          │                    │ Energy         │              │
│          │                    │ Waves          │              │
│          │                    │ Electricity    │              │
│          │                    │ Magnetism      │              │
│          │                    │ Nuclear        │              │
│          │                    │ Matter         │              │
├──────────┼────────────────────┼────────────────┼──────────────┤
│ Further  │ 9FM0               │ 10             │ Symbol-Aware │
│ Pure     │                    │ LOGS (ln, e^x) │ Patterns     │
│ Maths    │                    │ QUAD (ax²+bx+c)│ Hard floors  │
│          │                    │ IDENT (≤, ≥)   │ Multi-tag    │
│          │                    │ GRAPHS (y=f(x))│ LLM fallback │
│          │                    │ SERIES (Σ, Sₙ) │              │
│          │                    │ BINOMIAL (C(n,r))              │
│          │                    │ VECTORS (|a|·b)│              │
│          │                    │ COORD ((x,y))  │              │
│          │                    │ CALC (∫, d/dx) │              │
│          │                    │ TRIG (sin(A±B))│              │
├──────────┼────────────────────┼────────────────┼──────────────┤
│ Maths A  │ 9MA0               │ 6 (planned)    │ TBD          │
├──────────┼────────────────────┼────────────────┼──────────────┤
│ Maths B  │ 4MB1               │ 5 (planned)    │ TBD          │
├──────────┼────────────────────┼────────────────┼──────────────┤
│ Mech 1   │ WME1               │ 5 (planned)    │ TBD          │
└──────────┴────────────────────┴────────────────┴──────────────┘
```

## 🔧 Configuration Schema

```yaml
# YAML Config Structure

version: 2                          # Config version
subject:                            # Subject metadata
  code: "9FM0"
  name: "Further Pure Mathematics"
  board: "Edexcel"
  level: "IGCSE"

# OPTIONAL: Symbol grammar (triggers symbol-aware mode)
symbol_grammar:
  normalize:                        # Text normalizations
    superscripts_to_caret: true     # x² → x^2
    greek_letters_to_ascii_names: true  # θ → theta
    minus_to_ascii: true            # − → -
  
  tokens:                           # Pattern definitions
    derivatives: ["\\b(d/dx|dy/dx|f'\\(x\\))"]
    integrals: ["(∫|\\bint\\b)"]
    # ... more tokens
  
  methods_catalog:                  # Method detection
    diff_chain: ["chain rule"]
    int_parts: ["integration by parts"]
    # ... more methods

schema:                             # Output schema
  tag_unit: "question"              # Tag whole question
  allow_multi_tag: true             # Multiple topics allowed
  output_format: "json"             # JSON response

scoring:                            # Scoring weights
  weights:
    lexical: 0.35                   # Keyword weight
    symbols: 0.45                   # Symbol weight (primary)
    layout: 0.05                    # Layout weight
    co_tag_prior: 0.15              # Related topic boost
  
  penalties:
    negative_hits: -0.22            # Penalty for negatives
    too_generic: -0.10              # Generic question penalty

symbol_hard_floors:                 # Minimum confidences
  CALC:
    any_of: ["derivatives", "integrals"]
    min_confidence: 0.62
  # ... more floors

layout_signals:                     # Visual elements
  axes_grid: ["axes", "graph paper"]
  # ... more signals

topics:                             # Topic definitions
  - id: CALC                        # Topic ID
    code: "9"                       # Database code
    name: "Calculus"                # Display name
    
    lexical:                        # Keyword patterns
      any: ["differentiate", "integrate", ...]
    
    symbols:                        # Symbol requirements
      any_sets: ["derivatives", "integrals", "limits"]
    
    structural_patterns:            # Regex patterns
      any: ["quotient rule", "product rule", ...]
    
    co_tag_prior:                   # Related topics
      GRAPHS: 0.10                  # Boost if GRAPHS also matches
      TRIG: 0.05                    # Boost if TRIG also matches
  
  # ... more topics
```

## 🚀 Deployment Checklist

```
Setup Phase:
[ ] 1. Config created: config/further_pure_topics.yaml
[ ] 2. Classifier created: scripts/symbol_aware_classifier.py
[ ] 3. Pipeline updated: scripts/page_based_ingest.py
[ ] 4. DB setup script: scripts/setup_further_pure_db.py
[ ] 5. Batch processor: scripts/batch_process_further_pure.py
[ ] 6. Test suite: scripts/test_classifier.py
[ ] 7. Documentation: docs/FURTHER_PURE_SETUP.md

Execution Phase:
[ ] 1. Run: python scripts/setup_further_pure_db.py
[ ] 2. Verify: Subject + 10 topics in database
[ ] 3. Test: python scripts/test_classifier.py (3/3 pass)
[ ] 4. Process: python scripts/batch_process_further_pure.py
[ ] 5. Verify: Questions in database with topics
[ ] 6. UI Check: /generate → Select Further Pure → Topics visible
[ ] 7. Generate: Create worksheet → Verify PDF

Validation Phase:
[ ] 1. Physics still works (no regression)
[ ] 2. Further Pure questions classified correctly
[ ] 3. Multi-topic questions show evidence
[ ] 4. Confidence scores reasonable (> 0.60)
[ ] 5. PDFs compressed (~33% savings)
[ ] 6. Storage URLs working
[ ] 7. Worksheet generation working
```

---

**Ready to deploy!** 🎉
