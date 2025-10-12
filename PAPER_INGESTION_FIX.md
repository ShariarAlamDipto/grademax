# 🔧 Paper Ingestion Fix - Environment Loading

## ❌ Problem

When running the paper ingestion script, you got an error:
```
Exception: Select failed: 401 - {"message":"Invalid API key"}
```

Then after that was fixed:
```
Exception: Subject 4PH1 not found in database
```

---

## ✅ Fixes Applied

### Fix 1: Load Correct Environment File

**Problem**: Scripts were calling `load_dotenv()` which loads `.env` by default, but your keys are in `.env.ingest`.

**Solution**: Updated all Python scripts to explicitly load `.env.ingest`:

```python
# OLD (wrong):
load_dotenv()

# NEW (correct):
load_dotenv('.env.ingest')
```

**Files Updated**:
1. ✅ `scripts/page_based_ingest.py`
2. ✅ `scripts/bulk_ingest.py`
3. ✅ `scripts/complete_pipeline.py`
4. ✅ `scripts/list_storage.py`

---

### Fix 2: Query Filter Handling

**Problem**: The `SupabaseClient.select()` method was adding `eq.` prefix twice when filters already included operators.

**Before**:
```python
# Filter: {'code': 'eq.4PH1'}
# Generated URL: &code=eq.eq.4PH1  ❌ (double eq.)
```

**After**:
```python
# Filter: {'code': 'eq.4PH1'}
# Generated URL: &code=eq.4PH1  ✅ (correct)
```

**Solution**: Updated `scripts/supabase_client.py` to check if operator is already present:

```python
# Check if value already has operator (eq., neq., gt., etc.)
if isinstance(value, str) and any(op in value for op in ['eq.', 'neq.', 'gt.', ...]):
    # Value already has operator, use as-is
    url += f"&{key}={value}"
else:
    # No operator, add eq.
    url += f"&{key}=eq.{value}"
```

---

## 🚀 How to Run Now

### Correct Command Format:

```powershell
python scripts/page_based_ingest.py "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf" "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf"
```

**Important**: Use the full path to the PDF files, not just "QP.pdf" and "MS.pdf"

---

## 📁 Your PDF Files

You have papers in:
```
c:\Users\shari\grademax\data\raw\IGCSE\4PH1\2019\Jun\
├── 4PH1_1P.pdf    (Question Paper)
└── 4PH1_1P_MS.pdf (Mark Scheme)
```

---

## ✅ What Should Happen Now

When you run the command:

```
======================================================================
📋 Processing: 2019_Jun_1P
======================================================================

1️⃣  Creating paper record...
   ✅ Paper created: [UUID]

2️⃣  Splitting QP into pages...
   ✅ Split into N questions

3️⃣  Extracting mark schemes...
   ✅ Q1 MS extracted
   ✅ Q2 MS extracted
   ...

4️⃣  Classifying and uploading pages...
   ✅ [1/N] Q1: Topic 1 (Forces) | medium | conf: 0.92
   ✅ [2/N] Q2: Topic 2 (Electricity) | easy | conf: 0.88
   ...

✅ Processing complete!
```

---

## 🧪 Test the Fixes

### Test 1: Check Environment Loading
```powershell
python -c "from dotenv import load_dotenv; import os; load_dotenv('.env.ingest'); print('SUPABASE_URL:', os.getenv('SUPABASE_URL')[:30]); print('GEMINI_API_KEY:', os.getenv('GEMINI_API_KEY')[:20])"
```

Expected output:
```
SUPABASE_URL: https://tybaetnvnfgniotdfxze
GEMINI_API_KEY: AIzaSyBsqRLYDl7Isdbo
```

### Test 2: Check Database Connection
```powershell
python scripts/check_database.py
```

Expected output:
```
✅ Found 1 subject(s):
   - 4PH1: Physics
✅ Found 8 topic(s):
   - Topic ?: Forces and motion
   ...
```

### Test 3: Run Paper Ingestion
```powershell
python scripts/page_based_ingest.py "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf" "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf"
```

---

## 🔍 If You Still Get Errors

### Error: "Invalid API key"
**Check**: Environment variables loaded
```powershell
python -c "from dotenv import load_dotenv; import os; load_dotenv('.env.ingest'); print(os.getenv('SUPABASE_SERVICE_ROLE')[:30])"
```

### Error: "Subject not found"
**Check**: Database has the subject
```powershell
python scripts/check_database.py
```

If no subjects, you need to run database migrations first.

### Error: "File not found"
**Check**: PDF paths are correct
```powershell
ls data/raw/IGCSE/4PH1/2019/Jun/
```

---

## 📋 Summary of Changes

| File | Change | Status |
|------|--------|--------|
| `page_based_ingest.py` | Load `.env.ingest` | ✅ Fixed |
| `bulk_ingest.py` | Load `.env.ingest` | ✅ Fixed |
| `complete_pipeline.py` | Load `.env.ingest` | ✅ Fixed |
| `list_storage.py` | Load `.env.ingest` | ✅ Fixed |
| `supabase_client.py` | Fix double `eq.` in filters | ✅ Fixed |

---

## 🎯 Next Action

Try running the ingestion command now:

```powershell
python scripts/page_based_ingest.py "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf" "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf"
```

**This should work now!** 🚀
