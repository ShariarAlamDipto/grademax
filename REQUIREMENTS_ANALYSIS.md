# Requirements Analysis & Implementation Plan

## Critical Issues with Current Implementation

### ❌ VIOLATIONS OF NON-NEGOTIABLES

1. **Context Breaking** (CRITICAL)
   - Current: Tags individual parts (2(a)(i), 2(a)(ii) separately)
   - Required: Tag entire Question 2 as atomic bundle
   - Fix: Refactor tagging to question-level only

2. **Visual Fidelity Incomplete** (HIGH)
   - Current: Extract crops but no vector-first PDF builder
   - Required: pdf-lib vector region embedding, raster fallback only
   - Fix: Build new PDF generation module

3. **Segmentation Not Fence-Based** (HIGH)
   - Current: Regex patterns for (a), (b), (i), (ii)
   - Required: "Total for Question N = X marks" as hard fence
   - Fix: Rewrite segment.ts to respect fences

4. **No MS Linking** (HIGH)
   - Current: Parse MS but don't link to questions
   - Required: Confidence scores, ms_points[], verification
   - Fix: Build ms_parse_link.ts module

5. **No Auto-Detection** (MEDIUM)
   - Current: Manual file naming
   - Required: Front-page OCR → canonical naming
   - Fix: Build detect_metadata.ts

6. **No Year Filters** (MEDIUM)
   - Current: No year selection in builder
   - Required: List and range filters
   - Fix: Add to API and UI

## Architecture Redesign Required

### Database Schema Changes

```sql
-- ADD to questions table
ALTER TABLE questions ADD COLUMN IF NOT EXISTS header_bbox JSONB;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS header_visual_url TEXT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS context_text TEXT; -- Full stem + all parts
ALTER TABLE questions ADD COLUMN IF NOT EXISTS total_marks INT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS quality_flags TEXT[];

-- CREATE new tables
CREATE TABLE question_parts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
  code TEXT NOT NULL, -- '(a)', '(a)(i)', etc.
  marks INT,
  page_from INT,
  page_to INT,
  bbox_list JSONB NOT NULL, -- Array of {page, x, y, width, height}
  visual_hash TEXT,
  answer_space_lines INT,
  ms_link_confidence REAL,
  features JSONB,
  spec_refs TEXT[],
  diagram_urls TEXT[],
  diagram_dims JSONB,
  UNIQUE(question_id, code)
);

CREATE TABLE spec_statements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_id UUID REFERENCES subjects(id),
  spec_ref TEXT NOT NULL, -- e.g., "P1.2.3"
  text TEXT NOT NULL,
  topic_id UUID REFERENCES topics(id),
  UNIQUE(subject_id, spec_ref)
);

CREATE TABLE spec_match_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  spec_statement_id UUID REFERENCES spec_statements(id),
  rule_type TEXT CHECK (rule_type IN ('phrase', 'regex', 'formula')),
  pattern TEXT NOT NULL,
  weight REAL DEFAULT 1.0
);

CREATE TABLE topic_signals (
  question_id UUID REFERENCES questions(id),
  topic_id UUID REFERENCES topics(id),
  s1_sem REAL, -- Semantic similarity
  s2_lex REAL, -- Lexical match
  s3_kw REAL,  -- Keyword boost
  s4_struct REAL, -- Structural features
  final_score REAL,
  pipeline_version TEXT,
  computed_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY(question_id, topic_id)
);

CREATE TABLE part_topics (
  question_part_id UUID REFERENCES question_parts(id),
  topic_id UUID REFERENCES topics(id),
  confidence REAL,
  inherited_from_question BOOLEAN DEFAULT TRUE,
  PRIMARY KEY(question_part_id, topic_id)
);

-- ADD to papers table
ALTER TABLE papers ADD COLUMN IF NOT EXISTS meta JSONB;
ALTER TABLE papers ADD COLUMN IF NOT EXISTS doc_hash TEXT;
CREATE INDEX IF NOT EXISTS idx_papers_doc_hash ON papers(doc_hash);

-- Modify worksheet_items for part-level selection
CREATE TABLE IF NOT EXISTS worksheet_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  worksheet_id UUID REFERENCES worksheets(id) ON DELETE CASCADE,
  question_id UUID REFERENCES questions(id),
  part_code TEXT, -- NULL for whole question, or '(a)', '(a)(i)' for parts
  marks INT,
  answer_space_lines INT,
  spec_refs TEXT[],
  ms_points JSONB,
  estimated_seconds INT,
  UNIQUE(worksheet_id, question_id, part_code)
);
```

## Implementation Phases

### Phase 1: Fix Core Architecture (3-4 hours)
**Priority: CRITICAL**

1. **Database Migration** ✓
   - Run new schema changes
   - Backfill context_text for existing questions
   
2. **Fence-Based Segmentation** ✓
   - Rewrite segment.ts
   - Pattern: `/Total for Question\s+(\d+)\s*=\s*(\d+)\s*marks/i`
   - Hard boundaries at fences
   
3. **Question-Level Context** ✓
   - Extract full context (stem + all parts) as single text
   - Store in questions.context_text
   - Parts are children for marks/bbox only

4. **Question-Level Tagging** ✓
   - Tag using context_text (full question)
   - Store in question_topics (not at part level)
   - Cap at 3-4 topics per question

### Phase 2: MS Linking & Verification (2-3 hours)
**Priority: HIGH**

1. **MS Parser** ✓
   - Parse MS tables by (qnum, part, subpart)
   - Extract ms_points[] (bullets)
   
2. **Linking Algorithm** ✓
   - Match by composite key + marks + cue overlap
   - Compute ms_link_confidence [0,1]
   
3. **Verification API** ✓
   ```typescript
   POST /api/worksheets/ms/verify
   Returns: { part_code, marks, linked, confidence, hasPoints }[]
   ```

### Phase 3: Vector-First PDF Builder (4-5 hours)
**Priority: HIGH**

1. **PDF Region Embedding** ✓
   - Use pdf-lib to extract and embed vector regions
   - Preserve fonts, diagrams, spacing exactly
   
2. **Raster Fallback** ✓
   - Only for scanned/exotic pages
   - 300-400 DPI, cache by bbox hash
   
3. **Layout Engine** ✓
   - First-fit packing with soft scale (0.9× floor)
   - Deterministic answer lines
   - Multi-page bbox handling with "(continued)"

4. **Student/Teacher PDFs** ✓
   - Student: vector regions + answer lines
   - Teacher: same pages + appended answer pack

### Phase 4: Auto-Detection & Canonicalization (2-3 hours)
**Priority: MEDIUM**

1. **Front-Page Detection** ✓
   - Parse page 1 with pdfjs-dist
   - OCR fallback if text density low
   - Extract: Board, Level, Subject, Paper, Year, Season
   
2. **Canonical Naming** ✓
   - Format: `{Board}_{Level}_{SubjectCode}_{Year}{Season}_{PaperCode}`
   - Storage: `papers/{board}/{level}/{subject_code}/{year}/{season}/{paper_code}.pdf`
   
3. **Dedupe by doc_hash** ✓
   - SHA256 of normalized text
   - Skip if already ingested

### Phase 5: Year Filters & Builder UX (2 hours)
**Priority: MEDIUM**

1. **Year Selection** ✓
   - List: [2019, 2021, 2023]
   - Range: 2018-2023
   
2. **Builder Filters** ✓
   - Topics/Spec IDs
   - Difficulties
   - Years (list or range)
   - "Only unseen" toggle
   
3. **Mode Selection** ✓
   - Default: Whole questions (recommended)
   - Advanced: Parts only (auto-include stem)

### Phase 6: Rulepacks & Enhanced Tagging (3-4 hours)
**Priority: MEDIUM**

1. **YAML Rulepacks** ✓
   - spec_statements
   - phrase_rules, formula_rules
   - command_words tiers
   - aliases (×→x, ρ→rho, etc.)
   
2. **Multi-Stage Tagging** ✓
   ```
   S_rule_Q = phrase_rules ∪ formula_rules
   S_ms_Q   = cues from ms_points
   S_sem_Q  = semantic similarity (if needed)
   question_topics = cap_to_4(S_rule_Q ∪ S_ms_Q ∪ S_sem_Q)
   ```

### Phase 7: Testing & QA Dashboard (2-3 hours)
**Priority: HIGH**

1. **Acceptance Tests** ✓
   - Visual fidelity checks
   - Context preservation
   - Fence-based segmentation
   - MS linking ≥95% @ confidence ≥0.8
   - No duplicates
   - Year filters working
   
2. **QA Dashboard** ✓
   - Low ms_link_confidence alerts
   - Empty topics warnings
   - OCR hits tracking
   - Duplicate detection

## Total Estimated Time: 18-24 hours

## Current Status Assessment

**What needs immediate attention:**
1. ⚠️ **CRITICAL**: Refactor tagging to question-level (violates non-negotiable)
2. ⚠️ **CRITICAL**: Implement fence-based segmentation (violates non-negotiable)
3. ⚠️ **HIGH**: Build vector-first PDF generator (current has no student PDF output)
4. ⚠️ **HIGH**: Implement MS linking system

**What can wait:**
- Auto-detection (can use current manual naming temporarily)
- Year filters (can add to UI later)
- Rulepacks (can start with simpler rules)

## Recommended Immediate Actions

1. **Stop current ingestion** - it's creating wrong data structure
2. **Run database migration** - add question_parts, spec tables
3. **Rewrite segment.ts** - fence-based, context-preserving
4. **Refactor tagging** - question-level only
5. **Build PDF generator** - vector-first with pdf-lib
6. **Then**: Resume ingestion with correct architecture

## Decision Required

Do you want to:
- **Option A**: Fix critical issues first (items 1-4 above), ~8-10 hours
- **Option B**: Full rebuild following spec exactly, ~18-24 hours
- **Option C**: Continue with current approach but acknowledge deviations

**Recommendation**: Option A - Fix critical violations first, then iterate.
