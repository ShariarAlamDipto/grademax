# 🔧 Navigation Fix - Worksheet Generator Access

## ✅ Issue Fixed!

**Problem**: The navbar was pointing to `/worksheets` (deleted), but the new worksheet generator is at `/generate`.

**Solution**: Updated navbar link to point to the correct page.

---

## 🔗 How to Access Worksheet Generator

### Option 1: Use the Navigation Menu
1. Start your dev server: `npm run dev`
2. Visit: http://localhost:3000
3. Click **"Generate Worksheets"** in the navbar

### Option 2: Direct URL
Visit: **http://localhost:3000/generate**

---

## 🎨 What You'll See

The worksheet generator page includes:

### Topic Selection
Choose from 8 IGCSE Physics topics:
- 🚗 Forces and motion
- ⚡ Electricity
- 🌊 Waves
- 🔋 Energy resources
- 💧 Solids, liquids and gases
- 🧲 Magnetism and electromagnetism
- ☢️ Radioactivity and particles
- 🌌 Astrophysics

### Filters
- **Year Range**: 2017-2025 (adjustable)
- **Difficulty**: Easy, Medium, Hard (optional)
- **Question Limit**: How many questions (default: 20)
- **Shuffle**: Randomize question order

### Workflow
1. **Select Topics** - Click on topic cards
2. **Set Filters** - Adjust year range, difficulty, limit
3. **Click "Generate Worksheet"** - System queries database
4. **View Questions** - Preview the selected questions
5. **Click "Download PDFs"** - Get Worksheet.pdf + Markscheme.pdf

---

## 📝 Changes Made

### Updated File: `src/components/Navbar.tsx`

**Before:**
```tsx
<li><Link href="/worksheets" className="gradient-hover-sea">Worksheets</Link></li>
```

**After:**
```tsx
<li><Link href="/generate" className="gradient-hover-sea">Generate Worksheets</Link></li>
```

---

## ✅ Verification

Run your dev server and test:

```bash
npm run dev
```

Then:
1. ✅ Click "Generate Worksheets" in navbar
2. ✅ Should navigate to `/generate`
3. ✅ Should see the topic-based worksheet generator UI

---

## 🎯 Important Notes

### Before You Can Use It

You need to:
1. **Run database migrations** (creates the new schema)
2. **Process at least one paper** (populates the database)

### Database Migrations
```sql
-- In Supabase SQL Editor:
-- 1. Run: supabase/migrations/01_cleanup_old_data.sql
-- 2. Run: supabase/migrations/00_clean_schema.sql
```

### Process First Paper
```bash
python scripts/page_based_ingest.py "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf" "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf"
```

**Until you do these steps**, the generator will work but return "No questions found" because the database is empty.

---

## 🚀 Quick Start Guide

### 1. Start Dev Server
```bash
npm run dev
```

### 2. Access Generator
- Visit: http://localhost:3000
- Click: **"Generate Worksheets"** in navbar
- Or go directly to: http://localhost:3000/generate

### 3. After Migrations (If Not Done Yet)
If you see "No questions found":
1. Run database migrations in Supabase
2. Process a test paper with the ingestion script
3. Refresh the page and try again

---

## 📊 Page Features

### Topic Cards
- Click to select/deselect topics
- Selected topics are highlighted
- Multiple topics can be selected
- Questions matching ANY selected topic will be included

### Year Range Sliders
- **Start Year**: Minimum year (default: 2017)
- **End Year**: Maximum year (default: 2025)
- Only questions from these years will be included

### Difficulty Dropdown
- **All difficulties** (default)
- **Easy**: Basic recall, simple calculations
- **Medium**: Multi-step problems, application
- **Hard**: Complex synthesis, advanced

### Question Limit
- Default: 20 questions
- Adjustable: 1-100
- Limits how many questions are returned

### Shuffle Option
- **Off** (default): Questions in database order
- **On**: Randomizes question order

### Generate Button
- Queries database with your filters
- Shows loading spinner
- Displays matching questions

### Question Preview
- Shows all matched questions
- Displays:
  - Question number
  - Year, season, paper
  - Topics covered
  - Difficulty level
  - Has diagram indicator

### Download PDFs Button
- Appears after generation
- Triggers PDF merger service
- Downloads:
  - **Worksheet.pdf**: All question pages
  - **Markscheme.pdf**: All mark scheme pages

---

## 🎨 UI Preview

```
┌─────────────────────────────────────────────────┐
│  🎯 Generate Custom Physics Worksheet          │
│                                                  │
│  Select Topics:                                 │
│  ┌────────┐ ┌────────┐ ┌────────┐              │
│  │ 🚗     │ │ ⚡     │ │ 🌊     │              │
│  │ Forces │ │Electri-│ │ Waves  │   ...        │
│  └────────┘ └────────┘ └────────┘              │
│                                                  │
│  Year Range: [2017] ──── [2025]                │
│                                                  │
│  Difficulty: [All ▼]  Questions: [20]          │
│                                                  │
│  [ ] Shuffle questions                          │
│                                                  │
│  [🎯 Generate Worksheet]                        │
│                                                  │
│  ┌─────────────────────────────────────────┐   │
│  │ Questions (15 found):                    │   │
│  │                                           │   │
│  │ ┌───────────────────────────────────┐   │   │
│  │ │ 1  Question 1                      │   │   │
│  │ │    2019 Jun • Paper 1P             │   │   │
│  │ │    Topic 1  Medium  📊 Diagram     │   │   │
│  │ └───────────────────────────────────┘   │   │
│  │                                           │   │
│  │ [...more questions...]                   │   │
│  │                                           │   │
│  │ [📥 Download Worksheet + Markscheme PDFs]│   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

---

## ✅ Status

- ✅ Navigation link updated
- ✅ Generate page exists and working
- ✅ API endpoints ready
- ✅ Database schema ready (needs migration)
- ✅ Processing pipeline ready

**Next Step**: Run database migrations and process papers to populate the database!

---

## 🔗 Related Documentation

- `MIGRATION_GUIDE.md` - How to run database migrations
- `CLASSIFICATION_UPGRADE_COMPLETE.md` - Enhanced classifier details
- `FINAL_STATUS.md` - Complete system status

---

**You can now access the worksheet generator at http://localhost:3000/generate!** 🎉
