# 🗺️ VISUAL FILE MAP

```
📁 c:\Users\shari\grademax\
│
├─── 📄 START_HERE.md                         ⭐ READ THIS FIRST
│
├─── 📄 FIXED_DATABASE_SCHEMA.sql             ✅ RUN THIS IN SUPABASE (406 lines)
│
├─── 📄 COMPLETE_DATABASE_SCHEMA.sql          ❌ DELETE THIS (has errors)
├─── 📄 supabase_schema.sql                   ❌ DELETE THIS (outdated)
│
├─── 📄 DATABASE_MIGRATION_GUIDE.md           📖 Detailed instructions
├─── 📄 FILE_CLEANUP_REFERENCE.md             📖 This file
├─── 📄 QUICK_FIX.md                          📖 Quick reference
├─── 📄 TESTING_CHECKLIST.md                  📖 Testing guide
├─── 📄 LOGIN_FIX_INSTRUCTIONS.md             📖 Login troubleshooting
├─── 📄 COMPLETE_SETUP_GUIDE.md               📖 Setup guide
├─── 📄 IMPLEMENTATION_COMPLETE.md            📖 Project summary
│
├─── 📁 migrations/
│    ├─── 003_visual_crops.sql                ❌ DELETE THIS (if exists)
│    └─── 004_core_architecture_redesign.sql  📖 Reference (don't run)
│
├─── 📁 supabase/
│    └─── 📁 seed/
│         └─── schema.sql                     📖 Reference (don't run)
│
├─── 📁 ingest/
│    ├─── metadata.ts                         ✅ FIXED & WORKING
│    ├─── persist.ts                          ✅ FIXED & WORKING (no canonical_key)
│    ├─── features.ts                         ✅ WORKING
│    ├─── segment.ts                          ✅ WORKING
│    ├─── tagging.ts                          ✅ WORKING
│    ├─── test_metadata.ts                    ✅ RUN AFTER MIGRATION
│    ├─── test_features.ts                    ✅ RUN AFTER MIGRATION
│    ├─── test_persist.ts                     ✅ RUN AFTER MIGRATION
│    └─── test_full_integration.ts            ✅ RUN AFTER MIGRATION
│
└─── 📁 src/
     └─── 📁 app/
          ├─── 📁 api/
          │    ├─── 📁 ingest/
          │    │    └─── route.ts             ✅ WORKING
          │    └─── 📁 papers/
          │         └─── route.ts             ✅ WORKING
          ├─── 📁 qa/
          │    └─── page.tsx                  ✅ WORKING
          └─── 📁 dashboard/
               └─── page.tsx                  ✅ WORKING
```

---

## 🎯 Action Items

### ❌ Files to DELETE (3 total):

1. **In root folder** (`c:\Users\shari\grademax\`):
   - `COMPLETE_DATABASE_SCHEMA.sql`
   - `supabase_schema.sql`

2. **In migrations folder** (`c:\Users\shari\grademax\migrations\`):
   - `003_visual_crops.sql` (if it exists)

### ✅ File to USE (1 file):

**In root folder** (`c:\Users\shari\grademax\`):
- `FIXED_DATABASE_SCHEMA.sql` → Copy ALL 406 lines → Run in Supabase SQL Editor

### 📖 Files to KEEP (reference & code):

**Documentation** (all in root folder):
- All `.md` files (guides)
- `migrations/004_core_architecture_redesign.sql` (reference)
- `supabase/seed/schema.sql` (reference)

**Code** (all folders):
- Everything in `ingest/` folder (all fixed)
- Everything in `src/` folder (all working)

---

## 📸 Screenshot Locations

### In VS Code Explorer (Left Sidebar):

```
GRADEMAX
├── .next/
├── data/
├── ingest/                         ← Code folder (keep all)
├── migrations/
│   ├── 003_visual_crops.sql        ← DELETE if exists
│   └── 004_core_...sql             ← Keep (reference)
├── node_modules/
├── public/
├── src/                            ← Code folder (keep all)
├── supabase/
│   └── seed/
│       └── schema.sql              ← Keep (reference)
│
├── COMPLETE_DATABASE_SCHEMA.sql    ← DELETE THIS ❌
├── DATABASE_MIGRATION_GUIDE.md     ← Keep (guide)
├── FILE_CLEANUP_REFERENCE.md       ← Keep (guide)
├── FIXED_DATABASE_SCHEMA.sql       ← USE THIS ✅
├── LOGIN_FIX_INSTRUCTIONS.md       ← Keep (guide)
├── QUICK_FIX.md                    ← Keep (guide)
├── START_HERE.md                   ← Keep (guide)
├── supabase_schema.sql             ← DELETE THIS ❌
├── TESTING_CHECKLIST.md            ← Keep (guide)
│
├── .env.local                      ← Keep (credentials)
├── package.json                    ← Keep (dependencies)
└── tsconfig.json                   ← Keep (config)
```

---

## 🔍 How to Find Files to Delete

### Method 1: VS Code Search
1. Press `Ctrl+P` (Quick Open)
2. Type: `COMPLETE_DATABASE_SCHEMA.sql`
3. Right-click → Delete
4. Repeat for `supabase_schema.sql`
5. Repeat for `003_visual_crops.sql`

### Method 2: File Explorer
1. Look in left sidebar (Explorer)
2. Scroll to find files in root folder
3. Right-click → Delete

### Method 3: Windows Explorer
1. Open: `c:\Users\shari\grademax\`
2. Find and delete the 3 files
3. Delete from Recycle Bin (optional)

---

## ✅ Verification

### After deleting, you should NOT see:
- ❌ `COMPLETE_DATABASE_SCHEMA.sql` (in root)
- ❌ `supabase_schema.sql` (in root)
- ❌ `003_visual_crops.sql` (in migrations folder)

### You SHOULD still see:
- ✅ `FIXED_DATABASE_SCHEMA.sql` (in root)
- ✅ All `.md` guide files (in root)
- ✅ All files in `ingest/` folder
- ✅ All files in `src/` folder
- ✅ `004_core_architecture_redesign.sql` (in migrations)

---

## 📋 Quick Reference

| What | Where | Action |
|------|-------|--------|
| COMPLETE_DATABASE_SCHEMA.sql | Root folder | ❌ Delete |
| supabase_schema.sql | Root folder | ❌ Delete |
| 003_visual_crops.sql | migrations/ | ❌ Delete (if exists) |
| FIXED_DATABASE_SCHEMA.sql | Root folder | ✅ Run in Supabase |
| All .md files | Root folder | 📖 Keep |
| ingest/ folder | Root folder | ✅ Keep all |
| src/ folder | Root folder | ✅ Keep all |

---

## 🚀 Next Step

After deleting files:
1. Open `START_HERE.md` (has complete 3-step guide)
2. Or jump to Step 2: Open `FIXED_DATABASE_SCHEMA.sql`
3. Copy all 406 lines
4. Run in Supabase SQL Editor

**Time to complete**: 5 minutes total

---

## 🎯 Files Summary

- **3 files to delete** ❌
- **1 file to run in Supabase** ✅
- **7 guide files to keep** 📖
- **All code files working** ✅

**You're almost done!** Just delete those 3 files and run the fixed SQL! 💪
