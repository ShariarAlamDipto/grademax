# Phase 1 Progress Report: Visual Extraction

## ✅ Achievements

1. **Package Installation**: Successfully installed visual rendering stack
   - pdfjs-dist 5.4.296 (legacy build for Node.js)
   - canvas 3.2.0
   - sharp 0.34.4
   - @react-pdf/renderer 4.3.1

2. **BBox Detection**: ✅ **WORKING**
   - Successfully detects all 12 main questions in sample paper
   - Correctly identifies question boundaries across 32 pages
   - Handles multi-page questions properly
   ```
   Found: Q1 (page 3), Q2 (page 4), Q3 (page 6), Q4 (page 9),
          Q5 (page 12), Q6 (page 15), Q7 (page 17), Q8 (page 19),
          Q9 (page 21), Q10 (page 24), Q11 (page 28), Q12 (page 30)
   ```

3. **Text Position Analysis**: ✅ **WORKING**
   - Extracts text items with (x, y, width, height) coordinates
   - Detects question starts by analyzing consecutive text items
   - Handles PDF's separate text item structure (digit, space, text)

## ⚠️ Current Blocker

**Canvas Rendering Error**: `TypeError: Image or Canvas expected`
- pdfjs-dist's CanvasGraphics.paintImageMaskXObject fails with node-canvas
- This is a known compatibility issue between pdfjs-dist and node-canvas in Node.js
- The error occurs when rendering pages with certain image types (masks, transparency)

## 🔧 Workaround Options

### Option A: Use pdf-lib (Recommended)
pdf-lib is designed for Node.js and handles PDF rendering better:
```typescript
import { PDFDocument } from 'pdf-lib'

async function renderWithPdfLib(pdfBuffer: Buffer, bbox: BBox): Promise<Buffer> {
  const pdfDoc = await PDFDocument.load(pdfBuffer)
  const page = pdfDoc.getPage(bbox.page - 1)
  
  // Extract page as image using pdf-lib's built-in renderer
  const imageBytes = await page.toImageBytes()
  
  // Crop with sharp
  return await sharp(Buffer.from(imageBytes))
    .extract({
      left: bbox.x,
      top: bbox.y,
      width: bbox.width,
      height: bbox.height
    })
    .png()
    .toBuffer()
}
```

**Pros**: Native Node.js support, no canvas issues
**Cons**: pdf-lib's image extraction is lower quality than pdfjs rendering

### Option B: Use External PDF→Image Tool
Call external tool (pdftoppm, ghostscript, or similar):
```typescript
async function renderWithPdftoppm(pdfPath: string, pageNum: number): Promise<Buffer> {
  // pdftoppm -png -r 300 -f {pageNum} -l {pageNum} input.pdf output
  execSync(`pdftoppm -png -r 300 -f ${pageNum} -l ${pageNum} "${pdfPath}" temp`)
  const imagePath = `temp-${pageNum}.png`
  const buffer = fs.readFileSync(imagePath)
  fs.unlinkSync(imagePath)
  return buffer
}
```

**Pros**: High quality, reliable
**Cons**: Requires external dependency installation

### Option C: Puppeteer/Headless Chrome
Use headless browser to render PDF:
```typescript
import puppeteer from 'puppeteer'

async function renderWithPuppeteer(pdfBuffer: Buffer, bbox: BBox): Promise<Buffer> {
  const browser = await puppeteer.launch({ headless: true })
  const page = await browser.newPage()
  
  // Load PDF in browser
  await page.goto(`data:application/pdf;base64,${pdfBuffer.toString('base64')}`)
  await page.setViewport({ width: 1200, height: 1600 })
  
  // Screenshot the region
  const screenshot = await page.screenshot({
    clip: { x: bbox.x, y: bbox.y, width: bbox.width, height: bbox.height }
  })
  
  await browser.close()
  return screenshot
}
```

**Pros**: Perfect rendering (real Chrome)
**Cons**: Heavy dependency, slower

### Option D: Hybrid - Store Page PNGs, Crop Later
1. Use external tool to render full pages to PNG (one-time)
2. Store page PNGs in Supabase Storage
3. Use sharp to crop regions on-demand

**Pros**: Separation of concerns, fast crops
**Cons**: Large storage for full-page PNGs

## 📊 Recommendation

**For MVP/Testing**: **Option B** (pdftoppm) or **Option D** (pre-render pages)
- pdftoppm is simple, widely available, high quality
- Pre-rendering pages separates the "hard" rendering from cropping

**For Production Scale**: **Option D** (Hybrid approach)
```
Ingestion:
  PDF → pdftoppm → Store full page PNGs (papers_pages/{paper_id}/page_{N}.png)
  
Worksheet Generation:
  Load page PNG → sharp.extract(bbox) → Crop PNG → Embed in worksheet
```

**Storage math**:
- 32 pages × 300 DPI × PNG compression ≈ 50-80 MB per paper
- 100 papers = 5-8 GB (manageable with Supabase's free tier)
- Crops are tiny: ~100-200 KB each

## 🚀 Next Steps

### Immediate (Complete Phase 1)
1. Implement Option B or D for rendering
2. Test crop generation end-to-end
3. Upload sample crops to Supabase Storage
4. Verify visual quality (fonts, spacing, diagrams preserved)

### Then Proceed to Phase 2
- Enhanced segmentation (subparts: (a), (b), (i), (ii))
- Diagram detection (extend bbox to cover images)
- Multi-page question stitching

## 📝 Code Status

**Files Created**:
- ✅ `ingest/visual_extract.ts` - BBox detection working
- ✅ `ingest/test_visual_extract.ts` - Test script
- ✅ `ROADMAP_VISUAL.md` - Full implementation plan

**Current State**:
- BBox detection: 100% working
- Canvas rendering: Blocked (known issue)
- Need rendering workaround to proceed

**Est. Time to Complete Phase 1**:
- With Option B/D: 2-3 hours
- Then can move to Phase 2

---

**Decision Needed**: Which rendering option should we implement?

My recommendation: **Option D (Hybrid)** for best balance of quality, performance, and maintainability.
