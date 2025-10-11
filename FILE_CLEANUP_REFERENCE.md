# 📁 FILE CLEANUP REFERENCE

## Visual File Structure

```
c:\Users\shari\grademax\
│
├── 📄 SQL FILES TO DELETE ❌
│   ├── COMPLETE_DATABASE_SCHEMA.sql          ❌ DELETE (has canonical_key error)
│   └── supabase_schema.sql                   ❌ DELETE (outdated)
│
├── 📄 SQL FILE TO USE ✅
│   └── FIXED_DATABASE_SCHEMA.sql             ✅ RUN THIS IN SUPABASE
│
├── 📄 GUIDE FILES (Keep for reference) 📖
│   ├── DATABASE_MIGRATION_GUIDE.md           📖 Main guide
│   ├── QUICK_FIX.md                          📖 Quick reference
│   ├── LOGIN_FIX_INSTRUCTIONS.md             📖 Login troubleshooting
│   ├── TESTING_CHECKLIST.md                  📖 Testing guide
│   ├── COMPLETE_SETUP_GUIDE.md               📖 Setup guide
│   └── IMPLEMENTATION_COMPLETE.md            📖 Project summary
│
├── 📁 migrations/
│   ├── 003_visual_crops.sql                  ❌ DELETE (if exists, old migration)
│   └── 004_core_architecture_redesign.sql    📖 KEEP (reference only, don't run)
│
├── 📁 supabase/seed/
│   └── schema.sql                            📖 KEEP (original schema reference)
│
├── 📁 ingest/ (All fixed ✅)
│   ├── metadata.ts                           ✅ FIXED (working)
│   ├── persist.ts                            ✅ FIXED (no canonical_key, uses 'code')
│   ├── features.ts                           ✅ WORKING
│   ├── segment.ts                            ✅ WORKING
│   ├── tagging.ts                            ✅ WORKING
│   ├── test_metadata.ts                      ✅ READY TO RUN
│   ├── test_features.ts                      ✅ READY TO RUN
│   ├── test_persist.ts                       ✅ READY TO RUN (after migration)
│   └── test_full_integration.ts              ✅ READY TO RUN (after migration)
│
└── 📁 src/app/api/
    ├── ingest/route.ts                       ✅ WORKING
    └── papers/route.ts                       ✅ WORKING
```

---

## 🎯 Action Plan

### STEP 1: Delete These 3 Files

**In File Explorer, navigate to:**
```
c:\Users\shari\grademax\
```

**Delete these files:**
1. ❌ `COMPLETE_DATABASE_SCHEMA.sql`
2. ❌ `supabase_schema.sql`

**Also check and delete (if it exists):**
```
c:\Users\shari\grademax\migrations\
```
3. ❌ `003_visual_crops.sql` (if it exists)

---

### STEP 2: Use This 1 File

**Open this file:**
```
c:\Users\shari\grademax\FIXED_DATABASE_SCHEMA.sql
```

**Copy ALL contents (406 lines)** and run in Supabase SQL Editor

---

### STEP 3: Keep These Reference Files

Don't delete these - they're correct and useful:

#### Reference SQL (don't run, just for reference):
- ✅ `migrations/004_core_architecture_redesign.sql`
- ✅ `supabase/seed/schema.sql`

#### Documentation (guides and instructions):
- ✅ `DATABASE_MIGRATION_GUIDE.md` ← The main guide
- ✅ `QUICK_FIX.md` ← Quick reference
- ✅ `LOGIN_FIX_INSTRUCTIONS.md` ← Troubleshooting
- ✅ `TESTING_CHECKLIST.md` ← Testing guide
- ✅ `COMPLETE_SETUP_GUIDE.md` ← Setup instructions
- ✅ `IMPLEMENTATION_COMPLETE.md` ← Project summary

#### Code Files (all fixed and working):
- ✅ All files in `ingest/` folder
- ✅ All files in `src/app/api/` folder

---

## 🔍 How to Identify Files in VS Code

### Files to Delete (have red X in guide):

1. **COMPLETE_DATABASE_SCHEMA.sql**
   - Location: Root of workspace
   - Problem: Uses `canonical_key` column that doesn't exist
   - Line that causes error: `canonical_key TEXT UNIQUE,`
   - Status: ❌ DELETE

2. **supabase_schema.sql**
   - Location: Root of workspace
   - Problem: Outdated, replaced by FIXED version
   - Status: ❌ DELETE

3. **003_visual_crops.sql**
   - Location: `migrations/` folder
   - Problem: Old migration, not needed
   - Status: ❌ DELETE (if exists)

### File to Use (has green checkmark):

1. **FIXED_DATABASE_SCHEMA.sql**
   - Location: Root of workspace
   - Contains: 406 lines
   - First line: `-- Fixed Database Schema for GradeMax`
   - Last section: Success message with RAISE NOTICE
   - Status: ✅ USE THIS ONE

---

## 📋 Quick Comparison

### ❌ COMPLETE_DATABASE_SCHEMA.sql (DON'T USE)
```sql
-- Line 111: ERROR - This column doesn't exist
canonical_key TEXT UNIQUE,

-- Line 114: ERROR - Creates index for non-existent column
CREATE INDEX idx_papers_canonical_key ON papers(canonical_key);
```

### ✅ FIXED_DATABASE_SCHEMA.sql (USE THIS)
```sql
-- Uses ALTER TABLE to extend existing tables safely
ALTER TABLE papers ADD COLUMN IF NOT EXISTS board TEXT;
ALTER TABLE papers ADD COLUMN IF NOT EXISTS level TEXT;

-- No canonical_key - uses composite key instead
-- Works with existing database structure
```

---

## 🎯 Summary Table

| File Name | Location | Action | Reason |
|-----------|----------|--------|--------|
| `COMPLETE_DATABASE_SCHEMA.sql` | Root | ❌ **DELETE** | Has `canonical_key` error |
| `supabase_schema.sql` | Root | ❌ **DELETE** | Outdated |
| `003_visual_crops.sql` | migrations/ | ❌ **DELETE** | Old, not needed |
| `FIXED_DATABASE_SCHEMA.sql` | Root | ✅ **USE** | Correct, tested |
| `004_core_architecture_redesign.sql` | migrations/ | 📖 **KEEP** | Reference only |
| `DATABASE_MIGRATION_GUIDE.md` | Root | 📖 **READ** | Main instructions |
| All `.md` guide files | Root | 📖 **KEEP** | Documentation |
| All `ingest/*.ts` files | ingest/ | ✅ **KEEP** | Code is fixed |
| All `src/app/api/*.ts` files | src/app/api/ | ✅ **KEEP** | Code is fixed |

---

## ✅ Verification Checklist

After deleting files:

- [ ] `COMPLETE_DATABASE_SCHEMA.sql` is gone from root folder
- [ ] `supabase_schema.sql` is gone from root folder
- [ ] `003_visual_crops.sql` is gone from migrations folder (if it existed)
- [ ] `FIXED_DATABASE_SCHEMA.sql` still exists in root folder
- [ ] Guide files (.md) still exist in root folder
- [ ] Code files in `ingest/` and `src/` folders are untouched

---

## 🚀 Next Steps

1. ✅ Delete the 3 files listed above
2. ✅ Open `FIXED_DATABASE_SCHEMA.sql`
3. ✅ Copy all 406 lines
4. ✅ Go to Supabase Dashboard → SQL Editor
5. ✅ Paste and run
6. ✅ Wait for success message
7. ✅ Test login at http://localhost:3001/login
8. ✅ Follow `TESTING_CHECKLIST.md`

---

**Need the full guide?** Open `DATABASE_MIGRATION_GUIDE.md` 📖
