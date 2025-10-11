# Implementation Tracker
**Zero-Paid-API Worksheet Generator - Full Rebuild**

## Progress Overview
- **Started**: 2025-10-10
- **Target**: 3 weeks (31 hours)
- **Status**: 🔄 Week 1 - Day 1

---

## ✅ COMPLETED

### Database & Types (1h)
- [x] migration 004: Core architecture redesign
- [x] types/ingestion.ts: Complete type definitions
- [x] ingest/segment.ts: Fence-based segmentation (WIP - needs testing)

---

## 🔄 IN PROGRESS

### Week 1: Core Foundation

#### Day 1 (Today) - Target: 8h
- [x] Database migration (1h)
- [x] Type definitions (0.5h)
- [ ] **CURRENT**: Fence-based segmentation module (2h remaining)
  - [x] Basic structure
  - [ ] PDF.js integration
  - [ ] Testing with sample paper
- [ ] MS parsing & linking (3h)
- [ ] Context-aware tagging (4h)

---

## 📋 REMAINING MODULES

### Week 1: Core Foundation (8h remaining)

**Module 2: parse_pdf.ts** (1.5h)
```typescript
Purpose: Extract text items from PDF with pdfjs-dist
Output: TextItem[] with {text, x, y, width, height, fontSize}
Features:
- Page-by-page text extraction
- OCR fallback for low-text density pages
- Image/XObject detection
- Page dimensions
```

**Module 3: segment.ts** (1.5h remaining)
```typescript
Status: 70% complete
Remaining:
- PDF.js integration
- Multi-page bbox handling
- Testing with real paper
```

**Module 4: ms_parse_link.ts** (3h)
```typescript
Purpose: Parse MS and link to questions
Algorithm:
1. Detect MS table structure
2. Extract (qnum, part, marks, points)
3. Match by composite key + marks + cues
4. Compute confidence [0,1]
5. Store ms_points[], ms_snippet
```

**Module 5: tagging.ts** (4h)
```typescript
Purpose: Question-level topic tagging
Steps:
1. Load rulepacks (YAML)
2. Apply phrase_rules + formula_rules
3. Extract MS cues
4. Semantic fallback (MiniLM)
5. Cap to 3-4 topics
6. Store with provenance
```

### Week 2: PDF Builder & Detection (13h)

**Module 6: detect_metadata.ts** (3h)
```typescript
Purpose: Auto-detect paper metadata from page 1
Steps:
1. Render page 1 with pdfjs
2. Pattern match: Board, Level, Subject, Year, Season
3. OCR fallback if needed
4. Generate canonical storage key
5. Compute doc_hash for dedupe
```

**Module 7: bbox_synthesis.ts** (2h)
```typescript
Purpose: Generate precise bboxes for regions
Features:
- Header bbox (stem only)
- Part bbox_list (can span pages)
- Expand for adjacent diagrams
- Multi-page handling
```

**Module 8: lib/pdf_builder.ts** (5h)
```typescript
Purpose: Vector-first PDF generation
Features:
- pdf-lib region embedding
- Raster fallback (300 DPI)
- Layout engine (first-fit packing)
- Answer lines (deterministic)
- Student + Teacher PDFs
```

**Module 9: features.ts** (1h)
```typescript
Purpose: Extract question features
Extract:
- Command words (state, calculate, explain)
- Formulas (regex patterns)
- Answer space lines
- Estimated seconds (marks × factor)
```

**Module 10: persist.ts** (2h)
```typescript
Purpose: Idempotent database persistence
Features:
- UPSERT questions + parts
- Compute visual_hash
- Store doc_hash
- Skip unchanged (dedupe)
```

### Week 3: Rulepacks, API & Testing (10h)

**Module 11: rulepacks/** (4h)
```typescript
Structure:
- loader.ts: YAML parser
- matcher.ts: Rule application
- physics_igcse.yaml
- chemistry_igcse.yaml

YAML Format:
- spec_statements
- phrase_rules
- formula_rules
- command_words (tier1/2/3)
- aliases
```

**Module 12: API Routes** (3h)
```typescript
Routes:
- POST /api/ingest/run
- POST /api/worksheets/generate
- POST /api/worksheets/pdf
- POST /api/worksheets/ms/verify
- GET /api/admin/qa/*
```

**Module 13: Testing & QA** (3h)
```typescript
Acceptance Tests:
- Visual fidelity check
- Context preservation
- Fence boundaries
- MS linking ≥95% @ ≥0.8
- Year filters
- Dedupe guarantees
- Performance <1.5s for 20Q

QA Dashboard:
- Low confidence alerts
- Empty topics
- OCR hits
- Duplicates
```

---

## 🎯 Critical Path

### Must Complete First (Blockers)
1. ✅ Database migration
2. 🔄 Fence-based segmentation
3. ⏳ MS parsing & linking
4. ⏳ Context-aware tagging
5. ⏳ PDF builder (vector-first)

### Can Parallelize
- detect_metadata.ts (nice-to-have for MVP)
- rulepacks (can use simple rules initially)
- QA dashboard (post-launch)

---

## 🚀 Today's Goals (Day 1)

### Must Complete
- [x] Database migration created
- [x] Types defined
- [ ] segment.ts finished & tested
- [ ] parse_pdf.ts created
- [ ] Start ms_parse_link.ts

### Stretch Goals
- [ ] Complete ms_parse_link.ts
- [ ] Start tagging.ts

---

## 📊 Module Dependencies

```
parse_pdf.ts
    ↓
segment.ts → ms_parse_link.ts
    ↓              ↓
bbox_synthesis → tagging.ts → persist.ts
    ↓                           ↓
pdf_builder.ts ←────────────────┘
    ↓
API routes + UI
```

---

## ⚠️ Known Challenges

1. **PDF.js Text Extraction**: Text items can be fragmented
   - Solution: Normalize and merge adjacent items
   
2. **Fence Detection**: Some papers don't have "Total for Question"
   - Solution: Fallback to question number patterns
   
3. **MS Table Parsing**: Tables have inconsistent formats
   - Solution: Multiple parsing strategies with confidence

4. **Vector Region Embedding**: pdf-lib doesn't support all PDF features
   - Solution: Raster fallback at 300 DPI

5. **Performance**: Large PDFs can be slow
   - Solution: Caching, pagination, worker threads

---

## 📝 Next Steps (Immediate)

1. **Complete segment.ts**
   - Add PDF.js integration
   - Test with sample paper
   - Fix lint errors

2. **Create parse_pdf.ts**
   - pdfjs-dist text extraction
   - OCR detection
   - Page dimensions

3. **Create ms_parse_link.ts**
   - MS table parsing
   - Linking algorithm
   - Confidence calculation

4. **USER ACTION**: Run migration 004 in Supabase

---

**Last Updated**: 2025-10-10 (Day 1)
**Current Module**: segment.ts (70% complete)
**Next Module**: parse_pdf.ts
