# ⚡ Quick Fix: Restart Dev Server

## 🎯 The Problem
Frontend shows "Invalid API key" error when generating worksheets.

## ✅ The Solution
**Restart the Next.js dev server** (it needs to reload environment variables)

---

## 🚀 Steps to Fix (30 seconds)

### 1. Stop the Server
In the terminal running `npm run dev`:
- Press **`Ctrl + C`**

### 2. Start it Again
```powershell
npm run dev
```

### 3. Test
- Visit: http://localhost:3000/generate
- Select topics
- Click "Generate Worksheet"
- **Should work now!** ✅

---

## 🤔 Why?

Next.js reads `.env.local` **only at startup**. You created/updated the file while the server was running, so it never loaded the new values.

**After restart**: Server picks up the correct API keys from `.env.local` ✅

---

## ✅ Your Environment Files Are Correct

**`.env.local`** (frontend):
```
✅ NEXT_PUBLIC_SUPABASE_URL
✅ NEXT_PUBLIC_SUPABASE_ANON_KEY
```

**`.env.ingest`** (backend):
```
✅ SUPABASE_URL
✅ SUPABASE_SERVICE_ROLE
✅ GEMINI_API_KEY
✅ DATABASE_URL
```

**Nothing to change - just restart!**

---

## 📋 After Restart

You should be able to:
1. ✅ Generate worksheets
2. ✅ Download PDFs
3. ✅ See questions from the database

---

**Just press Ctrl+C and run `npm run dev` again!** 🚀
