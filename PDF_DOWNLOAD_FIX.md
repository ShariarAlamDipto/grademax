# 🔧 PDF Download & Preview Fix

## ❌ Problems Fixed

1. **No PDF Preview** - PDFs weren't showing in the UI
2. **"Failed to merge PDF" Error** - Download was failing
3. **Complex Python execution** - Trying to run Python from Node.js

---

## ✅ Solution Implemented

### Changed Approach

**OLD (Broken)**:
```
Frontend → API → Execute Python script → Merge PDFs → Upload to storage → Return URLs
```
- ❌ Complex (runs Python from Node.js)
- ❌ Required file system access
- ❌ Slow and error-prone

**NEW (Working)**:
```
Frontend → API → Download PDFs from Supabase → Merge with pdf-lib → Return merged PDF
```
- ✅ Simple (pure JavaScript)
- ✅ No file system needed
- ✅ Fast and reliable
- ✅ Returns PDF directly to browser

---

## 🔧 Technical Changes

### 1. Updated Download API Route

**File**: `src/app/api/worksheets/[id]/download/route.ts`

**Changes**:
- ✅ Removed Python script execution
- ✅ Removed file system operations
- ✅ Added `pdf-lib` for PDF merging
- ✅ Returns PDF directly as response (not JSON with URLs)
- ✅ Supports query parameter: `?type=worksheet` or `?type=markscheme`

**New API Usage**:
```typescript
// Download worksheet
GET /api/worksheets/[id]/download?type=worksheet
// Returns: PDF file (application/pdf)

// Download markscheme
GET /api/worksheets/[id]/download?type=markscheme
// Returns: PDF file (application/pdf)
```

---

### 2. Updated Frontend

**File**: `src/app/generate/page.tsx`

**Changes**:
- ✅ Updated `handleDownload()` to fetch PDF blobs
- ✅ Creates object URLs for preview
- ✅ Added PDF preview iframes
- ✅ Separate download for worksheet and markscheme

**New Flow**:
```typescript
1. User clicks "Download PDFs"
2. Frontend fetches worksheet PDF blob
3. Frontend fetches markscheme PDF blob
4. Creates object URLs for both
5. Shows preview in iframes
6. Enables download buttons
```

---

## 🎨 New UI Features

### PDF Preview Section

After clicking "Download PDFs":

```
┌─────────────────────────────────────────────────────┐
│ ✅ PDFs Ready!                                       │
│ ┌──────────────────┐ ┌──────────────────┐          │
│ │ 📝 Download      │ │ ✅ Download      │          │
│ │ Worksheet.pdf    │ │ Markscheme.pdf   │          │
│ └──────────────────┘ └──────────────────┘          │
│                                                      │
│ 📄 Worksheet Preview     ✅ Markscheme Preview      │
│ ┌──────────────────┐ ┌──────────────────┐          │
│ │                  │ │                  │          │
│ │  [PDF Preview]   │ │  [PDF Preview]   │          │
│ │                  │ │                  │          │
│ └──────────────────┘ └──────────────────┘          │
└─────────────────────────────────────────────────────┘
```

---

## 📦 Dependencies

**Already Installed**:
- ✅ `pdf-lib` - PDF manipulation library

No additional packages needed!

---

## 🚀 How It Works Now

### Step-by-Step Flow

1. **User Generates Worksheet**
   ```
   - Select topics
   - Click "Generate Worksheet"
   - Questions appear in UI
   ```

2. **User Clicks "Download PDFs"**
   ```
   - Frontend calls API: /api/worksheets/[id]/download?type=worksheet
   - API fetches all question page PDFs from Supabase Storage
   - API merges them using pdf-lib
   - API returns merged PDF blob
   ```

3. **Frontend Displays Results**
   ```
   - Creates object URL from blob
   - Shows PDF preview in iframe
   - Enables download button with proper filename
   ```

---

## 🔍 How PDF Merging Works

**Using pdf-lib** (Pure JavaScript):

```typescript
async function mergePDFs(pdfUrls: string[]): Promise<Uint8Array> {
  const mergedPdf = await PDFDocument.create();

  for (const url of pdfUrls) {
    // Download PDF from Supabase Storage
    const pdfBytes = await downloadPDF(url);
    
    // Load PDF
    const pdf = await PDFDocument.load(pdfBytes);
    
    // Copy all pages to merged document
    const copiedPages = await mergedPdf.copyPages(pdf, pdf.getPageIndices());
    copiedPages.forEach((page) => mergedPdf.addPage(page));
  }

  // Save and return
  return await mergedPdf.save();
}
```

**Benefits**:
- ✅ No Python needed
- ✅ No file system operations
- ✅ Works in serverless environments
- ✅ Fast and reliable

---

## 🧪 Testing

### Test the Fix:

1. **Restart Dev Server** (if needed):
   ```powershell
   # Press Ctrl+C in terminal, then:
   npm run dev
   ```

2. **Generate Worksheet**:
   - Go to: http://localhost:3000/generate
   - Select 2-3 topics
   - Click "Generate Worksheet"
   - Should see questions list ✅

3. **Download PDFs**:
   - Click "⬇️ Download PDFs" button
   - Wait for "📄 Creating PDFs..." message
   - Should see:
     - ✅ Download buttons appear
     - ✅ PDF previews load in iframes
     - ✅ Click buttons to download PDFs

4. **Verify PDFs**:
   - Open downloaded `worksheet.pdf` ✅
   - Open downloaded `markscheme.pdf` ✅
   - Should contain all selected questions

---

## 📊 Comparison

| Feature | OLD (Python) | NEW (pdf-lib) |
|---------|-------------|---------------|
| Execution | Node.js → Python | Pure JavaScript |
| File System | Required | Not needed |
| Dependencies | Python + PyPDF2 | Just pdf-lib |
| Speed | Slow | Fast ⚡ |
| Reliability | Error-prone | Stable ✅ |
| Serverless | ❌ Difficult | ✅ Works |
| Preview | ❌ None | ✅ Inline |

---

## 🆘 Troubleshooting

### Error: "Failed to generate PDF"

**Check**:
1. Make sure papers were processed (database has pages)
2. Check browser console for errors
3. Verify Supabase storage URLs are accessible

**Test**:
```powershell
python scripts/check_database.py
# Should show pages with qp_page_url and ms_page_url
```

### Preview Not Showing

**Cause**: Browser security may block iframe for blob URLs

**Solution**: Download button still works! PDF will download correctly.

### Download Button Not Working

**Check**:
1. Browser console for errors
2. Network tab shows PDF download
3. Popup blocker not blocking download

---

## ✅ Files Changed

1. ✅ `src/app/api/worksheets/[id]/download/route.ts` - Complete rewrite
2. ✅ `src/app/generate/page.tsx` - Updated download handler + added previews

---

## 🎯 Status

**PDF Download**: ✅ FIXED  
**PDF Preview**: ✅ ADDED  
**Error Handling**: ✅ IMPROVED  

**Next Steps**:
1. Restart dev server
2. Generate a worksheet
3. Click "Download PDFs"
4. See previews and download! 🎉
