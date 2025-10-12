# 🗄️ Database Migration Guide

## 📋 Current Situation

You have **old schema** with multiple scattered SQL files. We need a **clean start** for the new page-based architecture.

---

## 📁 SQL Files - What to Do

### ✅ KEEP (New System)
```
supabase/migrations/
  ├── 01_cleanup_old_data.sql       ✅ NEW - Drops old tables
  └── 00_clean_schema.sql           ✅ NEW - Creates new schema
```

### ❌ DELETE or IGNORE (Old System)
```
supabase/migrations/
  ├── 20251012_add_page_based_storage.sql  ❌ OLD - Not needed
  └── create_physics_topics.sql            ❌ OLD - Not needed

supabase/seed/
  ├── schema.sql                           ❌ OLD - Replaced by 00_clean_schema.sql
  └── igcse_physics_topics.sql             ❌ OLD - Topics now in 00_clean_schema.sql
```

**Action**: You can delete these old files OR just ignore them. The new migrations are self-contained.

---

## 🪣 Storage Bucket - What to Do

### Current Bucket: `question-pdfs`

**Status**: Can be REUSED with new structure

### OLD Structure (from previous system)
```
question-pdfs/
  ├── papers/2019_Jun_1P/Q3.pdf
  ├── 2019/Jun/1P/Q2.pdf
  └── topics/1/Q2.pdf
```

### NEW Structure (page-based system)
```
question-pdfs/
  ├── subjects/
  │   └── Physics/
  │       └── pages/
  │           ├── 2019_Jun_1P/
  │           │   ├── q1.pdf
  │           │   ├── q1_ms.pdf
  │           │   ├── q2.pdf
  │           │   └── q2_ms.pdf
  │           └── 2020_Oct_2P/
  │               ├── q1.pdf
  │               └── q1_ms.pdf
  └── generated/
      └── worksheets/
          ├── {uuid}_worksheet.pdf
          └── {uuid}_markscheme.pdf
```

### 🎯 Recommendation: CLEAR OLD FILES

**Option A: Keep everything (coexist)**
- Old files stay at old paths
- New files go to new paths
- No conflicts
- Pro: No data loss
- Con: Cluttered storage

**Option B: Clear old files (fresh start)** ⭐ RECOMMENDED
1. Go to Supabase Dashboard
2. Storage → `question-pdfs`
3. Select all files → Delete
4. Start fresh with new structure
5. Pro: Clean, organized
6. Con: Need to re-process papers

---

## 🚀 Migration Steps

### Step 1: Backup Current Data (Optional)
```sql
-- Export questions if you want to keep them
SELECT * FROM questions;
-- Save result to CSV
```

### Step 2: Run Cleanup Migration
In Supabase SQL Editor:
```sql
-- Run: supabase/migrations/01_cleanup_old_data.sql
```

This will:
- ✅ Drop all old tables
- ✅ Clear old constraints
- ✅ Prepare for new schema
- ⚠️ Note: Storage bucket untouched (you decide later)

### Step 3: Run New Schema
In Supabase SQL Editor:
```sql
-- Run: supabase/migrations/00_clean_schema.sql
```

This will:
- ✅ Create `subjects`, `topics`, `papers`, `pages` tables
- ✅ Create `worksheets`, `worksheet_items` tables
- ✅ Add GIN indexes for fast queries
- ✅ Seed 8 IGCSE Physics topics
- ✅ Set up RLS policies

### Step 4: Clear Storage (Optional but Recommended)
In Supabase Dashboard:
1. Go to **Storage** → `question-pdfs`
2. Select all files
3. Click **Delete**
4. Confirm

### Step 5: Verify Migration
```sql
-- Check tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Should see:
-- pages
-- papers
-- subjects
-- topics
-- worksheet_items
-- worksheets

-- Check topics seeded
SELECT code, name FROM topics ORDER BY code;

-- Should see 8 topics:
-- 1 | Forces and motion
-- 2 | Electricity
-- ...
```

### Step 6: Process Papers
```powershell
# Process your papers with new pipeline
python scripts/page_based_ingest.py `
  "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf" `
  "data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf"
```

---

## 📊 Migration Checklist

### Before Migration
- [ ] Export current data (if needed)
- [ ] Note how many questions you have
- [ ] Check storage usage
- [ ] Backup `.env` file

### During Migration
- [ ] Run `01_cleanup_old_data.sql`
- [ ] Verify tables dropped
- [ ] Run `00_clean_schema.sql`
- [ ] Verify new tables created
- [ ] Check topics seeded (should be 8)
- [ ] Verify indexes created

### After Migration
- [ ] Clear storage bucket (optional)
- [ ] Process papers with new pipeline
- [ ] Verify pages table populated
- [ ] Check storage structure correct
- [ ] Test frontend at `/generate`
- [ ] Generate test worksheet
- [ ] Download PDFs successfully

---

## 🔧 Storage Bucket Configuration

### Bucket Settings
```
Name: question-pdfs
Public: ✅ Yes (for public downloads)
File Size Limit: 50 MB (per file)
Allowed MIME Types: application/pdf
```

### RLS Policies Needed
```sql
-- Allow public read
CREATE POLICY "Public read access"
ON storage.objects FOR SELECT
USING (bucket_id = 'question-pdfs');

-- Allow authenticated insert (for pipeline)
CREATE POLICY "Authenticated insert"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'question-pdfs' AND auth.role() = 'authenticated');

-- Allow service role all access (for API)
CREATE POLICY "Service role all access"
ON storage.objects FOR ALL
USING (bucket_id = 'question-pdfs' AND auth.role() = 'service_role');
```

These policies should already exist. If not, add them in Supabase Dashboard:
- Storage → `question-pdfs` → Policies

---

## ❓ FAQ

### Q: Do I need to delete old SQL files?
**A**: No, you can keep them for reference. The new migrations are independent.

### Q: Will my old data be lost?
**A**: Yes, if you run the cleanup migration. But you probably want a fresh start with the new architecture.

### Q: Can I migrate old data to new schema?
**A**: Not easily. The schema is fundamentally different (questions → pages, single topic → array). Easier to re-process papers.

### Q: What about the storage bucket?
**A**: You can keep it and reuse it. Old files won't conflict with new structure. But clearing is cleaner.

### Q: How long does re-processing take?
**A**: 1 paper (~10 questions) = ~1 minute. 10 papers = ~15 minutes. Can run overnight for large batches.

### Q: Will the old system still work?
**A**: No, after migration the database schema changes completely. You must use the new system.

---

## 🎯 Recommended Path

**For Clean Start** (Recommended):

1. ✅ Run `01_cleanup_old_data.sql` - drops old tables
2. ✅ Run `00_clean_schema.sql` - creates new schema
3. ✅ Clear storage bucket - removes old files
4. ✅ Process papers - populate new system
5. ✅ Test frontend - verify everything works

**For Keeping Old Data** (Not recommended, but possible):

1. ⚠️ Export old questions to CSV
2. ✅ Run `01_cleanup_old_data.sql`
3. ✅ Run `00_clean_schema.sql`
4. ⚠️ Keep old storage files (won't interfere)
5. ✅ Process papers to new structure
6. ⚠️ Manually map old data if needed

---

## 🚨 Important Notes

### About Storage
- **Bucket name stays the same**: `question-pdfs`
- **URL format changes**: New paths use `subjects/Physics/pages/...`
- **Old files safe**: Won't be overwritten by new system
- **Clearing optional**: But recommended for clean slate

### About Database
- **Complete reset**: Old schema completely replaced
- **No automatic migration**: Must re-process papers
- **New indexes**: Much faster queries with GIN indexes
- **Topics array**: More flexible than old multi-table approach

### About Processing Time
- **Rate limited**: 15 requests/minute (Gemini API)
- **1 paper**: ~1 minute
- **10 papers**: ~15 minutes
- **100 papers**: ~2.5 hours
- **Can run overnight**: No manual intervention needed

---

## ✅ Ready to Migrate!

**Next step**: Run the cleanup migration in Supabase SQL Editor:
```sql
-- Copy and paste: supabase/migrations/01_cleanup_old_data.sql
```

Then run the new schema:
```sql
-- Copy and paste: supabase/migrations/00_clean_schema.sql
```

Then you're ready to process papers! 🚀
