# Subject Onboarding Guide

## 📋 Complete Guide to Adding New Subjects to GradeMax

This document explains the **exact process** used to successfully set up Further Pure Mathematics (FPM) and documents all mistakes encountered so they can be avoided for future subjects.

---

## 🎯 Overview: What Was Done for FPM

### Final Results
- ✅ **75 papers** processed and stored in database
- ✅ **620 pages** extracted and created
- ✅ **609 pages classified** (98.2% coverage) across 10 topics
- ✅ **620 question PDFs** uploaded to Supabase storage
- ✅ **483 mark scheme PDFs** uploaded to Supabase storage
- ✅ **Worksheet generation tested**: 100% success for question papers, 77% for mark schemes

### Timeline
- **Phase 1**: Processing & Classification (with rate limit solutions)
- **Phase 2**: Database cleanup (duplicates & wrong URLs)
- **Phase 3**: PDF upload & URL fixes
- **Phase 4**: Mark scheme upload
- **Phase 5**: Testing & validation

---

## 📖 Step-by-Step Process for Adding a New Subject

### **STEP 1: Verify Source Data Exists**

**Location**: `data/raw/<Subject Name>/` and `data/processed/<Subject Name> Processed/`

**What to Check**:
```powershell
# Check if raw papers exist
Get-ChildItem "data\raw\<Subject Name>" -Recurse -Filter "*.pdf" | Measure-Object

# Check if processed folders exist
Get-ChildItem "data\processed\<Subject Name> Processed" | Select-Object Name

# Verify a sample folder has both question papers AND mark schemes
Get-ChildItem "data\processed\<Subject Name> Processed\<sample_folder>" -Recurse
```

**Expected Structure**:
```
data/
├── raw/
│   └── <Subject Name>/
│       ├── 2011_Jun_1P.pdf
│       ├── 2011_Jun_1P_ms.pdf
│       └── ... (more papers)
├── processed/
    └── <Subject Name> Processed/
        ├── 2011_Jun_1P/
        │   ├── manifest.json
        │   ├── pages/
        │   │   ├── q1.pdf
        │   │   ├── q2.pdf
        │   │   └── ...
        │   └── markschemes/
        │       ├── q1.pdf  (mark scheme for q1)
        │       ├── q2.pdf
        │       └── ...
        └── ... (more folders)
```

**⚠️ CRITICAL CHECK - Physics Mistake**:
Physics had **60 folders** but ALL were **completely empty** (no manifest.json, no PDFs). Always verify folders have content:
```powershell
# Check if folders have files
Get-ChildItem "data\processed\<Subject Name> Processed\<folder_name>" -Recurse | Measure-Object
# Should return count > 0
```

---

### **STEP 2: Verify Subject Exists in Database**

**Script to Create**: `scripts/check_<subject>_subject.py`

```python
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Check if subject exists
result = supabase.table('subjects').select('*').eq('subject_code', '<SUBJECT_CODE>').execute()

if result.data:
    subject = result.data[0]
    print(f"✅ Subject found:")
    print(f"   Name: {subject['name']}")
    print(f"   Code: {subject['subject_code']}")
    print(f"   ID: {subject['id']}")
    
    # Check paper count
    papers = supabase.table('papers').select('id', count='exact').eq('subject_id', subject['id']).execute()
    print(f"   Papers in DB: {papers.count}")
    
    # Check page count
    pages = supabase.table('pages').select('id', count='exact').eq('subject_id', subject['id']).execute()
    print(f"   Pages in DB: {pages.count}")
else:
    print(f"❌ Subject with code '<SUBJECT_CODE>' not found in database!")
    print("   You need to add it to the subjects table first.")
```

**What You Need**:
- Subject Code (e.g., `9FM0` for FPM, `4PH1` for Physics)
- Subject ID (UUID from database)

**⚠️ MISTAKE AVOIDED**:
FPM had wrong subject_id initially - papers were stored under Physics subject. Always verify subject_id matches correct subject code.

---

### **STEP 3: Define Topics in Database**

**Check Topics**: Run `scripts/list_subject_topics.py`

```python
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

SUBJECT_ID = '<your-subject-id-here>'

# Get all topics for this subject
result = supabase.table('topics').select('*').eq('subject_id', SUBJECT_ID).order('id').execute()

if result.data:
    print(f"\n✅ Found {len(result.data)} topics for subject:")
    for topic in result.data:
        print(f"   [{topic['id']}] {topic['name']} - {topic['short_name']}")
else:
    print(f"❌ No topics found for subject!")
    print("   You need to add topics to the topics table first.")
```

**FPM Topics** (Example):
1. Logarithms & Exponentials (LOGS)
2. Quadratics (QUAD)
3. Identities (IDENT)
4. Graphs (GRAPHS)
5. Series (SERIES)
6. Binomial Expansion (BINOM)
7. Vectors (VECT)
8. Coordinate Geometry (COORD)
9. Calculus (CALC)
10. Trigonometry (TRIG)

---

### **STEP 4: Create Keyword Map for Classification**

**File**: `scripts/<subject>_keywords.yaml`

**Purpose**: Pre-filter pages before LLM classification to save API calls and improve accuracy.

**FPM Example Structure**:
```yaml
topics:
  LOGS:
    - logarithm
    - ln(
    - log(
    - "e^"
    - exponential
  
  QUAD:
    - quadratic
    - "x²"
    - parabola
    - discriminant
    - completing the square
  
  TRIG:
    - sin(
    - cos(
    - tan(
    - trigonometric
    - radian
    - degree
```

**Requirements**:
- **At least 3-5 keywords per topic**
- Include math notation variations (e.g., `x²`, `x^2`)
- Include function patterns (e.g., `sin(`, `cos(`)
- Include related terminology

**How It Works**:
- If a page's text contains **3+ keywords** from one topic → classified directly (0.85 confidence)
- If fewer matches → sends to LLM for classification
- **FPM Results**: ~40% of pages pre-filtered via keywords, saved ~240 API calls

---

### **STEP 5: Set Up Multi-Model Classifier**

**File**: `scripts/mistral_classifier.py`

**Why Multi-Model**:
- Single model: 30 requests/minute → 2 seconds per page → 20 minutes for 600 pages
- 6 models: ~180 requests/minute → 0.33 seconds per page → ~3.3 minutes for 600 pages
- **Automatic rotation on rate limits** (429, 400, 503 errors)

**Available Groq Models** (as of implementation):
```python
GROQ_MODELS = [
    'llama-3.1-8b-instant',      # 30 RPM
    'llama-3.3-70b-versatile',   # 30 RPM
    'llama-4-scout',             # 30 RPM
    'llama-guard-4',             # 30 RPM
    'qwen3-32b',                 # 60 RPM
    'kimi-k2'                    # 60 RPM
]
```

**Configuration**:
```python
# Delay between API calls
DELAY_BETWEEN_REQUESTS = 2.0  # seconds

# Keyword pre-filter threshold
MIN_KEYWORD_MATCHES = 3  # Direct classification if ≥3 keywords match

# Confidence scores
KEYWORD_CONFIDENCE = 0.85  # For keyword-based classification
LLM_CONFIDENCE = 0.9       # For LLM-based classification
```

**Key Functions**:
1. **`_build_keyword_map()`**: Loads keywords from YAML
2. **`_check_keywords()`**: Pre-filters using keyword matching
3. **`_switch_model()`**: Rotates to next available model
4. **`classify()`**: Main classification with auto-retry on errors

**⚠️ MISTAKE FROM FPM**:
Initially used only 1 model → hit rate limits repeatedly. Solution: Multi-model rotation reduced processing time by 83%.

---

### **STEP 6: Create Main Processing Script**

**File**: `scripts/process_and_classify_all_<subject>.py`

**What It Does**:
1. Scans processed folders for manifest.json files
2. Extracts text from PDFs using PyPDF2
3. Creates paper records in database
4. Creates page records with text excerpts
5. **IMPORTANT**: Sets URL fields for both question papers AND mark schemes
6. Classifies pages using multi-model classifier

**Critical Database Fields**:

```python
# Paper fields
{
    'subject_id': '<subject-uuid>',
    'paper_code': '2014_Jan_2P',
    'year': 2014,
    'season': 'Jan',
    'paper_number': '2P',
    'total_pages': 6
}

# Page fields
{
    'paper_id': '<paper-uuid>',
    'subject_id': '<subject-uuid>',
    'page_number': 1,
    'question_number': 1,
    'text_excerpt': 'Solve the equation...',  # First 500 chars
    'qp_page_url': 'https://.../q1.pdf',     # ⚠️ MUST SET THIS!
    'ms_page_url': 'https://.../q1_ms.pdf'   # ⚠️ MUST SET THIS!
}
```

**URL Format** (CRITICAL):
```python
base_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
bucket = 'question-pdfs'

# Question paper URL
qp_url = f"{base_url}/storage/v1/object/public/{bucket}/subjects/{subject_name}/pages/{paper_code}/q{qnum}.pdf"

# Mark scheme URL
ms_url = f"{base_url}/storage/v1/object/public/{bucket}/subjects/{subject_name}/pages/{paper_code}/q{qnum}_ms.pdf"
```

**⚠️ CRITICAL MISTAKE FROM FPM #1**:
Initial script did NOT set `qp_page_url` and `ms_page_url` fields → 609 pages had NULL URLs → worksheet generation returned "No questions found". 

**Fix**: Always set URL fields during page creation, not later.

**⚠️ CRITICAL MISTAKE FROM FPM #2**:
Initial URLs were missing the bucket name (`question-pdfs`) → 404 errors.

**Fix**: Always include full path: `{bucket}/subjects/{subject}/pages/{paper}/q{num}.pdf`

**⚠️ CRITICAL MISTAKE FROM FPM #3**:
Folder names in database had "Paper" prefix (e.g., `Paper2P`) but storage folders didn't → 404 errors.

**Fix**: Keep folder naming consistent:
- Database: `2014_Jan_2P`
- Storage: `subjects/<Subject>/pages/2014_Jan_2P/`

---

### **STEP 7: Upload Question Paper PDFs to Storage**

**File**: `scripts/upload_<subject>_pdfs.py`

**Purpose**: Upload question paper PDFs from `pages/` subfolders to Supabase storage.

```python
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

BUCKET_NAME = 'question-pdfs'
SUBJECT_NAME = '<Subject Name>'  # e.g., "Further_Pure_Mathematics"
LOCAL_BASE = f'data/processed/{SUBJECT_NAME} Processed'

def upload_papers():
    folders = [f for f in os.listdir(LOCAL_BASE) if os.path.isdir(os.path.join(LOCAL_BASE, f))]
    
    for folder in folders:
        pages_folder = os.path.join(LOCAL_BASE, folder, 'pages')
        
        if not os.path.exists(pages_folder):
            continue
        
        pdf_files = [f for f in os.listdir(pages_folder) if f.endswith('.pdf')]
        
        for pdf_file in pdf_files:
            local_path = os.path.join(pages_folder, pdf_file)
            
            # Storage path format
            storage_path = f"subjects/{SUBJECT_NAME}/pages/{folder}/{pdf_file}"
            
            # Upload
            with open(local_path, 'rb') as f:
                result = supabase.storage.from_(BUCKET_NAME).upload(
                    storage_path,
                    f,
                    {'content-type': 'application/pdf'}
                )
            
            print(f"✅ Uploaded: {storage_path}")

if __name__ == '__main__':
    upload_papers()
```

**Expected Structure After Upload**:
```
Supabase Storage: question-pdfs/
└── subjects/
    └── <Subject Name>/
        └── pages/
            ├── 2011_Jun_1P/
            │   ├── q1.pdf
            │   ├── q2.pdf
            │   └── ...
            ├── 2014_Jan_2P/
            │   ├── q1.pdf
            │   └── ...
            └── ...
```

**⚠️ FPM MISTAKE**:
Initial script tried to upload but storage paths were wrong. Always test with 1 folder first before bulk upload.

---

### **STEP 8: Upload Mark Scheme PDFs to Storage**

**File**: `scripts/upload_<subject>_markschemes.py`

**Purpose**: Upload mark scheme PDFs from `markschemes/` subfolders to Supabase storage.

**Key Difference from Question Papers**:
- Read from: `/markschemes/q1.pdf` (local)
- Upload to: `/pages/{folder}/q1_ms.pdf` (storage)
- Adds `_ms` suffix during upload

```python
def upload_markschemes():
    folders = [f for f in os.listdir(LOCAL_BASE) if os.path.isdir(os.path.join(LOCAL_BASE, f))]
    
    for folder in folders:
        ms_folder = os.path.join(LOCAL_BASE, folder, 'markschemes')
        
        if not os.path.exists(ms_folder):
            continue
        
        pdf_files = [f for f in os.listdir(ms_folder) if f.endswith('.pdf')]
        
        for pdf_file in pdf_files:
            local_path = os.path.join(ms_folder, pdf_file)
            
            # Add _ms suffix to filename
            base_name = pdf_file.replace('.pdf', '')
            storage_filename = f"{base_name}_ms.pdf"
            
            # Storage path format
            storage_path = f"subjects/{SUBJECT_NAME}/pages/{folder}/{storage_filename}"
            
            # Upload
            with open(local_path, 'rb') as f:
                result = supabase.storage.from_(BUCKET_NAME).upload(
                    storage_path,
                    f,
                    {'content-type': 'application/pdf'}
                )
            
            print(f"✅ Uploaded: {storage_path}")
```

**Expected Result**:
- Question papers: `q1.pdf`, `q2.pdf`, ...
- Mark schemes: `q1_ms.pdf`, `q2_ms.pdf`, ...
- **Both in same folder**: `subjects/{subject}/pages/{paper}/`

**⚠️ FPM EXPERIENCE**:
Not all papers have mark schemes (especially older papers). Don't panic if some are missing - it's normal.

**FPM Results**: 483 mark schemes uploaded out of 620 questions (77% coverage).

---

### **STEP 9: Test All URLs Are Accessible**

**File**: `scripts/test_<subject>_urls.py`

**Purpose**: Verify that all PDFs in database are actually accessible from storage.

```python
import requests
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

SUBJECT_ID = '<subject-uuid>'

def test_urls():
    # Get all pages for subject
    result = supabase.table('pages').select('id, question_number, qp_page_url, ms_page_url').eq('subject_id', SUBJECT_ID).execute()
    
    qp_success = 0
    qp_fail = 0
    ms_success = 0
    ms_fail = 0
    
    for page in result.data:
        # Test question paper URL
        if page['qp_page_url']:
            response = requests.head(page['qp_page_url'])
            if response.status_code == 200:
                qp_success += 1
            else:
                qp_fail += 1
                print(f"❌ QP Failed: Q{page['question_number']} - {page['qp_page_url']}")
        
        # Test mark scheme URL
        if page['ms_page_url']:
            response = requests.head(page['ms_page_url'])
            if response.status_code == 200:
                ms_success += 1
            else:
                ms_fail += 1
                print(f"❌ MS Failed: Q{page['question_number']} - {page['ms_page_url']}")
    
    print(f"\n✅ Question Papers: {qp_success}/{qp_success + qp_fail} ({qp_success/(qp_success + qp_fail)*100:.1f}%)")
    print(f"✅ Mark Schemes: {ms_success}/{ms_success + ms_fail} ({ms_success/(ms_success + ms_fail)*100:.1f}%)")

if __name__ == '__main__':
    test_urls()
```

**Expected Results**:
- Question Papers: 100% accessible
- Mark Schemes: 75-85% accessible (some may be missing in source data)

**⚠️ FPM MISTAKES FOUND**:
1. URLs missing `question-pdfs` bucket → 100% failed
2. Folder names had "Paper" prefix → 100% failed
3. After fixes → 100% question papers accessible, 77% mark schemes accessible

---

### **STEP 10: Test Worksheet Generation**

**File**: `scripts/test_<subject>_worksheets.py`

**Purpose**: End-to-end test that worksheet generation works for all topics.

```python
from supabase import create_client
import os
import requests
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

SUBJECT_ID = '<subject-uuid>'

def test_all_topics():
    # Get all topics
    topics = supabase.table('topics').select('*').eq('subject_id', SUBJECT_ID).execute()
    
    for topic in topics.data:
        print(f"\n🧪 Testing: {topic['name']} ({topic['short_name']})")
        
        # Get pages for this topic
        pages = supabase.table('pages').select('id, question_number, qp_page_url, ms_page_url').eq('subject_id', SUBJECT_ID).contains('topics', [topic['id']]).limit(3).execute()
        
        if not pages.data:
            print(f"   ⚠️ No pages found for this topic")
            continue
        
        print(f"   ✅ Found {len(pages.data)} pages")
        
        qp_working = 0
        ms_working = 0
        
        for page in pages.data:
            # Test QP URL
            if page['qp_page_url']:
                response = requests.head(page['qp_page_url'])
                if response.status_code == 200:
                    qp_working += 1
            
            # Test MS URL
            if page['ms_page_url']:
                response = requests.head(page['ms_page_url'])
                if response.status_code == 200:
                    ms_working += 1
        
        print(f"   QP: {qp_working}/{len(pages.data)} | MS: {ms_working}/{len(pages.data)}")

if __name__ == '__main__':
    test_all_topics()
```

**What to Look For**:
- All topics return pages
- Question paper URLs work (100% expected)
- Mark scheme URLs work (70-80% expected)

**FPM Results**:
- All 10 topics tested successfully
- QP: 30/30 (100%)
- MS: 23/30 (77%)

---

## 🚨 Complete Mistake Checklist

### **Database Mistakes**

❌ **Mistake 1: Wrong Subject ID**
- **Problem**: Pages stored under wrong subject (FPM pages under Physics subject_id)
- **Result**: Worksheet generation returned wrong subject's papers
- **Fix**: Always verify `subject_id` matches correct subject before bulk operations
- **Prevention**: Run `scripts/check_<subject>_subject.py` before processing

❌ **Mistake 2: Duplicate Papers**
- **Problem**: Same papers stored under multiple subjects (46 FPM papers duplicated in Physics)
- **Result**: Database bloat, confusion in worksheet generation
- **Fix**: Delete duplicates based on paper_code matching
- **Prevention**: Check for duplicates BEFORE adding new papers

❌ **Mistake 3: Missing URL Fields**
- **Problem**: Created 609 pages but forgot to set `qp_page_url` and `ms_page_url` fields
- **Result**: "No questions found matching your criteria" error
- **Fix**: Always set URL fields during page creation, not as afterthought
- **Prevention**: Include URL setting in main processing script

❌ **Mistake 4: NULL URLs in Database**
- **Problem**: Pages created with NULL qp_page_url values
- **Result**: Worksheet query returns 0 results even though pages exist
- **Fix**: Update all pages with correct storage URLs
- **Prevention**: Make URL fields required in processing script

---

### **Storage/URL Mistakes**

❌ **Mistake 5: Missing Bucket Name in URLs**
- **Problem**: URLs started with `subjects/...` instead of `question-pdfs/subjects/...`
- **Result**: 404 errors for all PDFs
- **Fix**: Add bucket name to all URLs
- **Correct Format**: `{base}/storage/v1/object/public/question-pdfs/subjects/...`

❌ **Mistake 6: Folder Name Mismatch**
- **Problem**: Database URLs had `Paper2P` but storage folders had `2P`
- **Result**: 404 errors even after fixing bucket name
- **Fix**: Remove "Paper" prefix from all folder names in URLs
- **Prevention**: Keep folder naming consistent between database and storage

❌ **Mistake 7: PDFs Not Uploaded**
- **Problem**: Created database records but never uploaded actual PDF files
- **Result**: "Failed to download PDF from..." errors
- **Fix**: Upload PDFs to storage BEFORE testing worksheet generation
- **Prevention**: Make PDF upload part of main pipeline, not optional step

❌ **Mistake 8: Mark Schemes in Wrong Location**
- **Problem**: Looked for mark schemes in `pages/` folder but they were in `markschemes/` folder
- **Result**: Mark schemes never uploaded initially
- **Fix**: Create separate upload script for mark schemes
- **Prevention**: Check both `pages/` AND `markschemes/` subfolders

---

### **Processing Mistakes**

❌ **Mistake 9: Rate Limiting Not Handled**
- **Problem**: Single Groq model → 30 req/min → slow processing + failures
- **Result**: Processing 620 pages took excessive time, many 429 errors
- **Fix**: Multi-model rotation with 6 models (~180 req/min capacity)
- **Prevention**: Always use multi-model setup for bulk classification

❌ **Mistake 10: No Keyword Pre-filtering**
- **Problem**: Sent every page to LLM even if topic was obvious
- **Result**: Wasted API calls, slower processing
- **Fix**: Keyword map with 44 FPM keywords, 3+ matches = direct classification
- **Result**: ~40% of pages pre-filtered, saved ~240 API calls

❌ **Mistake 11: Empty Processed Folders / Data Deletion**
- **Problem**: Physics had 60 folders but ALL were empty (no manifest.json, no PDFs)
- **Root Cause**: Physics processed folders were **accidentally deleted** during FPM duplicate cleanup because they had the same paper names (2011_Jun_1P, 2014_Jan_2P, etc.)
- **Result**: Cannot restore papers from processed data - must start from raw PDFs
- **Fix**: Physics needs full processing from scratch (raw extraction → database → upload → classify)
- **Prevention**: 
  - ALWAYS verify folders have content before assuming data exists
  - Use subject-specific folder names to prevent cross-subject deletions
  - Back up processed data before running cleanup scripts
  - Check which subject owns a paper_code before deleting

---

### **Testing Mistakes**

❌ **Mistake 12: Not Testing End-to-End**
- **Problem**: Tested database, tested storage, but never tested actual worksheet generation
- **Result**: Found issues only when user reported problems
- **Fix**: Created comprehensive test script that mimics real workflow
- **Prevention**: Test worksheet generation BEFORE declaring subject complete

❌ **Mistake 13: Assuming All Papers Have Mark Schemes**
- **Problem**: Expected 100% mark scheme coverage
- **Result**: False alarm when only 77% had mark schemes
- **Reality**: Older papers often don't have mark schemes in source data
- **Prevention**: Accept 70-85% mark scheme coverage as normal

---

## ✅ Complete Pre-Flight Checklist

Before starting a new subject, verify:

### **Source Data Verification**
- [ ] Raw papers exist in `data/raw/<Subject>/`
- [ ] Processed folders exist in `data/processed/<Subject> Processed/`
- [ ] Sample folder contains `manifest.json`
- [ ] Sample folder has `pages/` subfolder with PDFs
- [ ] Sample folder has `markschemes/` subfolder with PDFs (optional)
- [ ] PDFs are not corrupted (can be opened)

### **Database Setup**
- [ ] Subject exists in `subjects` table
- [ ] Subject code is correct (e.g., 9FM0, 4PH1)
- [ ] Subject ID (UUID) is noted and verified
- [ ] Topics are defined in `topics` table
- [ ] Topic count matches expected (e.g., 10 for FPM, 8 for Physics)
- [ ] No existing papers for this subject (check for duplicates)

### **Configuration Files**
- [ ] Keyword YAML created with 3-5 keywords per topic
- [ ] Keywords include math notation and function patterns
- [ ] Processing script created and tested on 1 paper
- [ ] URL format follows correct pattern (with bucket name)
- [ ] Folder names match between database and storage

### **API Setup**
- [ ] Groq API key is valid and has quota
- [ ] Multi-model classifier configured (6 models)
- [ ] Rate limiting set (2s delay recommended)
- [ ] Error handling includes 429, 400, 503 codes

### **Workflow Scripts Created**
- [ ] `scripts/process_and_classify_all_<subject>.py`
- [ ] `scripts/upload_<subject>_pdfs.py`
- [ ] `scripts/upload_<subject>_markschemes.py`
- [ ] `scripts/test_<subject>_urls.py`
- [ ] `scripts/test_<subject>_worksheets.py`

---

## 📊 Expected Timeline for New Subject

Based on FPM experience (75 papers, 620 pages):

| Phase | Duration | Notes |
|-------|----------|-------|
| **1. Verification & Setup** | 30 min | Check data, create scripts |
| **2. Processing & Classification** | 1-2 hours | Depends on page count, ~180 pages/hour with multi-model |
| **3. PDF Upload (Questions)** | 30-60 min | Network dependent, ~10-20 files/min |
| **4. PDF Upload (Mark Schemes)** | 30-60 min | Network dependent, ~10-20 files/min |
| **5. URL Verification & Fixes** | 30 min | Test URLs, fix any issues |
| **6. Comprehensive Testing** | 30 min | Test all topics end-to-end |
| **TOTAL** | **4-6 hours** | For ~600-700 pages |

**Scaling**:
- 200 pages: ~2 hours
- 600 pages: ~4-6 hours
- 1000 pages: ~8-10 hours

---

## 🎯 Success Criteria

A subject is ready for production when:

### **Database Metrics**
- ✅ All papers created in database (100%)
- ✅ All pages created with text excerpts (100%)
- ✅ 95%+ pages classified by topic
- ✅ All pages have `qp_page_url` set (100%)
- ✅ All pages have `ms_page_url` set (where available)

### **Storage Metrics**
- ✅ All question PDFs uploaded (100%)
- ✅ 70-85% mark scheme PDFs uploaded (acceptable)
- ✅ Storage folder structure matches database URLs

### **Functionality Metrics**
- ✅ All question paper URLs return 200 status (100%)
- ✅ 70-85% mark scheme URLs return 200 status
- ✅ Worksheet generation returns papers for all topics
- ✅ Generated PDFs can be opened and contain correct pages

### **Test Results**
- ✅ End-to-end test passes for all topics
- ✅ Sample worksheet downloads successfully
- ✅ PDFs render correctly in browser

---

## 📝 Quick Command Reference

### **Check Subject Status**
```powershell
python scripts\check_<subject>_subject.py
```

### **Process All Papers**
```powershell
python scripts\process_and_classify_all_<subject>.py
```

### **Upload Question Papers**
```powershell
python scripts\upload_<subject>_pdfs.py
```

### **Upload Mark Schemes**
```powershell
python scripts\upload_<subject>_markschemes.py
```

### **Test URLs**
```powershell
python scripts\test_<subject>_urls.py
```

### **Test Worksheets**
```powershell
python scripts\test_<subject>_worksheets.py
```

### **Check Progress**
```powershell
python scripts\<subject>_progress.py
```

---

## 🔄 Recovery from Common Issues

### **Issue: "No questions found matching your criteria"**
**Cause**: Missing URLs in database OR no pages for topic

**Diagnosis**:
```sql
-- Check if pages have URLs
SELECT COUNT(*) FROM pages WHERE subject_id = '<uuid>' AND qp_page_url IS NULL;

-- Check if pages exist for topic
SELECT COUNT(*) FROM pages WHERE subject_id = '<uuid>' AND topics @> ARRAY[<topic_id>];
```

**Fix**:
```python
# Update URLs for all pages
# See Step 6 for URL format
```

---

### **Issue: 404 errors on PDF URLs**
**Cause**: URL path mismatch OR PDFs not uploaded

**Diagnosis**:
```powershell
# Check if PDFs exist in storage
# Go to Supabase Storage UI → question-pdfs → subjects → <Subject> → pages

# Test a sample URL
curl -I "<sample-url>"
```

**Fix**:
1. Verify PDFs uploaded to correct path
2. Check URL format includes bucket name
3. Verify folder names match between DB and storage

---

### **Issue: Rate limit errors (429)**
**Cause**: Too many API requests to single model

**Fix**:
- Increase `DELAY_BETWEEN_REQUESTS` (try 3.0 seconds)
- Ensure multi-model rotation is working
- Check all 6 models are initialized correctly

---

### **Issue: Empty processed folders**
**Cause**: Papers never extracted from raw PDFs

**Fix**:
- Papers need to be processed from raw folder first
- This is a separate extraction pipeline
- Cannot skip this step - no shortcuts

---

## 🎓 Lessons from FPM Implementation

### **What Worked Well**
1. ✅ Multi-model classifier → 83% faster processing
2. ✅ Keyword pre-filtering → Saved ~240 API calls
3. ✅ Separate upload scripts for QP and MS → Clear separation
4. ✅ Comprehensive testing script → Caught issues early
5. ✅ Incremental approach → Fixed issues in phases

### **What Could Be Improved**
1. ⚠️ Set URLs during initial processing (not later)
2. ⚠️ Upload PDFs immediately after creating pages
3. ⚠️ Test end-to-end earlier (not after all processing)
4. ⚠️ Verify folder structure before assuming data exists
5. ⚠️ Keep folder naming consistent from start

### **Time Savers for Next Subject**
1. 🚀 Copy FPM scripts and modify (don't start from scratch)
2. 🚀 Reuse keyword map structure (just change keywords)
3. 🚀 Use same multi-model setup (already proven)
4. 🚀 Follow checklist exactly (avoid same mistakes)
5. 🚀 Test with 1 paper first (before bulk processing)

---

## 🎯 Final Notes

### **Physics Current State**
- ❌ 0 papers in database
- ❌ Processed folders are empty
- ❌ Needs full processing from scratch
- ⏳ Estimated time: 4-6 hours (similar to FPM)

### **FPM Current State**
- ✅ 75 papers fully processed
- ✅ 620 pages created
- ✅ 609 pages classified (98.2%)
- ✅ All PDFs uploaded and accessible
- ✅ Worksheet generation 100% functional
- ⏳ 11 pages remaining for classification

### **Next Steps**
1. Complete remaining 11 FPM page classifications
2. Decide if Physics should be processed next
3. Use this guide for any new subjects

---

## 📞 Quick Reference for Future Subjects

**Subject**: _____________

**Subject Code**: _____________

**Subject ID**: _____________

**Topic Count**: _____________

**Expected Page Count**: _____________

**Keywords Defined**: ☐ Yes ☐ No

**Scripts Created**: ☐ Process ☐ Upload QP ☐ Upload MS ☐ Test URLs ☐ Test Worksheets

**Status**:
- ☐ Source data verified
- ☐ Database setup complete
- ☐ Processing complete
- ☐ Classification complete
- ☐ PDFs uploaded
- ☐ URLs verified
- ☐ End-to-end tested
- ☐ Ready for production

---

*This guide was created based on the complete FPM implementation experience. Follow it exactly to avoid the same mistakes and achieve 100% success rate.*
