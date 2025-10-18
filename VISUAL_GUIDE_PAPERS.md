# 📊 Visual Guide: Paper Upload Structure

## 🎯 Current Setup

```
✅ Physics (4PH1) - READY
   - 1 paper processed (2019 Jun 1P)
   - 8 topics configured
   - Database ready
   - Storage configured
```

---

## 📁 Required Folder Structure

### For Same Subject (Add More Physics Papers)

```
data/raw/IGCSE/4PH1/
│
├── 2019/                          ← YEAR
│   ├── Jun/                       ← SEASON (Jun or Jan)
│   │   ├── 4PH1_1P.pdf           ✅ Question Paper (already added)
│   │   └── 4PH1_1P_MS.pdf        ✅ Mark Scheme (already added)
│   │
│   └── Jan/                       ⬅️ ADD THIS
│       ├── 4PH1_1P.pdf           ⬅️ NEW: Jan 2019 Question Paper
│       └── 4PH1_1P_MS.pdf        ⬅️ NEW: Jan 2019 Mark Scheme
│
├── 2020/                          ⬅️ ADD THIS YEAR
│   ├── Jun/
│   │   ├── 4PH1_1P.pdf           ⬅️ NEW: Paper 1
│   │   ├── 4PH1_1P_MS.pdf
│   │   ├── 4PH1_2P.pdf           ⬅️ NEW: Paper 2 (if available)
│   │   └── 4PH1_2P_MS.pdf
│   │
│   └── Jan/
│       ├── 4PH1_1P.pdf
│       └── 4PH1_1P_MS.pdf
│
├── 2021/                          ⬅️ ADD MORE YEARS
│   ├── Jun/
│   │   ├── 4PH1_1P.pdf
│   │   └── 4PH1_1P_MS.pdf
│   └── Jan/
│       └── ...
│
└── 2022/
    └── ...
```

---

### For New Subject (e.g., Chemistry)

```
data/raw/IGCSE/
│
├── 4PH1/                          ✅ Physics (exists)
│   └── ...
│
├── 4CH1/                          ⬅️ NEW SUBJECT FOLDER
│   │
│   ├── 2019/
│   │   ├── Jun/
│   │   │   ├── 4CH1_1P.pdf       ⬅️ Chemistry Question Paper
│   │   │   └── 4CH1_1P_MS.pdf    ⬅️ Chemistry Mark Scheme
│   │   │
│   │   └── Jan/
│   │       ├── 4CH1_1P.pdf
│   │       └── 4CH1_1P_MS.pdf
│   │
│   ├── 2020/
│   │   └── Jun/
│   │       ├── 4CH1_1P.pdf
│   │       └── 4CH1_1P_MS.pdf
│   │
│   └── 2021/
│       └── ...
│
├── 4BI1/                          ⬅️ Biology
│   └── ...
│
└── 4MA1/                          ⬅️ Maths
    └── ...
```

---

## 🏗️ Step-by-Step Visual Workflow

### Adding Physics Paper (Existing Subject)

```
1. ORGANIZE FILES
   └─> Create folder: data/raw/IGCSE/4PH1/2020/Jun/
       └─> Copy PDFs:
           - 4PH1_1P.pdf
           - 4PH1_1P_MS.pdf

2. RUN SCRIPT
   └─> python scripts/page_based_ingest.py <QP.pdf> <MS.pdf>
       └─> Splits into pages
           └─> Classifies topics
               └─> Uploads to storage
                   └─> Saves to database

3. VERIFY
   └─> python scripts/check_database.py
       └─> Shows papers, topics, pages
```

---

### Adding Chemistry (New Subject)

```
1. DATABASE SETUP
   └─> Add subject
       └─> Add topics
           └─> Verify

2. CONFIGURATION
   └─> Create config/chemistry_topics.yaml
       └─> Create scripts/chemistry_ingest.py
           └─> Modify subject code & name

3. ORGANIZE FILES
   └─> Create folder: data/raw/IGCSE/4CH1/2019/Jun/
       └─> Copy PDFs:
           - 4CH1_1P.pdf
           - 4CH1_1P_MS.pdf

4. RUN SCRIPT
   └─> python scripts/chemistry_ingest.py <QP.pdf> <MS.pdf>
       └─> Same process as Physics

5. VERIFY
   └─> python scripts/check_database.py
```

---

## 📝 File Naming Rules

### Question Papers
```
{SUBJECT_CODE}_{PAPER_NUMBER}{TIER}.pdf

Examples:
┌─────────────────────┬──────────────────────────────┐
│ Filename            │ Description                  │
├─────────────────────┼──────────────────────────────┤
│ 4PH1_1P.pdf         │ Physics Paper 1              │
│ 4PH1_2P.pdf         │ Physics Paper 2              │
│ 4CH1_1P.pdf         │ Chemistry Paper 1            │
│ 4BI1_1P.pdf         │ Biology Paper 1              │
│ 4MA1_1F.pdf         │ Maths Paper 1 (Foundation)   │
│ 4MA1_1H.pdf         │ Maths Paper 1 (Higher)       │
│ 4MA1_2F.pdf         │ Maths Paper 2 (Foundation)   │
│ 4MA1_2H.pdf         │ Maths Paper 2 (Higher)       │
└─────────────────────┴──────────────────────────────┘
```

### Mark Schemes
```
{SUBJECT_CODE}_{PAPER_NUMBER}{TIER}_MS.pdf

Examples:
┌─────────────────────┬──────────────────────────────┐
│ Filename            │ Description                  │
├─────────────────────┼──────────────────────────────┤
│ 4PH1_1P_MS.pdf      │ Physics P1 Mark Scheme       │
│ 4CH1_1P_MS.pdf      │ Chemistry P1 Mark Scheme     │
│ 4MA1_1F_MS.pdf      │ Maths P1 Foundation MS       │
│ 4MA1_1H_MS.pdf      │ Maths P1 Higher MS           │
└─────────────────────┴──────────────────────────────┘
```

---

## 🎓 Subject Code Map

```
┌──────┬─────────────────┬──────────┬─────────────┐
│ Code │ Subject         │ Status   │ Topics      │
├──────┼─────────────────┼──────────┼─────────────┤
│ 4PH1 │ Physics         │ ✅ Ready │ 8 topics    │
│ 4CH1 │ Chemistry       │ ➕ Add   │ 5 topics    │
│ 4BI1 │ Biology         │ ➕ Add   │ 5 topics    │
│ 4MA1 │ Mathematics     │ ➕ Add   │ 7 topics    │
│ 4SC1 │ Science (Dual)  │ ➕ Add   │ 10 topics   │
│ 4ET1 │ English Lang    │ ➕ Add   │ 5 skills    │
└──────┴─────────────────┴──────────┴─────────────┘
```

---

## 🔄 Processing Flow

```
PDF FILES
   │
   ├─> Question Paper (4PH1_1P.pdf)
   │
   └─> Mark Scheme (4PH1_1P_MS.pdf)
          │
          ▼
   ┌──────────────────┐
   │  PAGE SPLITTER   │  Splits into individual questions
   └────────┬─────────┘
            │
            ├─> q1.pdf
            ├─> q2.pdf
            ├─> q3.pdf
            └─> ...
               │
               ▼
   ┌──────────────────┐
   │  AI CLASSIFIER   │  Classifies topics using Gemini AI
   └────────┬─────────┘
            │
            ├─> Q1: Topic 1 (Forces)
            ├─> Q2: Topic 2 (Electricity)
            ├─> Q3: Topic 5 (Solids/Liquids/Gases)
            └─> ...
               │
               ▼
   ┌──────────────────┐
   │ SUPABASE STORAGE │  Uploads to cloud storage
   └────────┬─────────┘
            │
            └─> subjects/Physics/pages/2019_Jun_1P/
                   ├─> q1.pdf
                   ├─> q1_ms.pdf
                   ├─> q2.pdf
                   ├─> q2_ms.pdf
                   └─> ...
                      │
                      ▼
   ┌──────────────────┐
   │    DATABASE      │  Saves metadata
   └──────────────────┘
            │
            └─> pages table:
                   - question_number: "1"
                   - topics: ["1"]
                   - difficulty: "medium"
                   - qp_page_url: "subjects/Physics/pages/2019_Jun_1P/q1.pdf"
                   - ms_page_url: "subjects/Physics/pages/2019_Jun_1P/q1_ms.pdf"
```

---

## ⚡ Quick Commands

### Add Physics Papers (Same Subject)
```powershell
# Example: Adding 2020 Jun Paper 1
python scripts/page_based_ingest.py `
  "data/raw/IGCSE/4PH1/2020/Jun/4PH1_1P.pdf" `
  "data/raw/IGCSE/4PH1/2020/Jun/4PH1_1P_MS.pdf"
```

### Add New Subject (Chemistry)
```powershell
# 1. Add subject to database
python scripts/add_subject.py chemistry

# 2. Create config file (manual step)
# Copy config/physics_topics.yaml to config/chemistry_topics.yaml
# Edit to match Chemistry topics

# 3. Create ingestion script (manual step)
# Copy scripts/page_based_ingest.py to scripts/chemistry_ingest.py
# Change lines 102, 108, 109

# 4. Add papers
python scripts/chemistry_ingest.py `
  "data/raw/IGCSE/4CH1/2019/Jun/4CH1_1P.pdf" `
  "data/raw/IGCSE/4CH1/2019/Jun/4CH1_1P_MS.pdf"
```

---

## ✅ Verification Checklist

After adding papers, verify with:

```powershell
# Check database
python scripts/check_database.py

# Output should show:
# ✅ Subjects: Physics (4PH1), Chemistry (4CH1), etc.
# ✅ Topics: 8 for Physics, 5 for Chemistry, etc.
# ✅ Papers: List of all processed papers
# ✅ Pages: Individual questions with topics
```

---

## 🎯 Example: Complete Process

### Scenario: Adding 3 Physics Papers

```
STEP 1: Organize PDFs
├── data/raw/IGCSE/4PH1/2020/Jun/4PH1_1P.pdf ✅
├── data/raw/IGCSE/4PH1/2020/Jun/4PH1_1P_MS.pdf ✅
├── data/raw/IGCSE/4PH1/2020/Jan/4PH1_1P.pdf ✅
├── data/raw/IGCSE/4PH1/2020/Jan/4PH1_1P_MS.pdf ✅
├── data/raw/IGCSE/4PH1/2021/Jun/4PH1_1P.pdf ✅
└── data/raw/IGCSE/4PH1/2021/Jun/4PH1_1P_MS.pdf ✅

STEP 2: Run Scripts
python scripts/page_based_ingest.py "data/raw/IGCSE/4PH1/2020/Jun/4PH1_1P.pdf" "data/raw/IGCSE/4PH1/2020/Jun/4PH1_1P_MS.pdf"
# Wait ~2 minutes (4.5 sec between questions)

python scripts/page_based_ingest.py "data/raw/IGCSE/4PH1/2020/Jan/4PH1_1P.pdf" "data/raw/IGCSE/4PH1/2020/Jan/4PH1_1P_MS.pdf"
# Wait ~2 minutes

python scripts/page_based_ingest.py "data/raw/IGCSE/4PH1/2021/Jun/4PH1_1P.pdf" "data/raw/IGCSE/4PH1/2021/Jun/4PH1_1P_MS.pdf"
# Wait ~2 minutes

STEP 3: Verify
python scripts/check_database.py

RESULT:
✅ 4 papers total (2019 Jun + 3 new)
✅ ~40-60 questions (depending on paper length)
✅ All classified with topics
✅ All uploaded to storage
✅ Ready for worksheet generation!
```

---

## 📞 Need Help?

Run these commands if you get stuck:

```powershell
# List available subjects to add
python scripts/add_subject.py list

# Check what's in database
python scripts/check_database.py

# Check storage
python scripts/list_storage.py
```

---

**Full Guide:** `HOW_TO_ADD_PAPERS_AND_SUBJECTS.md`
**Quick Reference:** `QUICK_REFERENCE_PAPERS.md`
