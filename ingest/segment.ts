/**
 * segment.ts
 * Fence-based question segmentation using "Total for Question N = X marks"
 * 
 * NON-NEGOTIABLES:
 * - Fence boundaries are HARD - never split across a fence
 * - Context is ATOMIC - question = stem + all parts
 * - Parts are CHILDREN for marks/bbox only
 */

import type {
  BBox,
  TextItem,
  QuestionFence,
  SegmentedPart,
  SegmentedQuestion,
  SegmentationResult
} from '../types/ingestion.js'

// ============================================================================
// Constants
// ============================================================================

const FENCE_PATTERN = /Total\s+for\s+Question\s+(\d+)\s*=\s*(\d+)\s*marks?/i
const QUESTION_HEADER_PATTERN = /^(\d{1,2})\s+([A-Z])/
const PART_PATTERN = /^\(([a-h])\)/
const SUBPART_PATTERN = /^\((i{1,3}|iv|v|vi|vii|viii)\)/
const MARKS_PATTERN = /\[(\d+)\s*marks?\]/i

// Left margin thresholds for detecting part markers
const LEFT_MARGIN_THRESHOLD = 100 // pts from left edge
const SUBPART_INDENT_MIN = 30 // Additional indent for subparts

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Normalize text for matching
 */
function normalizeText(text: string): string {
  return text
    .trim()
    .replace(/\s+/g, ' ')
    .replace(/['']/g, "'")
    .replace(/[""]/g, '"')
}

/**
 * Check if text item is near left margin
 */
function isNearLeftMargin(item: TextItem, threshold: number = LEFT_MARGIN_THRESHOLD): boolean {
  return item.x < threshold
}

/**
 * Check if text item is indented (subpart)
 */
function isIndented(item: TextItem, baseX: number = 0): boolean {
  return item.x - baseX >= SUBPART_INDENT_MIN
}

/**
 * Extract marks from text
 */
function extractMarks(text: string): number | null {
  const match = text.match(MARKS_PATTERN)
  return match ? parseInt(match[1], 10) : null
}

/**
 * Find question number header (e.g., "1 ", "2 ", "12 ")
 */
function findQuestionHeader(items: TextItem[], fromIndex: number, questionNumber: string): {
  index: number
  item: TextItem | null
} {
  for (let i = fromIndex; i < items.length; i++) {
    const item = items[i]
    const text = normalizeText(item.text)
    
    // Check if this is EXACTLY the question number (standalone or with space)
    const isExactMatch = text === questionNumber || text === questionNumber + ' ' || text.startsWith(questionNumber + ' ')
    
    if (isExactMatch && isNearLeftMargin(item)) {
      // Check next few items for capital letter (question text might be separate)
      for (let j = i + 1; j < Math.min(i + 5, items.length); j++) {
        const nextItem = items[j]
        const nextText = normalizeText(nextItem.text)
        if (nextText && /^[A-Z]/.test(nextText)) {
          return { index: i, item }
        }
      }
      
      // If no capital found nearby, still accept if it's the first occurrence
      if (i === fromIndex || i === fromIndex + 1) {
        return { index: i, item }
      }
    }
    
    // Also check pattern match for "1 Some text"
    const headerMatch = text.match(QUESTION_HEADER_PATTERN)
    if (headerMatch && headerMatch[1] === questionNumber && isNearLeftMargin(item)) {
      return { index: i, item }
    }
  }
  
  return { index: -1, item: null }
}

/**
 * Find all part markers within a question range
 */
function findPartMarkers(items: TextItem[], startIndex: number, endIndex: number): Array<{
  index: number
  code: string
  type: 'part' | 'subpart'
  x: number
}> {
  const markers: Array<{ index: number; code: string; type: 'part' | 'subpart'; x: number }> = []
  
  for (let i = startIndex; i < endIndex; i++) {
    const item = items[i]
    const text = normalizeText(item.text)
    
    // Check for part marker like (a), (b)
    const partMatch = text.match(PART_PATTERN)
    if (partMatch && isNearLeftMargin(item)) {
      markers.push({
        index: i,
        code: `(${partMatch[1]})`,
        type: 'part',
        x: item.x
      })
      continue
    }
    
    // Check for subpart marker like (i), (ii), (iii)
    const subpartMatch = text.match(SUBPART_PATTERN)
    if (subpartMatch) {
      // Find parent part x position
      const parentX = markers.length > 0 && markers[markers.length - 1].type === 'part'
        ? markers[markers.length - 1].x
        : 0
      
      if (isIndented(item, parentX) || isNearLeftMargin(item, LEFT_MARGIN_THRESHOLD + 20)) {
        // Construct full code like (a)(i)
        const parentPart = markers.filter(m => m.type === 'part').pop()
        const parentCode = parentPart ? parentPart.code : '(a)' // Fallback
        const fullCode = `${parentCode}${text}`
        
        markers.push({
          index: i,
          code: fullCode,
          type: 'subpart',
          x: item.x
        })
      }
    }
  }
  
  return markers
}

/**
 * Extract text content between two indices
 */
function extractTextRange(items: TextItem[], startIndex: number, endIndex: number): string {
  return items
    .slice(startIndex, endIndex)
    .map(item => item.text)
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim()
}

/**
 * Build bbox for a text range
 */
function buildBBox(items: TextItem[], startIndex: number, endIndex: number, pageIndex: number): BBox | null {
  if (startIndex >= endIndex || startIndex < 0) return null
  
  const rangeItems = items.slice(startIndex, endIndex)
  if (rangeItems.length === 0) return null
  
  // Find bounding box
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  
  for (const item of rangeItems) {
    minX = Math.min(minX, item.x)
    minY = Math.min(minY, item.y)
    maxX = Math.max(maxX, item.x + item.width)
    maxY = Math.max(maxY, item.y + item.height)
  }
  
  // Add padding
  const padding = 10
  minX = Math.max(0, minX - padding)
  minY = Math.max(0, minY - padding)
  maxX = maxX + padding
  maxY = maxY + padding
  
  return {
    page: pageIndex,
    x: minX,
    y: minY,
    width: maxX - minX,
    height: maxY - minY
  }
}

// ============================================================================
// Main Segmentation Function
// ============================================================================

/**
 * Segment PDF into questions using fence-based approach
 * 
 * Algorithm:
 * 1. Find all fences: "Total for Question N = X marks"
 * 2. For each fence, extract question region
 * 3. Find question header and parts within region
 * 4. Build context text (stem + all parts) for tagging
 * 5. Extract header bbox (stem only) and part bboxes
 */
export async function segmentQuestions(
  textItems: TextItem[]
): Promise<SegmentationResult> {
  const questions: SegmentedQuestion[] = []
  const errors: string[] = []
  
  // Step 1: Find all fences
  const fences: QuestionFence[] = []
  
  for (let i = 0; i < textItems.length; i++) {
    const item = textItems[i]
    const text = normalizeText(item.text)
    const match = text.match(FENCE_PATTERN)
    
    if (match) {
      fences.push({
        questionNumber: match[1],
        totalMarks: parseInt(match[2], 10),
        pageIndex: Math.floor(i / 100), // Rough estimate, will refine
        yPosition: item.y,
        textIndex: i
      })
    }
  }
  
  console.log(`  📊 Found ${fences.length} question fences`)
  
  if (fences.length === 0) {
    errors.push('No question fences found - cannot segment')
    return {
      questions: [],
      metadata: {
        totalQuestions: 0,
        totalParts: 0,
        fencesFound: 0,
        ocrUsed: false,
        parsingErrors: errors
      }
    }
  }
  
  // Step 2: Process each question fence
  for (let fenceIdx = 0; fenceIdx < fences.length; fenceIdx++) {
    const fence = fences[fenceIdx]
    
    const startIndex = fenceIdx === 0 ? 0 : fences[fenceIdx - 1].textIndex + 1
    const endIndex = fence.textIndex
    
    try {
      // Find question header
      const { index: headerIndex } = findQuestionHeader(
        textItems,
        startIndex,
        fence.questionNumber
      )
      
      if (headerIndex === -1) {
        errors.push(`Question ${fence.questionNumber}: Header not found`)
        continue
      }
      
      // Find part markers
      const partMarkers = findPartMarkers(textItems, headerIndex, endIndex)
      
      // Extract stem (header to first part, or header to fence if no parts)
      const firstPartIndex = partMarkers.length > 0 ? partMarkers[0].index : endIndex
      const stemText = extractTextRange(textItems, headerIndex, firstPartIndex)
      const headerBBox = buildBBox(textItems, headerIndex, firstPartIndex, 0) // Page will be refined
      
      // Extract parts
      const parts: SegmentedPart[] = []
      
      if (partMarkers.length === 0) {
        // No parts found - treat entire question as single part
        const fullText = extractTextRange(textItems, headerIndex, endIndex)
        parts.push({
          code: '', // Empty code = whole question
          marks: fence.totalMarks,
          bboxList: headerBBox ? [headerBBox] : [],
          text: fullText,
          pageFrom: 0,
          pageTo: 0,
          hasStartMarker: false
        })
      } else {
        // Process each part
        for (let partIdx = 0; partIdx < partMarkers.length; partIdx++) {
          const marker = partMarkers[partIdx]
          const nextMarker = partMarkers[partIdx + 1]
          
          const partStartIndex = marker.index
          const partEndIndex = nextMarker ? nextMarker.index : endIndex
          
          const partText = extractTextRange(textItems, partStartIndex, partEndIndex)
          const partMarks = extractMarks(partText)
          const partBBox = buildBBox(textItems, partStartIndex, partEndIndex, 0)
          
          parts.push({
            code: marker.code,
            marks: partMarks,
            bboxList: partBBox ? [partBBox] : [],
            text: partText,
            pageFrom: 0,
            pageTo: 0,
            hasStartMarker: true
          })
        }
      }
      
      // Build full context text (stem + all parts)
      const contextText = [
        stemText,
        ...parts.map(p => p.text)
      ].join(' ').replace(/\s+/g, ' ').trim()
      
      // Create question object
      questions.push({
        questionNumber: fence.questionNumber,
        totalMarks: fence.totalMarks,
        contextText,
        headerBBox,
        headerText: stemText,
        parts,
        startPage: 0,
        endPage: 0
      })
      
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error)
      errors.push(`Question ${fence.questionNumber}: ${errorMsg}`)
    }
  }
  
  console.log(`  ✓ Segmented ${questions.length} questions with ${questions.reduce((sum, q) => sum + q.parts.length, 0)} parts`)
  
  return {
    questions,
    metadata: {
      totalQuestions: questions.length,
      totalParts: questions.reduce((sum, q) => sum + q.parts.length, 0),
      fencesFound: fences.length,
      ocrUsed: false,
      parsingErrors: errors
    }
  }
}

// ============================================================================
// Exports
// ============================================================================

export { FENCE_PATTERN, QUESTION_HEADER_PATTERN, PART_PATTERN, SUBPART_PATTERN }
