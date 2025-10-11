# MS Parsing & Linking - Detailed Specification

**Module**: `ingest/ms_parse_link.ts`  
**Estimated Time**: 3 hours  
**Dependencies**: `parse_pdf_v2.ts`, `segment.ts`, `types/ingestion.ts`

---

## 🎯 Objectives

1. **Parse markscheme PDFs** to extract marking points
2. **Link MS points to question parts** using composite key matching
3. **Calculate confidence scores** for each link
4. **Extract MS cues** (formulas, keywords) for topic detection
5. **Store results** in `MSLink` format for persistence

---

## 📋 Input/Output

### Input
```typescript
interface MSParseInput {
  questionPdfPath: string      // Path to question paper PDF
  msPath: string                // Path to markscheme PDF
  segmentedQuestions: SegmentedQuestion[]  // From segment.ts
}
```

### Output
```typescript
interface MSParseResult {
  links: MSLink[]               // Array of MS links for all parts
  stats: {
    totalParts: number
    linkedParts: number
    unlinkedParts: number
    avgConfidence: number
    warningCount: number
  }
  warnings: string[]            // Issues during parsing
}

interface MSLink {
  questionNumber: string        // "2"
  partCode: string             // "a(ii)"
  marks: number                // From question paper
  msPoints: string[]           // ["M1: Area = πr²", "A1: 78.5 cm²"]
  msSnippet: string            // Raw text from MS
  confidence: number           // [0, 1]
  matchMethod: 'exact' | 'fuzzy' | 'marks-only' | 'fallback'
}
```

---

## 🔬 MS Structure Analysis

### Common MS Formats

#### Format A: Table with columns
```
Question | Answer | Mark | Additional Guidance
---------|--------|------|--------------------
1(a)     | 5.2 N  | B1   | Accept 5.1-5.3
1(b)(i)  | kinetic| M1   | Must mention energy
```

#### Format B: Sequential list
```
1  (a) 5.2 (N) ✓                                    (1)
   (b) (i) kinetic energy ✓                         (1)
       (ii) M1: Uses E = ½mv²
            A1: 125 J                                (2)
```

#### Format C: Compact format
```
1  (a) 5.2 N [1]
   (b) (i) kinetic energy [1]
       (ii) E = ½mv² [M1]; 125 J [A1] [2]
```

### Mark Codes
- **B1**: Basic mark (single correct point)
- **M1, M2...**: Method mark
- **A1, A2...**: Accuracy mark
- **C1, C2...**: Communication mark
- **✓**: Simple correct answer

---

## 🧩 Algorithm Design

### Phase 1: Parse MS Structure

```typescript
function parseMSPDF(msPath: string): Promise<MSRawData> {
  // 1. Extract text items with positions (using parse_pdf_v2)
  // 2. Detect MS format (table vs list vs compact)
  // 3. Find question/part markers
  // 4. Extract marking points per part
  // 5. Aggregate by (questionNumber, partCode)
  
  return {
    format: 'table' | 'list' | 'compact',
    entries: MSEntry[]
  }
}

interface MSEntry {
  questionNumber: string    // "2"
  partCode: string         // "a(ii)"
  rawText: string          // Full text for this part
  markPoints: MarkPoint[]  // Parsed individual points
  totalMarks: number       // Sum of all marks
  lineNumbers: number[]    // Text item indices
}

interface MarkPoint {
  code: string            // "M1", "A1", "B1", "✓"
  marks: number           // Usually 1
  text: string            // "Area = πr²"
}
```

### Phase 2: Link to Question Parts

```typescript
function linkMSToQuestions(
  segmented: SegmentedQuestion[],
  msData: MSRawData
): MSLink[] {
  
  const links: MSLink[] = []
  
  for (const question of segmented) {
    for (const part of question.parts) {
      // Build composite key
      const key = `${question.questionNumber}${part.partCode}`
      
      // Find matching MS entry
      const msEntry = findMSEntry(msData, key)
      
      if (msEntry) {
        const link = createLink(question, part, msEntry)
        links.push(link)
      } else {
        // Log warning
        links.push(createEmptyLink(question, part))
      }
    }
  }
  
  return links
}
```

### Phase 3: Calculate Confidence

```typescript
function calculateConfidence(
  part: SegmentedPart,
  msEntry: MSEntry
): number {
  
  let score = 0.0
  
  // Factor 1: Key match (40%)
  if (exactKeyMatch(part, msEntry)) {
    score += 0.4
  } else if (fuzzyKeyMatch(part, msEntry)) {
    score += 0.2
  }
  
  // Factor 2: Marks equality (30%)
  if (part.marks === msEntry.totalMarks) {
    score += 0.3
  } else if (Math.abs(part.marks - msEntry.totalMarks) <= 1) {
    score += 0.15
  }
  
  // Factor 3: Cue overlap (30%)
  const cueOverlap = calculateCueOverlap(
    part.contextText,
    msEntry.rawText
  )
  score += cueOverlap * 0.3
  
  return Math.min(1.0, score)
}

function calculateCueOverlap(
  questionText: string,
  msText: string
): number {
  // Extract cues: formulas, units, key terms
  const qCues = extractCues(questionText)
  const msCues = extractCues(msText)
  
  // Jaccard similarity
  const intersection = qCues.filter(c => msCues.includes(c))
  const union = [...new Set([...qCues, ...msCues])]
  
  return union.length > 0 ? intersection.length / union.length : 0
}

function extractCues(text: string): string[] {
  const cues: string[] = []
  
  // 1. Extract formulas (contains =, ×, ÷, √, π, etc.)
  const formulaPattern = /[a-zA-Z]\s*=\s*[^.]+/g
  const formulas = text.match(formulaPattern) || []
  cues.push(...formulas.map(f => f.trim()))
  
  // 2. Extract units (m, kg, N, J, W, etc.)
  const unitPattern = /\b\d+(\.\d+)?\s*([a-zA-Z]{1,3})\b/g
  const units = [...text.matchAll(unitPattern)].map(m => m[2])
  cues.push(...units)
  
  // 3. Extract key physics terms (energy, force, velocity, etc.)
  const keyTerms = [
    'energy', 'kinetic', 'potential', 'force', 'velocity',
    'acceleration', 'mass', 'pressure', 'volume', 'temperature'
  ]
  for (const term of keyTerms) {
    if (text.toLowerCase().includes(term)) {
      cues.push(term)
    }
  }
  
  return [...new Set(cues)]
}
```

---

## 🧪 Test Cases

### Test Case 1: Perfect Match
```typescript
Input:
  Question: "2(a)(ii) Calculate the area. π = 3.14"
  MS Entry: "2(a)(ii) M1: Area = πr² ; A1: 78.5 cm² [2]"
  
Expected:
  confidence: 1.0
  matchMethod: 'exact'
  marks: 2
  msPoints: ["M1: Area = πr²", "A1: 78.5 cm²"]
```

### Test Case 2: Marks Mismatch
```typescript
Input:
  Question: "2(b) State the formula [1]"
  MS Entry: "2(b) F = ma [2]"  // Wrong marks!
  
Expected:
  confidence: 0.5 (key match + cue overlap, but marks wrong)
  matchMethod: 'exact'
  marks: 1 (from question)
  warning: "Marks mismatch: Q says 1, MS says 2"
```

### Test Case 3: Missing MS Entry
```typescript
Input:
  Question: "5(c)(iii) Explain the result [2]"
  MS Entry: null (not found in MS)
  
Expected:
  confidence: 0.0
  matchMethod: 'fallback'
  marks: 2 (from question)
  msPoints: []
  warning: "No MS entry found for 5(c)(iii)"
```

---

## 📊 MS Format Detection

### Strategy
1. Sample first 2 pages of MS
2. Count occurrences of:
   - Table headers (`Question`, `Answer`, `Mark`)
   - Part markers with indentation (`(a)`, `(b)(i)`)
   - Mark codes (`M1`, `A1`, `B1`, `✓`)
3. Classify based on pattern density

```typescript
function detectMSFormat(textItems: TextItem[]): MSFormat {
  const sample = textItems.slice(0, 200) // First 200 items
  
  const hasTableHeaders = sample.some(item => 
    /Question.*Answer.*Mark/i.test(item.text)
  )
  
  const hasIndentedParts = sample.filter(item =>
    /^\s{2,}\([a-z]\)/.test(item.text)
  ).length > 5
  
  const markCodeDensity = sample.filter(item =>
    /\b[MABC]\d\b/.test(item.text)
  ).length / sample.length
  
  if (hasTableHeaders) return 'table'
  if (hasIndentedParts && markCodeDensity > 0.1) return 'list'
  return 'compact'
}
```

---

## 🔧 Implementation Plan

### Step 1: Parse MS PDF (1h)
- [ ] Use `parse_pdf_v2` to extract text items
- [ ] Implement `detectMSFormat()`
- [ ] Implement format-specific parsers:
  - [ ] `parseTableFormat()`
  - [ ] `parseListFormat()`
  - [ ] `parseCompactFormat()`
- [ ] Aggregate into `MSEntry[]`

### Step 2: Composite Key Matching (0.5h)
- [ ] Implement `findMSEntry()` with exact match
- [ ] Implement fuzzy matching for typos
- [ ] Handle edge cases (missing parts, extra parts)

### Step 3: Confidence Calculation (0.5h)
- [ ] Implement `calculateConfidence()`
- [ ] Implement `extractCues()` for formulas/units/terms
- [ ] Implement `calculateCueOverlap()` with Jaccard

### Step 4: Link Creation (0.5h)
- [ ] Implement `createLink()`
- [ ] Format `msPoints[]` array
- [ ] Generate `msSnippet` (truncate if >200 chars)
- [ ] Assign `matchMethod`

### Step 5: Testing (0.5h)
- [ ] Create `test_ms_parsing.ts`
- [ ] Test with real MS PDF (4PH1_1P_MS.pdf)
- [ ] Validate confidence scores
- [ ] Check for unlinked parts

---

## 📁 File Structure

```
ingest/
├── ms_parse_link.ts          # Main module (NEW)
├── test_ms_parsing.ts         # Test script (NEW)
├── segment.ts                 # Existing (dependency)
├── parse_pdf_v2.ts            # Existing (dependency)
└── debug_ms.ts                # Debug helper (NEW)
```

---

## 🚨 Edge Cases

### 1. Multi-part answers
```
2(a)(i) and (ii) Both require same formula [2]
```
**Solution**: Link to both parts with 50% confidence

### 2. Alternative answers
```
1(a) Accept: north / N / upward [1]
```
**Solution**: Parse all alternatives into `msPoints[]`

### 3. Range answers
```
1(b) 5.1-5.3 (N) ✓ [1]
```
**Solution**: Extract range as single point

### 4. Combined marks
```
2(c) M1 for method, A1 for answer (2)
```
**Solution**: Parse into 2 separate `MarkPoint` objects

### 5. Page breaks mid-answer
```
Page 3: 2(d)(i) M1: Starts calculation...
Page 4: ... A1: Final answer 45 J
```
**Solution**: Track line numbers, merge across pages

---

## 🎓 Success Criteria

- [ ] **Parse accuracy**: >95% of MS entries extracted correctly
- [ ] **Link accuracy**: >90% of question parts linked to MS
- [ ] **Confidence**: Average confidence >0.8 for exact matches
- [ ] **Performance**: Parse entire MS in <5 seconds
- [ ] **Robustness**: Handle all 3 MS formats
- [ ] **Cue extraction**: Extract >80% of formulas correctly

---

## 📝 Example Output

```typescript
{
  links: [
    {
      questionNumber: "2",
      partCode: "a(ii)",
      marks: 2,
      msPoints: [
        "M1: Area = πr²",
        "A1: 78.5 cm²"
      ],
      msSnippet: "2(a)(ii) M1: Area = πr² ; A1: 78.5 cm² Accept 78-79",
      confidence: 0.95,
      matchMethod: 'exact'
    },
    // ... more links
  ],
  stats: {
    totalParts: 61,
    linkedParts: 58,
    unlinkedParts: 3,
    avgConfidence: 0.87,
    warningCount: 5
  },
  warnings: [
    "Marks mismatch: Q2(d) expects 2, MS shows 3",
    "No MS entry found for Q5(c)(iii)",
    // ... more warnings
  ]
}
```

---

## 🔄 Next Steps After Completion

1. **Integrate with persistence** (`persist.ts`)
2. **Use MS cues for tagging** (`tagging.ts`)
3. **Generate MS verification report** (API route)
4. **Build teacher PDF with answers** (`pdf_builder.ts`)

---

**Status**: 📝 Spec complete, ready to implement  
**Time to build**: ~3 hours  
**Priority**: HIGH (Critical path for full system)
