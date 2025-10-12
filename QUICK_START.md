# 🚀 QUICK START GUIDE

## ✅ System Status: READY

All connections tested and working:
- ✅ REST API
- ✅ PostgreSQL (IPv4 pooler)
- ✅ Gemini AI

---

## 📝 What Changed

### PostgreSQL Connection FIXED:
```bash
# OLD (broken - IPv6 only):
db.tybaetnvnfgniotdfxze.supabase.co

# NEW (working - IPv4 proxy):
aws-1-ap-southeast-1.pooler.supabase.com:6543
```

---

## 🏃 Quick Commands

### Process a Paper:
```powershell
python scripts/page_based_ingest.py "path/to/QP.pdf" "path/to/MS.pdf"
```

### Start Frontend:
```powershell
npm run dev
```

### Test Connections:
```powershell
python scripts/test_db_connection.py
```

### Check Database:
```powershell
python scripts/check_database.py
```

---

## 📊 Database Access

### REST API (SupabaseClient):
```python
from scripts.supabase_client import SupabaseClient
db = SupabaseClient()
subjects = db.select('subjects', '*')
```

### PostgreSQL Direct:
```python
import psycopg2
import os
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
```

---

## 🔑 Environment Files

### `.env.ingest`:
- SUPABASE_URL ✅
- SUPABASE_SERVICE_ROLE ✅
- DATABASE_URL ✅ (IPv4 pooler)
- GEMINI_API_KEY ✅

### `.env.local`:
- NEXT_PUBLIC_SUPABASE_URL ✅
- NEXT_PUBLIC_SUPABASE_ANON_KEY ✅

---

## 📚 Documentation

| File | What It Covers |
|------|---------------|
| `ALL_SYSTEMS_OPERATIONAL.md` | Complete status |
| `POSTGRESQL_SUCCESS.md` | PostgreSQL fix details |
| `KEYS_CONFIGURED_SUMMARY.md` | All API keys |
| `READY_TO_PROCESS.md` | Getting started |

---

## 🎯 Next Action

**Process your first paper:**

```powershell
python scripts/page_based_ingest.py "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf" "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf"
```

Then:
```powershell
npm run dev
```

Visit: **http://localhost:3000/generate**

---

**Everything is ready! Go build something amazing!** 🎓✨
