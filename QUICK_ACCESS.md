# 🎯 Quick Access Guide - Worksheet Generator

## ✅ Fixed!

The navbar now correctly links to your worksheet generator.

---

## 🚀 How to Access (3 Ways)

### 1️⃣ Via Navbar (Easiest)
```
1. Run: npm run dev
2. Open: http://localhost:3000
3. Click: "Generate Worksheets" in the top navigation
```

### 2️⃣ Direct URL
```
http://localhost:3000/generate
```

### 3️⃣ From Home Page
```
1. Visit: http://localhost:3000
2. Look for any "Generate" or "Worksheets" links
3. Or use the navbar
```

---

## 📍 What Changed

**Navbar Link Updated:**
- ❌ Old: `/worksheets` (page deleted)
- ✅ New: `/generate` (active worksheet generator)

---

## 🎨 What You'll See

### Worksheet Generator Features:

**Topic Selection** (Choose 1 or more)
- 🚗 Forces and motion
- ⚡ Electricity  
- 🌊 Waves
- 🔋 Energy resources
- 💧 Solids, liquids and gases
- 🧲 Magnetism and electromagnetism
- ☢️ Radioactivity and particles
- 🌌 Astrophysics

**Filters**
- Year Range: 2017-2025
- Difficulty: Easy/Medium/Hard
- Question Limit: 1-100
- Shuffle: Randomize order

**Actions**
1. Select topics → Set filters → Generate
2. Preview questions
3. Download PDFs (Worksheet + Markscheme)

---

## ⚠️ Important: Database Setup Required

Before the generator will return questions, you need to:

### Step 1: Run Migrations (5 minutes)
```sql
-- In Supabase SQL Editor:
1. Run: supabase/migrations/01_cleanup_old_data.sql
2. Run: supabase/migrations/00_clean_schema.sql
```

### Step 2: Process Papers (per paper: ~2 minutes)
```bash
python scripts/page_based_ingest.py "data/raw/.../QP.pdf" "data/raw/.../MS.pdf"
```

**Until you do this**, the generator will show:
```
⚠️ No questions found matching your criteria
```

This is normal - the database is empty until you migrate and process papers.

---

## 🧪 Quick Test

### 1. Start Server
```bash
npm run dev
```

### 2. Navigate
- Click **"Generate Worksheets"** in navbar
- Should see the generator UI

### 3. Try It (After Migrations)
1. Select "Forces and motion"
2. Click "Generate Worksheet"
3. Should see questions (if database populated)
4. Click "Download PDFs"
5. Should download Worksheet.pdf + Markscheme.pdf

---

## ✅ Checklist

- [x] Navbar link updated
- [x] Generate page exists
- [x] API endpoints ready
- [ ] Database migrations run (you need to do this)
- [ ] Papers processed (you need to do this)

---

## 🎉 You're All Set!

**Access the generator at:** http://localhost:3000/generate

Just remember to run migrations and process papers before expecting results!

---

## 📚 Need Help?

- **Migration steps**: See `MIGRATION_GUIDE.md`
- **Processing papers**: See `CLASSIFICATION_UPGRADE_COMPLETE.md`
- **System overview**: See `FINAL_STATUS.md`

**Happy worksheet generating!** 🚀
