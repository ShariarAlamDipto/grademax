# ✅ ULTRA-SIMPLE CHECKLIST

Copy this checklist and check off each item as you complete it.

---

## 🗑️ DELETE (3 files)

Find and delete these files:

- [ ] **COMPLETE_DATABASE_SCHEMA.sql** (in root folder)
- [ ] **supabase_schema.sql** (in root folder)  
- [ ] **003_visual_crops.sql** (in migrations folder, if it exists)

**How**: Right-click each file → Delete

---

## 📋 RUN IN SUPABASE (1 file)

### File to use:
- [ ] Open **FIXED_DATABASE_SCHEMA.sql** (in root folder)

### Steps:
- [ ] Select ALL text (Ctrl+A)
- [ ] Copy (Ctrl+C)
- [ ] Go to https://supabase.com/dashboard
- [ ] Select project: **tybaetnvnfgniotdfxze**
- [ ] Click **SQL Editor** (left sidebar)
- [ ] Click **New Query**
- [ ] Paste (Ctrl+V)
- [ ] Click **Run** (or Ctrl+Enter)
- [ ] Wait for success message (5-10 seconds)

### Success message will say:
```
✅ Fixed database schema applied successfully!
✅ profiles (with auto-creation trigger) - FIXES LOGIN LOOP
```

---

## 🧪 TEST

### Test login:
- [ ] Go to: http://localhost:3001/login
- [ ] Click "Continue with Google"
- [ ] Should redirect to **/dashboard** (NOT /login)
- [ ] Should see "Hi, [Your Name] 👋"

### If login works:
- [ ] 🎉 **YOU'RE DONE!**

### If login still loops:
- [ ] Open **LOGIN_FIX_INSTRUCTIONS.md**
- [ ] Follow troubleshooting steps

---

## 🧪 RUN TESTS (Optional)

After migration, test the pipeline:

- [ ] `npx tsx ingest/test_metadata.ts` (should show 8/8 passed)
- [ ] `npx tsx ingest/test_features.ts` (should show 12 questions analyzed)
- [ ] `npx tsx ingest/test_persist.ts` (should save to database)
- [ ] `npx tsx ingest/test_full_integration.ts` (should complete in ~1.3s)

---

## 📊 Summary

**Total time**: 5 minutes  
**Files to delete**: 3  
**Files to run**: 1  
**Result**: Login fixed + All modules working

---

## 🆘 Need Help?

**Detailed guides** (in your workspace):
- `START_HERE.md` - Simple 3-step guide
- `DATABASE_MIGRATION_GUIDE.md` - Complete instructions
- `VISUAL_FILE_MAP.md` - File locations
- `TESTING_CHECKLIST.md` - Complete testing

**Key file locations**:
- Root folder: `c:\Users\shari\grademax\`
- Migrations folder: `c:\Users\shari\grademax\migrations\`

---

**Start now**: Delete those 3 files! ✅
