/**
 * Metadata Detection Module
 * 
 * Extracts metadata from PDF filenames and content:
 * - Board (Cambridge, Edexcel, AQA, OCR)
 * - Level (IGCSE, IAL, A-Level, GCSE)
 * - Subject code and name
 * - Paper type (QP/MS)
 * - Year and season
 * - Paper number and variant
 */

import type { DetectedMetadata } from '../types/ingestion'
import * as path from 'path'

// ============================================================================
// Main Entry Point
// ============================================================================

/**
 * Detect metadata from PDF path and content
 */
export function detectMetadata(
  pdfPath: string,
  firstPageText?: string
): DetectedMetadata {
  console.log('🔍 Detecting metadata...')
  
  const filename = path.basename(pdfPath)
  const dirname = path.dirname(pdfPath)
  
  // Detect from filename (primary source)
  const filenameMetadata = detectFromFilename(filename)
  
  // Detect from directory structure
  const dirMetadata = detectFromDirectory(dirname)
  
  // Detect from content (fallback)
  const contentMetadata = firstPageText ? detectFromContent(firstPageText) : {}
  
  // Merge metadata (filename > directory > content)
  const board = filenameMetadata.board || dirMetadata.board || contentMetadata.board || 'Unknown'
  const level = filenameMetadata.level || dirMetadata.level || contentMetadata.level || 'Unknown'
  const subjectCode = filenameMetadata.subjectCode || dirMetadata.subjectCode || contentMetadata.subjectCode || 'Unknown'
  const subjectName = filenameMetadata.subjectName || dirMetadata.subjectName || contentMetadata.subjectName || 'Unknown'
  const paperType = filenameMetadata.paperType || 'QP'
  const yearStr = filenameMetadata.year || dirMetadata.year || contentMetadata.year || '2024'
  const year = parseInt(yearStr)
  const season = filenameMetadata.season || dirMetadata.season || contentMetadata.season || 'Unknown'
  const paperNumber = filenameMetadata.paperNumber || '1'
  const variant = filenameMetadata.variant || 'P'
  const confidence = calculateConfidence(filenameMetadata, dirMetadata, contentMetadata)
  
  // Determine detection source
  let detectedFrom: 'page1' | 'ocr' | 'filename_fallback' = 'filename_fallback'
  if (firstPageText && contentMetadata.board) {
    detectedFrom = 'page1'
  } else if (filenameMetadata.board) {
    detectedFrom = 'filename_fallback'
  }
  
  // Create canonical key (for storage path)
  const canonicalKey = `${board}/${level}/${subjectCode}/${year}/${season}/${paperType}${paperNumber}${variant}`
  
  // Create document hash placeholder (will be computed from full PDF later)
  const docHash = 'placeholder'
  
  const metadata: DetectedMetadata = {
    board,
    level,
    subjectCode,
    subjectName,
    paperType,
    paperNumber,
    variant,
    year,
    season,
    detectedFrom,
    confidence,
    canonicalKey,
    docHash
  }
  
  console.log(`  ✓ Board: ${metadata.board}`)
  console.log(`  ✓ Level: ${metadata.level}`)
  console.log(`  ✓ Subject: ${metadata.subjectName} (${metadata.subjectCode})`)
  console.log(`  ✓ Type: ${metadata.paperType}`)
  if (metadata.year) console.log(`  ✓ Year: ${metadata.year}`)
  if (metadata.season) console.log(`  ✓ Season: ${metadata.season}`)
  if (metadata.paperNumber) console.log(`  ✓ Paper: ${metadata.paperNumber}`)
  console.log(`  ✓ Confidence: ${(metadata.confidence * 100).toFixed(0)}%`)
  
  return metadata
}

// ============================================================================
// Filename Detection
// ============================================================================

interface PartialMetadata {
  board?: string
  level?: string
  subjectCode?: string
  subjectName?: string
  paperType?: 'QP' | 'MS'
  year?: string
  season?: string
  paperNumber?: string
  variant?: string
}

/**
 * Detect metadata from filename
 * 
 * Common patterns:
 * - Edexcel IGCSE: 4PH1_1P_Jun_2019.pdf, 4PH1_1P_MS_Jun_2019.pdf
 * - Cambridge IGCSE: 0625_s19_qp_11.pdf, 0625_s19_ms_11.pdf
 * - AQA GCSE: 8463-1H-QP-JUN19.pdf
 */
function detectFromFilename(filename: string): PartialMetadata {
  const metadata: PartialMetadata = {}
  
  // Remove extension
  const name = filename.replace(/\.pdf$/i, '')
  
  // Detect paper type (MS vs QP)
  if (/MS|markscheme|mark.?scheme/i.test(name)) {
    metadata.paperType = 'MS'
  } else if (/QP|question.?paper/i.test(name)) {
    metadata.paperType = 'QP'
  }
  
  // Pattern 1: Edexcel IGCSE (e.g., 4PH1_1P_Jun_2019.pdf)
  const edexcelMatch = name.match(/(\d[A-Z]{2,3}\d)_(\d[A-Z]+)(?:_MS)?.*?([A-Z][a-z]{2}).*?(\d{4})/i)
  if (edexcelMatch) {
    metadata.board = 'Edexcel'
    metadata.level = 'IGCSE'
    metadata.subjectCode = edexcelMatch[1]
    metadata.paperNumber = edexcelMatch[2]
    metadata.season = seasonCodeToName(edexcelMatch[3])
    metadata.year = edexcelMatch[4]
    metadata.subjectName = edexcelCodeToSubject(edexcelMatch[1])
    return metadata
  }
  
  // Pattern 2: Cambridge IGCSE (e.g., 0625_s19_qp_11.pdf)
  const cambridgeMatch = name.match(/(\d{4})_([swm])(\d{2})_(qp|ms)_(\d+)/i)
  if (cambridgeMatch) {
    metadata.board = 'Cambridge'
    metadata.level = 'IGCSE'
    metadata.subjectCode = cambridgeMatch[1]
    metadata.season = cambridgeSeasonCode(cambridgeMatch[2])
    metadata.year = '20' + cambridgeMatch[3]
    metadata.paperType = cambridgeMatch[4].toUpperCase() === 'QP' ? 'QP' : 'MS'
    metadata.paperNumber = cambridgeMatch[5]
    metadata.subjectName = cambridgeCodeToSubject(cambridgeMatch[1])
    return metadata
  }
  
  // Pattern 3: AQA GCSE (e.g., 8463-1H-QP-JUN19.pdf)
  const aqaMatch = name.match(/(\d{4})-(\d[HF])-([QM][PS])-([A-Z]{3})(\d{2})/i)
  if (aqaMatch) {
    metadata.board = 'AQA'
    metadata.level = 'GCSE'
    metadata.subjectCode = aqaMatch[1]
    metadata.paperNumber = aqaMatch[2]
    metadata.paperType = aqaMatch[3].toUpperCase().includes('Q') ? 'QP' : 'MS'
    metadata.season = seasonCodeToName(aqaMatch[4])
    metadata.year = '20' + aqaMatch[5]
    metadata.subjectName = aqaCodeToSubject(aqaMatch[1])
    return metadata
  }
  
  // Pattern 4: Generic subject code detection
  const subjectCodeMatch = name.match(/\b(\d[A-Z]{2,3}\d|\d{4})\b/i)
  if (subjectCodeMatch) {
    metadata.subjectCode = subjectCodeMatch[1]
    metadata.subjectName = edexcelCodeToSubject(subjectCodeMatch[1]) || 
                           cambridgeCodeToSubject(subjectCodeMatch[1]) ||
                           'Unknown'
  }
  
  // Pattern 5: Year detection
  const yearMatch = name.match(/\b(20\d{2})\b/)
  if (yearMatch) {
    metadata.year = yearMatch[1]
  }
  
  // Pattern 6: Season detection
  if (/jan|january/i.test(name)) metadata.season = 'January'
  else if (/feb|february/i.test(name)) metadata.season = 'February'
  else if (/mar|march/i.test(name)) metadata.season = 'March'
  else if (/may/i.test(name)) metadata.season = 'May'
  else if (/jun|june/i.test(name)) metadata.season = 'June'
  else if (/oct|october/i.test(name)) metadata.season = 'October'
  else if (/nov|november/i.test(name)) metadata.season = 'November'
  else if (/sum|summer/i.test(name)) metadata.season = 'Summer'
  else if (/win|winter/i.test(name)) metadata.season = 'Winter'
  
  return metadata
}

// ============================================================================
// Directory Detection
// ============================================================================

/**
 * Detect metadata from directory structure
 * e.g., /data/raw/IGCSE/4PH1/2019/Jun/
 */
function detectFromDirectory(dirPath: string): PartialMetadata {
  const metadata: PartialMetadata = {}
  
  const parts = dirPath.split(/[/\\]/)
  
  // Look for level indicators
  for (const part of parts) {
    if (/igcse/i.test(part)) metadata.level = 'IGCSE'
    else if (/gcse/i.test(part) && !/igcse/i.test(part)) metadata.level = 'GCSE'
    else if (/ial|international.*a.*level/i.test(part)) metadata.level = 'IAL'
    else if (/a.?level/i.test(part)) metadata.level = 'A-Level'
  }
  
  // Look for board
  for (const part of parts) {
    if (/edexcel|pearson/i.test(part)) metadata.board = 'Edexcel'
    else if (/cambridge|cie|caie/i.test(part)) metadata.board = 'Cambridge'
    else if (/aqa/i.test(part)) metadata.board = 'AQA'
    else if (/ocr/i.test(part)) metadata.board = 'OCR'
  }
  
  // Look for subject code
  for (const part of parts) {
    if (/^\d[A-Z]{2,3}\d$|^\d{4}$/i.test(part)) {
      metadata.subjectCode = part
      break
    }
  }
  
  // Look for year
  for (const part of parts) {
    if (/^20\d{2}$/.test(part)) {
      metadata.year = part
      break
    }
  }
  
  // Look for season
  for (const part of parts) {
    if (/^(jan|feb|mar|may|jun|oct|nov)$/i.test(part)) {
      metadata.season = seasonCodeToName(part)
      break
    } else if (/^(january|february|march|may|june|october|november|summer|winter)$/i.test(part)) {
      metadata.season = part.charAt(0).toUpperCase() + part.slice(1).toLowerCase()
      break
    }
  }
  
  return metadata
}

// ============================================================================
// Content Detection
// ============================================================================

/**
 * Detect metadata from PDF content (fallback)
 */
function detectFromContent(text: string): PartialMetadata {
  const metadata: PartialMetadata = {}
  
  // Board detection
  if (/edexcel|pearson/i.test(text)) metadata.board = 'Edexcel'
  else if (/cambridge|cie|caie/i.test(text)) metadata.board = 'Cambridge'
  else if (/aqa/i.test(text)) metadata.board = 'AQA'
  else if (/ocr/i.test(text)) metadata.board = 'OCR'
  
  // Level detection
  if (/igcse|international gcse/i.test(text)) metadata.level = 'IGCSE'
  else if (/gcse/i.test(text) && !/igcse/i.test(text)) metadata.level = 'GCSE'
  else if (/international.*a.*level|ial/i.test(text)) metadata.level = 'IAL'
  else if (/a.?level|gce/i.test(text)) metadata.level = 'A-Level'
  
  // Subject detection
  if (/physics/i.test(text)) metadata.subjectName = 'Physics'
  else if (/chemistry/i.test(text)) metadata.subjectName = 'Chemistry'
  else if (/biology/i.test(text)) metadata.subjectName = 'Biology'
  else if (/mathematics|maths/i.test(text)) metadata.subjectName = 'Mathematics'
  
  return metadata
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Convert season code to full name
 */
function seasonCodeToName(code: string): string {
  const lower = code.toLowerCase()
  if (lower === 'jan') return 'January'
  if (lower === 'feb') return 'February'
  if (lower === 'mar') return 'March'
  if (lower === 'may') return 'May'
  if (lower === 'jun') return 'June'
  if (lower === 'oct') return 'October'
  if (lower === 'nov') return 'November'
  if (lower === 'sum') return 'Summer'
  if (lower === 'win') return 'Winter'
  return code
}

/**
 * Convert Cambridge season code
 */
function cambridgeSeasonCode(code: string): string {
  if (code.toLowerCase() === 's') return 'Summer'
  if (code.toLowerCase() === 'w') return 'Winter'
  if (code.toLowerCase() === 'm') return 'March'
  return code
}

/**
 * Map Edexcel subject code to name
 */
function edexcelCodeToSubject(code: string): string {
  const codeMap: Record<string, string> = {
    '4PH1': 'Physics',
    '4CH1': 'Chemistry',
    '4BI1': 'Biology',
    '4MA1': 'Mathematics',
    '4SC1': 'Science (Double Award)',
    '1PH0': 'Physics (9-1)',
    '1CH0': 'Chemistry (9-1)',
    '1BI0': 'Biology (9-1)',
    '1MA1': 'Mathematics (9-1)'
  }
  return codeMap[code.toUpperCase()] || 'Unknown'
}

/**
 * Map Cambridge subject code to name
 */
function cambridgeCodeToSubject(code: string): string {
  const codeMap: Record<string, string> = {
    '0625': 'Physics',
    '0620': 'Chemistry',
    '0610': 'Biology',
    '0580': 'Mathematics',
    '0972': 'Physics (9-1)',
    '0971': 'Chemistry (9-1)',
    '0970': 'Biology (9-1)'
  }
  return codeMap[code] || 'Unknown'
}

/**
 * Map AQA subject code to name
 */
function aqaCodeToSubject(code: string): string {
  const codeMap: Record<string, string> = {
    '8463': 'Physics',
    '8462': 'Chemistry',
    '8461': 'Biology',
    '8300': 'Mathematics',
    '8464': 'Combined Science Trilogy'
  }
  return codeMap[code] || 'Unknown'
}

/**
 * Calculate confidence score
 */
function calculateConfidence(
  filename: PartialMetadata,
  directory: PartialMetadata,
  content: PartialMetadata
): number {
  let score = 0
  let maxScore = 0
  
  // Board (weight: 0.2)
  maxScore += 0.2
  if (filename.board) score += 0.2
  else if (directory.board) score += 0.15
  else if (content.board) score += 0.1
  
  // Level (weight: 0.2)
  maxScore += 0.2
  if (filename.level) score += 0.2
  else if (directory.level) score += 0.15
  else if (content.level) score += 0.1
  
  // Subject (weight: 0.3)
  maxScore += 0.3
  if (filename.subjectCode && filename.subjectName !== 'Unknown') score += 0.3
  else if (directory.subjectCode) score += 0.2
  else if (content.subjectName) score += 0.1
  
  // Year/Season (weight: 0.2)
  maxScore += 0.2
  if (filename.year) score += 0.1
  if (filename.season || directory.season) score += 0.1
  
  // Paper type (weight: 0.1)
  maxScore += 0.1
  if (filename.paperType) score += 0.1
  
  return Math.min(score / maxScore, 1)
}
