/**
 * PDF Builder Module - Vector-First Worksheet Generation
 * 
 * Uses pdf-lib to:
 * 1. Extract pages from source PDFs
 * 2. Draw vector boxes around selected question parts
 * 3. Combine into a single worksheet PDF
 * 4. Add header/footer with metadata
 * 
 * Strategy: Copy source pages as-is (preserves quality), overlay vector graphics
 */

import { PDFDocument, PDFPage, rgb, StandardFonts } from 'pdf-lib'
import * as fs from 'fs'
import type { SegmentedQuestion, BBox, PDFBuildResult } from '../types/ingestion'

// ============================================================================
// Types
// ============================================================================

/**
 * Internal worksheet item for PDF building
 * (Different from the database WorksheetItem)
 */
export interface BuildWorksheetItem {
  questionNumber: string
  partCode: string
  bboxList: BBox[]
  headerBBox: BBox | null
  marks: number
  topics: string[]
}

// ============================================================================
// Main Entry Point
// ============================================================================

export interface WorksheetConfig {
  title: string
  subtitle?: string
  includeAnswers: boolean
  boxColor?: { r: number; g: number; b: number }
  boxThickness?: number
  showLabels?: boolean
  headerText?: string
  footerText?: string
}

export interface BuildInput {
  sourceQPPath: string
  sourceMSPath?: string
  items: BuildWorksheetItem[]
  config: WorksheetConfig
}

/**
 * Build a worksheet PDF from selected question parts
 */
export async function buildWorksheetPDF(input: BuildInput): Promise<PDFBuildResult> {
  console.log('📄 Building worksheet PDF...')
  
  const startTime = Date.now()
  const layoutWarnings: string[] = []
  const rasterFallbackCount = 0
  let vectorRegionCount = 0
  let totalMarks = 0
  
  try {
    // Step 1: Load source PDF
    console.log(`  📖 Loading source PDF: ${input.sourceQPPath}`)
    const sourcePdfBytes = fs.readFileSync(input.sourceQPPath)
    const sourcePdf = await PDFDocument.load(sourcePdfBytes)
    
    // Step 2: Create new PDF for worksheet
    const worksheetPdf = await PDFDocument.create()
    
    // Step 3: Process each item (question or part)
    console.log(`  🔨 Processing ${input.items.length} items...`)
    const pageMapping = new Map<number, number>() // source page -> worksheet page
    
    for (const item of input.items) {
      try {
        await addItemToWorksheet(
          worksheetPdf,
          sourcePdf,
          item,
          input.config,
          pageMapping
        )
        vectorRegionCount++
        totalMarks += item.marks
      } catch (err) {
        const warning = `Failed to add item ${item.questionNumber}${item.partCode || ''}: ${err}`
        layoutWarnings.push(warning)
        console.error(`  ❌ ${warning}`)
      }
    }
    
    // Step 4: Add header and footer to all pages
    if (input.config.headerText || input.config.footerText) {
      console.log('  📝 Adding header/footer...')
      await addHeaderFooter(worksheetPdf, input.config)
    }
    
    // Step 5: Save PDF
    const pdfBytes = await worksheetPdf.save()
    const buildTime = Date.now() - startTime
    
    console.log(`  ✓ Built worksheet PDF: ${pdfBytes.length} bytes in ${buildTime}ms`)
    
    // Estimate time (rough: 1-2 mins per mark)
    const estimatedMinutes = Math.ceil(totalMarks * 1.5)
    
    return {
      studentPdf: Buffer.from(pdfBytes),
      metadata: {
        totalPages: worksheetPdf.getPageCount(),
        totalMarks,
        estimatedMinutes,
        rasterFallbackCount,
        vectorRegionCount,
        layoutWarnings
      }
    }
  } catch (err) {
    throw new Error(`PDF build failed: ${err}`)
  }
}

// ============================================================================
// Item Processing
// ============================================================================

/**
 * Add a single item (question or part) to the worksheet
 */
async function addItemToWorksheet(
  worksheetPdf: PDFDocument,
  sourcePdf: PDFDocument,
  item: BuildWorksheetItem,
  config: WorksheetConfig,
  pageMapping: Map<number, number>
): Promise<void> {
  // Determine which pages we need to copy
  const pagesToCopy = new Set<number>()
  
  if (item.headerBBox) {
    pagesToCopy.add(item.headerBBox.page)
  }
  
  if (item.bboxList) {
    for (const bbox of item.bboxList) {
      pagesToCopy.add(bbox.page)
    }
  }
  
  // Copy pages if not already copied
  for (const pageIndex of Array.from(pagesToCopy).sort()) {
    if (!pageMapping.has(pageIndex)) {
      // Copy this page to worksheet
      const [copiedPage] = await worksheetPdf.copyPages(sourcePdf, [pageIndex])
      worksheetPdf.addPage(copiedPage)
      const worksheetPageIndex = worksheetPdf.getPageCount() - 1
      pageMapping.set(pageIndex, worksheetPageIndex)
    }
  }
  
  // Draw boxes on the relevant pages
  const boxColor = config.boxColor || { r: 0, g: 0.5, b: 1 } // Default: blue
  const thickness = config.boxThickness || 2
  
  // Draw header box (if exists)
  if (item.headerBBox) {
    const worksheetPageIndex = pageMapping.get(item.headerBBox.page)
    if (worksheetPageIndex !== undefined) {
      const page = worksheetPdf.getPage(worksheetPageIndex)
      drawBox(page, item.headerBBox, boxColor, thickness)
      
      // Add label if enabled
      if (config.showLabels) {
        await addLabel(page, item.headerBBox, `Q${item.questionNumber}`, worksheetPdf)
      }
    }
  }
  
  // Draw part boxes (if exist)
  if (item.bboxList) {
    for (const bbox of item.bboxList) {
      const worksheetPageIndex = pageMapping.get(bbox.page)
      if (worksheetPageIndex !== undefined) {
        const page = worksheetPdf.getPage(worksheetPageIndex)
        drawBox(page, bbox, boxColor, thickness)
        
        // Add label if enabled
        if (config.showLabels && item.partCode) {
          await addLabel(page, bbox, `${item.questionNumber}${item.partCode}`, worksheetPdf)
        }
      }
    }
  }
}

// ============================================================================
// Drawing Functions
// ============================================================================

/**
 * Draw a box around a bounding box region
 */
function drawBox(
  page: PDFPage,
  bbox: BBox,
  color: { r: number; g: number; b: number },
  thickness: number
): void {
  const { x, y, width, height } = bbox
  const pageHeight = page.getHeight()
  
  // Convert PDF coordinates (bottom-left origin) to page coordinates
  const pdfY = pageHeight - y - height
  
  // Draw rectangle
  page.drawRectangle({
    x,
    y: pdfY,
    width,
    height,
    borderColor: rgb(color.r, color.g, color.b),
    borderWidth: thickness,
    color: rgb(1, 1, 1), // White fill (transparent effect)
    opacity: 0.1
  })
}

/**
 * Add a text label to a box
 */
async function addLabel(
  page: PDFPage,
  bbox: BBox,
  label: string,
  pdfDoc: PDFDocument
): Promise<void> {
  const font = await pdfDoc.embedFont(StandardFonts.HelveticaBold)
  const fontSize = 10
  const pageHeight = page.getHeight()
  const pdfY = pageHeight - bbox.y - bbox.height
  
  // Position label at top-left of box
  page.drawText(label, {
    x: bbox.x + 5,
    y: pdfY + bbox.height - 15,
    size: fontSize,
    font,
    color: rgb(0, 0, 1) // Blue
  })
}

/**
 * Add header and footer to all pages
 */
async function addHeaderFooter(
  pdfDoc: PDFDocument,
  config: WorksheetConfig
): Promise<void> {
  const font = await pdfDoc.embedFont(StandardFonts.Helvetica)
  const pages = pdfDoc.getPages()
  
  for (let i = 0; i < pages.length; i++) {
    const page = pages[i]
    const { height } = page.getSize()
    
    // Header
    if (config.headerText) {
      page.drawText(config.headerText, {
        x: 50,
        y: height - 30,
        size: 10,
        font,
        color: rgb(0, 0, 0)
      })
    }
    
    // Footer with page number
    const footerText = config.footerText 
      ? `${config.footerText} | Page ${i + 1} of ${pages.length}`
      : `Page ${i + 1} of ${pages.length}`
    
    page.drawText(footerText, {
      x: 50,
      y: 30,
      size: 8,
      font,
      color: rgb(0.5, 0.5, 0.5)
    })
  }
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Convert segmented questions to worksheet items
 */
export function questionsToWorksheetItems(
  questions: SegmentedQuestion[],
  includeAllParts: boolean = true
): BuildWorksheetItem[] {
  const items: BuildWorksheetItem[] = []
  
  for (const question of questions) {
    if (includeAllParts) {
      // Create items for each part
      for (const part of question.parts) {
        items.push({
          questionNumber: question.questionNumber,
          partCode: part.code,
          bboxList: part.bboxList,
          headerBBox: question.headerBBox,
          marks: part.marks || 0,
          topics: [] // Will be populated by tagging
        })
      }
    } else {
      // Create single item for whole question
      items.push({
        questionNumber: question.questionNumber,
        partCode: '',
        bboxList: question.parts.flatMap(p => p.bboxList),
        headerBBox: question.headerBBox,
        marks: question.totalMarks,
        topics: [] // Will be populated by tagging
      })
    }
  }
  
  return items
}

/**
 * Filter worksheet items by topics
 */
export function filterItemsByTopics(
  items: BuildWorksheetItem[],
  allowedTopics: string[]
): BuildWorksheetItem[] {
  return items.filter(item => 
    item.topics.some((topic: string) => allowedTopics.includes(topic))
  )
}

/**
 * Filter worksheet items by difficulty
 */
export function filterItemsByMarks(
  items: BuildWorksheetItem[],
  minMarks: number,
  maxMarks: number
): BuildWorksheetItem[] {
  return items.filter(item => 
    item.marks >= minMarks && item.marks <= maxMarks
  )
}

/**
 * Save PDF to file
 */
export function savePDF(pdfBuffer: Buffer, outputPath: string): void {
  fs.writeFileSync(outputPath, pdfBuffer)
  console.log(`✓ Saved PDF to: ${outputPath}`)
}
