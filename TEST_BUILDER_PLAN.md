# GradeMax Test Builder — Detailed Implementation Plan

> **Goal:** Build a SaveMyExams-style Test Builder where teachers/students can select a **Subject → Topic → Subtopic → Question Type**, see matching questions, pick them individually, and generate a custom test paper PDF with a corresponding mark scheme.

---

## 1. How SaveMyExams Test Builder Works (Analysis)

| Step | Feature | Detail |
|------|---------|--------|
| 1 | **Subject picker** | Choose Biology / Physics / Maths / Chemistry etc. |
| 2 | **Exam board + level** | e.g. Edexcel IGCSE, CIE A-Level |
| 3 | **Topic tree** | Hierarchical: Topic → Subtopic → Sub-subtopic |
| 4 | **Question type filter** | Short answer, Structured, Multiple choice, Extended response |
| 5 | **Difficulty filter** | Easy / Medium / Hard |
| 6 | **Individual question cards** | Each shows preview, marks, topic tags, difficulty badge |
| 7 | **Add to test** | Click to add individual questions to test basket |
| 8 | **Test basket sidebar** | Shows selected questions, total marks, reorder by drag |
| 9 | **Teacher-only questions** | Questions students haven't seen |
| 10 | **PDF generation** | Download print-ready Question Paper + Mark Scheme PDFs |

---

## 2. Current GradeMax State

### What You Already Have
- ✅ **Supabase DB** with: `subjects`, `topics`, `papers`, `pages`, `questions`, `question_parts`, `question_tags`, `worksheets`, `worksheet_items`
- ✅ **Page-based system** — each question page stored as individual PDF in Supabase Storage with `qp_page_url` and `ms_page_url`
- ✅ **Topic classification** — `pages.topics[]` array contains topic codes; `question_tags` table has confidence-scored topic assignments
- ✅ **Basic Worksheet Generator** — (`/generate`) lets you pick subject → topics → year range → difficulty → generates merged PDF
- ✅ **Subjects** — Physics (4PH1), Pure Maths (4PM1), Maths A, Maths B, Chemistry, Biology, ICT, English, IAL Pure 1-4, Mechanics 1, Statistics 1
- ✅ **Physics topics** — 22 subtopics (1a-8b) covering all 8 chapters
- ✅ **Pure Maths topics** — 10 topics (LOGS, QUAD, IDENT, GRAPHS, SERIES, BINOM, VECT, COORD, CALC, TRIG)

### What's Missing for a Test Builder
- ❌ **Hierarchical topic tree** (Topic → Subtopic → Sub-subtopic)
- ❌ **Question-type classification** (MCQ, structured, extended response, etc.)
- ❌ **Individual question preview cards** with mark counts
- ❌ **Test basket / cart** (add/remove individual questions)
- ❌ **Drag-to-reorder** in basket
- ❌ **Question-level browsing** (currently page-level)
- ❌ **Per-question mark scheme linking** at part level
- ❌ **Subtopic-level granularity** for all subjects

---

## 3. Database Schema Changes

### 3.1 Enhanced Topic Hierarchy Table

Currently `topics` has a `parent_id` column but it's unused. We need a **3-level hierarchy**:

```
Level 0 (Chapter):    "1 - Forces and Motion"
Level 1 (Topic):      "1c - Forces, movement, shape and momentum"
Level 2 (Subtopic):   "1c.1 - Newton's First Law"
                      "1c.2 - Newton's Second Law (F=ma)"
                      "1c.3 - Momentum & Conservation"
```

**Migration SQL:**

```sql
-- Add hierarchy depth and display order
ALTER TABLE topics ADD COLUMN IF NOT EXISTS depth INTEGER DEFAULT 0;       -- 0=chapter, 1=topic, 2=subtopic
ALTER TABLE topics ADD COLUMN IF NOT EXISTS display_order INTEGER DEFAULT 0;
ALTER TABLE topics ADD COLUMN IF NOT EXISTS question_count INTEGER DEFAULT 0; -- cached count
ALTER TABLE topics ADD COLUMN IF NOT EXISTS icon TEXT;                       -- emoji or icon name
ALTER TABLE topics ADD COLUMN IF NOT EXISTS spec_ref TEXT;                   -- specification reference
```

### 3.2 Question Type Classification

```sql
-- Add question type to pages table
ALTER TABLE pages ADD COLUMN IF NOT EXISTS question_type TEXT;  
-- Values: 'mcq', 'short_answer', 'structured', 'extended_response', 'calculation', 'diagram', 'practical'

ALTER TABLE pages ADD COLUMN IF NOT EXISTS marks INTEGER;
ALTER TABLE pages ADD COLUMN IF NOT EXISTS estimated_time_minutes INTEGER;

-- Add question type to questions table too
ALTER TABLE questions ADD COLUMN IF NOT EXISTS question_type TEXT;
```

### 3.3 Test Builder Tables

```sql
-- Tests (replaces/supplements worksheets for the test-builder flow)
CREATE TABLE IF NOT EXISTS tests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  title TEXT NOT NULL DEFAULT 'Untitled Test',
  subject_id UUID NOT NULL REFERENCES subjects(id),
  
  -- Test metadata
  total_marks INTEGER DEFAULT 0,
  total_questions INTEGER DEFAULT 0,
  estimated_time_minutes INTEGER DEFAULT 0,
  difficulty_mix JSONB,            -- {"easy": 3, "medium": 5, "hard": 2}
  topic_coverage JSONB,            -- {"1a": 2, "2b": 3} - questions per topic
  
  -- Generated PDFs
  question_paper_url TEXT,
  mark_scheme_url TEXT,
  
  -- Status
  status TEXT DEFAULT 'draft',     -- 'draft', 'finalized', 'shared'
  is_teacher_only BOOLEAN DEFAULT FALSE,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Test Items (individual questions in a test)
CREATE TABLE IF NOT EXISTS test_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  test_id UUID NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
  page_id UUID NOT NULL REFERENCES pages(id),            -- link to the page
  question_id UUID REFERENCES questions(id),              -- optional link to question
  
  sequence_order INTEGER NOT NULL,    -- position in test
  marks INTEGER,
  
  -- Override fields (teacher can customize)
  custom_marks INTEGER,               -- override original marks
  include_mark_scheme BOOLEAN DEFAULT TRUE,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(test_id, page_id)
);

CREATE INDEX idx_tests_user ON tests(user_id);
CREATE INDEX idx_tests_subject ON tests(subject_id);
CREATE INDEX idx_test_items_test ON test_items(test_id);
CREATE INDEX idx_test_items_page ON test_items(page_id);
```

---

## 4. Complete Topic Taxonomy — Per Subject

### 4.1 Physics IGCSE (4PH1) — Edexcel

Already have 22 subtopics. Need to add **Level 2 (sub-subtopics)** for individual concept granularity:

```
Chapter 1: Forces and Motion
├── 1a: Units
│   ├── 1a.1: SI base units
│   └── 1a.2: Derived units and prefixes
├── 1b: Movement and position
│   ├── 1b.1: Distance-time graphs
│   ├── 1b.2: Speed and average speed
│   └── 1b.3: Velocity-time graphs and acceleration
├── 1c: Forces, movement, shape and momentum
│   ├── 1c.1: Types of forces (gravity, friction, air resistance)
│   ├── 1c.2: Resultant forces
│   ├── 1c.3: Newton's laws of motion
│   ├── 1c.4: Momentum (p = mv)
│   ├── 1c.5: Conservation of momentum
│   ├── 1c.6: Stopping distances
│   └── 1c.7: Hooke's law and elastic deformation
├── 1d: Energy and work
│   ├── 1d.1: Work done (W = Fd)
│   ├── 1d.2: Kinetic energy (KE = ½mv²)
│   ├── 1d.3: Gravitational potential energy (GPE = mgh)
│   ├── 1d.4: Conservation of energy
│   └── 1d.5: Efficiency

Chapter 2: Electricity
├── 2a: Mains electricity
│   ├── 2a.1: AC vs DC
│   ├── 2a.2: Wiring a plug
│   ├── 2a.3: Fuses and circuit breakers
│   └── 2a.4: Earthing and safety
├── 2b: Energy and voltage in circuits
│   ├── 2b.1: Current, voltage, resistance (V = IR)
│   ├── 2b.2: Series circuits
│   ├── 2b.3: Parallel circuits
│   ├── 2b.4: Electrical power (P = IV = I²R)
│   └── 2b.5: Energy transferred (E = VIt)
├── 2c: Electric charge
│   ├── 2c.1: Static electricity and charging
│   ├── 2c.2: Electric fields
│   └── 2c.3: Current as flow of charge (Q = It)

Chapter 3: Waves
├── 3a: Properties of waves
│   ├── 3a.1: Transverse vs longitudinal waves
│   ├── 3a.2: Wave equation (v = fλ)
│   ├── 3a.3: Amplitude, frequency, wavelength, period
│   └── 3a.4: Wave diagrams
├── 3b: The electromagnetic spectrum
│   ├── 3b.1: EM spectrum order and properties
│   ├── 3b.2: Uses of EM waves
│   └── 3b.3: Dangers of EM radiation
├── 3c: Light and sound
│   ├── 3c.1: Reflection and plane mirrors
│   ├── 3c.2: Refraction and Snell's law
│   ├── 3c.3: Total internal reflection
│   ├── 3c.4: Lenses (converging/diverging)
│   ├── 3c.5: Sound waves and hearing
│   └── 3c.6: Diffraction

Chapter 4: Energy Resources
├── 4a: Energy resources and electricity generation
│   ├── 4a.1: Fossil fuels
│   ├── 4a.2: Nuclear energy
│   ├── 4a.3: Renewable sources (solar, wind, hydro, tidal, geothermal)
│   └── 4a.4: Comparing energy resources
├── 4b: Work and power
│   ├── 4b.1: Work done calculations
│   ├── 4b.2: Power (P = W/t)
│   └── 4b.3: Efficiency calculations

Chapter 5: Solids, Liquids and Gases
├── 5a: Density and pressure
│   ├── 5a.1: Density calculations (ρ = m/V)
│   ├── 5a.2: Pressure in solids (P = F/A)
│   └── 5a.3: Pressure in fluids and atmosphere
├── 5b: Change of state
│   ├── 5b.1: States of matter and particle model
│   ├── 5b.2: Heating/cooling curves
│   └── 5b.3: Specific and latent heat
├── 5c: Ideal gas molecules
│   ├── 5c.1: Kinetic theory and Brownian motion
│   ├── 5c.2: Gas pressure and temperature
│   └── 5c.3: Boyle's law and gas equations

Chapter 6: Magnetism and Electromagnetism
├── 6a: Magnetism
│   ├── 6a.1: Magnetic materials and poles
│   ├── 6a.2: Magnetic field patterns
│   └── 6a.3: Electromagnets
├── 6b: Electromagnetism
│   ├── 6b.1: Motor effect and Fleming's LHR
│   ├── 6b.2: Electromagnetic induction and Fleming's RHR
│   ├── 6b.3: Generators (AC/DC)
│   └── 6b.4: Transformers (Vs/Vp = Ns/Np)

Chapter 7: Radioactivity and Particles
├── 7a: Radioactivity
│   ├── 7a.1: Atomic structure
│   ├── 7a.2: Alpha, beta, gamma properties
│   ├── 7a.3: Half-life and decay curves
│   ├── 7a.4: Uses and dangers of radiation
│   └── 7a.5: Nuclear equations
├── 7b: Fission and fusion
│   ├── 7b.1: Nuclear fission and chain reactions
│   └── 7b.2: Nuclear fusion in stars

Chapter 8: Astrophysics
├── 8a: Motion in the Universe
│   ├── 8a.1: Orbital motion and gravity
│   └── 8a.2: Satellites (geostationary, polar)
├── 8b: Stellar evolution
│   ├── 8b.1: Hertzsprung-Russell diagram
│   ├── 8b.2: Life cycle of stars
│   └── 8b.3: Red shift, Big Bang, expanding universe
```

### 4.2 Further Pure Mathematics (4PM1) — Edexcel IGCSE

```
Chapter 1: Logarithmic Functions & Indices (LOGS)
├── LOGS.1: Laws of indices
├── LOGS.2: Laws of logarithms
├── LOGS.3: Solving exponential equations
├── LOGS.4: Change of base formula
└── LOGS.5: Natural logarithms (ln)

Chapter 2: Quadratic Function (QUAD)
├── QUAD.1: Completing the square
├── QUAD.2: Quadratic formula and discriminant
├── QUAD.3: Sketching quadratics
├── QUAD.4: Simultaneous equations (one linear, one quadratic)
└── QUAD.5: Quadratic inequalities

Chapter 3: Identities & Inequalities (IDENT)
├── IDENT.1: Factor theorem
├── IDENT.2: Remainder theorem
├── IDENT.3: Polynomial division
├── IDENT.4: Linear inequalities
└── IDENT.5: Rational inequalities

Chapter 4: Graphs (GRAPHS)
├── GRAPHS.1: Graphs of polynomials
├── GRAPHS.2: Rational functions and asymptotes
├── GRAPHS.3: Modulus functions |f(x)|
├── GRAPHS.4: Graph transformations (translations, stretches, reflections)
└── GRAPHS.5: Intersection of curves

Chapter 5: Series (SERIES)
├── SERIES.1: Arithmetic sequences and series
├── SERIES.2: Geometric sequences and series
├── SERIES.3: Sum to infinity
├── SERIES.4: Sigma notation
└── SERIES.5: Convergence conditions

Chapter 6: Binomial Series (BINOM)
├── BINOM.1: Binomial expansion (positive integer n)
├── BINOM.2: Binomial expansion (rational n)
├── BINOM.3: Approximations using binomial series
└── BINOM.4: Validity of expansion

Chapter 7: Scalar & Vector Quantities (VECT)
├── VECT.1: Vector notation and representation
├── VECT.2: Position vectors
├── VECT.3: Magnitude and direction
├── VECT.4: Vector addition and subtraction
└── VECT.5: Scalar (dot) product

Chapter 8: Rectangular Cartesian Coordinates (COORD)
├── COORD.1: Distance between two points
├── COORD.2: Midpoint formula
├── COORD.3: Gradient and equation of a line
├── COORD.4: Parallel and perpendicular lines
├── COORD.5: Equation of a circle
└── COORD.6: Tangent and normal to a circle

Chapter 9: Calculus (CALC)
├── CALC.1: Differentiation from first principles
├── CALC.2: Differentiation rules (power, chain, product, quotient)
├── CALC.3: Tangents and normals
├── CALC.4: Stationary points and curve sketching
├── CALC.5: Integration (reverse of differentiation)
├── CALC.6: Definite integrals and area under curve
└── CALC.7: Applications (rates of change, kinematics)

Chapter 10: Trigonometry (TRIG)
├── TRIG.1: Trigonometric ratios and exact values
├── TRIG.2: Trigonometric identities
├── TRIG.3: Solving trigonometric equations
├── TRIG.4: Graphs of trig functions
├── TRIG.5: Sine and cosine rules
└── TRIG.6: Area of triangle (½ab sin C)
```

---

## 5. Question Type Classification

### 5.1 Question Types to Support

| Type Code | Display Name | Description | Icon |
|-----------|-------------|-------------|------|
| `mcq` | Multiple Choice | A/B/C/D options | ○ |
| `short_answer` | Short Answer | 1-3 marks, single calculation or recall | ✏️ |
| `structured` | Structured | Multi-part (a)(b)(c) with scaffolding | 📋 |
| `extended` | Extended Response | 5+ marks, requires explanation | 📝 |
| `calculation` | Calculation | Pure numerical working | 🔢 |
| `diagram` | Diagram/Drawing | Draw, label, or complete diagram | 🎨 |
| `practical` | Practical | Experimental method, data analysis | 🔬 |
| `prove` | Prove/Show | Mathematical proof or derivation | ∴ |

### 5.2 Auto-Classification Script

Create a script that reads the question text and marks to classify:

```python
# scripts/classify_question_types.py
def classify_question_type(text: str, marks: int, has_diagram: bool) -> str:
    text_lower = text.lower()
    
    # MCQ detection
    if any(pattern in text_lower for pattern in ['(a)', '(b)', '(c)', '(d)']) and marks <= 1:
        return 'mcq'
    
    # Diagram questions
    if has_diagram and any(w in text_lower for w in ['draw', 'sketch', 'label', 'complete the diagram']):
        return 'diagram'
    
    # Prove/Show
    if any(w in text_lower for w in ['prove that', 'show that', 'hence show', 'verify']):
        return 'prove'
    
    # Practical
    if any(w in text_lower for w in ['experiment', 'apparatus', 'method', 'describe how you would']):
        return 'practical'
    
    # Extended response (high marks, explanation required)
    if marks >= 5 and any(w in text_lower for w in ['explain', 'discuss', 'evaluate', 'describe']):
        return 'extended'
    
    # Calculation
    if any(w in text_lower for w in ['calculate', 'find the value', 'determine', 'work out']):
        return 'calculation'
    
    # Structured (multi-part)
    if '(a)' in text or '(b)' in text or '(i)' in text:
        return 'structured'
    
    # Short answer (low marks)
    if marks <= 3:
        return 'short_answer'
    
    return 'structured'  # default
```

---

## 6. Frontend Architecture — Step by Step

### 6.1 Page Route: `/test-builder`

```
src/app/test-builder/
├── page.tsx                      # Main test builder page (server component)
├── layout.tsx                    # Layout with sidebar
└── [testId]/
    ├── page.tsx                  # Edit existing test
    └── preview/
        └── page.tsx              # PDF preview page
```

### 6.2 Components Breakdown

```
src/components/test-builder/
├── TestBuilderPage.tsx           # Main orchestrator (client component)
├── SubjectSelector.tsx           # Subject cards grid
├── TopicTree.tsx                 # Collapsible topic → subtopic → sub-subtopic tree
├── FilterBar.tsx                 # Difficulty, question type, year range, marks range
├── QuestionBrowser.tsx           # Grid/list of matching questions
├── QuestionCard.tsx              # Individual question preview card
├── TestBasket.tsx                # Selected questions sidebar (sticky)
├── TestBasketItem.tsx            # Draggable item in basket
├── TestSummary.tsx               # Total marks, time, topic coverage stats
├── QuestionPreviewModal.tsx      # Full question + mark scheme preview
├── GenerateTestDialog.tsx        # Final options before PDF generation
└── DifficultyBadge.tsx           # Color-coded difficulty indicator
```

### 6.3 UI Flow (Screen by Screen)

#### Screen 1: Subject Selection
```
┌─────────────────────────────────────────────────────────┐
│  🎯 Test Builder                                        │
│                                                         │
│  Select Subject:                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Physics  │ │Pure Maths│ │Chemistry │ │ Biology  │   │
│  │ 4PH1     │ │ 4PM1     │ │ 4CH1     │ │ 4BI1     │   │
│  │ IGCSE    │ │ IGCSE    │ │ IGCSE    │ │ IGCSE    │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│  │  P1 (IAL)│ │  P2 (IAL)│ │  M1 (IAL)│               │
│  └──────────┘ └──────────┘ └──────────┘               │
└─────────────────────────────────────────────────────────┘
```

#### Screen 2: Topic Tree + Question Browser + Basket (3-column layout)
```
┌──────────────┬─────────────────────────────┬──────────────┐
│  TOPICS      │  QUESTIONS (24 found)       │  TEST BASKET │
│              │                              │              │
│  ▼ Ch1 Force │  ┌─────────────────────┐    │  My Test     │
│    □ 1a Unit │  │ Q3 (2019 Jun P1)    │    │  ──────────  │
│    ■ 1b Move │  │ ★★☆ Medium | 6 marks│    │  1. Q3 - 6m  │
│    □ 1c Forc │  │ Topics: 1b, 1c      │    │  2. Q7 - 4m  │
│    □ 1d Ener │  │ Type: Calculation    │    │  3. Q2 - 8m  │
│  ▶ Ch2 Elec  │  │ [Preview] [+ Add]   │    │              │
│  ▶ Ch3 Waves │  └─────────────────────┘    │  Total: 18m  │
│  ▶ Ch4 Energ │  ┌─────────────────────┐    │  Time: ~27m  │
│  ▶ Ch5 Solid │  │ Q7 (2020 Oct P1)    │    │              │
│  ▶ Ch6 Magne │  │ ★☆☆ Easy | 4 marks  │    │  [Generate]  │
│  ▶ Ch7 Radio │  │ Topics: 1b          │    │  [Clear All] │
│  ▶ Ch8 Astro │  │ Type: Short Answer  │    │              │
│              │  │ [Preview] [+ Add]   │    │              │
│  ──────────  │  └─────────────────────┘    │              │
│  FILTERS     │                              │              │
│  Difficulty: │  ┌─────────────────────┐    │              │
│  [All ▼]     │  │ Q2 (2021 Jan P2)    │    │              │
│  Type:       │  │ ★★★ Hard | 8 marks  │    │              │
│  [All ▼]     │  │ Topics: 1b, 1d      │    │              │
│  Year:       │  │ Type: Structured    │    │              │
│  [2011-2025] │  │ [Preview] [+ Add]   │    │              │
│  Marks:      │  └─────────────────────┘    │              │
│  [1] - [20]  │                              │              │
└──────────────┴─────────────────────────────┴──────────────┘
```

#### Screen 3: Question Preview Modal
```
┌─────────────────────────────────────────────────────────┐
│  Q3 — 2019 June Paper 1                    [✕ Close]   │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  ┌───────────────────┐  ┌───────────────────┐          │
│  │  Question Paper   │  │  Mark Scheme      │          │
│  │                   │  │                   │          │
│  │  [PDF Preview]    │  │  [PDF Preview]    │          │
│  │                   │  │                   │          │
│  └───────────────────┘  └───────────────────┘          │
│                                                         │
│  Topics: 1b Movement, 1c Forces                        │
│  Difficulty: Medium  |  Marks: 6  |  Est. Time: 9 min  │
│  Type: Calculation   |  Year: 2019 | Season: June      │
│                                                         │
│  [Add to Test]                    [Already in Test ✓]   │
└─────────────────────────────────────────────────────────┘
```

---

## 7. API Routes

### 7.1 New API Endpoints

```
GET  /api/test-builder/topics?subjectId=xxx
     → Returns hierarchical topic tree with question counts

GET  /api/test-builder/questions?subjectId=xxx&topics=1b,1c&difficulty=medium&type=calculation&yearStart=2015&yearEnd=2025&marks_min=1&marks_max=10&page=1&limit=20
     → Returns paginated question cards with metadata

GET  /api/test-builder/questions/[pageId]/preview
     → Returns question + mark scheme PDF URLs for preview

POST /api/test-builder/tests
     → Create new test
     Body: { title, subject_id, items: [{ page_id, sequence }] }

PUT  /api/test-builder/tests/[testId]
     → Update test (reorder, add/remove questions)

GET  /api/test-builder/tests/[testId]/download?type=qp|ms|both
     → Generate and download PDF

GET  /api/test-builder/tests
     → List user's saved tests

DELETE /api/test-builder/tests/[testId]
       → Delete a test
```

### 7.2 Topics API Response Shape

```json
{
  "topics": [
    {
      "id": "uuid",
      "code": "1",
      "name": "Forces and Motion",
      "depth": 0,
      "questionCount": 45,
      "children": [
        {
          "id": "uuid",
          "code": "1b",
          "name": "Movement and position",
          "depth": 1,
          "questionCount": 18,
          "children": [
            {
              "id": "uuid",
              "code": "1b.1",
              "name": "Distance-time graphs",
              "depth": 2,
              "questionCount": 7
            },
            {
              "id": "uuid",
              "code": "1b.2",
              "name": "Speed and average speed",
              "depth": 2,
              "questionCount": 6
            }
          ]
        }
      ]
    }
  ]
}
```

### 7.3 Questions API Response Shape

```json
{
  "questions": [
    {
      "id": "page-uuid",
      "questionNumber": "3",
      "year": 2019,
      "season": "June",
      "paperNumber": "1P",
      "topics": ["1b", "1c"],
      "topicNames": ["Movement and position", "Forces"],
      "difficulty": "medium",
      "marks": 6,
      "questionType": "calculation",
      "hasDiagram": false,
      "estimatedTime": 9,
      "qpPageUrl": "https://...pdf",
      "msPageUrl": "https://...pdf",
      "textExcerpt": "A car accelerates uniformly from rest..."
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "totalPages": 3
  }
}
```

---

## 8. Step-by-Step Execution Plan

### Phase 1: Database & Classification (Backend Foundation)
**Estimated Time: 3-4 days**

| # | Task | Detail |
|---|------|--------|
| 1.1 | Run topic hierarchy migration | Add `depth`, `display_order`, `question_count` to `topics` |
| 1.2 | Seed Physics sub-subtopics | Insert ~65 Level 2 subtopics under existing 22 Level 1 topics |
| 1.3 | Seed Pure Maths sub-subtopics | Insert ~50 Level 2 subtopics under existing 10 topics |
| 1.4 | Add `question_type` column | ALTER pages, questions tables |
| 1.5 | Create `tests` + `test_items` tables | Run migration SQL |
| 1.6 | Build question-type classifier | Python script using text analysis + LLM |
| 1.7 | Run classifier on all existing pages | Populate `question_type` for Physics + Pure Maths |
| 1.8 | Reclassify with sub-subtopics | Update `pages.topics[]` to use granular codes (1b.1 instead of just 1b) |
| 1.9 | Update `question_count` cache | SQL query to count questions per topic at each level |

### Phase 2: API Layer
**Estimated Time: 2-3 days**

| # | Task | Detail |
|---|------|--------|
| 2.1 | `GET /api/test-builder/topics` | Hierarchical topic tree with counts |
| 2.2 | `GET /api/test-builder/questions` | Paginated, filtered question browser |
| 2.3 | `POST /api/test-builder/tests` | Create test with selected questions |
| 2.4 | `PUT /api/test-builder/tests/[id]` | Update test (reorder, add/remove) |
| 2.5 | `GET /api/test-builder/tests/[id]/download` | PDF generation (QP + MS) |
| 2.6 | `GET /api/test-builder/tests` | List saved tests |
| 2.7 | `DELETE /api/test-builder/tests/[id]` | Delete test |

### Phase 3: Frontend — Core UI
**Estimated Time: 4-5 days**

| # | Task | Detail |
|---|------|--------|
| 3.1 | Create `/test-builder` route | Page layout with 3-column design |
| 3.2 | `SubjectSelector` component | Card grid, click to select |
| 3.3 | `TopicTree` component | Collapsible accordion with checkboxes and counts |
| 3.4 | `FilterBar` component | Difficulty, type, year, marks range dropdowns |
| 3.5 | `QuestionCard` component | Preview card with metadata badges |
| 3.6 | `QuestionBrowser` component | Grid/list view with pagination |
| 3.7 | `TestBasket` component | Sticky sidebar with selected questions |
| 3.8 | `QuestionPreviewModal` | Side-by-side QP + MS PDF preview |
| 3.9 | Drag-and-drop reordering | Use `@dnd-kit/sortable` for basket reordering |
| 3.10 | Test summary stats | Total marks, time, topic coverage chart |

### Phase 4: PDF Generation & Polish
**Estimated Time: 2-3 days**

| # | Task | Detail |
|---|------|--------|
| 4.1 | PDF merge with cover page | Add test title, date, total marks on page 1 |
| 4.2 | Page numbering | Inject page numbers into merged PDF |
| 4.3 | Mark scheme generation | Separate PDF with MS pages in same order |
| 4.4 | Download as ZIP | Option to download QP + MS as zip |
| 4.5 | Save & load tests | Persist test to DB, load later |
| 4.6 | Print-ready formatting | A4-optimized margins, headers |

### Phase 5: Extend to All Subjects
**Estimated Time: 2-3 days per subject**

| # | Task | Detail |
|---|------|--------|
| 5.1 | Chemistry IGCSE | Seed topics, classify questions |
| 5.2 | Biology IGCSE | Seed topics, classify questions |
| 5.3 | Maths A IGCSE | Seed topics, classify questions |
| 5.4 | Maths B IGCSE | Seed topics, classify questions |
| 5.5 | IAL Pure 1-4 | Seed topics, classify questions |
| 5.6 | IAL Mechanics 1 | Seed topics, classify questions |
| 5.7 | IAL Statistics 1 | Seed topics, classify questions |

---

## 9. Technical Implementation Details

### 9.1 Topic Tree Component (React)

```tsx
// Recursive collapsible tree with checkbox selection
interface TopicNode {
  id: string;
  code: string;
  name: string;
  depth: number;
  questionCount: number;
  children: TopicNode[];
}

function TopicTree({ topics, selected, onToggle }) {
  return (
    <div className="space-y-1">
      {topics.map(topic => (
        <TopicTreeNode 
          key={topic.id} 
          topic={topic} 
          selected={selected}
          onToggle={onToggle}
          depth={0}
        />
      ))}
    </div>
  );
}

function TopicTreeNode({ topic, selected, onToggle, depth }) {
  const [expanded, setExpanded] = useState(depth === 0); // chapters expanded by default
  const isSelected = selected.includes(topic.code);
  const hasChildren = topic.children?.length > 0;
  
  return (
    <div style={{ paddingLeft: depth * 16 }}>
      <div className="flex items-center gap-2 py-1 hover:bg-gray-700/50 rounded px-2">
        {hasChildren && (
          <button onClick={() => setExpanded(!expanded)}>
            {expanded ? '▼' : '▶'}
          </button>
        )}
        <input 
          type="checkbox" 
          checked={isSelected}
          onChange={() => onToggle(topic.code)}
        />
        <span className="flex-1">{topic.code} — {topic.name}</span>
        <span className="text-xs text-gray-400 bg-gray-700 px-2 py-0.5 rounded-full">
          {topic.questionCount}
        </span>
      </div>
      {expanded && hasChildren && (
        <div>
          {topic.children.map(child => (
            <TopicTreeNode
              key={child.id}
              topic={child}
              selected={selected}
              onToggle={onToggle}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}
```

### 9.2 Question Card Component

```tsx
function QuestionCard({ question, isInBasket, onAdd, onRemove, onPreview }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 hover:border-blue-500 transition">
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className="font-bold text-white">
            Q{question.questionNumber}
          </h3>
          <p className="text-xs text-gray-400">
            {question.year} {question.season} Paper {question.paperNumber}
          </p>
        </div>
        <DifficultyBadge level={question.difficulty} />
      </div>
      
      {/* Topic chips */}
      <div className="flex flex-wrap gap-1 mb-3">
        {question.topicNames.map(t => (
          <span key={t} className="text-xs bg-blue-900/50 text-blue-300 px-2 py-0.5 rounded">
            {t}
          </span>
        ))}
      </div>
      
      {/* Text excerpt */}
      <p className="text-sm text-gray-300 line-clamp-2 mb-3">
        {question.textExcerpt}
      </p>
      
      {/* Footer */}
      <div className="flex items-center justify-between">
        <div className="flex gap-3 text-xs text-gray-400">
          <span>{question.marks} marks</span>
          <span>{question.questionType}</span>
          <span>~{question.estimatedTime} min</span>
        </div>
        <div className="flex gap-2">
          <button onClick={() => onPreview(question)} className="text-blue-400 text-sm hover:underline">
            Preview
          </button>
          {isInBasket ? (
            <button onClick={() => onRemove(question.id)} className="bg-red-500/20 text-red-400 px-3 py-1 rounded text-sm">
              Remove
            </button>
          ) : (
            <button onClick={() => onAdd(question)} className="bg-green-500/20 text-green-400 px-3 py-1 rounded text-sm">
              + Add
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
```

### 9.3 Test Basket with Drag-and-Drop

```tsx
// Using @dnd-kit/sortable for reordering
import { DndContext, closestCenter } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable';

function TestBasket({ items, onReorder, onRemove, onGenerate }) {
  const totalMarks = items.reduce((sum, q) => sum + (q.marks || 0), 0);
  const totalTime = items.reduce((sum, q) => sum + (q.estimatedTime || 0), 0);
  
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 sticky top-4">
      <h2 className="text-lg font-bold text-white mb-4">
        Your Test ({items.length} questions)
      </h2>
      
      <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={items.map(i => i.id)} strategy={verticalListSortingStrategy}>
          {items.map((item, index) => (
            <SortableBasketItem 
              key={item.id} 
              item={item} 
              index={index}
              onRemove={onRemove}
            />
          ))}
        </SortableContext>
      </DndContext>
      
      <div className="mt-4 pt-4 border-t border-gray-600 text-sm text-gray-300 space-y-1">
        <div className="flex justify-between">
          <span>Total Marks:</span>
          <span className="font-bold text-white">{totalMarks}</span>
        </div>
        <div className="flex justify-between">
          <span>Est. Time:</span>
          <span className="font-bold text-white">{totalTime} min</span>
        </div>
      </div>
      
      <button 
        onClick={onGenerate}
        disabled={items.length === 0}
        className="w-full mt-4 bg-gradient-to-r from-green-500 to-emerald-600 text-white py-3 rounded-xl font-bold"
      >
        Generate Test PDF
      </button>
    </div>
  );
}
```

---

## 10. Key Design Decisions

| Decision | Choice | Reasoning |
|----------|--------|-----------|
| **Data source** | `pages` table (not `questions`) | Pages already have PDF URLs, topic arrays, and are the atomic unit for PDF generation |
| **Topic matching** | `pages.topics` array overlap | Already indexed with GIN, supports multi-topic questions |
| **State management** | React `useState` + URL params | No need for Redux; URL params enable shareable filter states |
| **Drag-and-drop** | `@dnd-kit/sortable` | Best React DnD library, accessible, lightweight |
| **PDF generation** | `pdf-lib` merge (existing) | Already proven in worksheet generator |
| **Auth** | Supabase Auth (existing) | Tests linked to `user_id` via RLS |

---

## 11. File Checklist — What to Create

```
# Database
supabase/migrations/XX_test_builder_schema.sql

# API Routes
src/app/api/test-builder/topics/route.ts
src/app/api/test-builder/questions/route.ts
src/app/api/test-builder/tests/route.ts
src/app/api/test-builder/tests/[testId]/route.ts
src/app/api/test-builder/tests/[testId]/download/route.ts

# Pages
src/app/test-builder/page.tsx
src/app/test-builder/layout.tsx

# Components
src/components/test-builder/TestBuilderPage.tsx
src/components/test-builder/SubjectSelector.tsx
src/components/test-builder/TopicTree.tsx
src/components/test-builder/FilterBar.tsx
src/components/test-builder/QuestionBrowser.tsx
src/components/test-builder/QuestionCard.tsx
src/components/test-builder/TestBasket.tsx
src/components/test-builder/TestBasketItem.tsx
src/components/test-builder/TestSummary.tsx
src/components/test-builder/QuestionPreviewModal.tsx
src/components/test-builder/DifficultyBadge.tsx
src/components/test-builder/GenerateTestDialog.tsx

# Scripts
scripts/seed_subtopics_physics.sql
scripts/seed_subtopics_pure_maths.sql
scripts/classify_question_types.py
scripts/update_topic_counts.sql

# Package additions
# npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
```

---

## 12. Priority Order (What to Build First)

```
Week 1: Foundation
  ✅ Day 1-2: DB migration + topic seeds (Physics + Pure Maths subtopics)
  ✅ Day 3: Question type classifier + run on existing data
  ✅ Day 4-5: API routes for topics, questions, tests

Week 2: Frontend Core
  ✅ Day 6-7: Subject selector + Topic tree + Filter bar
  ✅ Day 8-9: Question browser + Question cards
  ✅ Day 10: Test basket + Drag-and-drop

Week 3: Polish + Extend
  ✅ Day 11-12: PDF generation with cover page + mark scheme
  ✅ Day 13: Save/load tests, test history
  ✅ Day 14-15: Extend classification to remaining subjects
```

---

## Summary

You have **80% of the backend infrastructure** already built (pages with PDFs, topic tags, worksheets, PDF merging). The main work is:

1. **Deepen the topic hierarchy** (add sub-subtopics as Level 2)
2. **Add question-type classification** (MCQ vs structured vs calculation etc.)
3. **Build the 3-column test builder UI** (topic tree | question cards | basket)
4. **Add individual question selection** (not bulk topic selection like current)
5. **Implement drag-and-drop reordering** in the test basket
6. **Generate polished PDFs** with cover page and page numbers

The existing `/generate` worksheet generator can remain as a "quick generate" option while the new `/test-builder` becomes the premium, granular tool.
