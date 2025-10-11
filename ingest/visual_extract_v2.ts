/**
 * visual_extract_v2.ts
 * Hybrid approach: Render full pages to PNG, then crop regions
 * Uses pdf-to-png-converter (includes poppler) + sharp for cropping
 */
import { pdfToPng } from 'pdf-to-png-converter'
import sharp from 'sharp'
import crypto from 'crypto'
import fs from 'fs'
import path from 'path'

// Re-use types from v1
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

export interface QuestionBounds {
  questionNumber: string
  bboxes: BBox[]
  marks?: number
  level?: 'main' | 'subpart' | 'subsubpart'
}

/**
 * Render all pages of a PDF to PNG images at specified DPI
 * Returns array of PNG buffers, one per page
 */
export async function renderPdfToPngs(
  pdfBuffer: Buffer,
  targetDpi: number = 300
): Promise<Buffer[]> {
  console.log(`  Rendering PDF pages at ${targetDpi} DPI...`)
  
  const pngPages = await pdfToPng(pdfBuffer, {
    disableFontFace: false,
    useSystemFonts: true,
    viewportScale: targetDpi / 72,
    verbosityLevel: 0
  })
  
  console.log(`    ✓ Rendered ${pngPages.length} pages`)
  
  // pdfToPng returns array of {name: string, content: Buffer} objects
  return pngPages.map((page) => page.content as Buffer)
}

/**
 * Crop a region from a page PNG using sharp
 */
export async function cropRegion(
  pagePng: Buffer,
  bbox: BBox,
  targetDpi: number = 300
): Promise<VisualCrop> {
  // bbox coordinates are in PDF points (72 DPI), scale to target DPI
  const scale = targetDpi / 72
  
  const scaledBBox = {
    left: Math.floor(bbox.x * scale),
    top: Math.floor(bbox.y * scale),
    width: Math.floor(bbox.width * scale),
    height: Math.floor(bbox.height * scale)
  }
  
  // Get page dimensions to ensure bbox is within bounds
  const pageInfo = await sharp(pagePng).metadata()
  
  // Clamp bbox to page boundaries
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
  
  // Compute visual hash
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
 * Detect question boundaries with full subpart hierarchy
 * Uses the advanced bbox detector
 */
export async function detectQuestionBoundsAccurate(
  pdfBuffer: Buffer
): Promise<QuestionBounds[]> {
  const { detectAllQuestionParts } = await import('./bbox_detector.js')
  
  console.log(`  Running advanced bbox detection...`)
  const parts = await detectAllQuestionParts(pdfBuffer)
  
  // Convert to QuestionBounds format
  const bounds: QuestionBounds[] = parts.map(part => ({
    questionNumber: part.questionNumber,
    bboxes: [part.bbox],
    marks: part.marks,
    level: part.level
  }))
  
  console.log(`    ✓ Detected ${bounds.length} question parts with accurate bboxes`)
  
  return bounds
}

/**
 * Main extraction function: Render pages, detect bboxes, crop regions
 */
export async function extractAllVisualCrops(
  pdfBuffer: Buffer,
  targetDpi: number = 300
): Promise<Array<{ questionNumber: string; crop: VisualCrop; marks?: number }>> {
  console.log('🎨 Starting visual crop extraction...')
  
  // Step 1: Render all pages to PNG
  const pagePngs = await renderPdfToPngs(pdfBuffer, targetDpi)
  
  // Step 2: Detect question boundaries
  const bounds = await detectQuestionBoundsAccurate(pdfBuffer)
  
  // Step 3: Crop each question region
  console.log(`  Cropping ${bounds.length} question regions...`)
  const crops: Array<{ questionNumber: string; crop: VisualCrop; marks?: number }> = []
  
  for (const bound of bounds) {
    // For now, only handle single-page questions
    if (bound.bboxes.length === 1) {
      const bbox = bound.bboxes[0]
      const pageIndex = bbox.page - 1
      
      if (pageIndex >= 0 && pageIndex < pagePngs.length) {
        try {
          const crop = await cropRegion(pagePngs[pageIndex], bbox, targetDpi)
          crops.push({
            questionNumber: bound.questionNumber,
            crop,
            marks: bound.marks
          })
        } catch (error) {
          console.warn(`    ⚠️  Failed to crop question ${bound.questionNumber}:`, error)
        }
      }
    }
  }
  
  console.log(`  ✓ Successfully cropped ${crops.length} questions`)
  
  return crops
}

/**
 * Save page PNGs to disk for caching/debugging
 */
export async function savePagePngs(
  pdfBuffer: Buffer,
  outputDir: string,
  targetDpi: number = 300
): Promise<string[]> {
  const pagePngs = await renderPdfToPngs(pdfBuffer, targetDpi)
  
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true })
  }
  
  const savedPaths: string[] = []
  
  for (let i = 0; i < pagePngs.length; i++) {
    const filename = path.join(outputDir, `page_${String(i + 1).padStart(3, '0')}.png`)
    fs.writeFileSync(filename, pagePngs[i])
    savedPaths.push(filename)
  }
  
  console.log(`  💾 Saved ${savedPaths.length} page PNGs to ${outputDir}`)
  
  return savedPaths
}
