# 🚀 Quick Start - Ingest Papers & Generate Worksheets

## ✅ Status Check

Run this to see current status:
```powershell
node -e "import('./test_questions_count.ts')"
```

**Current Status:**
- ✅ Subjects: 20
- ✅ Topics: 21 (Physics)
- ❌ Papers: 0
- ❌ Questions: 0

**This is why worksheets are empty!**

---

## 📦 What You Need

1. **Past Paper PDFs** - Question Papers (QP) and Mark Schemes (MS)
2. **Organized folder structure**
3. **Run the ingestion script**

---

## 📁 Step 1: Organize Your PDFs

Create this folder structure:

```
c:\Users\shari\grademax\data\
└── raw\
    └── IGCSE\
        └── 4PH1\
            ├── 2023\
            │   └── Jun\
            │       ├── 4PH1_1H.pdf        (Question Paper)
            │       └── 4PH1_1H_MS.pdf     (Mark Scheme)
            ├── 2022\
            │   └── Jun\
            │       ├── 4PH1_1H.pdf
            │       └── 4PH1_1H_MS.pdf
            └── ... (more papers)
```

**Important:**
- Keep year/season folders
- QP and MS should have same name (MS has `_MS` suffix)
- Naming: `4PH1_1H.pdf`, `4PH1_1F.pdf`, etc.

---

## 🚀 Step 2: Run Ingestion

```powershell
# Dry run first (test without saving)
npm run ingest:papers -- --dry-run

# If that works, run for real
npm run ingest:papers
```

**What happens:**
1. Scans `data/raw/` for PDFs
2. Extracts text from PDFs
3. Splits into questions
4. Parses markschemes
5. Links MS to questions
6. Auto-tags topics using AI
7. Calculates difficulty
8. Saves to Supabase database

**Output:**
```
📚 Loading topics...
✅ Loaded 21 topics

📂 Scanning: data/raw/IGCSE/4PH1/
✅ Found 10 paper pairs

[1/10] Processing: 2023 Jun 4PH1_1H.pdf
  ✅ Extracted 15 questions
  ✅ Parsed markscheme
  ✅ Linked 15/15 questions to MS
  ✅ Tagged 45 topic tags
  ✅ Uploaded to Supabase

[2/10] Processing: 2023 Jun 4PH1_1F.pdf
  ✅ Extracted 12 questions
  ...

🎉 Complete! Ingested 10 papers, 141 questions
```

---

## ✅ Step 3: Verify

```powershell
node -e "import('./test_questions_count.ts')"
```

Should now show:
```
✅ Papers: 10
✅ Questions: 141
✅ Topic Tags: 420
```

---

## 🎨 Step 4: Generate Worksheets

1. Go to: http://localhost:3001/worksheets
2. Select "Edexcel IGCSE Physics (4PH1)"
3. Select topics (or leave empty for all)
4. Choose difficulty
5. Click "Generate Worksheet"
6. **Questions appear!** 🎉

---

## 🐛 Troubleshooting

### "No PDFs found"

Check your folder structure:
```powershell
dir data\raw\IGCSE\4PH1\ /s
```

Should show PDF files. If not, create folders and add PDFs.

### "Error: SUPABASE_SERVICE_ROLE not found"

1. Copy `.env.ingest.example` to `.env.ingest`
2. Add your Supabase service role key:
```
SUPABASE_URL=https://tybaetnvnfgniotdfxze.supabase.co
SUPABASE_SERVICE_ROLE=your_service_role_key_here
```

Get service role key from:
- Supabase Dashboard → Settings → API
- Copy "service_role" key (NOT anon key!)

### "Topics not loading"

Make sure you ran the topics SQL:
```powershell
# Should show 21 topics
node -e "import('./test_supabase_connection.ts')"
```

If 0 topics, run `ADD_PHYSICS_TOPICS_ONLY.sql` in Supabase first.

---

## 📊 Expected Timeline

| Papers | Questions | Time | Difficulty |
|--------|-----------|------|------------|
| 1 paper | ~15 questions | 2 min | ⭐ Easy |
| 5 papers | ~75 questions | 10 min | ⭐⭐ Medium |
| 20 papers | ~300 questions | 40 min | ⭐⭐⭐ Advanced |

**Recommendation:** Start with 1-2 papers to test!

---

## 🎯 Alternative: Use Existing Ingestion Script

You already have `ingest/ingest_papers.ts`!

**Quick Commands:**

```powershell
# See help
npm run ingest:papers -- --help

# Dry run (test)
npm run ingest:papers -- --dry-run

# Process all papers in data/raw/
npm run ingest:papers

# Process specific directory
npm run ingest:papers -- --data-dir=./my_papers/
```

---

## ✅ Success Criteria

After ingestion, you should have:

| Item | Before | After |
|------|--------|-------|
| Papers | 0 | 10+ |
| Questions | 0 | 100+ |
| Topic Tags | 0 | 300+ |
| Worksheet Generation | ❌ Empty | ✅ Works! |

---

## 🚀 Next Steps

1. **Get 1-2 test papers** (QP + MS PDFs)
2. **Put in `data/raw/IGCSE/4PH1/2023/Jun/`**
3. **Run**: `npm run ingest:papers -- --dry-run`
4. **Check output** (should show questions extracted)
5. **Run for real**: `npm run ingest:papers`
6. **Verify**: `node -e "import('./test_questions_count.ts')"`
7. **Test worksheets**: http://localhost:3001/worksheets

**Then you're done!** The system will work end-to-end! 🎉

---

## 💡 Where to Get Papers

1. **Your school/college** - Past exam papers
2. **Official exam board** - Edexcel website
3. **Past paper websites** - Many free resources online
4. **Your existing collection** - If you have printed papers, scan them

**Need help finding papers?** Let me know and I can guide you!

---

## 📞 Still Having Issues?

1. Run the diagnostic:
   ```powershell
   node -e "import('./test_questions_count.ts')"
   ```

2. Check you have PDFs:
   ```powershell
   dir data\raw\IGCSE\4PH1\ /s /b | findstr .pdf
   ```

3. Try dry run:
   ```powershell
   npm run ingest:papers -- --dry-run
   ```

4. Check .env.ingest file exists and has credentials

5. Show me the error output!

---

## Summary

**Problem:** No questions → Worksheets empty  
**Solution:** Ingest papers → Questions extracted  
**Result:** Worksheets work! ✨

**Time:** 10-20 minutes for a few papers  
**Complexity:** Easy if PDFs are organized

**Ready to try?** Get some PDFs and run the ingestion! 🚀
