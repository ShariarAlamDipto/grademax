# Full Rebuild Implementation Plan
**Based on Complete Requirements Spec**

## Phase 1: Database & Infrastructure ✅
**Time**: 1 hour
**Status**: ✅ COMPLETE

### Tasks
- [x] Create migration 004 (core architecture redesign)
- [x] Create type definitions (types/ingestion.ts)
- [x] Set up module structure
- [ ] Run migration in Supabase (USER ACTION REQUIRED)

---

## Phase 2: Fence-Based Segmentation (NEXT)
**Time**: 2-3 hours
**Status**: ⏳ PENDING

### Module: `ingest/segment.ts`
**Purpose**: Extract questions using "Total for Question N = X marks" fences

**Algorithm**:
```typescript
1. Parse all text with pdfjs-dist
2. Find all fences: /Total for Question\s+(\d+)\s*=\s*(\d+)\s*marks/i
3. For each question fence:
   - Extract text from previous fence (or start) to current fence
   - Find question number header (e.g., "1 ", "2 ")
   - Identify parts: (a), (b), (c) using left-margin banding
   - Identify subparts: (i), (ii), (iii) within parts
   - Build hierarchy: question → parts → subparts
4. Store:
   - questions.context_text = full stem + all part text (for tagging)
   - questions.header_bbox = bbox of stem region (before first part)
   - question_parts.bbox_list = array of bboxes per part
```

**Output**:
```typescript
interface SegmentedQuestion {
  questionNumber: string // "1", "2", etc.
  totalMarks: number
  contextText: string // Full text for tagging
  headerBBox: BBox // Stem region
  parts: Array<{
    code: string // "(a)", "(b)", "(a)(i)", etc.
    marks: number
    bboxList: BBox[] // Can span multiple pages
    text: string // For MS linking
  }>
}
```

---

## Phase 3: Markscheme Parsing & Linking
**Time**: 2-3 hours
**Status**: ⏳ PENDING

### Module: `ingest/ms_parse_link.ts`
**Purpose**: Parse MS and link to questions with confidence scores

**Algorithm**:
```typescript
1. Parse MS PDF:
   - Detect table structure (qnum, part, marks columns)
   - Extract bullet points per part
   - Identify formulas, keywords
   
2. For each question part:
   - Match by (qnum, part, subpart) composite key
   - Verify marks equality
   - Compute cue overlap (formulas + keywords)
   - Calculate confidence: 
     confidence = 0.4 * key_match + 0.3 * marks_match + 0.3 * cue_overlap
   
3. Store:
   - question_parts.ms_link_confidence
   - question_parts.ms_points (array of bullet strings)
   - question_parts.ms_snippet (short excerpt for QA)
```

**Output**:
```typescript
interface MSLink {
  partId: string
  confidence: number // [0, 1]
  msPoints: string[] // ["Award 1 mark for...", "Accept ±0.1"]
  msSnippet: string // First 100 chars
}
```

---

## Phase 4: Context-Aware Tagging
**Time**: 3-4 hours
**Status**: ⏳ PENDING

### Module: `ingest/tagging.ts`
**Purpose**: Tag whole questions using rules + MS + semantic fallback

**Algorithm**:
```typescript
1. Load rulepacks (YAML):
   - phrase_rules: {"kinetic energy" → P1.2.3}
   - formula_rules: {/E\s*=\s*mc²/ → P2.1.4}
   - command_words: {calculate: tier2, explain: tier3}
   
2. For each question (using context_text):
   a) Rule matching:
      S_rule_Q = phrase_rules ∪ formula_rules
      
   b) MS cue extraction:
      S_ms_Q = extract_topics_from(ms_points)
      
   c) Semantic fallback (if S_rule_Q ∪ S_ms_Q empty):
      S_sem_Q = top_k_similar(context_text, spec_statements, k=5, τ=0.7)
      
   d) Combine and cap:
      topics = cap_to_4(S_rule_Q ∪ S_ms_Q ∪ S_sem_Q)
      
3. Store:
   - question_topics(question_id, topic_id, confidence, source)
   - topic_signals(question_id, topic_id, s1_sem, s2_lex, s3_kw, final_score)
```

**Output**:
```typescript
interface QuestionTag {
  questionId: string
  topicId: string
  confidence: number
  source: 'rule_phrase' | 'rule_formula' | 'ms_cue' | 'semantic'
  signals: {
    s1_sem: number
    s2_lex: number
    s3_kw: number
    s4_struct: number
  }
}
```

---

## Phase 5: Vector-First PDF Builder
**Time**: 4-5 hours
**Status**: ⏳ PENDING

### Module: `lib/pdf_builder.ts`
**Purpose**: Generate student/teacher PDFs with embedded vector regions

**Algorithm**:
```typescript
1. Create new PDF with pdf-lib
2. Add front page:
   - Title, subject, year range
   - Total marks, recommended time
   - Candidate name line
   
3. For each worksheet item:
   a) Load source PDF
   b) Extract vector region using bbox coordinates
   c) Embed into output PDF at target position
   d) If vector fails (scanned page):
      - Render bbox region at 300 DPI
      - Cache by bbox hash
      - Embed as image
   e) Add marks badge (top-right)
   f) Draw answer lines below (deterministic)
   
4. Layout engine:
   - Target width: 470pt (printable)
   - Scale: scale = 470 / bbox.width
   - Soft downscale floor: 0.9×
   - Min effective font size: ~9pt
   - Page break if overflow
   
5. Teacher PDF:
   - Same pages as student
   - Append "Answer Pack" with ms_points
```

**Output**:
```typescript
interface PDFOutput {
  studentPdf: Buffer
  teacherPdf: Buffer
  metadata: {
    totalPages: number
    totalMarks: number
    estimatedMinutes: number
    rasterFallbackCount: number
  }
}
```

---

## Phase 6: Front-Page Auto-Detection
**Time**: 2-3 hours
**Status**: ⏳ PENDING

### Module: `ingest/detect_metadata.ts`
**Purpose**: Parse front page and generate canonical naming

**Algorithm**:
```typescript
1. Render page 1 with pdfjs-dist
2. Extract text items with positions
3. Pattern matching:
   - Board: /Cambridge|Edexcel|AQA|OCR/i
   - Level: /IGCSE|IAL|A\s*Level|GCSE/i
   - Subject: /Physics|Chemistry|Biology|Mathematics/i + code
   - Paper: /Paper\s*(\d+)/i
   - Year: /\b(20\d{2})\b/
   - Season: /June?|November?|March?|May/i
   
4. If text density < 50 chars/page:
   - Run tesseract.js OCR
   - Cache result
   
5. Fallback naming:
   - Parse filename with regex
   - Use standard format
   
6. Generate canonical storage key:
   papers/{board}/{level}/{subject_code}/{year}/{season}/{paper_code}.pdf
   
7. Compute doc_hash (SHA256 of normalized text)
8. Skip if doc_hash exists
```

**Output**:
```typescript
interface DetectedMetadata {
  board: string
  level: string
  subjectCode: string
  subjectName: string
  paperType: 'QP' | 'MS'
  paperNumber: string
  variant: string
  year: number
  season: string
  detectedFrom: 'page1' | 'ocr' | 'filename_fallback'
  confidence: number
  canonicalKey: string
  docHash: string
}
```

---

## Phase 7: Year Filters & Builder API
**Time**: 2 hours
**Status**: ⏳ PENDING

### Module: `app/api/worksheets/generate/route.ts`
**Purpose**: Generate worksheets with year filtering

**API**:
```typescript
POST /api/worksheets/generate
{
  subjectCode: string
  topicIds: string[]
  specRefs?: string[]
  difficulties?: ('easy' | 'medium' | 'hard')[]
  yearFrom?: number
  yearTo?: number
  yearsList?: number[]
  count: number
  mixPreset?: '60-30-10' | 'ascending'
  wholeQuestion?: boolean // default: true
  onlyUnseen?: boolean
  teacherVersion?: boolean
  includeMarkscheme?: boolean
}

Response: {
  worksheetId: string
  questionCount: number
  totalMarks: number
  estimatedMinutes: number
}
```

**Algorithm**:
```typescript
1. Build query:
   - Filter by subject, topics
   - Year filter: WHERE year IN (yearsList) OR year BETWEEN (yearFrom, yearTo)
   - Difficulty filter
   - Exclude: SELECT question_id FROM worksheet_items WHERE worksheet_id IN (last N)
   
2. Apply mix preset:
   - 60-30-10: 60% easy, 30% medium, 10% hard
   - Ascending: ORDER BY difficulty ASC
   
3. Dedupe check:
   - Ensure no (question_id, part_code) repeats
   - Check visual_hash collisions
   
4. Create worksheet + items
5. Return worksheetId
```

---

## Phase 8: Rulepacks System
**Time**: 3-4 hours
**Status**: ⏳ PENDING

### Module: `ingest/rulepacks/`
**Structure**:
```
rulepacks/
  physics_igcse.yaml
  chemistry_igcse.yaml
  loader.ts
  matcher.ts
```

**YAML Format**:
```yaml
subject: Physics IGCSE
code: 4PH1

spec_statements:
  - ref: P1.2.3
    topic_id: uuid-here
    text: "Describe the energy transfers involving kinetic and potential energy"
    keywords:
      - kinetic energy
      - potential energy
      - energy transfer

phrase_rules:
  - pattern: "kinetic energy"
    spec_refs: [P1.2.3, P1.2.4]
    weight: 1.0
  - pattern: "gravitational potential energy"
    spec_refs: [P1.2.5]
    weight: 1.0

formula_rules:
  - pattern: "E\\s*=\\s*mc²"
    spec_refs: [P2.1.4]
    weight: 1.5
  - pattern: "KE\\s*=\\s*½mv²"
    spec_refs: [P1.2.3]
    weight: 1.5

command_words:
  tier1_recall: [state, define, label, name]
  tier2_calculate: [calculate, determine, find, work out]
  tier3_explain: [explain, describe, suggest, evaluate]

aliases:
  "×": "x"
  "÷": "/"
  "ρ": "rho"
  "Ω": "ohm"
```

---

## Phase 9: Testing & QA Dashboard
**Time**: 2-3 hours
**Status**: ⏳ PENDING

### Module: `app/api/admin/qa/route.ts`
**Purpose**: Monitor quality and catch issues

**Endpoints**:
```typescript
GET /api/admin/qa/low-confidence
// Returns questions with ms_link_confidence < 0.8

GET /api/admin/qa/empty-topics
// Returns questions with no topics

GET /api/admin/qa/ocr-hits
// Returns questions where OCR was used

GET /api/admin/qa/duplicates
// Returns potential duplicates by visual_hash

POST /api/worksheets/ms/verify
// Returns MS linking report per worksheet
```

**Dashboard**:
- Visual fidelity checker (compare source vs output)
- Context preservation validator
- Fence boundary checker
- MS linking quality report

---

## Phase 10: Integration & Polish
**Time**: 2-3 hours
**Status**: ⏳ PENDING

### Tasks
- [ ] Wire all modules together
- [ ] Update `ingest_papers.ts` to use new modules
- [ ] Build worksheet generator UI
- [ ] Add year filter controls
- [ ] Implement "Only unseen" toggle
- [ ] Add acceptance tests
- [ ] Performance optimization
- [ ] Documentation

---

## Implementation Order

### Week 1: Core Foundation
1. ✅ Database migration (1h)
2. 🔄 Fence-based segmentation (3h)
3. 🔄 MS parsing & linking (3h)
4. 🔄 Context-aware tagging (4h)

### Week 2: PDF & Detection
5. 🔄 Vector-first PDF builder (5h)
6. 🔄 Front-page auto-detection (3h)
7. 🔄 Year filters & builder API (2h)

### Week 3: Rulepacks & Testing
8. 🔄 Rulepacks system (4h)
9. 🔄 Testing & QA dashboard (3h)
10. 🔄 Integration & polish (3h)

**Total**: 31 hours over 3 weeks

---

## Success Criteria

### Visual Fidelity
- [ ] Student PDFs use ONLY embedded vector regions
- [ ] Diagrams preserved exactly
- [ ] Fonts, spacing identical to source
- [ ] Raster fallback < 10% of cases
- [ ] DPI ≥ 300 for any rasters

### Context & Tagging
- [ ] Topics assigned at question level
- [ ] ≥98% questions have ≥1 topic
- [ ] Average ≥1.6 topics/question
- [ ] Cap ≤4 topics/question
- [ ] Parts inherit with priors

### Segmentation
- [ ] Fences define hard boundaries
- [ ] 100% parts have valid bbox_list
- [ ] No cross-fence splits
- [ ] OCR used only on flagged pages

### MS Linking
- [ ] ≥95% parts have confidence ≥ 0.8
- [ ] Marks equality verified
- [ ] MS verification endpoint working

### Year Filters
- [ ] List and range filters working
- [ ] Strictly honored in queries
- [ ] "Only unseen" excludes last N worksheets

### Deduplication
- [ ] No duplicates within worksheet
- [ ] Visual hash prevents duplicates
- [ ] Strict mode for near-duplicates

### Performance
- [ ] 20-question worksheet renders < 1.5s
- [ ] PDF < 8MB
- [ ] Raster fallbacks < 10%

---

**Status**: Phase 1 in progress
**Next**: Run migration, then start segmentation module
