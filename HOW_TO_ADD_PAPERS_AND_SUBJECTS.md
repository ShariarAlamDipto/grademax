# 📚 Complete Guide: Adding Papers and Subjects to GradeMax

## 🎯 Overview

This guide shows you **exactly** how to add:
1. **More Physics papers** (same subject, different years/seasons)
2. **New subjects** (Chemistry, Maths, Biology, etc.)
3. **Papers for new subjects**

---

## 📁 Current Structure

Your current setup:
```
data/raw/IGCSE/4PH1/2019/Jun/
├── 4PH1_1P.pdf      ← Question Paper
└── 4PH1_1P_MS.pdf   ← Mark Scheme
```

**Breakdown:**
- `IGCSE` = Qualification level
- `4PH1` = Subject code (Physics)
- `2019` = Year
- `Jun` = Season (Jun/Jan)
- `1P` = Paper number

---

## 🔧 Part 1: Adding More Physics Papers

### Step 1: Organize Your Files

Follow this **exact structure**:

```
data/raw/IGCSE/4PH1/
├── 2019/
│   ├── Jun/
│   │   ├── 4PH1_1P.pdf       ✅ Already added
│   │   └── 4PH1_1P_MS.pdf    ✅ Already added
│   └── Jan/
│       ├── 4PH1_1P.pdf       ⬅️ Add this
│       └── 4PH1_1P_MS.pdf    ⬅️ Add this
├── 2020/
│   ├── Jun/
│   │   ├── 4PH1_1P.pdf       ⬅️ Add this
│   │   └── 4PH1_1P_MS.pdf    ⬅️ Add this
│   └── Jan/
│       ├── 4PH1_1P.pdf       ⬅️ Add this
│       └── 4PH1_1P_MS.pdf    ⬅️ Add this
├── 2021/
│   ├── Jun/
│   │   ├── 4PH1_1P.pdf
│   │   ├── 4PH1_1P_MS.pdf
│   │   ├── 4PH1_2P.pdf       ⬅️ Paper 2 (if exists)
│   │   └── 4PH1_2P_MS.pdf
│   └── Jan/
│       └── ...
└── 2022/
    └── ...
```

### Step 2: Create Folders and Add PDFs

```powershell
# Example: Adding 2020 Jun Physics Paper

# 1. Create folders
New-Item -ItemType Directory -Force -Path "data\raw\IGCSE\4PH1\2020\Jun"

# 2. Copy your PDFs there
# Put these files in: data\raw\IGCSE\4PH1\2020\Jun\
#   - 4PH1_1P.pdf       (Question Paper)
#   - 4PH1_1P_MS.pdf    (Mark Scheme)
```

### Step 3: Run Ingestion Script

```powershell
# Process the paper
python scripts/page_based_ingest.py "data/raw/IGCSE/4PH1/2020/Jun/4PH1_1P.pdf" "data/raw/IGCSE/4PH1/2020/Jun/4PH1_1P_MS.pdf"
```

**What happens:**
1. ✅ Splits PDF into individual question pages
2. ✅ Classifies each question by topic using AI
3. ✅ Uploads to Supabase Storage: `subjects/Physics/pages/2020_Jun_1P/q1.pdf`
4. ✅ Saves to database with topics, difficulty, etc.

---

## 🆕 Part 2: Adding a New Subject (e.g., Chemistry)

### Step 1: Add Subject to Database

You need to add the subject to your database first:

```sql
-- Run this in Supabase SQL Editor
-- https://supabase.com/dashboard → SQL Editor

INSERT INTO subjects (code, name, level, exam_board)
VALUES 
  ('4CH1', 'Chemistry', 'IGCSE', 'Edexcel'),
  ('4MA1', 'Mathematics', 'IGCSE', 'Edexcel'),
  ('4BI1', 'Biology', 'IGCSE', 'Edexcel');

-- Get the subject IDs for next step
SELECT * FROM subjects;
```

**Subject Codes (Edexcel IGCSE):**
- `4PH1` = Physics ✅ (already added)
- `4CH1` = Chemistry
- `4MA1` = Mathematics
- `4BI1` = Biology
- `4SC1` = Science (Double Award)

### Step 2: Add Topics for New Subject

Each subject has different topics. You need to add them:

```sql
-- Example: Chemistry Topics
INSERT INTO topics (subject_id, topic_number, name, description)
VALUES 
  -- Replace 'SUBJECT_UUID_HERE' with the UUID from Step 1
  ('SUBJECT_UUID_HERE', '1', 'Principles of Chemistry', 'States of matter, elements, compounds'),
  ('SUBJECT_UUID_HERE', '2', 'Chemistry of the Elements', 'Periodic table, groups'),
  ('SUBJECT_UUID_HERE', '3', 'Organic Chemistry', 'Hydrocarbons, alcohols, acids'),
  ('SUBJECT_UUID_HERE', '4', 'Physical Chemistry', 'Energetics, rates, equilibrium'),
  ('SUBJECT_UUID_HERE', '5', 'Chemistry in Society', 'Industrial processes');
```

**For Mathematics Topics:**
```sql
INSERT INTO topics (subject_id, topic_number, name, description)
VALUES 
  ('MATHS_UUID_HERE', '1', 'Number', 'Integers, fractions, decimals, percentages'),
  ('MATHS_UUID_HERE', '2', 'Algebra', 'Expressions, equations, sequences'),
  ('MATHS_UUID_HERE', '3', 'Geometry', 'Shapes, angles, transformations'),
  ('MATHS_UUID_HERE', '4', 'Statistics', 'Data collection, averages, probability'),
  ('MATHS_UUID_HERE', '5', 'Graphs', 'Coordinates, linear graphs, curves');
```

### Step 3: Create Topic Configuration File

Create `config/chemistry_topics.yaml` (copy from `physics_topics.yaml`):

```yaml
# config/chemistry_topics.yaml
topics:
  "1":
    name: "Principles of Chemistry"
    keywords:
      - "states of matter"
      - "elements"
      - "compounds"
      - "mixtures"
      - "atoms"
      - "molecules"
  
  "2":
    name: "Chemistry of the Elements"
    keywords:
      - "periodic table"
      - "groups"
      - "alkali metals"
      - "halogens"
      - "noble gases"
  
  "3":
    name: "Organic Chemistry"
    keywords:
      - "hydrocarbons"
      - "alkanes"
      - "alkenes"
      - "alcohols"
      - "carboxylic acids"
  
  "4":
    name: "Physical Chemistry"
    keywords:
      - "energetics"
      - "rates of reaction"
      - "equilibrium"
      - "electrolysis"
  
  "5":
    name: "Chemistry in Society"
    keywords:
      - "industrial processes"
      - "ammonia"
      - "sulfuric acid"
      - "metals"
```

### Step 4: Modify Ingestion Script for New Subject

You need to change the subject in the script. Two options:

#### **Option A: Create Subject-Specific Script** (Recommended)

Copy and modify for each subject:

```powershell
# Copy the script
Copy-Item "scripts\page_based_ingest.py" "scripts\chemistry_ingest.py"
```

Then edit `scripts/chemistry_ingest.py`:

```python
# Line 108-109: Change subject
self.subject_code = "4CH1"     # Change from "4PH1"
self.subject_name = "Chemistry"  # Change from "Physics"

# Line 102: Change config file
def __init__(self, config_path: str = "config/chemistry_topics.yaml"):
```

#### **Option B: Make Script Accept Parameters** (Better)

Modify the script to accept subject as parameter. I can help you do this!

### Step 5: Organize Chemistry PDFs

```
data/raw/IGCSE/4CH1/
├── 2019/
│   ├── Jun/
│   │   ├── 4CH1_1P.pdf
│   │   └── 4CH1_1P_MS.pdf
│   └── Jan/
│       ├── 4CH1_1P.pdf
│       └── 4CH1_1P_MS.pdf
├── 2020/
│   └── Jun/
│       ├── 4CH1_1P.pdf
│       └── 4CH1_1P_MS.pdf
└── ...
```

### Step 6: Process Chemistry Papers

```powershell
# If using Option A (chemistry_ingest.py)
python scripts/chemistry_ingest.py "data/raw/IGCSE/4CH1/2019/Jun/4CH1_1P.pdf" "data/raw/IGCSE/4CH1/2019/Jun/4CH1_1P_MS.pdf"

# If using Option B (modified script - I'll help you create this)
python scripts/page_based_ingest.py "data/raw/IGCSE/4CH1/2019/Jun/4CH1_1P.pdf" "data/raw/IGCSE/4CH1/2019/Jun/4CH1_1P_MS.pdf" --subject 4CH1
```

---

## 📊 Complete Folder Structure Example

Here's what your `data/raw/` should look like with multiple subjects:

```
data/raw/IGCSE/
├── 4PH1/                          ← Physics
│   ├── 2019/
│   │   ├── Jun/
│   │   │   ├── 4PH1_1P.pdf
│   │   │   └── 4PH1_1P_MS.pdf
│   │   └── Jan/
│   │       ├── 4PH1_1P.pdf
│   │       └── 4PH1_1P_MS.pdf
│   ├── 2020/
│   │   ├── Jun/
│   │   │   ├── 4PH1_1P.pdf
│   │   │   ├── 4PH1_1P_MS.pdf
│   │   │   ├── 4PH1_2P.pdf        ← Paper 2
│   │   │   └── 4PH1_2P_MS.pdf
│   │   └── Jan/
│   │       └── ...
│   └── 2021/
│       └── ...
│
├── 4CH1/                          ← Chemistry (New!)
│   ├── 2019/
│   │   ├── Jun/
│   │   │   ├── 4CH1_1P.pdf
│   │   │   └── 4CH1_1P_MS.pdf
│   │   └── Jan/
│   │       └── ...
│   └── 2020/
│       └── ...
│
├── 4MA1/                          ← Maths (New!)
│   ├── 2019/
│   │   ├── Jun/
│   │   │   ├── 4MA1_1F.pdf       ← Foundation tier
│   │   │   ├── 4MA1_1F_MS.pdf
│   │   │   ├── 4MA1_1H.pdf       ← Higher tier
│   │   │   └── 4MA1_1H_MS.pdf
│   │   └── Jan/
│   │       └── ...
│   └── 2020/
│       └── ...
│
└── 4BI1/                          ← Biology (New!)
    ├── 2019/
    │   └── Jun/
    │       ├── 4BI1_1P.pdf
    │       └── 4BI1_1P_MS.pdf
    └── 2020/
        └── ...
```

---

## 🎯 Quick Reference: File Naming Convention

### Question Papers:
```
{SUBJECT_CODE}_{PAPER_NUMBER}{TIER}.pdf

Examples:
- 4PH1_1P.pdf         (Physics Paper 1)
- 4PH1_2P.pdf         (Physics Paper 2)
- 4CH1_1P.pdf         (Chemistry Paper 1)
- 4MA1_1F.pdf         (Maths Paper 1 Foundation)
- 4MA1_1H.pdf         (Maths Paper 1 Higher)
- 4BI1_1P.pdf         (Biology Paper 1)
```

### Mark Schemes:
```
{SUBJECT_CODE}_{PAPER_NUMBER}{TIER}_MS.pdf

Examples:
- 4PH1_1P_MS.pdf      (Physics Paper 1 Mark Scheme)
- 4CH1_1P_MS.pdf      (Chemistry Paper 1 Mark Scheme)
- 4MA1_1F_MS.pdf      (Maths Paper 1 Foundation Mark Scheme)
```

---

## 🚀 Step-by-Step: Adding Your First New Subject

Let's say you want to add **Chemistry**:

### **Day 1: Database Setup**

1. **Add Subject to Database:**
   ```sql
   -- In Supabase SQL Editor
   INSERT INTO subjects (code, name, level, exam_board)
   VALUES ('4CH1', 'Chemistry', 'IGCSE', 'Edexcel');
   
   -- Get the UUID
   SELECT id, code, name FROM subjects WHERE code = '4CH1';
   -- Copy the UUID (e.g., '123e4567-e89b-12d3-a456-426614174000')
   ```

2. **Add Chemistry Topics:**
   ```sql
   -- Replace YOUR_CHEMISTRY_UUID with the UUID from step 1
   INSERT INTO topics (subject_id, topic_number, name, description)
   VALUES 
     ('YOUR_CHEMISTRY_UUID', '1', 'Principles of Chemistry', 'States, atoms, compounds'),
     ('YOUR_CHEMISTRY_UUID', '2', 'Chemistry of Elements', 'Periodic table, groups'),
     ('YOUR_CHEMISTRY_UUID', '3', 'Organic Chemistry', 'Hydrocarbons, alcohols'),
     ('YOUR_CHEMISTRY_UUID', '4', 'Physical Chemistry', 'Energetics, rates'),
     ('YOUR_CHEMISTRY_UUID', '5', 'Chemistry in Society', 'Industrial processes');
   ```

3. **Verify:**
   ```sql
   SELECT t.topic_number, t.name, s.name as subject
   FROM topics t
   JOIN subjects s ON t.subject_id = s.id
   WHERE s.code = '4CH1'
   ORDER BY t.topic_number;
   ```

### **Day 2: Configuration**

4. **Create Topic Config:**
   ```powershell
   # Copy physics config as template
   Copy-Item "config\physics_topics.yaml" "config\chemistry_topics.yaml"
   
   # Edit chemistry_topics.yaml to match your Chemistry topics
   ```

5. **Create Ingestion Script:**
   ```powershell
   # Copy and rename
   Copy-Item "scripts\page_based_ingest.py" "scripts\chemistry_ingest.py"
   ```

6. **Edit `scripts/chemistry_ingest.py`:**
   - Line 102: `config_path: str = "config/chemistry_topics.yaml"`
   - Line 108: `self.subject_code = "4CH1"`
   - Line 109: `self.subject_name = "Chemistry"`

### **Day 3: Add Papers**

7. **Organize PDFs:**
   ```powershell
   # Create folder structure
   New-Item -ItemType Directory -Force -Path "data\raw\IGCSE\4CH1\2019\Jun"
   
   # Copy your PDFs to:
   # data\raw\IGCSE\4CH1\2019\Jun\4CH1_1P.pdf
   # data\raw\IGCSE\4CH1\2019\Jun\4CH1_1P_MS.pdf
   ```

8. **Process First Chemistry Paper:**
   ```powershell
   python scripts/chemistry_ingest.py "data/raw/IGCSE/4CH1/2019/Jun/4CH1_1P.pdf" "data/raw/IGCSE/4CH1/2019/Jun/4CH1_1P_MS.pdf"
   ```

9. **Verify:**
   ```powershell
   python scripts/check_database.py
   ```

---

## ✅ Checklist for Adding Each Paper

- [ ] PDF files downloaded and renamed correctly
- [ ] Folder structure created: `data/raw/IGCSE/{SUBJECT}/{YEAR}/{SEASON}/`
- [ ] Question paper named: `{CODE}_{PAPER}.pdf`
- [ ] Mark scheme named: `{CODE}_{PAPER}_MS.pdf`
- [ ] Subject exists in database (run SQL query to check)
- [ ] Topics exist for subject (run SQL query to check)
- [ ] Config file exists: `config/{subject}_topics.yaml`
- [ ] Run ingestion script with correct paths
- [ ] Check output for errors
- [ ] Verify in database: `python scripts/check_database.py`

---

## 🔍 Troubleshooting

### Error: "Subject 4CH1 not found in database"
**Solution:** Add subject to database first (see Part 2, Step 1)

### Error: "Invalid API key"
**Solution:** Make sure `.env.ingest` has correct Supabase keys

### Error: "Classification failed"
**Solution:** 
- Check Gemini API key in `.env.ingest`
- Check `config/{subject}_topics.yaml` exists
- Rate limiting: Script waits 4.5 seconds between questions

### PDFs not uploading to Storage
**Solution:**
- Check Supabase Storage bucket `question-pdfs` exists
- Check bucket is public
- Check service role key in `.env.ingest`

---

## 📝 Example Commands

### Add Multiple Physics Papers in Batch:

```powershell
# 2019 Jun Paper 1
python scripts/page_based_ingest.py "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf" "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf"

# 2019 Jan Paper 1
python scripts/page_based_ingest.py "data/raw/IGCSE/4PH1/2019/Jan/4PH1_1P.pdf" "data/raw/IGCSE/4PH1/2019/Jan/4PH1_1P_MS.pdf"

# 2020 Jun Paper 1
python scripts/page_based_ingest.py "data/raw/IGCSE/4PH1/2020/Jun/4PH1_1P.pdf" "data/raw/IGCSE/4PH1/2020/Jun/4PH1_1P_MS.pdf"

# 2020 Jun Paper 2
python scripts/page_based_ingest.py "data/raw/IGCSE/4PH1/2020/Jun/4PH1_2P.pdf" "data/raw/IGCSE/4PH1/2020/Jun/4PH1_2P_MS.pdf"
```

### Check Database After Adding:

```powershell
python scripts/check_database.py
```

---

## 🎓 Subject Codes Reference (Edexcel IGCSE)

| Code  | Subject          | Topics Needed |
|-------|------------------|---------------|
| 4PH1  | Physics          | ✅ (8 topics) |
| 4CH1  | Chemistry        | ~5 topics     |
| 4BI1  | Biology          | ~5 topics     |
| 4MA1  | Mathematics      | ~7 topics     |
| 4SC1  | Science (Double) | ~10 topics    |
| 4ET1  | English Language | ~5 skills     |

---

## 💡 Pro Tips

1. **Batch Processing**: Process all papers from one year, then move to next year
2. **Rate Limiting**: Script waits 4.5 seconds between questions (Gemini API limit)
3. **Backup**: Keep original PDFs in a separate backup folder
4. **Naming**: Be consistent with file naming (use underscores, not spaces)
5. **Verification**: Always run `check_database.py` after adding papers
6. **Storage**: Papers are stored in Supabase Storage under `subjects/{SubjectName}/pages/`

---

## 🎯 Next Steps

**Want me to help you:**
1. ✅ Create SQL queries to add specific subjects?
2. ✅ Modify the ingestion script to accept subject as parameter?
3. ✅ Create topic configuration files for new subjects?
4. ✅ Set up batch processing scripts?

Just let me know which subject you want to add first! 🚀
