/**
 * bbox_detector.ts
 * Advanced bounding box detection for questions and subparts
 * Detects: Main questions (1, 2, 3...) + Subparts (a, b, c...) + Sub-subparts (i, ii, iii...)
 */
import type { PDFDocumentProxy } from 'pdfjs-dist'

export interface TextItem {
  text: string
  x: number
  y: number
  width?: number
  height?: number
}

export interface BBox {
  page: number
  x: number
  y: number
  width: number
  height: number
}

export interface QuestionPart {
  questionNumber: string  // "1", "2(a)", "2(a)(i)", etc.
  bbox: BBox
  marks?: number
  level: 'main' | 'subpart' | 'subsubpart'
}

/**
 * Extract text items with positions from a page using pdfjs-dist
 */
export async function extractTextItems(
  doc: PDFDocumentProxy,
  pageNum: number
): Promise<TextItem[]> {
  const page = await doc.getPage(pageNum)
  const textContent = await page.getTextContent()
  const viewport = page.getViewport({ scale: 1.0 })
  
  const items: TextItem[] = []
  
  for (const item of textContent.items) {
    if ('str' in item && 'transform' in item) {
      const tx = item.transform[4]
      const ty = item.transform[5]
      const y = viewport.height - ty - 10 // Top-down coordinate
      
      items.push({
        text: item.str,
        x: tx,
        y,
        width: item.width || 0,
        height: item.height || 10
      })
    }
  }
  
  return items
}

/**
 * Detect main question starts (1, 2, 3...)
 * Pattern: digit + space + capital letter on same line
 */
export function detectMainQuestions(items: TextItem[]): Array<{ num: string; index: number; y: number; x: number }> {
  const questions: Array<{ num: string; index: number; y: number; x: number }> = []
  
  for (let i = 0; i < items.length - 2; i++) {
    const item1 = items[i]
    const item2 = items[i + 1]
    const item3 = items[i + 2]
    
    const isDigit = /^\d{1,2}$/.test(item1.text.trim())
    const isSpace = item2.text.trim() === ''
    const startsWithCap = /^[A-Z]/.test(item3.text.trim())
    const sameLine = Math.abs(item1.y - item3.y) < 5
    
    // Check if it's at the left margin (not indented)
    const atLeftMargin = item1.x < 100
    
    if (isDigit && isSpace && startsWithCap && sameLine && atLeftMargin) {
      questions.push({
        num: item1.text.trim(),
        index: i,
        y: item1.y,
        x: item1.x
      })
    }
  }
  
  return questions
}

/**
 * Detect subparts within a question region (a), (b), (c)...
 * Pattern: "(a)" or " (a) " with proper indentation
 */
export function detectSubparts(
  items: TextItem[],
  startY: number,
  endY: number,
  parentX: number
): Array<{ code: string; index: number; y: number; x: number }> {
  const subparts: Array<{ code: string; index: number; y: number; x: number }> = []
  
  for (let i = 0; i < items.length; i++) {
    const item = items[i]
    
    // Check if within Y range
    if (item.y < startY || item.y > endY) continue
    
    // Check for subpart pattern: (a), (b), (c), (d), (e)
    const match = item.text.trim().match(/^\(([a-h])\)$/)
    if (match) {
      // Should be slightly indented from main question
      const isIndented = item.x > parentX + 10 && item.x < parentX + 80
      
      if (isIndented) {
        subparts.push({
          code: `(${match[1]})`,
          index: i,
          y: item.y,
          x: item.x
        })
      }
    }
  }
  
  return subparts
}

/**
 * Detect sub-subparts within a subpart region (i), (ii), (iii)...
 * Pattern: "(i)", "(ii)", "(iii)", "(iv)", "(v)", "(vi)"
 */
export function detectSubSubparts(
  items: TextItem[],
  startY: number,
  endY: number,
  parentX: number
): Array<{ code: string; index: number; y: number; x: number }> {
  const subsubparts: Array<{ code: string; index: number; y: number; x: number }> = []
  
  for (let i = 0; i < items.length; i++) {
    const item = items[i]
    
    // Check if within Y range
    if (item.y < startY || item.y > endY) continue
    
    // Check for sub-subpart pattern: (i), (ii), (iii), (iv), (v), (vi)
    const match = item.text.trim().match(/^\((i{1,3}|iv|v|vi)\)$/)
    if (match) {
      // Should be further indented from subpart
      const isIndented = item.x > parentX + 10
      
      if (isIndented) {
        subsubparts.push({
          code: `(${match[1]})`,
          index: i,
          y: item.y,
          x: item.x
        })
      }
    }
  }
  
  return subsubparts
}

/**
 * Extract marks from text pattern: [5] or (5) or [5 marks]
 */
export function extractMarks(items: TextItem[], startIndex: number, endIndex: number): number | undefined {
  for (let i = startIndex; i <= Math.min(endIndex, items.length - 1); i++) {
    const text = items[i].text
    const match = text.match(/[\[\(](\d+)\s*(?:marks?)?[\]\)]/)
    if (match) {
      return parseInt(match[1])
    }
  }
  return undefined
}

/**
 * Build hierarchical question structure with bboxes
 */
export async function buildQuestionHierarchy(
  doc: PDFDocumentProxy,
  pageNum: number,
  pageWidth: number,
  pageHeight: number
): Promise<QuestionPart[]> {
  const items = await extractTextItems(doc, pageNum)
  const parts: QuestionPart[] = []
  
  // Detect main questions
  const mainQuestions = detectMainQuestions(items)
  
  for (let i = 0; i < mainQuestions.length; i++) {
    const main = mainQuestions[i]
    const nextMain = mainQuestions[i + 1]
    
    // Determine question region
    const startY = main.y - 10
    const endY = nextMain ? nextMain.y : pageHeight
    
    // Create main question bbox
    const mainBBox: BBox = {
      page: pageNum,
      x: 40,
      y: startY,
      width: pageWidth - 80,
      height: endY - startY
    }
    
    // Detect subparts within this question
    const subparts = detectSubparts(items, startY, endY, main.x)
    
    if (subparts.length === 0) {
      // No subparts - single question
      const marks = extractMarks(items, main.index, nextMain?.index || items.length)
      parts.push({
        questionNumber: main.num,
        bbox: mainBBox,
        marks,
        level: 'main'
      })
    } else {
      // Has subparts - create hierarchy
      for (let j = 0; j < subparts.length; j++) {
        const sub = subparts[j]
        const nextSub = subparts[j + 1]
        
        const subStartY = sub.y - 5
        const subEndY = nextSub ? nextSub.y : endY
        
        const subBBox: BBox = {
          page: pageNum,
          x: 40,
          y: subStartY,
          width: pageWidth - 80,
          height: subEndY - subStartY
        }
        
        // Detect sub-subparts
        const subsubparts = detectSubSubparts(items, subStartY, subEndY, sub.x)
        
        if (subsubparts.length === 0) {
          // No sub-subparts
          const marks = extractMarks(items, sub.index, nextSub?.index || (nextMain?.index || items.length))
          parts.push({
            questionNumber: `${main.num}${sub.code}`,
            bbox: subBBox,
            marks,
            level: 'subpart'
          })
        } else {
          // Has sub-subparts
          for (let k = 0; k < subsubparts.length; k++) {
            const subsub = subsubparts[k]
            const nextSubSub = subsubparts[k + 1]
            
            const subsubStartY = subsub.y - 5
            const subsubEndY = nextSubSub ? nextSubSub.y : subEndY
            
            const subsubBBox: BBox = {
              page: pageNum,
              x: 40,
              y: subsubStartY,
              width: pageWidth - 80,
              height: subsubEndY - subsubStartY
            }
            
            const marks = extractMarks(items, subsub.index, nextSubSub?.index || (nextSub?.index || items.length))
            parts.push({
              questionNumber: `${main.num}${sub.code}${subsub.code}`,
              bbox: subsubBBox,
              marks,
              level: 'subsubpart'
            })
          }
        }
      }
    }
  }
  
  return parts
}

/**
 * Detect all question parts across all pages
 */
export async function detectAllQuestionParts(pdfBuffer: Buffer): Promise<QuestionPart[]> {
  const pdfjsLib = await import('pdfjs-dist/legacy/build/pdf.mjs')
  
  const data = new Uint8Array(pdfBuffer)
  const loadingTask = pdfjsLib.getDocument({ data })
  const doc = await loadingTask.promise
  
  const allParts: QuestionPart[] = []
  
  console.log(`  Analyzing ${doc.numPages} pages for question parts...`)
  
  for (let pageNum = 1; pageNum <= doc.numPages; pageNum++) {
    const page = await doc.getPage(pageNum)
    const viewport = page.getViewport({ scale: 1.0 })
    
    const parts = await buildQuestionHierarchy(doc, pageNum, viewport.width, viewport.height)
    allParts.push(...parts)
    
    if (parts.length > 0) {
      console.log(`    Page ${pageNum}: Found ${parts.length} parts`)
    }
  }
  
  console.log(`    ✓ Total: ${allParts.length} question parts detected`)
  
  return allParts
}
