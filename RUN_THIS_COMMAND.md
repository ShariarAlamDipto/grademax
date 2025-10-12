# 🚀 Quick Command Reference

## ✅ Fixed and Ready to Run

### Process Paper (CORRECT COMMAND):
```powershell
python scripts/page_based_ingest.py "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf" "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf"
```

---

## 🔧 What Was Fixed

1. ✅ Scripts now load `.env.ingest` (not `.env`)
2. ✅ Query filters handle `eq.` prefix correctly
3. ✅ All environment variables accessible

---

## 📋 Files You Have

```
data/raw/IGCSE/4PH1/2019/Jun/
├── 4PH1_1P.pdf       ← Question Paper
└── 4PH1_1P_MS.pdf    ← Mark Scheme
```

---

## ⚠️ Common Mistakes

### ❌ Wrong:
```powershell
python scripts/page_based_ingest.py "QP.pdf" "MS.pdf"
```
**Problem**: Files don't exist in current directory

### ✅ Correct:
```powershell
python scripts/page_based_ingest.py "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf" "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf"
```
**Solution**: Use full path to files

---

## 🧪 Test Commands

```powershell
# 1. Check database
python scripts/check_database.py

# 2. Test connections
python scripts/test_db_connection.py

# 3. Process paper
python scripts/page_based_ingest.py "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf" "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf"

# 4. Start frontend
npm run dev
```

---

**Ready to go! Run the paper processing command above.** 🎓
