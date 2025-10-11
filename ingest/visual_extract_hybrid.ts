/**
 * visual_extract_hybrid.ts
 * Combines text-based structure detection with visual bbox location
 */
import { pdfToPng } from 'pdf-to-png-converter'
import sharp from 'sharp'
import crypto from 'crypto'
import type { PDFDocumentProxy } from 'pdfjs-dist'
import { MANUAL_BBOX_OVERRIDES } from './manual_bboxes.js'

export interface BBox {
  page: number
  x: number
  y: number
  width: number
  height: number
}

export interface VisualCrop {
  bbox: BBox
  pngBuffer: Buffer
  width: number
  height: number
  visualHash: string
  dpi: number
}

export interface QuestionPart {
  questionNumber: string
  bbox: BBox
  crop: VisualCrop
  marks?: number
}

/**
 * Render PDF pages to PNG
 */
export async function renderPdfToPngs(
  pdfBuffer: Buffer,
  targetDpi: number = 300
): Promise<Buffer[]> {
  const pngPages = await pdfToPng(pdfBuffer, {
    disableFontFace: false,
    useSystemFonts: true,
    viewportScale: targetDpi / 72,
    verbosityLevel: 0
  })
  
  return pngPages.map((page) => page.content as Buffer)
}

/**
 * Crop region from page PNG
 */
export async function cropRegion(
  pagePng: Buffer,
  bbox: BBox,
  targetDpi: number = 300
): Promise<VisualCrop> {
  const scale = targetDpi / 72
  
  const scaledBBox = {
    left: Math.floor(bbox.x * scale),
    top: Math.floor(bbox.y * scale),
    width: Math.floor(bbox.width * scale),
    height: Math.floor(bbox.height * scale)
  }
  
  // Get page dimensions
  const pageInfo = await sharp(pagePng).metadata()
  
  // Clamp to page boundaries
  if (scaledBBox.left < 0) scaledBBox.left = 0
  if (scaledBBox.top < 0) scaledBBox.top = 0
  if (scaledBBox.left + scaledBBox.width > (pageInfo.width || 0)) {
    scaledBBox.width = (pageInfo.width || 0) - scaledBBox.left
  }
  if (scaledBBox.top + scaledBBox.height > (pageInfo.height || 0)) {
    scaledBBox.height = (pageInfo.height || 0) - scaledBBox.top
  }
  
  // Crop and optimize
  const croppedBuffer = await sharp(pagePng)
    .extract(scaledBBox)
    .png({ compressionLevel: 9, adaptiveFiltering: true })
    .toBuffer()
  
  const visualHash = crypto.createHash('sha256').update(croppedBuffer).digest('hex')
  
  return {
    bbox,
    pngBuffer: croppedBuffer,
    width: scaledBBox.width,
    height: scaledBBox.height,
    visualHash,
    dpi: targetDpi
  }
}

/**
 * Find bbox for a specific question part using pdfjs text search
 */
async function findPartBBox(
  doc: PDFDocumentProxy,
  questionNumber: string
): Promise<BBox | null> {
  // Parse question number: "1", "2(a)", "2(a)(i)"
  const mainMatch = questionNumber.match(/^(\d{1,2})/)
  if (!mainMatch) return null
  
  const mainNum = mainMatch[1]
  const hasSubpart = questionNumber.includes('(')
  
  // Search for this question across pages
  for (let pageNum = 1; pageNum <= doc.numPages; pageNum++) {
    const page = await doc.getPage(pageNum)
    const textContent = await page.getTextContent()
    const viewport = page.getViewport({ scale: 1.0 })
    
    const items: Array<{ text: string; x: number; y: number }> = []
    for (const item of textContent.items) {
      if ('str' in item && 'transform' in item) {
        const tx = item.transform[4]
        const ty = item.transform[5]
        const y = viewport.height - ty - 10
        items.push({ text: item.str, x: tx, y })
      }
    }
    
    // Look for exact match or pattern match
    for (let i = 0; i < items.length; i++) {
      const item = items[i]
      const text = item.text.trim()
      
      // Check if this item matches our question number
      let isMatch = false
      
      if (!hasSubpart) {
        // Main question: "1 " or "1" - be very permissive
        // Try multiple strategies:
        // 1. Exact match near left margin
        if (text === mainNum && item.x < 100) {
          isMatch = true
        }
        // 2. Number followed by space in same text item
        else if (text.startsWith(mainNum + ' ') && item.x < 100) {
          isMatch = true
        }
        // 3. Number at end of text, next item starts with capital
        else if (text.endsWith(mainNum) && item.x < 100) {
          const nextText = items[i + 1]?.text.trim() || ''
          if (/^[A-Z]/.test(nextText)) {
            isMatch = true
          }
        }
      } else {
        // Subpart: look for "(a)" or "(i)" anywhere
        const subpartPattern = questionNumber.substring(mainNum.length)
        isMatch = text === subpartPattern || text.includes(subpartPattern)
      }
      
      if (isMatch) {
        // Found it! Create bbox
        const startY = item.y - 10
        
        // Find next question part or end of page for height
        let endY = viewport.height - 40
        
        // Look ahead for next part
        for (let j = i + 1; j < items.length; j++) {
          const nextText = items[j].text.trim()
          // Check if it's another question number or subpart
          if (/^\d{1,2}$/.test(nextText) || /^\([a-h]\)$/.test(nextText) || /^\((i{1,3}|iv|v|vi)\)$/.test(nextText)) {
            if (items[j].y > startY + 20) { // Ensure it's below current
              endY = items[j].y - 5
              break
            }
          }
        }
        
        return {
          page: pageNum,
          x: 40,
          y: startY,
          width: viewport.width - 80,
          height: endY - startY
        }
      }
    }
  }
  
  return null
}

/**
 * Parse question number into hierarchy: [mainNum, subpart, subsubpart]
 * Examples: "1" → [1], "2(a)" → [2, "a"], "2(a)(i)" → [2, "a", "i"]
 */
function parseQuestionNumber(questionNumber: string): [number, string?, string?] {
  const mainMatch = questionNumber.match(/^(\d{1,2})/)
  if (!mainMatch) return [0]
  
  const mainNum = parseInt(mainMatch[1], 10)
  
  const subpartMatch = questionNumber.match(/\(([a-h])\)/)
  const subsubpartMatch = questionNumber.match(/\(([a-h])\)\((i{1,3}|iv|v|vi)\)/)
  
  if (subsubpartMatch) {
    return [mainNum, subsubpartMatch[1], subsubpartMatch[2]]
  } else if (subpartMatch) {
    return [mainNum, subpartMatch[1]]
  } else {
    return [mainNum]
  }
}

/**
 * Estimate bbox by dividing parent bbox equally
 */
function estimateBBox(parentBBox: BBox, childIndex: number, totalChildren: number): BBox {
  const childHeight = parentBBox.height / totalChildren
  
  return {
    page: parentBBox.page,
    x: parentBBox.x,
    y: parentBBox.y + (childIndex * childHeight),
    width: parentBBox.width,
    height: childHeight
  }
}

/**
 * Extract all question parts with visual crops
 */
export async function extractAllQuestionParts(
  pdfBuffer: Buffer,
  targetDpi: number = 300
): Promise<QuestionPart[]> {
  console.log('🎨 Hybrid extraction: Text structure + Visual crops')
  
  // Step 1: Get question structure from text parser
  const { extractQuestions } = await import('./parse_pdf.js')
  const pdfParse = await import('pdf-parse')
  
  const data = await pdfParse.default(pdfBuffer)
  const questions = extractQuestions(data.text)
  
  console.log(`  ✓ Text parser found ${questions.length} parts`)
  
  // Step 2: Render all pages
  console.log(`  Rendering pages at ${targetDpi} DPI...`)
  const pagePngs = await renderPdfToPngs(pdfBuffer, targetDpi)
  console.log(`    ✓ Rendered ${pagePngs.length} pages`)
  
  // Step 3: Find bbox for each question part
  const pdfjsLib = await import('pdfjs-dist/legacy/build/pdf.mjs')
  const loadingTask = pdfjsLib.getDocument({ data: new Uint8Array(pdfBuffer) })
  const doc = await loadingTask.promise
  
  console.log(`  Finding bboxes for ${questions.length} parts...`)
  
  // First pass: Find all bboxes we can detect
  const detectedBBoxes = new Map<string, BBox>()
  
  // Start with manual overrides
  for (const [qNum, bbox] of Object.entries(MANUAL_BBOX_OVERRIDES)) {
    detectedBBoxes.set(qNum, bbox)
  }
  
  // Then try automatic detection
  for (const q of questions) {
    if (!detectedBBoxes.has(q.questionNumber)) {
      const bbox = await findPartBBox(doc, q.questionNumber)
      if (bbox) {
        detectedBBoxes.set(q.questionNumber, bbox)
      }
    }
  }
  
  const manualCount = Object.keys(MANUAL_BBOX_OVERRIDES).length
  console.log(`  ✓ Detected ${detectedBBoxes.size} bboxes (${manualCount} manual, ${detectedBBoxes.size - manualCount} auto)`)
  
  // Debug: Show what was detected
  console.log(`  📍 Detected: ${Array.from(detectedBBoxes.keys()).join(', ')}`)
  
  // Second pass: Estimate missing bboxes using equal division
  const allBBoxes = new Map<string, BBox>(detectedBBoxes)
  
  // Group questions by hierarchy
  const questionsByMain = new Map<number, typeof questions>()
  for (const q of questions) {
    const [mainNum] = parseQuestionNumber(q.questionNumber)
    if (!questionsByMain.has(mainNum)) {
      questionsByMain.set(mainNum, [])
    }
    questionsByMain.get(mainNum)!.push(q)
  }
  
  let estimatedCount = 0
  
  // For each main question, estimate missing parts
  for (const [mainNum, mainQuestions] of questionsByMain) {
    // Find main question bbox OR use any detected part as anchor
    let anchorBBox = detectedBBoxes.get(String(mainNum))
    
    if (!anchorBBox) {
      // Main not detected, try to find ANY detected part in this question
      for (const q of mainQuestions) {
        if (detectedBBoxes.has(q.questionNumber)) {
          anchorBBox = detectedBBoxes.get(q.questionNumber)!
          break
        }
      }
    }
    
    if (!anchorBBox) {
      console.log(`    ⚠️  No anchor found for Question ${mainNum}, skipping estimation`)
      continue
    }
    
    // Group by subpart
    const bySubpart = new Map<string, typeof questions>()
    const standaloneSubparts: typeof questions = []
    
    for (const q of mainQuestions) {
      const [_mainNum, subpart, subsubpart] = parseQuestionNumber(q.questionNumber)
      
      if (subpart && !subsubpart) {
        // Standalone subpart like 2(a)
        standaloneSubparts.push(q)
      } else if (subpart && subsubpart) {
        // Sub-subpart like 2(a)(i)
        const subpartKey = `${mainNum}(${subpart})`
        if (!bySubpart.has(subpartKey)) {
          bySubpart.set(subpartKey, [])
        }
        bySubpart.get(subpartKey)!.push(q)
      }
    }
    
    // First, estimate missing standalone subparts by dividing anchor bbox
    if (standaloneSubparts.length > 0) {
      const missingSubparts = standaloneSubparts.filter(q => !detectedBBoxes.has(q.questionNumber))
      
      if (missingSubparts.length > 0) {
        // Divide anchor bbox equally among ALL subparts (detected + missing)
        standaloneSubparts.forEach((q, idx) => {
          if (!allBBoxes.has(q.questionNumber)) {
            const estimatedBBox = estimateBBox(anchorBBox!, idx, standaloneSubparts.length)
            allBBoxes.set(q.questionNumber, estimatedBBox)
            estimatedCount++
          }
        })
      }
    }
    
    // Then, estimate missing sub-subparts
    for (const [subpartKey, subsubparts] of bySubpart) {
      // Check if parent subpart has a bbox (detected or estimated)
      const parentBBox = allBBoxes.get(subpartKey)
      
      if (parentBBox && subsubparts.length > 0) {
        // Divide parent bbox equally among sub-subparts
        subsubparts.forEach((q, idx) => {
          if (!detectedBBoxes.has(q.questionNumber)) {
            const estimatedBBox = estimateBBox(parentBBox, idx, subsubparts.length)
            allBBoxes.set(q.questionNumber, estimatedBBox)
            estimatedCount++
          }
        })
      } else if (!parentBBox && anchorBBox) {
        // Parent not found, estimate sub-subparts from anchor directly
        subsubparts.forEach((q, idx) => {
          if (!allBBoxes.has(q.questionNumber)) {
            const estimatedBBox = estimateBBox(anchorBBox!, idx, subsubparts.length)
            allBBoxes.set(q.questionNumber, estimatedBBox)
            estimatedCount++
          }
        })
      }
    }
  }
  
  console.log(`  ✓ Estimated ${estimatedCount} additional bboxes`)
  console.log(`  ✓ Total bboxes: ${allBBoxes.size}/${questions.length}`)
  
  // Step 4: Extract crops
  const parts: QuestionPart[] = []
  
  for (const q of questions) {
    const bbox = allBBoxes.get(q.questionNumber)
    
    if (bbox && bbox.page >= 1 && bbox.page <= pagePngs.length) {
      try {
        const crop = await cropRegion(pagePngs[bbox.page - 1], bbox, targetDpi)
        parts.push({
          questionNumber: q.questionNumber,
          bbox,
          crop,
          marks: q.marks
        })
      } catch (error) {
        console.warn(`    ⚠️  Failed to crop ${q.questionNumber}:`, error)
      }
    } else {
      console.warn(`    ⚠️  No bbox available for ${q.questionNumber}`)
    }
  }
  
  console.log(`  ✓ Successfully extracted ${parts.length}/${questions.length} parts`)
  
  return parts
}
