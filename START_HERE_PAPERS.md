# 🎯 START HERE: Adding Papers & Subjects

## 📚 What You Need to Know

You currently have:
- ✅ **Physics (4PH1)** - 1 paper processed (2019 Jun 1P)
- ✅ **8 Physics topics** configured
- ✅ **System ready** for more papers

---

## 🚀 Two Scenarios

### Scenario 1: Adding More Physics Papers ⚡ (Easy - 5 minutes)
**You just need more papers for Physics**

### Scenario 2: Adding New Subjects 🆕 (Moderate - 15 minutes)  
**You want to add Chemistry, Maths, Biology, etc.**

---

## ⚡ Scenario 1: More Physics Papers

### What You Do:

1. **Organize your PDFs like this:**
   ```
   data/raw/IGCSE/4PH1/2020/Jun/
   ├── 4PH1_1P.pdf       ← Question Paper
   └── 4PH1_1P_MS.pdf    ← Mark Scheme
   ```

2. **Run this command:**
   ```powershell
   python scripts/page_based_ingest.py "data/raw/IGCSE/4PH1/2020/Jun/4PH1_1P.pdf" "data/raw/IGCSE/4PH1/2020/Jun/4PH1_1P_MS.pdf"
   ```

3. **Wait ~2 minutes** (processes each question with AI)

4. **Done!** ✅

**Example Structure:**
```
data/raw/IGCSE/4PH1/
├── 2019/Jun/  ✅ Already done
├── 2019/Jan/  ⬅️ Add this
├── 2020/Jun/  ⬅️ Add this
├── 2020/Jan/  ⬅️ Add this
└── 2021/Jun/  ⬅️ Add this
```

---

## 🆕 Scenario 2: Adding New Subject (e.g., Chemistry)

### What You Do:

#### Step 1: Add Subject to Database (2 minutes)
```powershell
# Use the helper script
python scripts/add_subject.py chemistry
```

This adds:
- ✅ Chemistry subject (code: 4CH1)
- ✅ 5 Chemistry topics
- ✅ Database records

#### Step 2: Create Config Files (5 minutes)

**A. Copy topic config:**
```powershell
Copy-Item "config\physics_topics.yaml" "config\chemistry_topics.yaml"
```

**B. Edit `config/chemistry_topics.yaml`:**
- Replace Physics topics with Chemistry topics
- See `HOW_TO_ADD_PAPERS_AND_SUBJECTS.md` for examples

**C. Create ingestion script:**
```powershell
Copy-Item "scripts\page_based_ingest.py" "scripts\chemistry_ingest.py"
```

**D. Edit `scripts/chemistry_ingest.py`:**
- Line 102: `config_path: str = "config/chemistry_topics.yaml"`
- Line 108: `self.subject_code = "4CH1"`
- Line 109: `self.subject_name = "Chemistry"`

#### Step 3: Add Chemistry Papers (5 minutes)

**Organize PDFs:**
```
data/raw/IGCSE/4CH1/2019/Jun/
├── 4CH1_1P.pdf
└── 4CH1_1P_MS.pdf
```

**Run script:**
```powershell
python scripts/chemistry_ingest.py "data/raw/IGCSE/4CH1/2019/Jun/4CH1_1P.pdf" "data/raw/IGCSE/4CH1/2019/Jun/4CH1_1P_MS.pdf"
```

#### Step 4: Verify
```powershell
python scripts/check_database.py
```

**Done!** ✅

---

## 📋 File Naming Rules (IMPORTANT!)

### Folder Structure:
```
data/raw/IGCSE/{SUBJECT_CODE}/{YEAR}/{SEASON}/
```

### File Names:
```
Question Paper:  {CODE}_{PAPER}.pdf
Mark Scheme:     {CODE}_{PAPER}_MS.pdf

Examples:
- 4PH1_1P.pdf        (Physics Paper 1)
- 4PH1_1P_MS.pdf     (Physics Paper 1 Mark Scheme)
- 4CH1_1P.pdf        (Chemistry Paper 1)
- 4MA1_1F.pdf        (Maths Paper 1 Foundation)
- 4MA1_1H_MS.pdf     (Maths Paper 1 Higher Mark Scheme)
```

---

## 🎓 Subject Codes

| Code | Subject | Command to Add |
|------|---------|----------------|
| 4PH1 | Physics | ✅ Already have |
| 4CH1 | Chemistry | `python scripts/add_subject.py chemistry` |
| 4BI1 | Biology | `python scripts/add_subject.py biology` |
| 4MA1 | Maths | `python scripts/add_subject.py maths` |

---

## 📁 Examples

### Adding 2020 Jun Physics Paper:
```powershell
# 1. Create folder
New-Item -ItemType Directory -Force -Path "data\raw\IGCSE\4PH1\2020\Jun"

# 2. Put PDFs in that folder:
#    - 4PH1_1P.pdf
#    - 4PH1_1P_MS.pdf

# 3. Run
python scripts/page_based_ingest.py "data/raw/IGCSE/4PH1/2020/Jun/4PH1_1P.pdf" "data/raw/IGCSE/4PH1/2020/Jun/4PH1_1P_MS.pdf"
```

### Adding Chemistry (First Time):
```powershell
# 1. Add to database
python scripts/add_subject.py chemistry

# 2. Setup config files (see Step 2 above)

# 3. Create folder
New-Item -ItemType Directory -Force -Path "data\raw\IGCSE\4CH1\2019\Jun"

# 4. Put PDFs in that folder:
#    - 4CH1_1P.pdf
#    - 4CH1_1P_MS.pdf

# 5. Run
python scripts/chemistry_ingest.py "data/raw/IGCSE/4CH1/2019/Jun/4CH1_1P.pdf" "data/raw/IGCSE/4CH1/2019/Jun/4CH1_1P_MS.pdf"
```

---

## ✅ Checklist

### For Each Paper:
- [ ] PDFs downloaded
- [ ] PDFs renamed correctly (`{CODE}_{PAPER}.pdf`)
- [ ] Folder created: `data/raw/IGCSE/{CODE}/{YEAR}/{SEASON}/`
- [ ] PDFs placed in folder
- [ ] Subject exists in database (check with `python scripts/check_database.py`)
- [ ] Topics configured for subject
- [ ] Run ingestion script
- [ ] Verify with `python scripts/check_database.py`

---

## 🆘 Common Issues

| Issue | Fix |
|-------|-----|
| "Subject not found" | Add subject to database first (`add_subject.py`) |
| "Invalid API key" | Check `.env.ingest` has correct keys |
| "No such file" | Check PDF path and filename exactly |
| "Classification failed" | Ensure config YAML file exists |

---

## 📖 Full Documentation

1. **START HERE** ← You are here!
2. **Quick Reference:** `QUICK_REFERENCE_PAPERS.md`
3. **Visual Guide:** `VISUAL_GUIDE_PAPERS.md`
4. **Complete Guide:** `HOW_TO_ADD_PAPERS_AND_SUBJECTS.md`

---

## 🎯 What Do You Want to Do?

### Option A: Add more Physics papers
→ Go to **Scenario 1** above

### Option B: Add Chemistry
→ Run: `python scripts/add_subject.py chemistry`
→ Then follow **Scenario 2** above

### Option C: Add Biology
→ Run: `python scripts/add_subject.py biology`
→ Then follow **Scenario 2** above

### Option D: Add Maths
→ Run: `python scripts/add_subject.py maths`
→ Then follow **Scenario 2** above

### Option E: See all available subjects
→ Run: `python scripts/add_subject.py list`

---

## ⚡ Quick Commands

```powershell
# Check what's in database
python scripts/check_database.py

# Add a new subject
python scripts/add_subject.py chemistry

# List available subjects to add
python scripts/add_subject.py list

# Process a Physics paper
python scripts/page_based_ingest.py "path/to/QP.pdf" "path/to/MS.pdf"

# Process a Chemistry paper (after setup)
python scripts/chemistry_ingest.py "path/to/QP.pdf" "path/to/MS.pdf"
```

---

**Ready to start? Pick your scenario above!** 🚀
