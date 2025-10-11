/**
 * parse_pdf_v2.ts
 * NEW: Extract text items, images, and metadata from PDF using pdfjs-dist
 * Replaces old parse_pdf.ts with proper PDF.js integration
 */

import * as pdfjs from 'pdfjs-dist/legacy/build/pdf.mjs'
import type { TextItem as PDFTextItem } from 'pdfjs-dist/types/src/display/api'
import type { TextItem, Dimensions } from '../types/ingestion.js'

// ============================================================================
// Constants
// ============================================================================

const LOW_TEXT_DENSITY_THRESHOLD = 50 // chars per page
const OCR_CONFIDENCE_THRESHOLD = 0.6

// ============================================================================
// Types
// ============================================================================

export interface PageData {
  pageIndex: number
  textItems: TextItem[]
  images: ImageInfo[]
  dimensions: Dimensions
  textDensity: number
  ocrUsed: boolean
}

export interface ImageInfo {
  x: number
  y: number
  width: number
  height: number
  name: string
}

export interface ParseResult {
  pages: PageData[]
  metadata: {
    totalPages: number
    totalTextItems: number
    ocrPagesCount: number
    averageTextDensity: number
  }
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Check if page has low text density (likely scanned)
 */
function hasLowTextDensity(text: string): boolean {
  const charCount = text.replace(/\s/g, '').length
  return charCount < LOW_TEXT_DENSITY_THRESHOLD
}

/**
 * Normalize text item coordinates (PDF has origin at bottom-left)
 */
function normalizeTextItem(
  item: PDFTextItem & { transform?: number[]; hasEOL?: boolean },
  pageHeight: number
): TextItem {
  const transform = item.transform || [1, 0, 0, 1, 0, 0]
  const x = transform[4]
  const y = pageHeight - transform[5] // Flip Y-axis
  const width = item.width || 0
  const height = item.height || Math.abs(transform[3]) || 12 // Estimate from transform
  
  return {
    text: item.str || '',
    x,
    y,
    width,
    height,
    fontSize: height // Approximate font size from height
  }
}

/**
 * Extract images/XObjects from page
 */
async function extractImages(page: pdfjs.PDFPageProxy): Promise<ImageInfo[]> {
  const images: ImageInfo[] = []
  
  try {
    const ops = await page.getOperatorList()
    
    // Look for image operations (simplified - full implementation would parse OPS)
    for (let i = 0; i < ops.fnArray.length; i++) {
      const fn = ops.fnArray[i]
      
      // OPS.paintImageXObject = 85
      if (fn === 85) {
        const args = ops.argsArray[i]
        if (args && args.length > 0) {
          // Extract image info (simplified)
          images.push({
            x: 0,
            y: 0,
            width: 100,
            height: 100,
            name: String(args[0])
          })
        }
      }
    }
  } catch (error) {
    console.warn('Failed to extract images:', error)
  }
  
  return images
}

/**
 * OCR fallback using tesseract.js (if available)
 */
async function ocrPage(page: pdfjs.PDFPageProxy): Promise<TextItem[]> {
  console.log(`  ⚠️  OCR not implemented yet - page ${page.pageNumber} has low text density`)
  
  // TODO: Implement tesseract.js OCR
  // 1. Render page to canvas at 300 DPI
  // 2. Run tesseract.recognize()
  // 3. Extract text with bounding boxes
  // 4. Cache result by page hash
  
  return []
}

// ============================================================================
// Main Parsing Function
// ============================================================================

/**
 * Parse PDF and extract text items, images, and metadata
 */
export async function parsePDFV2(pdfBuffer: Buffer): Promise<ParseResult> {
  console.log('📄 Parsing PDF with pdfjs-dist...')
  
  // Load PDF document
  const loadingTask = pdfjs.getDocument({
    data: new Uint8Array(pdfBuffer),
    useSystemFonts: true,
    standardFontDataUrl: undefined
  })
  
  const doc = await loadingTask.promise
  const numPages = doc.numPages
  
  console.log(`  ✓ Loaded ${numPages} pages`)
  
  const pages: PageData[] = []
  let ocrPagesCount = 0
  let totalTextItems = 0
  
  // Process each page
  for (let pageNum = 1; pageNum <= numPages; pageNum++) {
    const page = await doc.getPage(pageNum)
    const viewport = page.getViewport({ scale: 1.0 })
    
    // Get text content
    const textContent = await page.getTextContent()
    const rawText = textContent.items
      .map(item => ('str' in item ? item.str : ''))
      .join(' ')
    
    const textDensity = rawText.replace(/\s/g, '').length
    const needsOCR = hasLowTextDensity(rawText)
    
    let textItems: TextItem[]
    
    if (needsOCR) {
      // Use OCR fallback
      textItems = await ocrPage(page)
      ocrPagesCount++
    } else {
      // Extract text items with positions
      textItems = textContent.items
        .filter(item => 'str' in item)
        .map(item => normalizeTextItem(item as PDFTextItem & { transform?: number[] }, viewport.height))
    }
    
    // Extract images
    const images = await extractImages(page)
    
    pages.push({
      pageIndex: pageNum - 1,
      textItems,
      images,
      dimensions: {
        width: viewport.width,
        height: viewport.height
      },
      textDensity,
      ocrUsed: needsOCR
    })
    
    totalTextItems += textItems.length
  }
  
  const averageTextDensity = pages.reduce((sum, p) => sum + p.textDensity, 0) / pages.length
  
  console.log(`  ✓ Extracted ${totalTextItems} text items from ${numPages} pages`)
  if (ocrPagesCount > 0) {
    console.log(`  ⚠️  ${ocrPagesCount} pages flagged for OCR (not yet implemented)`)
  }
  
  return {
    pages,
    metadata: {
      totalPages: numPages,
      totalTextItems,
      ocrPagesCount,
      averageTextDensity
    }
  }
}

/**
 * Parse PDF from file path
 */
export async function parsePDFFromPath(pdfPath: string): Promise<ParseResult> {
  const fs = await import('fs')
  const buffer = fs.readFileSync(pdfPath)
  return parsePDFV2(buffer)
}

/**
 * Get all text items flattened across pages
 */
export function flattenTextItems(parseResult: ParseResult): TextItem[] {
  return parseResult.pages.flatMap(page => page.textItems)
}

/**
 * Get text content as string (for doc_hash computation)
 */
export function extractFullText(parseResult: ParseResult): string {
  return parseResult.pages
    .flatMap(page => page.textItems.map(item => item.text))
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim()
}

// ============================================================================
// Exports
// ============================================================================

export { hasLowTextDensity, normalizeTextItem, OCR_CONFIDENCE_THRESHOLD }
