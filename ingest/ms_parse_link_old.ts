/**
 * ms_parse_link.ts
 * Parse markscheme PDFs and link answers to question parts
 * 
 * Supports 3 MS formats:
 * - Table: "Question | Answer | Mark | Guidance"
 * - List: Indented parts with M1/A1/B1 codes
 * - Compact: Inline "[M1] [A1] [2]" notation
 */

import { parsePDFFromPath, flattenTextItems } from './parse_pdf_v2.js'
import type { TextItem, SegmentedQuestion, SegmentedPart, MSLink } from '../types/ingestion.js'

// ============================================================================
// Types
// ============================================================================

type MSFormat = 'table' | 'list' | 'compact' | 'unknown'

interface MSEntry {
  questionNumber: string    // "2"
  partCode: string         // "a(ii)" or "" for whole question
  rawText: string          // Full text for this part
  markPoints: MarkPoint[]  // Parsed individual points
  totalMarks: number       // Sum of all marks
  lineIndices: number[]    // Text item indices
}

interface MarkPoint {
  code: string            // "M1", "A1", "B1", "✓"
  marks: number           // Usually 1
  text: string            // "Area = πr²"
}

interface MSRawData {
  format: MSFormat
  entries: MSEntry[]
}

export interface MSParseResult {
  links: MSLink[]
  stats: {
    totalParts: number
    linkedParts: number
    unlinkedParts: number
    avgConfidence: number
    warningCount: number
  }
  warnings: string[]
}

// ============================================================================
// Main Entry Points
// ============================================================================

/**
 * Parse MS PDF and link to segmented questions
 */
export async function parseAndLinkMS(
  msPath: string,
  segmentedQuestions: SegmentedQuestion[]
): Promise<MSParseResult> {
  console.log('📋 Parsing markscheme PDF...')
  
  // Step 1: Parse MS PDF
  const msData = await parseMSPDF(msPath)
  console.log(`  ✓ Detected format: ${msData.format}`)
  console.log(`  ✓ Found ${msData.entries.length} MS entries`)
  
  // Step 2: Link to questions
  const links = linkMSToQuestions(segmentedQuestions, msData)
  
  // Step 3: Calculate stats
  const stats = calculateStats(links)
  
  // Step 4: Generate warnings
  const warnings = generateWarnings(links, segmentedQuestions, msData)
  
  return { links, stats, warnings }
}

// ============================================================================
// Phase 1: Parse MS PDF
// ============================================================================

/**
 * Parse MS PDF and extract entries
 */
async function parseMSPDF(msPath: string): Promise<MSRawData> {
  // Parse PDF
  const result = await parsePDFFromPath(msPath)
  const textItems = flattenTextItems(result)
  
  console.log(`  📄 Extracted ${textItems.length} text items from MS`)
  
  // Detect format
  const format = detectMSFormat(textItems)
  
  // Parse based on format
  let entries: MSEntry[] = []
  if (format === 'table') {
    entries = parseTableFormat(textItems)
  } else if (format === 'list') {
    entries = parseListFormat(textItems)
  } else if (format === 'compact') {
    entries = parseCompactFormat(textItems)
  } else {
    // Fallback: try list format
    console.log('  ⚠️  Unknown format, trying list parser...')
    entries = parseListFormat(textItems)
  }
  
  return { format, entries }
}

/**
 * Detect MS format from text items
 */
function detectMSFormat(textItems: TextItem[]): MSFormat {
  // Use more items for better detection
  const sample = textItems.slice(0, 500) // First 500 items
  
  // Check for list format: question numbers at left + part codes
  const qNumbers = sample.filter(item => 
    /^(\d+)\s*$/.test(item.text.trim()) && item.x < 100
  ).length
  
  const partCodes = sample.filter(item =>
    /^\([a-z]\)\s*$/.test(item.text.trim()) || /^\([ivx]+\)\s*$/.test(item.text.trim())
  ).length
  
  // List format is most common
  if (qNumbers >= 3 && partCodes >= 5) {
    return 'list'
  }
  
  // Check for actual data table (not just header)
  // Look for rows with: number | text | number pattern
  let tableRowPattern = 0
  for (let i = 0; i < sample.length - 3; i++) {
    const curr = sample[i]
    const next1 = sample[i + 1]
    const next2 = sample[i + 2]
    
    if (/^\d+$/.test(curr.text.trim()) && 
        next1.text.length > 5 && 
        /^\d+$/.test(next2.text.trim())) {
      tableRowPattern++
    }
  }
  
  if (tableRowPattern > 10) {
    return 'table'
  }
  
  // Check for compact format with inline marks
  const hasInlineMarks = sample.filter(item =>
    /\[\d+\]/.test(item.text) || /\d+\(a\).*\[\d+\]/.test(item.text)
  ).length
  
  if (hasInlineMarks > 10) {
    return 'compact'
  }
  
  // Default to list (most common)
  return 'list'
}

/**
 * Parse table format MS
 * Example: "Question | Answer | Mark | Guidance"
 */
function parseTableFormat(textItems: TextItem[]): MSEntry[] {
  const entries: MSEntry[] = []
  
  // Find table header row
  const headerIndex = textItems.findIndex(item =>
    /Question.*Mark/i.test(item.text)
  )
  
  if (headerIndex === -1) {
    console.log('  ⚠️  No table header found')
    return entries
  }
  
  // Parse rows after header
  let currentEntry: Partial<MSEntry> | null = null
  
  for (let i = headerIndex + 1; i < textItems.length; i++) {
    const item = textItems[i]
    const text = item.text.trim()
    
    // Check if this is a question number (start of row)
    const qMatch = text.match(/^(\d+)\s*$/)
    if (qMatch) {
      // Save previous entry
      if (currentEntry && currentEntry.questionNumber) {
        entries.push(completeEntry(currentEntry))
      }
      
      // Start new entry
      currentEntry = {
        questionNumber: qMatch[1],
        partCode: '',
        rawText: text,
        markPoints: [],
        totalMarks: 0,
        lineIndices: [i]
      }
      continue
    }
    
    // Check if this is a part code
    const partMatch = text.match(/^\(([a-z])\)(?:\(([ivx]+)\))?/)
    if (partMatch && currentEntry) {
      const part = partMatch[1]
      const subpart = partMatch[2]
      currentEntry.partCode = subpart ? `${part}(${subpart})` : part
      currentEntry.rawText += ' ' + text
      currentEntry.lineIndices?.push(i)
      continue
    }
    
    // Accumulate text for current entry
    if (currentEntry) {
      currentEntry.rawText += ' ' + text
      currentEntry.lineIndices?.push(i)
      
      // Extract marks
      const markMatch = text.match(/\[(\d+)\]|\((\d+)\)|^(\d+)$/)
      if (markMatch) {
        const marks = parseInt(markMatch[1] || markMatch[2] || markMatch[3])
        currentEntry.totalMarks = marks
      }
      
      // Extract mark codes
      const codeMatches = text.matchAll(/\b([MABC]\d+)\b/g)
      for (const match of codeMatches) {
        currentEntry.markPoints?.push({
          code: match[1],
          marks: 1,
          text: text
        })
      }
    }
  }
  
  // Save last entry
  if (currentEntry && currentEntry.questionNumber) {
    entries.push(completeEntry(currentEntry))
  }
  
  return entries
}

/**
 * Parse list format MS
 * Example: "1  (a) answer [1]"
 */
function parseListFormat(textItems: TextItem[]): MSEntry[] {
  const entries: MSEntry[] = []
  let currentEntry: Partial<MSEntry> | null = null
  let currentQuestionNumber = ''
  let currentMainPart = '' // Track current (a), (b), (c) for subpart context
  
  for (let i = 0; i < textItems.length; i++) {
    const item = textItems[i]
    const text = item.text.trim()
    
    // Check for question number with part: "2 (a)" or "2 (i)"
    const qWithPartMatch = text.match(/^(\d+)\s+\(([a-z]+|[ivx]+)\)/)
    if (qWithPartMatch) {
      // Save previous entry
      if (currentEntry && currentEntry.questionNumber) {
        entries.push(completeEntry(currentEntry))
      }
      
      const qNum = qWithPartMatch[1]
      const partStr = qWithPartMatch[2]
      currentQuestionNumber = qNum
      
      // Determine if it's a main part or subpart based on format
      let partCode: string
      if (/^[ivx]+$/.test(partStr)) {
        // Roman numeral after question number - treat as main part for now
        partCode = `(${partStr})`
        currentMainPart = partStr
      } else {
        // Letter - this is a main part
        partCode = `(${partStr})`
        currentMainPart = partStr
      }
      
      currentEntry = {
        questionNumber: qNum,
        partCode,
        rawText: text,
        markPoints: [],
        totalMarks: 0,
        lineIndices: [i]
      }
      continue
    }
    
    // Check for standalone question number
    const standaloneQMatch = text.match(/^(\d+)\s*$/)
    if (standaloneQMatch && item.x < 100) { // Near left margin
      // Save previous entry
      if (currentEntry && currentEntry.questionNumber) {
        entries.push(completeEntry(currentEntry))
      }
      
      currentQuestionNumber = standaloneQMatch[1]
      currentMainPart = ''
      
      currentEntry = {
        questionNumber: standaloneQMatch[1],
        partCode: '',
        rawText: text,
        markPoints: [],
        totalMarks: 0,
        lineIndices: [i]
      }
      continue
    }
    
    // Check for part marker (a), (b), (c) - could be standalone or with subpart
    // Only match single letters a-h (not roman numerals i, v, x)
    const partMatch = text.match(/^\(([a-hj-uw-z])\)(?:\s*\(([ivx]+)\))?/)
    if (partMatch && currentQuestionNumber) {
      const part = partMatch[1]
      const subpart = partMatch[2]
      
      // Save previous entry if exists
      if (currentEntry && currentEntry.partCode) {
        entries.push(completeEntry(currentEntry))
      }
      
      // Update current main part tracker
      currentMainPart = part
      
      currentEntry = {
        questionNumber: currentQuestionNumber,
        partCode: subpart ? `(${part})(${subpart})` : `(${part})`,
        rawText: text,
        markPoints: [],
        totalMarks: 0,
        lineIndices: [i]
      }
      continue
    }
    
    // Check for standalone subpart marker (i), (ii), (iii), (iv), (v)
    const subpartMatch = text.match(/^\(([ivx]+)\)/)
    if (subpartMatch && currentMainPart) {
      const subpart = subpartMatch[1]
      
      // Save previous entry
      if (currentEntry && currentEntry.partCode) {
        entries.push(completeEntry(currentEntry))
      }
      
      // Create new entry for subpart, maintaining parent context
      currentEntry = {
        questionNumber: currentQuestionNumber,
        partCode: `(${currentMainPart})(${subpart})`,
        rawText: text,
        markPoints: [],
        totalMarks: 0,
        lineIndices: [i]
      }
      continue
    }
    
    // Accumulate text for current entry
    if (currentEntry) {
      currentEntry.rawText += ' ' + text
      currentEntry.lineIndices?.push(i)
      
      // Extract marks from patterns like [2], (2), or "2 marks"
      const markMatch = text.match(/\[(\d+)\]|\((\d+)\)|(\d+)\s*marks?/)
      if (markMatch) {
        const marks = parseInt(markMatch[1] || markMatch[2] || markMatch[3])
        currentEntry.totalMarks = Math.max(currentEntry.totalMarks || 0, marks)
      }
      
      // Extract mark codes (M1, A1, B1, C1, etc.)
      const codeMatches = text.matchAll(/\b([MABC]\d+)\b/g)
      for (const match of codeMatches) {
        const codeText = text.substring(Math.max(0, match.index! - 50), match.index! + 50)
        currentEntry.markPoints?.push({
          code: match[1],
          marks: 1,
          text: codeText.trim()
        })
      }
      
      // Check for check mark (✓) - common mark indicator
      if (text.includes('✓') || text.includes('√')) {
        if (currentEntry.markPoints?.length === 0) {
          currentEntry.markPoints?.push({
            code: '✓',
            marks: 1,
            text: text
          })
        }
      }
    }
  }
  
  // Save last entry
  if (currentEntry && currentEntry.questionNumber) {
    entries.push(completeEntry(currentEntry))
  }
  
  return entries
}

/**
 * Parse compact format MS
 * Example: "1(a) answer [M1] [A1] [2]"
 */
function parseCompactFormat(textItems: TextItem[]): MSEntry[] {
  const entries: MSEntry[] = []
  
  for (let i = 0; i < textItems.length; i++) {
    const item = textItems[i]
    const text = item.text.trim()
    
    // Check for question with part: "1(a)" or "2(b)(i)"
    const qMatch = text.match(/^(\d+)\(([a-z])\)(?:\(([ivx]+)\))?/)
    if (qMatch) {
      const qNum = qMatch[1]
      const part = qMatch[2]
      const subpart = qMatch[3]
      
      // Extract marks and codes from rest of line
      const markPoints: MarkPoint[] = []
      const codeMatches = text.matchAll(/\[([MABC]\d+)\]/g)
      for (const match of codeMatches) {
        markPoints.push({
          code: match[1],
          marks: 1,
          text: text
        })
      }
      
      const totalMarkMatch = text.match(/\[(\d+)\]$/)
      const totalMarks = totalMarkMatch ? parseInt(totalMarkMatch[1]) : markPoints.length
      
      entries.push({
        questionNumber: qNum,
        partCode: subpart ? `${part}(${subpart})` : part,
        rawText: text,
        markPoints,
        totalMarks,
        lineIndices: [i]
      })
    }
  }
  
  return entries
}

/**
 * Complete partial entry with defaults
 */
function completeEntry(partial: Partial<MSEntry>): MSEntry {
  return {
    questionNumber: partial.questionNumber || '',
    partCode: partial.partCode || '',
    rawText: partial.rawText || '',
    markPoints: partial.markPoints || [],
    totalMarks: partial.totalMarks || partial.markPoints?.length || 0,
    lineIndices: partial.lineIndices || []
  }
}

// ============================================================================
// Phase 2: Link MS to Questions
// ============================================================================

/**
 * Link MS entries to segmented questions
 */
function linkMSToQuestions(
  questions: SegmentedQuestion[],
  msData: MSRawData
): MSLink[] {
  const links: MSLink[] = []
  
  for (const question of questions) {
    for (const part of question.parts) {
      // Find matching MS entry
      const msEntry = findMSEntry(msData.entries, question.questionNumber, part.code)
      
      if (msEntry) {
        // Create link with confidence
        const link = createLink(question.questionNumber, part, msEntry)
        links.push(link)
      } else {
        // Create empty link
        links.push(createEmptyLink(question.questionNumber, part))
      }
    }
  }
  
  return links
}

/**
 * Find MS entry by composite key
 */
function findMSEntry(
  entries: MSEntry[],
  questionNumber: string,
  partCode: string
): MSEntry | null {
  // Try exact match first
  const exactMatch = entries.find(e => 
    e.questionNumber === questionNumber && e.partCode === partCode
  )
  
  if (exactMatch) {
    return exactMatch
  }
  
  // Normalize both codes for comparison
  const normalizedTargetCode = normalizePartCodeForMatch(partCode)
  
  for (const entry of entries) {
    if (entry.questionNumber !== questionNumber) continue
    
    const normalizedEntryCode = normalizePartCodeForMatch(entry.partCode)
    
    // Try direct normalized match
    if (normalizedEntryCode === normalizedTargetCode) {
      return entry
    }
    
    // Try semantic match (handle MS format variations)
    if (partCodesMatch(partCode, entry.partCode)) {
      return entry
    }
  }
  
  // If looking for whole question and no part code, try empty part
  if (partCode === '') {
    const result = entries.find(e => e.questionNumber === questionNumber && e.partCode === '')
    return result || null
  }
  
  return null
}

/**
 * Normalize part code for matching
 * Examples: "(a)" → "a", "(a)(i)" → "a.i", "(i)" → "i"
 */
function normalizePartCodeForMatch(code: string): string {
  return code
    .replace(/\(/g, '')
    .replace(/\)/g, '')
    .replace(/\s/g, '')
    .toLowerCase()
    .replace(/\]\[/g, '.')
}

/**
 * Check if two part codes semantically match
 * Handles MS format variations like "(i)" vs "(a)(i)"
 */
function partCodesMatch(code1: string, code2: string): boolean {
  const norm1 = normalizePartCodeForMatch(code1)
  const norm2 = normalizePartCodeForMatch(code2)
  
  // Direct match
  if (norm1 === norm2) return true
  
  // Check if one is a substring/suffix of the other
  // e.g., "i" matches "a.i" (MS often omits the parent part)
  if (norm1.endsWith(norm2) || norm2.endsWith(norm1)) return true
  
  // Check if they share the same final component
  // e.g., "a.i" and "i" both end with "i"
  const parts1 = norm1.split('.')
  const parts2 = norm2.split('.')
  if (parts1[parts1.length - 1] === parts2[parts2.length - 1]) return true
  
  return false
}

/**
 * Create MS link with confidence calculation
 */
function createLink(
  questionNumber: string,
  part: SegmentedPart,
  msEntry: MSEntry
): MSLink {
  const confidence = calculateConfidence(part, msEntry)
  
  // Format MS points
  const msPoints = msEntry.markPoints.map(mp => 
    `${mp.code}: ${mp.text.substring(0, 100)}`
  )
  
  // Create snippet (truncate if needed)
  const msSnippet = msEntry.rawText.length > 200 
    ? msEntry.rawText.substring(0, 197) + '...'
    : msEntry.rawText
  
  // Calculate match details
  const keyMatch = part.code === msEntry.partCode
  const marksMatch = part.marks === msEntry.totalMarks
  const cueOverlap = calculateCueOverlap(part.text, msEntry.rawText)
  
  return {
    partId: `${questionNumber}${part.code}`,
    questionNumber,
    partCode: part.code,
    confidence,
    msPoints,
    msSnippet,
    matchDetails: {
      keyMatch,
      marksMatch,
      cueOverlap
    }
  }
}

/**
 * Create empty link for unmatched part
 */
function createEmptyLink(
  questionNumber: string,
  part: SegmentedPart
): MSLink {
  return {
    partId: `${questionNumber}${part.code}`,
    questionNumber,
    partCode: part.code,
    confidence: 0,
    msPoints: [],
    msSnippet: '',
    matchDetails: {
      keyMatch: false,
      marksMatch: false,
      cueOverlap: 0
    }
  }
}

// ============================================================================
// Phase 3: Confidence Calculation
// ============================================================================

/**
 * Calculate confidence score [0, 1]
 * Formula: 0.4 × key_match + 0.3 × marks_match + 0.3 × cue_overlap
 */
function calculateConfidence(
  part: SegmentedPart,
  msEntry: MSEntry
): number {
  let score = 0.0
  
  // Factor 1: Key match (40%)
  if (part.code === msEntry.partCode) {
    score += 0.4
  } else if (normalizePartCode(part.code) === normalizePartCode(msEntry.partCode)) {
    score += 0.2 // Fuzzy match
  }
  
  // Factor 2: Marks equality (30%)
  if (part.marks && msEntry.totalMarks) {
    if (part.marks === msEntry.totalMarks) {
      score += 0.3
    } else if (Math.abs(part.marks - msEntry.totalMarks) <= 1) {
      score += 0.15
    }
  } else {
    // No marks to compare, give partial credit
    score += 0.15
  }
  
  // Factor 3: Cue overlap (30%)
  if (part.text) {
    const overlap = calculateCueOverlap(part.text, msEntry.rawText)
    score += overlap * 0.3
  } else {
    score += 0.15 // No context, give partial credit
  }
  
  return Math.min(1.0, score)
}

/**
 * Normalize part code for comparison
 */
function normalizePartCode(code: string): string {
  return code.replace(/\s/g, '').toLowerCase()
}

/**
 * Calculate cue overlap using Jaccard similarity
 */
function calculateCueOverlap(questionText: string, msText: string): number {
  const qCues = extractCues(questionText)
  const msCues = extractCues(msText)
  
  if (qCues.length === 0 && msCues.length === 0) {
    return 0.5 // No cues to compare
  }
  
  // Jaccard similarity
  const intersection = qCues.filter(c => msCues.includes(c))
  const union = [...new Set([...qCues, ...msCues])]
  
  return union.length > 0 ? intersection.length / union.length : 0
}

/**
 * Extract cues (formulas, units, key terms) from text
 */
function extractCues(text: string): string[] {
  const cues: string[] = []
  const lowerText = text.toLowerCase()
  
  // 1. Extract formulas (contains =, ×, ÷, √, π, etc.)
  const formulaPattern = /[a-zA-Z]\s*=\s*[^.;]+/g
  const formulas = text.match(formulaPattern) || []
  cues.push(...formulas.map(f => f.trim().toLowerCase()))
  
  // 2. Extract units (m, kg, N, J, W, etc.)
  const unitPattern = /\d+(?:\.\d+)?\s*([a-zA-Z]{1,3})\b/g
  const units = [...text.matchAll(unitPattern)].map(m => m[1].toLowerCase())
  cues.push(...units)
  
  // 3. Extract key physics terms
  const keyTerms = [
    'energy', 'kinetic', 'potential', 'force', 'velocity', 'speed',
    'acceleration', 'mass', 'pressure', 'volume', 'temperature',
    'current', 'voltage', 'resistance', 'power', 'charge',
    'wave', 'frequency', 'wavelength', 'amplitude', 'period',
    'momentum', 'impulse', 'work', 'efficiency', 'density'
  ]
  
  for (const term of keyTerms) {
    if (lowerText.includes(term)) {
      cues.push(term)
    }
  }
  
  return [...new Set(cues)] // Remove duplicates
}

// ============================================================================
// Phase 4: Stats & Warnings
// ============================================================================

/**
 * Calculate statistics
 */
function calculateStats(links: MSLink[]) {
  const totalParts = links.length
  const linkedParts = links.filter(l => l.confidence > 0).length
  const unlinkedParts = totalParts - linkedParts
  const avgConfidence = links.reduce((sum, l) => sum + l.confidence, 0) / totalParts
  const warningCount = links.filter(l => l.confidence < 0.5).length
  
  return {
    totalParts,
    linkedParts,
    unlinkedParts,
    avgConfidence,
    warningCount
  }
}

/**
 * Generate warnings for issues
 */
function generateWarnings(
  links: MSLink[],
  _questions: SegmentedQuestion[],
  msData: MSRawData
): string[] {
  const warnings: string[] = []
  
  // Warn about unlinked parts
  for (const link of links) {
    if (link.confidence === 0) {
      warnings.push(`No MS entry found for Q${link.questionNumber}${link.partCode}`)
    } else if (link.confidence < 0.5) {
      warnings.push(`Low confidence (${link.confidence.toFixed(2)}) for Q${link.questionNumber}${link.partCode}`)
    }
  }
  
  // Warn about unused MS entries
  const usedKeys = new Set(links.map(l => `${l.questionNumber}${l.partCode}`))
  for (const entry of msData.entries) {
    const key = `${entry.questionNumber}${entry.partCode}`
    if (!usedKeys.has(key)) {
      warnings.push(`MS entry ${key} not matched to any question part`)
    }
  }
  
  return warnings
}
