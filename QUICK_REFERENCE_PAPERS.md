# 🚀 Quick Reference: Adding Papers

## ⚡ For Existing Subject (Physics)

### 1. Organize Files
```
data/raw/IGCSE/4PH1/{YEAR}/{SEASON}/
├── 4PH1_1P.pdf       ← Question Paper
└── 4PH1_1P_MS.pdf    ← Mark Scheme
```

**Example:**
```powershell
# Create folder
New-Item -ItemType Directory -Force -Path "data\raw\IGCSE\4PH1\2020\Jun"

# Put your PDFs in:
# data\raw\IGCSE\4PH1\2020\Jun\4PH1_1P.pdf
# data\raw\IGCSE\4PH1\2020\Jun\4PH1_1P_MS.pdf
```

### 2. Run Script
```powershell
python scripts/page_based_ingest.py "data/raw/IGCSE/4PH1/2020/Jun/4PH1_1P.pdf" "data/raw/IGCSE/4PH1/2020/Jun/4PH1_1P_MS.pdf"
```

### 3. Verify
```powershell
python scripts/check_database.py
```

---

## 🆕 For New Subject (e.g., Chemistry)

### 1. Add to Database
```sql
-- In Supabase SQL Editor (https://supabase.com/dashboard)

-- Add subject
INSERT INTO subjects (code, name, level, exam_board)
VALUES ('4CH1', 'Chemistry', 'IGCSE', 'Edexcel');

-- Get the UUID
SELECT id FROM subjects WHERE code = '4CH1';
-- Copy the UUID (e.g., 'abc-123-def-456')

-- Add topics (replace YOUR_UUID with actual UUID)
INSERT INTO topics (subject_id, topic_number, name, description)
VALUES 
  ('YOUR_UUID', '1', 'Principles of Chemistry', 'States, atoms, compounds'),
  ('YOUR_UUID', '2', 'Chemistry of Elements', 'Periodic table'),
  ('YOUR_UUID', '3', 'Organic Chemistry', 'Hydrocarbons'),
  ('YOUR_UUID', '4', 'Physical Chemistry', 'Energetics, rates'),
  ('YOUR_UUID', '5', 'Chemistry in Society', 'Industrial');
```

### 2. Create Config File
```powershell
# Copy template
Copy-Item "config\physics_topics.yaml" "config\chemistry_topics.yaml"

# Edit chemistry_topics.yaml with Chemistry topics
```

### 3. Create Ingestion Script
```powershell
# Copy script
Copy-Item "scripts\page_based_ingest.py" "scripts\chemistry_ingest.py"
```

**Edit `scripts/chemistry_ingest.py`:**
- Line 102: `config_path: str = "config/chemistry_topics.yaml"`
- Line 108: `self.subject_code = "4CH1"`
- Line 109: `self.subject_name = "Chemistry"`

### 4. Add Papers
```powershell
# Organize files
New-Item -ItemType Directory -Force -Path "data\raw\IGCSE\4CH1\2019\Jun"

# Put PDFs in:
# data\raw\IGCSE\4CH1\2019\Jun\4CH1_1P.pdf
# data\raw\IGCSE\4CH1\2019\Jun\4CH1_1P_MS.pdf

# Run script
python scripts/chemistry_ingest.py "data/raw/IGCSE/4CH1/2019/Jun/4CH1_1P.pdf" "data/raw/IGCSE/4CH1/2019/Jun/4CH1_1P_MS.pdf"
```

---

## 📋 File Naming Convention

| Type | Format | Example |
|------|--------|---------|
| Question Paper | `{CODE}_{PAPER}.pdf` | `4PH1_1P.pdf` |
| Mark Scheme | `{CODE}_{PAPER}_MS.pdf` | `4PH1_1P_MS.pdf` |
| Paper 2 | `{CODE}_2P.pdf` | `4PH1_2P.pdf` |
| Foundation Tier | `{CODE}_1F.pdf` | `4MA1_1F.pdf` |
| Higher Tier | `{CODE}_1H.pdf` | `4MA1_1H.pdf` |

---

## 🎓 Subject Codes (Edexcel IGCSE)

| Code | Subject | Status |
|------|---------|--------|
| 4PH1 | Physics | ✅ Active |
| 4CH1 | Chemistry | ➕ Add |
| 4BI1 | Biology | ➕ Add |
| 4MA1 | Mathematics | ➕ Add |
| 4SC1 | Science (Double) | ➕ Add |

---

## 📁 Folder Structure

```
data/raw/IGCSE/
├── 4PH1/                    ← Physics (exists)
│   ├── 2019/
│   │   ├── Jun/
│   │   │   ├── 4PH1_1P.pdf
│   │   │   └── 4PH1_1P_MS.pdf
│   │   └── Jan/
│   │       └── ...
│   └── 2020/
│       └── ...
│
├── 4CH1/                    ← Chemistry (add new)
│   ├── 2019/
│   │   └── Jun/
│   │       ├── 4CH1_1P.pdf
│   │       └── 4CH1_1P_MS.pdf
│   └── 2020/
│       └── ...
│
└── 4MA1/                    ← Maths (add new)
    └── 2019/
        └── Jun/
            ├── 4MA1_1F.pdf    ← Foundation
            ├── 4MA1_1F_MS.pdf
            ├── 4MA1_1H.pdf    ← Higher
            └── 4MA1_1H_MS.pdf
```

---

## ⚠️ Common Issues

| Issue | Solution |
|-------|----------|
| "Subject not found" | Add subject to database first |
| "Invalid API key" | Check `.env.ingest` has correct keys |
| "Classification failed" | Ensure `config/{subject}_topics.yaml` exists |
| PDFs not uploading | Check Supabase Storage bucket is public |

---

## 🔍 Check Commands

```powershell
# Check database status
python scripts/check_database.py

# List storage files
python scripts/list_storage.py
```

---

## 📚 Full Documentation

See: `HOW_TO_ADD_PAPERS_AND_SUBJECTS.md`
