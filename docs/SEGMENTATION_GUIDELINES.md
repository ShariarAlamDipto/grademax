# Question Paper Segmentation Guidelines

**Version:** 2.0  
**Last Updated:** October 31, 2025  
**Based On:** Physics hardened processor achieving 90% MS linking

---

## Overview

This document provides comprehensive guidelines for implementing question-level segmentation for new exam board subjects. Follow these patterns to avoid common pitfalls and achieve high-quality results.

---

## Table of Contents

1. [Core Architecture](#core-architecture)
2. [Critical Success Patterns](#critical-success-patterns)
3. [Common Pitfalls & Solutions](#common-pitfalls--solutions)
4. [OCR & Text Extraction](#ocr--text-extraction)
5. [Question Detection (QP)](#question-detection-qp)
6. [Mark Scheme Linking (MS)](#mark-scheme-linking-ms)
7. [Validation & Quality Checks](#validation--quality-checks)
8. [Implementation Checklist](#implementation-checklist)
9. [Testing Strategy](#testing-strategy)
10. [Subject-Specific Adaptations](#subject-specific-adaptations)

---

## Core Architecture

### Single Source of Truth Pattern

**✅ DO THIS:**
```python
# Build N_QP from authoritative markers (e.g., "Total for Question N" lines)
TOTAL_PATTERN = re.compile(r"(?i)\(?\s*Total\s+for\s+[Qq]uestion\s+(\d{1,2})")
N_QP = sorted({int(m.group(1)) for txt in qp_pages for m in TOTAL_PATTERN.finditer(txt)})

# Gate ALL detections to N_QP
if qnum not in N_QP:
    continue  # Skip false positives
```

**❌ DON'T DO THIS:**
```python
# Don't trust start patterns alone - they generate phantom questions
if pattern.match(line):
    questions.append(qnum)  # No validation against authority!
```

**Why:** Start patterns match page numbers, headers, and random numbers. End markers (totals) are more reliable since they're part of the official mark allocation.

**Lesson from Physics:** We initially detected Q200, Q2000, Q230 (page numbers) until we gated everything to N_QP from totals.

---

## Critical Success Patterns

### 1. Preserve Newlines During Normalization

**✅ DO THIS:**
```python
def normalize_ocr_text(text):
    # Fix glyphs
    text = text.replace('−', '-').replace('×', '*')
    
    # Collapse spaces/tabs but PRESERVE newlines
    text = re.sub(r'[ \t]+', ' ', text)  # Spaces only
    text = re.sub(r'\n\s*\n', '\n', text)  # Remove blank lines
    
    return text
```

**❌ DON'T DO THIS:**
```python
# This BREAKS regex patterns using ^ (start of line)
text = re.sub(r'\s+', ' ', text)  # Collapses newlines!
```

**Why:** Regex patterns like `^\s*(\d+)\s+[A-Z]` require line boundaries (`^`). If you collapse all whitespace, everything becomes one giant line and `^` only matches at the start of the entire text.

**Lesson from Physics:** MS linking went from 0% to 90% after fixing this. The pattern `^\s*1\s+a` couldn't match "1 a" when the text was `"...number 1 a light;..."` on a single line.

---

### 2. Different Scrubbing Rules for QP vs MS

**✅ DO THIS:**
```python
# QP: Scrub aggressively (remove headers, footers, page numbers)
qp_pages = extract_pages(qp_path, skip_scrubbing=False)

# MS: Don't scrub answer rows!
ms_pages = extract_pages(ms_path, skip_scrubbing=True)
```

**❌ DON'T DO THIS:**
```python
# Same scrubbing for both kills MS answer rows
qp_pages = extract_pages(qp_path)
ms_pages = extract_pages(ms_path)  # Removes "1 a answer..." rows!
```

**Why:** MS tables have rows like "1 a answer text" which look like bare numbers to header/footer scrapers. QP needs aggressive scrubbing to avoid false positives from page numbers.

**Patterns to scrub (QP only):**
- `^Page \d+ of \d+$`
- `^\d{2}$` (bare page numbers)
- `^(Edexcel|BTEC|Copyright).*$`
- `^\*[A-Z0-9]+\*$` (exam codes like `*P61936A0332*`)
- `^(DO\s+)?NOT\s+WRITE.*$`
- `^Turn\s+over$`

---

### 3. Clamp Question Ends by Next Start

**✅ DO THIS:**
```python
# Find next question's start for clamping
next_qnum = qnum + 1
next_start_page = starts[next_qnum][0] if next_qnum in starts else None

# Clamp end by next start (prevents runaway spans)
if end_page is not None and next_start_page is not None:
    end_page = min(end_page, next_start_page - 1)
```

**❌ DON'T DO THIS:**
```python
# If OCR misses end marker, Q2 can run to page 31!
if qnum in ends:
    end_page = ends[qnum]
# No fallback if end missing!
```

**Why:** OCR sometimes misses end markers. Without clamping, questions can span dozens of pages. The next question's start is a hard boundary.

---

### 4. Recover Missing Starts

**✅ DO THIS:**
```python
def recover_missing_starts(n_qp, starts, ends, pages):
    for qnum in n_qp:
        if qnum in starts:
            continue
        
        if qnum not in ends:
            continue
        
        end_page = ends[qnum][0]
        
        # Search backward 2-3 pages from end
        for offset in range(3):
            search_page = end_page - offset
            if search_page < 0:
                break
            
            pattern = re.compile(rf"^\s*{qnum}\s+(?=\S)", re.MULTILINE)
            if pattern.search(pages[search_page]['text']):
                starts[qnum] = (search_page, "recovered")
                break
        
        # Fallback: use previous question's end + 1
        if qnum not in starts and qnum > 1:
            prev_end = ends[qnum - 1][0]
            starts[qnum] = (prev_end + 1, "fallback")
```

**Why:** Position-based start detection can fail for questions with unusual layouts. But if we know the end (from totals), we can work backward.

**Lesson from Physics:** 2011 papers had 13/14 questions with fallback starts, still achieved 92.9% MS linking.

---

### 5. Position-Aware Detection (Optional but Recommended)

**✅ DO THIS:**
```python
# Use relative positions (percentage of page width)
x_rel = word['x0'] / page_width

# Left margin: 4%-18% for question starts
if not (0.04 <= x_rel <= 0.18):
    continue  # Not in margin, skip

# Auto-detect MS column by clustering
x_positions = [...]  # Collect x-positions from detected rows
question_col_x = sorted(x_positions)[len(x_positions) // 2]  # Median

# Accept rows within ±2% of column
if abs(x_rel - question_col_x) < 0.02:
    # Valid MS row
```

**Why:** Absolute pixel positions vary with scan DPI. Relative positions work across different PDFs. Clustering adapts to actual layout instead of hardcoding.

**When to use:** If simple text patterns have >10% false positive rate. Position adds precision but requires pdfplumber word-level extraction.

---

## Common Pitfalls & Solutions

### Pitfall 1: False Positives from Page Numbers

**Problem:** Detecting Q52, Q34, Q200 from page footers or headers.

**Solutions:**
1. ✅ Gate to N_QP (only accept questions in authoritative set)
2. ✅ Position validation (page numbers not in left margin)
3. ✅ Header/footer scrubbing
4. ✅ Limit question number range (e.g., 1-15 for typical papers)

```python
# Combined defense
QUESTION_START = re.compile(r"^([1-9]|1[0-5])\s+(?=\S)", re.MULTILINE)
if qnum not in N_QP or qnum > 15:
    continue
if x_rel > 0.18:  # Not in left margin
    continue
```

---

### Pitfall 2: Missing Questions (Gaps)

**Problem:** N_QP shows [1, 2, 3, 5, 6] - where's Q4?

**Solutions:**
1. ✅ Check OCR quality - might be garbled text
2. ✅ Relax pattern temporarily to see what's detected
3. ✅ Use recovery algorithm if end marker exists
4. ✅ Manual inspection of that paper

```python
# Validation check
expected = list(range(1, max(N_QP) + 1))
gaps = set(expected) - set(N_QP)
if gaps:
    print(f"⚠️  Missing questions: {sorted(gaps)}")
    # Flag for manual review
```

---

### Pitfall 3: OCR Encoding Issues (CID characters)

**Problem:** Papers with `(cid:117)` or garbled characters.

**Solutions:**
1. ✅ Try different PDF extraction (PyMuPDF, PyPDF2, pdfplumber)
2. ✅ OCR normalization with fuzzy matching
3. ✅ For totally broken OCR: use image-based OCR (Tesseract, AWS Textract)
4. ✅ Document as known limitation, skip those years

```python
# Fuzzy fix for common OCR errors
text = re.sub(r'Quest[il1]on', 'Question', text, flags=re.IGNORECASE)
text = re.sub(r'totalforquestion', 'Total for Question', text, flags=re.IGNORECASE)

# Glyph mapping
replacements = {
    '−': '-', '–': '-', '—': '-',
    '×': '*', '·': '*',
    'ﬁ': 'fi', 'ﬂ': 'fl',
}
```

**Lesson from Physics:** 2013, 2015, 2019 papers had CID issues. We got 90% success on clean years, documented problematic ones.

---

### Pitfall 4: MS Linking at 0%

**Problem:** All MS detection patterns fail.

**Debug checklist:**
1. ❓ Are newlines preserved? Check with `print(text[:200])`
2. ❓ Is header page detected? Add debug logging
3. ❓ Are patterns matching? Run pattern on raw text separately
4. ❓ Is scrubbing removing MS rows? Try `skip_scrubbing=True`
5. ❓ Is position filtering too strict? Temporarily remove it

```python
# Minimal debug version
for page in ms_pages:
    text = page['text']
    matches = MS_ROW_PATTERN.finditer(text)
    print(f"Page {page['page_index']}: {len(list(matches))} matches")
    print(f"First 200 chars: {text[:200]}")
```

**Lesson from Physics:** We went from 0% → 33% → 75% → 90% by fixing:
1. Newline preservation (0% → 33%)
2. Disable MS scrubbing (33% → 75%)  
3. Position column detection (75% → 90%)

---

## OCR & Text Extraction

### Recommended Stack

```python
import pdfplumber  # Best for layout + text
import PyPDF2      # For page extraction/splitting
# Alternative: PyMuPDF (fitz) for speed
```

### Extraction Template

```python
def extract_pages_with_metadata(pdf_path, skip_scrubbing=False):
    pages_data = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            # Dimensions for relative positioning
            width = page.width
            height = page.height
            
            # Text extraction
            raw_text = page.extract_text() or ""
            
            # OCR normalization
            normalized = normalize_ocr_text(raw_text)
            
            # Conditional scrubbing
            clean_text = normalized if skip_scrubbing else scrub_headers(normalized)
            
            # Words for position-aware detection
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            
            pages_data.append({
                'page_index': i,
                'text': clean_text,
                'raw_text': raw_text,  # Keep for debugging
                'width': width,
                'height': height,
                'words': words
            })
    
    return pages_data
```

### Normalization Checklist

```python
def normalize_ocr_text(text):
    # 1. Glyph mapping
    glyphs = {
        '−': '-', '–': '-', '—': '-',  # Dashes
        '×': '*', '·': '*',             # Multiplication
        'ﬁ': 'fi', 'ﬂ': 'fl',          # Ligatures
        ''': "'", '"': '"',             # Smart quotes
    }
    for old, new in glyphs.items():
        text = text.replace(old, new)
    
    # 2. Collapsed tokens (OCR merges words)
    text = re.sub(r'totalforquestion', 'Total for Question', text, flags=re.IGNORECASE)
    text = re.sub(r'questionumber', 'Question number', text, flags=re.IGNORECASE)
    
    # 3. Fuzzy fixes (common OCR misreads)
    text = re.sub(r'Quest[il1]on', 'Question', text, flags=re.IGNORECASE)
    text = re.sub(r'[Qq]uest10n', 'Question', text, flags=re.IGNORECASE)
    
    # 4. Normalize whitespace BUT PRESERVE NEWLINES!
    text = re.sub(r'[ \t]+', ' ', text)      # Collapse spaces/tabs
    text = re.sub(r'\n\s*\n', '\n', text)   # Remove blank lines
    
    return text
```

---

## Question Detection (QP)

### Step-by-Step Algorithm

```python
def segment_qp_questions(qp_pages_data, n_qp):
    # 1. Build authority (totals)
    # Already done in n_qp
    
    # 2. Detect starts (with position validation)
    starts = detect_starts(qp_pages_data, n_qp)
    
    # 3. Detect ends (from totals)
    ends = detect_ends(qp_pages_data, n_qp)
    
    # 4. Recover missing starts
    starts.update(recover_missing_starts(n_qp, starts, ends, qp_pages_data))
    
    # 5. Build spans with clamping
    questions = []
    for qnum in n_qp:
        start_page = starts.get(qnum, [None])[0]
        end_page = ends.get(qnum, [None])[0]
        
        # Clamp by next start
        next_start = starts.get(qnum + 1, [None])[0]
        if end_page and next_start:
            end_page = min(end_page, next_start - 1)
        
        # Fallbacks
        if start_page is None:
            start_page = end_page or 0
        if end_page is None:
            end_page = len(qp_pages_data) - 1
        
        questions.append({
            'qnum': qnum,
            'qp_pages': list(range(start_page, end_page + 1)),
            'start_page': start_page,
            'end_page': end_page
        })
    
    return questions
```

### Pattern Examples by Subject

#### Physics / Further Maths (Edexcel)
```python
# Start: "1 Figure 1 shows", "2 The diagram", "3 (a) Calculate"
QP_START = re.compile(r"^\s*([1-9]|1[0-5])\s+(?=\S)", re.MULTILINE)

# End: "(Total for Question 1 = 11 marks)"
QP_END = re.compile(
    r"(?i)\(?\s*Total\s+for\s+[Qq]uestion\s+(\d{1,2})\s*[:=]\s*(\d+)\s*marks?\)?",
    re.IGNORECASE
)

# Position: x_rel in [0.04, 0.18] (left margin)
```

#### OCR / Cambridge Style (May differ)
```python
# Start: Often "Question 1" explicitly
QP_START = re.compile(r"^\s*Question\s+(\d{1,2})", re.MULTILINE | re.IGNORECASE)

# End: May use "END OF QUESTION 1"
QP_END = re.compile(r"(?i)END\s+OF\s+QUESTION\s+(\d{1,2})")
```

#### AQA Style
```python
# Start: Numbered with optional bold markers
QP_START = re.compile(r"^\s*(\d{1,2})\s+[A-Z0-9]", re.MULTILINE)

# End: Often no explicit marker, use next start
# Rely on clamping algorithm
```

---

## Mark Scheme Linking (MS)

### MS Format Analysis First

**Before coding, analyze 3-5 sample MS manually:**

1. How are questions numbered?
   - `1 (a)`, `1 a`, `Q1 (a)`, `1.`, `1)`?
2. Where do sections end?
   - "Total for question 1", "END", blank space?
3. What's the table structure?
   - Columns: Question | Answer | Marks?
   - Or narrative format?
4. How are intro pages marked?
   - "General Marking Guidance", copyright, examiner instructions?
5. Are x-positions consistent?
   - Question numbers at x≈60-80 or x≈40-100?

### Detector Template

```python
def segment_ms_questions(ms_pages_data, n_qp):
    # 1. Find header page and column structure
    header_page, question_col_x = detect_ms_structure(ms_pages_data)
    
    if header_page is None:
        # Heuristic fallback
        header_page = 2
        question_col_x = 0.08
    
    # 2. Collect rows by page (gated to N_QP)
    rows_by_page = defaultdict(set)
    
    for page_data in ms_pages_data:
        page_idx = page_data['page_index']
        
        # Skip intro pages BEFORE header
        if page_idx < header_page:
            continue
        
        text = page_data['text']
        
        # Match MS rows
        for match in MS_ROW_PATTERN.finditer(text):
            qnum = int(match.group(1))
            
            # Gate to N_QP
            if qnum not in n_qp:
                continue
            
            # Optional: position validation
            if question_col_x:
                x_rel = get_x_position(match, page_data)
                if abs(x_rel - question_col_x) > 0.02:
                    continue
            
            rows_by_page[page_idx].add(qnum)
    
    # 3. Build spans (from first row to total marker)
    ms_spans = {}
    
    for qnum in n_qp:
        # Find start page (first page with this qnum)
        start_page = None
        for page_idx in sorted(rows_by_page.keys()):
            if qnum in rows_by_page[page_idx]:
                start_page = page_idx
                break
        
        if start_page is None:
            continue
        
        # Find end page (total marker)
        end_page = start_page
        for page_idx in range(start_page, len(ms_pages_data)):
            text = ms_pages_data[page_idx]['text']
            if re.search(rf"(?i)Total\s+for\s+[Qq]uestion\s+{qnum}\b", text):
                end_page = page_idx
                break
        
        ms_spans[qnum] = {
            'pages': list(range(start_page, end_page + 1))
        }
    
    return ms_spans
```

### MS Pattern Examples

#### Physics / Further Maths (Table format)
```python
# Rows: "1 a answer...", "2 (b) answer..."
MS_ROW = re.compile(
    r"^\s*(\d{1,2})\s+(\([a-h]\)|\([ivx]+\)|[a-h]\b|[ivx]+\b)",
    re.MULTILINE | re.IGNORECASE
)

# Section end: "Total for Question 1 = 6 marks"
MS_END = re.compile(r"(?i)Total\s+for\s+[Qq]uestion\s+(\d{1,2})")

# Header: "Question | Answer | Notes | Marks"
MS_HEADER = re.compile(r"Question.*Answer.*Marks", re.IGNORECASE | re.DOTALL)
```

#### Narrative Format (Some Cambridge papers)
```python
# Questions in paragraphs: "1. The answer is X because..."
MS_ROW = re.compile(r"^\s*(\d{1,2})[.)]", re.MULTILINE)

# Section end: Double newline or next question
MS_END = None  # Use next question start as boundary
```

---

## Validation & Quality Checks

### Consistency Checks

```python
def validate_question_set(questions, n_qp):
    issues = []
    
    # 1. Numbering check (no gaps)
    found_qnums = sorted([q['qnum'] for q in questions])
    expected = list(range(1, max(n_qp) + 1))
    gaps = set(expected) - set(found_qnums)
    extra = set(found_qnums) - set(expected)
    
    if gaps:
        issues.append(f"❌ Missing questions: {sorted(gaps)}")
    if extra:
        issues.append(f"❌ Phantom questions: {sorted(extra)}")
    
    # 2. Overlap check (non-boundary)
    for i in range(len(questions) - 1):
        curr_end = questions[i]['end_page']
        next_start = questions[i + 1]['start_page']
        if curr_end > next_start:
            issues.append(
                f"⚠️  Q{questions[i]['qnum']} overlaps Q{questions[i+1]['qnum']}"
            )
    
    # 3. Coverage check
    for q in questions:
        if not q.get('qp_pages'):
            issues.append(f"❌ Q{q['qnum']} has no QP pages")
        if not q.get('ms_pages'):
            issues.append(f"⚠️  Q{q['qnum']} has no MS pages")
    
    # 4. Sanity check (page counts)
    for q in questions:
        qp_count = len(q.get('qp_pages', []))
        if qp_count > 10:
            issues.append(f"⚠️  Q{q['qnum']} spans {qp_count} pages (suspicious)")
        if qp_count == 0:
            issues.append(f"❌ Q{q['qnum']} has 0 pages")
    
    # 5. Marks parity (if available)
    marks_mismatches = 0
    for q in questions:
        if 'marks_qp' in q and 'marks_ms' in q:
            if q['marks_qp'] != q['marks_ms']:
                marks_mismatches += 1
    
    if marks_mismatches > 0:
        issues.append(f"⚠️  {marks_mismatches} questions have QP/MS marks mismatch")
    
    return issues
```

### Success Metrics

**Target benchmarks based on Physics experience:**

- ✅ **Excellent:** 90-100% MS linking, no phantom questions, all gaps explained
- ✅ **Good:** 80-89% MS linking, <5% phantom questions
- ⚠️  **Acceptable:** 70-79% MS linking, documented known issues
- ❌ **Needs work:** <70% MS linking or >10% phantom questions

```python
def calculate_metrics(questions):
    total = len(questions)
    with_ms = sum(1 for q in questions if q.get('ms_pages'))
    
    avg_qp_pages = sum(len(q['qp_pages']) for q in questions) / total
    avg_ms_pages = sum(len(q.get('ms_pages', [])) for q in questions) / total
    
    return {
        'total_questions': total,
        'ms_linking_pct': (with_ms / total * 100) if total > 0 else 0,
        'avg_qp_pages': avg_qp_pages,
        'avg_ms_pages': avg_ms_pages
    }
```

---

## Implementation Checklist

### Phase 1: Analysis (Before Coding)

- [ ] Collect 5-10 sample papers (different years)
- [ ] Manually identify question boundaries in QP
- [ ] Document question start patterns (format, position, markers)
- [ ] Document question end patterns (totals, markers, page breaks)
- [ ] Analyze MS structure (table vs narrative, numbering format)
- [ ] Note intro pages and how to skip them
- [ ] Check for OCR quality issues (CID characters, garbled text)
- [ ] Document typical question count per paper
- [ ] Identify special cases (multi-page questions, diagrams, etc.)

### Phase 2: Pattern Development

- [ ] Write regex for question starts (test on 3 papers)
- [ ] Write regex for question ends/totals (test on 3 papers)
- [ ] Write regex for MS rows (test on 3 papers)
- [ ] Write regex for MS section ends
- [ ] Implement OCR normalization (glyph mapping, fuzzy fixes)
- [ ] Implement header/footer scrubbing (QP only)
- [ ] Test patterns on raw extracted text before full pipeline

### Phase 3: Core Algorithm

- [ ] Implement `extract_pages_with_metadata()` with dual scrubbing modes
- [ ] Implement `build_authoritative_n_qp()` from totals
- [ ] Implement `detect_qp_starts()` with position validation
- [ ] Implement `detect_qp_ends()` from totals
- [ ] Implement `recover_missing_starts()` with backward search
- [ ] Implement `segment_qp_questions()` with clamping
- [ ] Implement `detect_ms_structure()` for header/column finding
- [ ] Implement `segment_ms_questions()` with gating to N_QP
- [ ] Link MS spans to questions

### Phase 4: Validation

- [ ] Implement `validate_question_set()` with all checks
- [ ] Add evidence capture (start/end text snippets)
- [ ] Add marks extraction and parity checking
- [ ] Implement consistency checks (numbering, gaps, overlaps)
- [ ] Add detailed logging for debugging

### Phase 5: Testing

- [ ] Test on 1 paper (recent year, clean OCR)
- [ ] Test on 1 paper (old year, may have issues)
- [ ] Test on 1 paper (mid-range year)
- [ ] Run validation checks on all 3
- [ ] Iterate based on validation issues
- [ ] Test on 10 papers across all years
- [ ] Calculate aggregate metrics
- [ ] Document known limitations

### Phase 6: Production

- [ ] Clean up debug logging
- [ ] Add progress indicators
- [ ] Implement error handling for bad PDFs
- [ ] Add UTF-8 encoding fix for Windows
- [ ] Create processing script for all papers
- [ ] Create monitoring script for database stats
- [ ] Document subject-specific quirks
- [ ] Update this guideline with lessons learned

---

## Testing Strategy

### Test Set Selection

**Minimum viable test set:**
- 3 papers: one old (2011-2014), one mid (2015-2019), one recent (2020+)
- 2 paper types: Paper 1 and Paper 2 (if different formats)
- 1 edge case: shortest paper, longest paper, or known problematic year

**Full validation test set:**
- 10-12 papers evenly distributed across years
- All paper types (P1, P2, P3 if applicable)
- Known edge cases documented

### Debug Script Template

```python
"""
Quick debug script for pattern testing
Run this BEFORE full pipeline to validate patterns
"""

import pdfplumber
import re

# Your patterns
QUESTION_START = re.compile(r"...")
QUESTION_END = re.compile(r"...")

test_papers = [
    ("2024", "May-Jun", 1, "path/to/qp.pdf"),
    ("2018", "Jan", 1, "path/to/qp.pdf"),
    ("2011", "May-Jun", 1, "path/to/qp.pdf"),
]

for year, season, paper, path in test_papers:
    print(f"\n{'='*60}")
    print(f"Testing: {year} {season} P{paper}")
    print(f"{'='*60}")
    
    with pdfplumber.open(path) as pdf:
        # Test on first 5 pages
        for i in range(min(5, len(pdf.pages))):
            page = pdf.pages[i]
            text = page.extract_text() or ""
            
            # Normalize
            text = normalize_ocr_text(text)
            
            # Test patterns
            starts = list(QUESTION_START.finditer(text))
            ends = list(QUESTION_END.finditer(text))
            
            print(f"\nPage {i+1}:")
            print(f"  Starts: {[m.group(0) for m in starts]}")
            print(f"  Ends: {[m.group(0) for m in ends]}")
            
            # Show first 200 chars
            print(f"  Text preview: {text[:200]}")
```

### Validation Report Template

```json
{
  "subject": "Physics",
  "board": "Pearson Edexcel",
  "test_date": "2025-10-31",
  "papers_tested": 12,
  "years_tested": "2011-2024",
  
  "results": {
    "papers_passed": 11,
    "papers_with_warnings": 1,
    "papers_failed": 0,
    "pass_rate": 91.7,
    
    "avg_questions_per_paper": 10.8,
    "avg_ms_linking": 90.0,
    "avg_qp_pages_per_question": 3.2,
    "avg_ms_pages_per_question": 1.4
  },
  
  "issues": [
    {
      "paper": "2018 Jan P1",
      "issue": "Q3, Q4, Q12 missing MS",
      "severity": "warning",
      "root_cause": "MS rows not detected (position filtering too strict)"
    }
  ],
  
  "known_limitations": [
    "2013, 2015, 2019 papers have OCR encoding issues (CID characters)",
    "Some papers missing MS in source data (not processor fault)"
  ],
  
  "recommendation": "Ready for production. 90% MS linking exceeds 80% target."
}
```

---

## Subject-Specific Adaptations

### When to Customize

**Use standard patterns if:**
- Exam board is Edexcel/Pearson (same format as Physics/FPM)
- Papers have clear "Total for Question N" markers
- MS is in table format with subparts
- Questions numbered sequentially 1-15

**Customize patterns if:**
- Different exam board (Cambridge, AQA, OCR)
- No explicit totals (use next start as boundary)
- Narrative MS format (not table)
- Questions use letters (A, B, C) or Roman numerals
- Multi-part papers (Section A, Section B with separate numbering)

### Adaptation Checklist

1. **Analyze format differences:**
   - How are questions numbered?
   - What marks the end?
   - How is MS structured?

2. **Modify patterns:**
   ```python
   # Example: Cambridge uses "END OF QUESTION"
   QP_END = re.compile(r"(?i)END\s+OF\s+QUESTION\s+(\d{1,2})")
   
   # Example: AQA uses "QUESTION 1" explicitly
   QP_START = re.compile(r"^\s*QUESTION\s+(\d{1,2})", re.MULTILINE)
   ```

3. **Adjust position ranges:**
   ```python
   # Some boards have wider margins
   x_rel_range = (0.06, 0.22)  # Instead of (0.04, 0.18)
   ```

4. **Modify MS detection:**
   ```python
   # Narrative format: just question number at start
   MS_ROW = re.compile(r"^\s*(\d{1,2})[.)]?\s", re.MULTILINE)
   ```

5. **Test thoroughly:**
   - Run same validation suite
   - Achieve >80% MS linking target
   - Document any board-specific quirks

### Example: Cambridge Adaptation

```python
# Cambridge often uses:
# - "Question 1" explicitly
# - "END OF QUESTION" markers
# - Narrative MS (not table)

QP_START = re.compile(
    r"^\s*Question\s+(\d{1,2})\b",
    re.MULTILINE | re.IGNORECASE
)

QP_END = re.compile(
    r"(?i)(?:END\s+OF|Total\s+for)\s+QUESTION\s+(\d{1,2})"
)

MS_ROW = re.compile(
    r"^\s*(\d{1,2})[.)\s]+",  # More permissive
    re.MULTILINE
)

# May need different column detection
# Cambridge MS often has question number further left
question_col_x = 0.05  # Instead of 0.08
```

---

## Success Stories & Lessons

### Physics (Hardened v2.0)

**Achievement:** 90% MS linking (45/50 test questions)

**Key factors:**
1. ✅ Preserving newlines in normalization (+60% improvement)
2. ✅ Skipping MS scrubbing (+15% improvement)
3. ✅ Position-aware column detection (+10% improvement)
4. ✅ Gating to N_QP (eliminated all phantom questions)
5. ✅ Recovery algorithm (caught 13 missing starts in 2011 paper)

**Final results by year:**
- 2024: 100% (12/12)
- 2020: 91.7% (11/12)
- 2011: 92.9% (13/14)
- 2018: 75.0% (9/12)

**Known limitations:**
- 2013, 2015, 2019: OCR encoding issues (documented, skipped)
- Some MS rows missed due to position filtering edge cases

---

### Further Pure Maths (v1.0)

**Achievement:** 98.2% classification (609/620 pages)

**Key factors:**
1. ✅ Similar structure to Physics (same board)
2. ✅ Consistent "Total for question" markers
3. ✅ Table-based MS format
4. ✅ Clean OCR across all years

**Lessons:**
- When format is consistent, standard patterns work well
- Classification is separate concern from segmentation
- 98% is excellent but 100% is elusive (always a few edge cases)

---

## Common Questions

### Q: What MS linking percentage is acceptable?

**A:** Target thresholds:
- **90-100%:** Excellent, ready for production
- **80-89%:** Good, acceptable with documented issues
- **70-79%:** Needs improvement, investigate patterns
- **<70%:** Not ready, major issues to fix

### Q: Should I use ML/AI for detection?

**A:** Start with regex/rules first:
- ✅ Faster to develop
- ✅ More explainable/debuggable
- ✅ No training data needed
- ✅ Works well for structured documents

Consider ML if:
- Regex approach <70% after optimization
- Highly variable layouts
- No consistent patterns
- Multi-language papers

### Q: How to handle multi-part papers (Section A, B)?

**A:** Two approaches:

**Approach 1: Renumber (recommended)**
```python
# Section A: Q1-Q10, Section B: Q11-Q15
# Store as: Q1-Q15 with metadata
questions[i]['section'] = 'A' or 'B'
```

**Approach 2: Compound keys**
```python
# Store as: A1, A2, ..., A10, B1, B2, ..., B5
questions[i]['qnum'] = 'A1'
questions[i]['section'] = 'A'
questions[i]['section_qnum'] = 1
```

### Q: What if there are no "Total" markers?

**A:** Fallback hierarchy:
1. Use next question start as boundary (with -1 page)
2. Look for "END OF QUESTION" or similar
3. Use consistent page count (if all questions are ~3 pages)
4. Manual boundaries as last resort

```python
# Example: No totals, use next start
if qnum + 1 in starts:
    end_page = starts[qnum + 1] - 1
else:
    end_page = len(pages) - 1
```

### Q: How to handle diagrams/figures spanning pages?

**A:** Include them in question span:
- Diagrams are part of question context
- Don't try to split them out
- Let question span cover all related pages
- Classification models can handle multi-page PDFs

### Q: Should I extract sub-questions separately?

**A:** **No, keep questions as whole units:**
- Classification works at question level (Q1, Q2, ...)
- Subparts (a, b, c) share context
- Splitting creates complexity
- Worksheet generation combines them anyway

Exception: If explicitly required by business logic.

---

## Maintenance & Updates

### When to Update Patterns

- ✅ New exam year with format changes
- ✅ MS linking drops below 80%
- ✅ Phantom questions appear
- ✅ OCR quality changes (different scan source)

### Version Control

Document changes:
```json
{
  "version": "2.1",
  "date": "2025-11-15",
  "changes": [
    "Added support for 2025 papers with new format",
    "Fixed MS column detection for wider margins",
    "Improved OCR normalization for French characters"
  ],
  "validation": {
    "papers_tested": 15,
    "ms_linking": 92.5,
    "recommendation": "Deploy to production"
  }
}
```

### Testing After Updates

- [ ] Run full validation suite on updated code
- [ ] Test on 3 papers from previous year (regression test)
- [ ] Test on 3 papers from new year (new format test)
- [ ] Compare metrics with previous version
- [ ] Document any regressions

---

## Quick Reference Card

### 🎯 Golden Rules

1. **Single source of truth:** Build N_QP from totals, gate everything to it
2. **Preserve newlines:** Never use `\s+` for all whitespace
3. **Different scrubbing:** QP aggressive, MS minimal
4. **Clamp ends:** Use next start as hard boundary
5. **Recover missing:** Backward search from end marker
6. **Position awareness:** Use relative coords, not absolute pixels
7. **Validate early:** Run checks on 3 papers before processing all
8. **Document issues:** Known limitations are okay, surprises are not

### ⚠️ Red Flags

- 🚨 MS linking <70%: Major pattern issues
- 🚨 Phantom questions detected: Need N_QP gating
- 🚨 Questions spanning >10 pages: Missing end detection
- 🚨 Gaps in question numbers: OCR issues or wrong patterns
- 🚨 All questions have same page count: Not detecting boundaries

### ✅ Success Checklist

- [ ] 80%+ MS linking achieved
- [ ] No phantom questions (all in N_QP)
- [ ] No gaps in numbering (or explained)
- [ ] Sensible page counts (1-6 pages per question typically)
- [ ] Validation passes on 10+ papers
- [ ] Known limitations documented
- [ ] Code reviewed and tested

---

## Conclusion

These guidelines distill hard-won lessons from implementing Physics segmentation (achieving 90% MS linking) and Further Maths (98.2% classification). The key insight: **start with patterns, validate early, iterate based on metrics**.

**Remember:**
- Perfect is the enemy of good (90% is excellent)
- Document known limitations (OCR issues, missing source data)
- Test early and often (don't wait until processing all papers)
- Position-aware detection adds 10-15% accuracy
- Preserving newlines is non-negotiable for regex patterns

Follow this guide for new subjects, adapt patterns as needed, and maintain the same quality standards. Good luck! 🚀

---

**Version History:**
- v2.0 (2025-10-31): Complete rewrite based on Physics hardened processor
- v1.0 (2025-10-15): Initial version from FPM experience

**Authors:** AI Agent Team, Based on Physics & FPM implementation experience
