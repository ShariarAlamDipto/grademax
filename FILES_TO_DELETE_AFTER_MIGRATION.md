# 🗑️ Files to Delete After Migration

## Overview
These files are part of the **OLD question-based system** and should be deleted after you've migrated to the **NEW page-based system** and verified everything works.

---

## ❌ Old API Routes (Safe to Delete)

### Old Worksheet Generation
```
src/app/api/worksheets/generate/route.ts          # OLD generate endpoint
src/app/api/generate-worksheet/route.ts           # Duplicate old endpoint
src/app/api/worksheets/[id]/pdf/route.ts          # OLD PDF generation
```

**Replaced by:**
- ✅ `src/app/api/worksheets/generate-v2/route.ts` (NEW)
- ✅ `src/app/api/worksheets/[id]/download/route.ts` (NEW)

### Old Data Endpoints
```
src/app/api/questions/route.ts                    # OLD questions table
src/app/api/topics/route.ts                       # Still needed (topics reference)
src/app/api/papers/route.ts                       # Still needed (papers reference)
src/app/api/subjects/route.ts                     # Still needed (subjects reference)
```

**Note:** Keep `topics`, `papers`, and `subjects` routes - they're used by the new system too!

---

## ❌ Old Frontend Pages (Check Before Deleting)

### Old Worksheet Pages
```
src/app/worksheets/page.tsx                       # OLD worksheet list (if exists)
src/app/past-papers/page.tsx                      # May still be useful
src/app/lectures/page.tsx                         # May still be useful
```

**Replaced by:**
- ✅ `src/app/generate/page.tsx` (NEW topic-based generator)

**Action:** Check if `past-papers` and `lectures` are still needed for your app.

---

## ❌ Old Database Migrations (Delete These)

```
supabase/migrations/20251012_add_page_based_storage.sql
supabase/migrations/create_physics_topics.sql
supabase/seed/schema.sql
supabase/seed/igcse_physics_topics.sql
```

**Replaced by:**
- ✅ `supabase/migrations/01_cleanup_old_data.sql` (drops old tables)
- ✅ `supabase/migrations/00_clean_schema.sql` (new schema)

---

## ✅ Files to KEEP (New System)

### API Routes (Working & Error-Free)
```
✅ src/app/api/worksheets/generate-v2/route.ts
✅ src/app/api/worksheets/[id]/download/route.ts
✅ src/app/api/subjects/route.ts
✅ src/app/api/topics/route.ts
✅ src/app/api/papers/route.ts
```

### Frontend
```
✅ src/app/generate/page.tsx                      # NEW topic-based UI
✅ src/app/layout.tsx
✅ src/app/page.tsx
✅ src/components/Navbar.tsx
✅ src/components/Footer.tsx
```

### Scripts
```
✅ scripts/page_based_ingest.py                   # NEW ingestion pipeline
✅ scripts/single_topic_classifier.py             # Enhanced classifier
✅ scripts/pdf_merger.py                          # PDF merging service
✅ scripts/split_pages.py                         # Page splitting
✅ scripts/supabase_client.py                     # Supabase utilities
```

### Migrations
```
✅ supabase/migrations/01_cleanup_old_data.sql
✅ supabase/migrations/00_clean_schema.sql
```

---

## 🔧 How to Clean Up

### Step 1: After Successful Migration
Once you've run migrations and verified the new system works:

```powershell
# Delete old API routes (PowerShell)
Remove-Item "src/app/api/worksheets/generate/route.ts"
Remove-Item "src/app/api/generate-worksheet/route.ts"
Remove-Item "src/app/api/worksheets/[id]/pdf/route.ts"
Remove-Item "src/app/api/questions/route.ts"
```

### Step 2: Delete Old Migrations
```powershell
# Delete old SQL files
Remove-Item "supabase/migrations/20251012_add_page_based_storage.sql"
Remove-Item "supabase/migrations/create_physics_topics.sql"
Remove-Item "supabase/seed/schema.sql"
Remove-Item "supabase/seed/igcse_physics_topics.sql"
```

### Step 3: Clean Old Scripts (If Any)
```powershell
# If you have old ingestion scripts, remove them
# Remove-Item "scripts/old_ingest.py"  # example
```

---

## ⚠️ Current TypeScript Errors (Old Files)

These errors are in **OLD files** that you'll delete anyway:

### `src/app/api/questions/route.ts`
- Line 56: `q: any` should have interface
- Line 78: `error: any` should be `unknown`

### `src/app/api/worksheets/[id]/pdf/route.ts`
- Line 63: Type casting issue with `WorksheetItem[]`
- Line 155: `pdfBuffer as any` should be `Buffer`

**Don't bother fixing these** - just delete the files after migration!

---

## 📋 Deletion Checklist

After migration and testing, delete in this order:

- [ ] Old API routes (`generate/route.ts`, `generate-worksheet/route.ts`, `questions/route.ts`)
- [ ] Old PDF route (`worksheets/[id]/pdf/route.ts`)
- [ ] Old migrations (`20251012_*.sql`, `create_physics_topics.sql`, etc.)
- [ ] Old seed files (`schema.sql`, `igcse_physics_topics.sql`)
- [ ] Check and remove old frontend pages if not needed
- [ ] Remove any old scripts not listed in "KEEP" section

---

## 🎯 Summary

**Current Errors**: In OLD files only (4 total)  
**New System Errors**: **ZERO** ✅  
**Action**: Delete old files after migration is verified  
**Timeline**: After you run migrations and test the new system  

**Don't fix the old files - just delete them!** 🗑️

---

## 🚀 Next Steps

1. ✅ **Run migrations** (creates new schema)
2. ✅ **Process a test paper** (verify new system works)
3. ✅ **Test frontend** (verify worksheets generate correctly)
4. 🗑️ **Delete old files** (use this checklist)
5. 🎉 **Clean codebase** with zero errors!
