# GradeMax Visual Rendering Implementation Roadmap

## 🎯 Vision
Build a production-grade worksheet generator that preserves **EXACT visual fidelity** by rendering PDF crops (not text) and maximizes topic matching with deterministic rules + semantic fallback.

## 📊 Current State (As of Implementation Start)

### ✅ Completed
- UUID schema with Supabase (pgvector)
- Text extraction pipeline with pdf-parse
- Question segmentation (main questions + subparts)
- Topic auto-tagging with MiniLM-L6-v2 embeddings
- Basic markscheme linking by question number
- 50 questions ingested with proper numbers (1, 2(a)(i), etc.)
- 47 markscheme entries matched
- 21 topics loaded

### ⚠️ Current Limitations
- **Text-based rendering** - loses formatting, fonts, spacing, diagrams
- No visual crop extraction
- Basic topic matching (embeddings only, no rule-based system)
- No perceptual deduplication
- No PDF export (@react-pdf/renderer not integrated)
- No front-page metadata detection
- No answer space calculation

## 🏗️ Architecture Pivot

### Before (Text-Based)
```
PDF → pdf-parse → Text → Question segmentation → Store text → 
Render from text (loses formatting)
```

### After (Visual Crops)
```
PDF → pdfjs-dist → Text items + positions → BBox detection →
Render crops at 300 DPI → Store PNGs → Embed crops in worksheet
(preserves exact formatting)
```

## 📋 Implementation Phases

### Phase 1: Visual Extraction Core ✅ STARTED
**Goal**: Extract visual crops with exact fidelity

**Components**:
- [x] Install: pdfjs-dist, canvas, sharp, @react-pdf/renderer
- [ ] `visual_extract.ts`: BBox detection + PNG rendering
- [ ] Test on sample paper (verify crops match original)
- [ ] Upload crops to Supabase Storage
- [ ] Store visual_url, visual_dims, visual_hash in DB

**Acceptance**:
- ✓ Crops preserve fonts, spacing, diagrams
- ✓ DPI ≥ 300
- ✓ File size reasonable (< 200 KB per question)

**Migration Needed**:
```sql
ALTER TABLE questions ADD COLUMN visual_url TEXT;
ALTER TABLE questions ADD COLUMN visual_dims JSONB; -- {width, height, dpi}
ALTER TABLE questions ADD COLUMN visual_hash TEXT; -- sha256 for dedup
CREATE INDEX idx_questions_visual_hash ON questions(visual_hash);
```

---

### Phase 2: Enhanced Segmentation
**Goal**: Detect precise bounding boxes for all question parts

**Components**:
- [ ] `bbox_detector.ts`: Advanced segmentation with:
  - Text item clustering by y-coordinate (line detection)
  - Left-margin analysis for part headers (a), (b), (i), (ii)
  - Fence detection: `/Total for Question\s+(\d+)/`
  - Diagram detection: extend bbox to cover XObjects
  - Multi-page stitching
- [ ] Handle subparts: (a), (b), (i), (ii) with proper hierarchy
- [ ] Store per-part bboxes (not just main questions)

**Schema Changes**:
```sql
-- Store bbox per part, not per question
ALTER TABLE questions ADD COLUMN bboxes JSONB; -- [{page, x, y, w, h}]
```

---

### Phase 3: Rulepack System
**Goal**: Maximize topic/spec matching with deterministic rules

**Components**:
- [ ] `rulepacks/`: YAML files per subject
  ```yaml
  subject: "4PH1_Physics"
  spec_statements:
    - ref: "1a.1"
      text: "Recall and use SI units"
      topic_id: "uuid"
      keywords: ["units", "SI", "conversion"]
    - ref: "1b.2"
      text: "Describe motion using displacement-time graphs"
      keywords: ["displacement", "graph", "motion"]
  
  phrase_rules:
    - pattern: "SI unit"
      spec_refs: ["1a.1"]
    - pattern: "displacement.*graph"
      spec_refs: ["1b.2"]
  
  formula_rules:
    - pattern: "F\\s*=\\s*m\\s*[×x]\\s*a"
      spec_refs: ["1c.5"]
  
  command_words:
    - word: "recall"
      difficulty: 1
    - word: "calculate"
      difficulty: 2
    - word: "explain"
      difficulty: 3
  ```

- [ ] `rulepack_loader.ts`: Load and index rules
- [ ] `spec_matcher.ts`:
  ```typescript
  function matchSpecs(questionText: string, msPoints: string[]): SpecMatch[] {
    // 1. Deterministic rules (phrase + formula)
    const ruleMatches = applyPhraseRules(questionText)
      .concat(applyFormulaRules(questionText))
    
    // 2. MS-derived specs (if msPoints present)
    const msMatches = extractSpecsFromMS(msPoints)
    
    // 3. Semantic fallback (if rule matches empty OR multi-topic hint)
    let semanticMatches = []
    if (ruleMatches.length === 0 || hasMultiTopicHint(questionText)) {
      semanticMatches = await semanticSearch(questionText, topK=3, threshold=0.42)
    }
    
    // 4. Union + cap logic
    const allMatches = unique([...ruleMatches, ...msMatches, ...semanticMatches])
    const cap = isCalculation(questionText) ? 3 : 2
    return allMatches.slice(0, cap)
  }
  ```

**Schema Changes**:
```sql
ALTER TABLE questions ADD COLUMN spec_refs TEXT[]; -- multi-label
CREATE TABLE topic_signals (
  question_id UUID REFERENCES questions(id),
  topic_id UUID REFERENCES topics(id),
  s1_semantic FLOAT,  -- embedding similarity
  s2_lexical FLOAT,   -- BM25 score
  s3_keyword FLOAT,   -- keyword boost
  s4_structural FLOAT, -- part position, command word
  final_score FLOAT,
  pipeline_version TEXT,
  computed_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (question_id, topic_id)
);
```

---

### Phase 4: Metadata Detection & Canonical Storage
**Goal**: Auto-detect board, subject, year from PDF front page

**Components**:
- [ ] `metadata_detector.ts`:
  - Parse front page for: Board, Level, Subject, Year, Season, Paper Code
  - Fallback to header/footer scan (pages 2-3)
  - Generate canonical filename: `{Board}_{Level}_{SubjectCode}_{Year}{Season}_{PaperCode}.pdf`
- [ ] Upload to canonical path: `papers/{board}/{level}/{subject}/{year}/{season}/{code}.pdf`
- [ ] Store `doc_hash` (sha256 of content) for dedup

**Schema Changes**:
```sql
ALTER TABLE papers ADD COLUMN meta JSONB; -- {board, level, subject_name, detected_from}
ALTER TABLE papers ADD COLUMN doc_hash TEXT UNIQUE;
CREATE INDEX idx_papers_doc_hash ON papers(doc_hash);
```

---

### Phase 5: Answer Space Calculation
**Goal**: Precompute answer lines for each part

**Components**:
- [ ] `answer_space.ts`:
  ```typescript
  function calculateAnswerLines(marks: number, commandWords: string[]): number {
    if (isMCQ) return 0
    
    let lines = marksToLines[marks] || Math.ceil(marks * 2.5)
    
    if (hasWord(commandWords, ['calculate', 'show'])) lines += 2
    if (hasWord(commandWords, ['explain', 'evaluate', 'derive'])) lines += 4
    
    return lines
  }
  ```

**Schema Changes**:
```sql
ALTER TABLE questions ADD COLUMN answer_space_lines INT;
ALTER TABLE questions ADD COLUMN command_words TEXT[];
```

---

### Phase 6: PDF Export (Student/Teacher)
**Goal**: Generate worksheets with visual crops

**Components**:
- [ ] `pdf_export/student_pdf.tsx`:
  ```tsx
  import { Document, Page, Image, Text } from '@react-pdf/renderer'
  
  function StudentWorksheet({ items }) {
    return (
      <Document>
        <Page size="A4">
          <Text>Physics Worksheet - Total: {totalMarks} marks</Text>
        </Page>
        {items.map(item => (
          <Page key={item.id}>
            {/* Visual crop */}
            <Image src={item.visual_url} />
            {/* Marks badge */}
            <Text style={{position: 'absolute', right: 10, top: 10}}>
              [{item.marks}]
            </Text>
            {/* Answer lines */}
            {renderAnswerLines(item.answer_space_lines)}
          </Page>
        ))}
      </Document>
    )
  }
  ```

- [ ] `pdf_export/teacher_pdf.tsx`: Same as student + Answer Pack append
- [ ] API route: `/api/worksheets/[id]/pdf`

---

### Phase 7: Builder UX with Dedupe Guards
**Goal**: Filters + visual cards + no-repeat enforcement

**Components**:
- [ ] Filter panel:
  - Board → Level → Subject → Topics (multi-select)
  - Spec IDs (autocomplete)
  - Difficulty range
  - Year range
  - "Only unseen" toggle
- [ ] Question cards:
  - Thumbnail (scaled visual crop)
  - Marks, spec chips, estimated time
  - "In Recent" badge (if in last N worksheets)
  - Disable "Add" if already in selection
- [ ] Mix presets: 60/30/10 Easy/Med/Hard
- [ ] Real-time totals: marks, time, topic distribution

**Schema Changes**:
```sql
CREATE TABLE user_worksheets (
  user_id UUID,
  worksheet_id UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Track recent worksheets for "Only unseen"
CREATE INDEX idx_user_worksheets_recent 
  ON user_worksheets(user_id, created_at DESC);
```

---

### Phase 8: Deduplication (Hard + Near-Duplicate)
**Goal**: Zero duplicates within worksheet, optional cross-worksheet

**Components**:
- [ ] Hard uniqueness:
  ```sql
  CREATE UNIQUE INDEX idx_worksheet_items_unique
    ON worksheet_items(worksheet_id, question_id);
  ```
- [ ] Visual hash check (exact duplicates)
- [ ] Perceptual hash (near-duplicates):
  ```typescript
  import { imageHash } from 'sharp-phash'
  
  async function isNearDuplicate(crop1: Buffer, crop2: Buffer): Promise<boolean> {
    const hash1 = await imageHash(crop1)
    const hash2 = await imageHash(crop2)
    const distance = hammingDistance(hash1, hash2)
    return distance < 5 // threshold
  }
  ```
- [ ] "Only unseen" filter:
  ```sql
  SELECT q.* FROM questions q
  WHERE q.id NOT IN (
    SELECT wi.question_id 
    FROM worksheet_items wi
    JOIN user_worksheets uw ON wi.worksheet_id = uw.worksheet_id
    WHERE uw.user_id = $1
      AND uw.created_at > NOW() - INTERVAL '30 days'
  )
  ```

---

### Phase 9: QA Dashboard
**Goal**: Monitor ingestion quality

**Components**:
- [ ] `/admin/qa` page showing:
  - Papers with low MS link confidence (< 0.8)
  - Questions missing spec_refs
  - Duplicate visual_hash detected
  - OCR usage rate
  - Topic signal distribution (S1-S4)
- [ ] Export to CSV for manual review

---

## 🚀 Migration Strategy

### Option A: Gradual (Recommended)
1. Keep existing text-based system running
2. Ingest NEW papers with visual crops in parallel
3. Add feature flag: `USE_VISUAL_CROPS`
4. Test with pilot users
5. Migrate historical papers (run batch job)
6. Deprecate text rendering

### Option B: Big Bang
1. Run migration script on all 50 existing questions
2. Extract visual crops from stored PDFs
3. Update all records with visual_url
4. Deploy new UI immediately

**Recommendation**: Option A for safety

---

## 📏 Acceptance Criteria (Must Pass)

### Visual Fidelity
- [ ] Student PDF contains ONLY visual crops (no reflowed text)
- [ ] Diagrams preserved
- [ ] DPI ≥ 300
- [ ] PDF size < 8 MB per 20-part worksheet

### Segmentation
- [ ] 100% parts have bboxes
- [ ] Fences respected
- [ ] Multi-page parts handled

### MS Linking
- [ ] ≥ 95% parts have confidence ≥ 0.8

### Topic/Spec Matching
- [ ] ≥ 98% parts have ≥ 1 spec_ref
- [ ] Multi-topic parts average ≥ 1.6 spec_refs
- [ ] Caps enforced (≤3 per part)

### Deduplication
- [ ] Zero duplicates within worksheet
- [ ] "Only unseen" blocks last N worksheets
- [ ] Near-duplicate threshold < δ

### Performance
- [ ] MV refresh < 30s on 50k parts
- [ ] Crop generation < 2s per page
- [ ] PDF export < 5s for 20-part worksheet

---

## 🛠️ Next Steps

1. **Immediate**: Fix visual_extract.ts TypeScript errors
2. **Today**: Test crop extraction on sample paper
3. **This Week**: Complete Phase 1 (visual extraction + storage)
4. **Next Week**: Phase 2 (enhanced segmentation) + Phase 3 (rulepacks)
5. **Following**: Phases 4-6 (metadata, answer space, PDF export)

---

## 📚 Resources

- [pdfjs-dist API](https://mozilla.github.io/pdf.js/api/)
- [@react-pdf/renderer docs](https://react-pdf.org/)
- [sharp image processing](https://sharp.pixelplumbing.com/)
- [pgvector similarity search](https://github.com/pgvector/pgvector)

---

**Status**: Phase 1 in progress
**Last Updated**: 2025-10-10
