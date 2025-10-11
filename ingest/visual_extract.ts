/**
 * visual_extract.ts
 * Extract visual crops from PDF using pdfjs-dist
 * Preserves EXACT layout, fonts, spacing, diagrams
 */
// Use legacy build for Node.js environment
import * as pdfjsLib from 'pdfjs-dist/legacy/build/pdf.mjs'
import { createCanvas } from 'canvas'
import sharp from 'sharp'
import crypto from 'crypto'

// Types
export interface BBox {
  page: number
  x: number      // left
  y: number      // top (from top of page)
  width: number
  height: number
}

export interface VisualCrop {
  bbox: BBox
  pngBuffer: Buffer
  width: number
  height: number
  visualHash: string  // sha256 for deduplication
  dpi: number
}

export interface QuestionBounds {
  questionNumber: string
  bboxes: BBox[]  // Can span multiple pages
  marks?: number
}

/**
 * Initialize pdfjs-dist with proper worker
 */
export async function initPdfJs() {
  // pdfjs-dist v5 doesn't require manual worker setup in Node.js
  // The library handles it automatically
}

/**
 * Load PDF document from buffer
 */
export async function loadPdfDocument(pdfBuffer: Buffer): Promise<pdfjsLib.PDFDocumentProxy> {
  const data = new Uint8Array(pdfBuffer)
  const loadingTask = pdfjsLib.getDocument({ data })
  return await loadingTask.promise
}

/**
 * Get text items with positions for bbox detection
 */
export async function getTextItemsWithPositions(
  doc: pdfjsLib.PDFDocumentProxy,
  pageNum: number
): Promise<Array<{ text: string; x: number; y: number; width: number; height: number }>> {
  const page = await doc.getPage(pageNum)
  const textContent = await page.getTextContent()
  const viewport = page.getViewport({ scale: 1.0 })
  
  const items: Array<{ text: string; x: number; y: number; width: number; height: number }> = []
  
  for (const item of textContent.items) {
    if ('str' in item && 'transform' in item) {
      const tx = item.transform[4]
      const ty = item.transform[5]
      const text = item.str
      
      // Approximate width and height
      const width = item.width || 0
      const height = item.height || 10
      
      // Convert to top-down y coordinate
      const y = viewport.height - ty - height
      
      items.push({
        text,
        x: tx,
        y,
        width,
        height
      })
    }
  }
  
  return items
}

/**
 * Detect question boundaries using text position analysis
 * Returns bounding boxes for each question/part
 */
export async function detectQuestionBounds(
  doc: pdfjsLib.PDFDocumentProxy,
  startPage: number = 1,
  endPage?: number
): Promise<QuestionBounds[]> {
  const bounds: QuestionBounds[] = []
  const lastPage = endPage || doc.numPages
  
  console.log(`  Scanning pages ${startPage} to ${lastPage}...`)
  
  let currentQuestion: QuestionBounds | null = null
  
  for (let pageNum = startPage; pageNum <= lastPage; pageNum++) {
    const page = await doc.getPage(pageNum)
    const viewport = page.getViewport({ scale: 1.0 })
    const items = await getTextItemsWithPositions(doc, pageNum)
    
    console.log(`    Page ${pageNum}: ${items.length} text items`)
    
    // Debug: show first 10 items on page 4 (where questions should start)
    if (pageNum === 4) {
      console.log(`    DEBUG - First 20 items on page 4:`)
      items.slice(0, 20).forEach((item, idx) => {
        console.log(`      [${idx}] "${item.text}" at y=${item.y.toFixed(1)}`)
      })
    }
    
    // Find question starts
    // Text items are separate, so look for a digit followed by capital letter on same line
    for (let i = 0; i < items.length - 2; i++) {
      const item1 = items[i]
      const item2 = items[i + 1]
      const item3 = items[i + 2]
      
      // Check if: digit, space/empty, then text starting with capital
      const isDigit = /^\d{1,2}$/.test(item1.text.trim())
      const isSpace = item2.text.trim() === ''
      const startsWithCap = /^[A-Z]/.test(item3.text.trim())
      const sameLine = Math.abs(item1.y - item3.y) < 5 // Within 5 points vertically
      
      if (isDigit && isSpace && startsWithCap && sameLine) {
        const questionNum = item1.text.trim()
        console.log(`    Found question ${questionNum} at y=${item1.y}`)
        
        // Save previous question
        if (currentQuestion) {
          bounds.push(currentQuestion)
        }
        
        // Start new question
        currentQuestion = {
          questionNumber: questionNum,
          bboxes: [{
            page: pageNum,
            x: 0, // Full width for now
            y: item1.y,
            width: viewport.width,
            height: 0 // Will compute later
          }]
        }
      }
    }
  }
  
  // Finalize last question
  if (currentQuestion) {
    bounds.push(currentQuestion)
  }
  
  // Compute heights (distance to next question or page end)
  for (let i = 0; i < bounds.length; i++) {
    const current = bounds[i]
    const next = bounds[i + 1]
    
    if (next && next.bboxes[0].page === current.bboxes[0].page) {
      // Same page - height is distance to next question
      current.bboxes[0].height = next.bboxes[0].y - current.bboxes[0].y
    } else {
      // Different page or last question - use page height
      const page = await doc.getPage(current.bboxes[0].page)
      const viewport = page.getViewport({ scale: 1.0 })
      current.bboxes[0].height = viewport.height - current.bboxes[0].y
    }
  }
  
  return bounds
}

/**
 * Render a bounding box region to PNG at specified DPI
 */
export async function renderBBoxToPng(
  doc: pdfjsLib.PDFDocumentProxy,
  bbox: BBox,
  targetDpi: number = 300
): Promise<VisualCrop> {
  const page = await doc.getPage(bbox.page)
  
  // Calculate scale for target DPI
  // PDF default is 72 DPI
  const scale = targetDpi / 72
  const scaledViewport = page.getViewport({ scale })
  
  // Scale bbox
  const scaledBBox = {
    x: bbox.x * scale,
    y: bbox.y * scale,
    width: bbox.width * scale,
    height: bbox.height * scale
  }
  
  // Create canvas for full page
  const canvas = createCanvas(scaledViewport.width, scaledViewport.height)
  const context = canvas.getContext('2d')
  
  // Render full page - pdfjs-dist v5 requires both canvas and canvasContext
  const renderContext = {
    canvas: canvas as unknown as HTMLCanvasElement,
    canvasContext: context as unknown as CanvasRenderingContext2D,
    viewport: scaledViewport
  }
  
  await page.render(renderContext).promise
  
  // Extract crop region
  const cropCanvas = createCanvas(scaledBBox.width, scaledBBox.height)
  const cropContext = cropCanvas.getContext('2d')
  
  cropContext.drawImage(
    canvas,
    scaledBBox.x, scaledBBox.y, scaledBBox.width, scaledBBox.height,
    0, 0, scaledBBox.width, scaledBBox.height
  )
  
  // Convert to PNG buffer
  const pngBuffer = cropCanvas.toBuffer('image/png')
  
  // Compute visual hash
  const visualHash = crypto.createHash('sha256').update(pngBuffer).digest('hex')
  
  // Optimize with sharp
  const optimizedBuffer = await sharp(pngBuffer)
    .png({ compressionLevel: 9, adaptiveFiltering: true })
    .toBuffer()
  
  return {
    bbox,
    pngBuffer: optimizedBuffer,
    width: scaledBBox.width,
    height: scaledBBox.height,
    visualHash,
    dpi: targetDpi
  }
}

/**
 * Extract visual crops for all questions in a paper
 */
export async function extractAllVisualCrops(
  pdfBuffer: Buffer,
  targetDpi: number = 300
): Promise<Array<{ questionNumber: string; crop: VisualCrop; marks?: number }>> {
  await initPdfJs()
  const doc = await loadPdfDocument(pdfBuffer)
  
  // Detect question boundaries
  const bounds = await detectQuestionBounds(doc)
  
  // Render each question
  const crops: Array<{ questionNumber: string; crop: VisualCrop; marks?: number }> = []
  
  for (const bound of bounds) {
    // For now, only handle single-page questions
    // TODO: Handle multi-page questions
    if (bound.bboxes.length === 1) {
      const crop = await renderBBoxToPng(doc, bound.bboxes[0], targetDpi)
      crops.push({
        questionNumber: bound.questionNumber,
        crop,
        marks: bound.marks
      })
    }
  }
  
  return crops
}
