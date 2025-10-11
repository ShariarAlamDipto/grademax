/**
 * MS Parsing Module - Simplified Approach
 * 
 * Instead of trying to match individual parts, this extracts the ENTIRE
 * markscheme for each question and links it to the question.
 */

import { parsePDFFromPath } from './parse_pdf_v2'
import type { SegmentedQuestion, MSLink, TextItem } from '../types/ingestion'

// ============================================================================
// Main Entry Point
// ============================================================================

/**
 * Parse MS PDF and link entire markscheme to each question
 */
export async function parseAndLinkMS(
  msPdfPath: string,
  segmentedQuestions: SegmentedQuestion[]
): Promise<MSLink[]> {
  console.log('📋 Parsing markscheme PDF...')
  
  // Parse MS PDF
  const msResult = await parsePDFFromPath(msPdfPath)
  
  // Flatten text items from all pages
  const textItems: TextItem[] = []
  for (const page of msResult.pages) {
    textItems.push(...page.textItems)
  }
  
  console.log(`  📄 Extracted ${textItems.length} text items from MS`)
  
  // Extract entire markscheme for each question
  const questionMarkschemes = extractQuestionMarkschemes(textItems)
  console.log(`  ✓ Extracted markschemes for ${questionMarkschemes.size} questions`)
  
  // Create links - one per question with entire MS text
  const links: MSLink[] = []
  
  for (const question of segmentedQuestions) {
    const qNum = question.questionNumber.toString()
    const msText = questionMarkschemes.get(qNum)
    
    if (msText && msText.length > 0) {
      // Create a single link for the entire question with full MS
      links.push({
        partId: `q${qNum}`, // Question-level ID
        questionNumber: question.questionNumber,
        partCode: '', // Empty for question-level MS
        confidence: 1.0, // High confidence since we matched the question
        msPoints: [],
        msSnippet: msText,
        matchDetails: {
          keyMatch: true,
          marksMatch: true,
          cueOverlap: 1.0
        }
      })
      
      console.log(`  ✓ Q${qNum}: ${msText.length} chars of markscheme`)
    } else {
      // No MS found for this question
      console.log(`  ⚠️  Q${qNum}: No markscheme found`)
      links.push({
        partId: `q${qNum}`,
        questionNumber: question.questionNumber,
        partCode: '',
        confidence: 0,
        msPoints: [],
        msSnippet: '',
        matchDetails: {
          keyMatch: false,
          marksMatch: false,
          cueOverlap: 0
        }
      })
    }
  }
  
  console.log(`\n📊 Summary:`)
  console.log(`  Total questions: ${segmentedQuestions.length}`)
  console.log(`  Linked questions: ${links.filter(l => l.confidence > 0).length}`)
  console.log(`  Average MS length: ${Math.round(links.reduce((sum, l) => sum + l.msSnippet.length, 0) / links.length)} chars`)
  
  return links
}

// ============================================================================
// Question-Level MS Extraction
// ============================================================================

/**
 * Extract entire markscheme text for each question.
 * 
 * Strategy:
 * 1. Find reliable question number markers (e.g., "1", "2 (a)", "Question 3")
 * 2. Collect all text until the next question marker
 * 3. Return map of question number -> full MS text
 */
function extractQuestionMarkschemes(textItems: TextItem[]): Map<string, string> {
  const markschemes = new Map<string, string>()
  
  let currentQuestion = ''
  let currentText: string[] = []
  
  for (let i = 0; i < textItems.length; i++) {
    const item = textItems[i]
    const text = item.text.trim()
    
    // Skip empty lines
    if (!text) continue
    
    // Check for question number at start of line
    // Patterns to match:
    // - "1" (standalone at left margin)
    // - "2 (a)" (question with part)
    // - "Question 3"
    // 
    // Must be at left margin (x < 100) to avoid page numbers
    const qMatch = text.match(/^(\d+)\b/)
    const isQuestionMarker = qMatch && (
      // Standalone question number at left margin
      (/^\d+\s*$/.test(text) && item.x < 100) ||
      // Question number with part code immediately following
      /^\d+\s+\([a-z]\)/.test(text) ||
      // "Question N"
      /^Question\s+\d+/.test(text)
    )
    
    if (isQuestionMarker && qMatch) {
      const qNum = parseInt(qMatch[1])
      
      // Only accept reasonable question numbers (1-20)
      // This filters out page numbers like "24"
      if (qNum >= 1 && qNum <= 20) {
        // Save previous question's markscheme
        if (currentQuestion && currentText.length > 0) {
          const msText = currentText.join(' ').trim()
          // Only save if we have substantial content
          if (msText.length > 20) {
            markschemes.set(currentQuestion, msText)
            console.log(`    Q${currentQuestion}: ${currentText.length} text items, ${msText.length} chars`)
          }
        }
        
        // Start new question
        currentQuestion = qNum.toString()
        currentText = [text]
      }
    } else if (currentQuestion) {
      // Skip page numbers and other noise
      // Page numbers are typically: "2", "Page 2", "*P12345*", etc.
      const isPageNumber = (
        /^Page\s+\d+/.test(text) ||
        /^\*P\d+\*/.test(text) ||
        (/^\d+$/.test(text) && item.x > 200) // Right side = page number
      )
      
      if (!isPageNumber) {
        // Accumulate text for current question
        currentText.push(text)
      }
    }
  }
  
  // Save last question
  if (currentQuestion && currentText.length > 0) {
    const msText = currentText.join(' ').trim()
    if (msText.length > 20) {
      markschemes.set(currentQuestion, msText)
      console.log(`    Q${currentQuestion}: ${currentText.length} text items, ${msText.length} chars`)
    }
  }
  
  return markschemes
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Extract mark indicators from text (e.g., "[2]", "(3)", "M1", "A1")
 * (Currently unused but kept for future granular parsing)
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function extractMarks(text: string): number {
  // Look for patterns like [2], (3), "2 marks"
  const markMatch = text.match(/\[(\d+)\]|\((\d+)\)|(\d+)\s*marks?/i)
  if (markMatch) {
    return parseInt(markMatch[1] || markMatch[2] || markMatch[3])
  }
  
  // Count mark codes (M1, A1, B1, C1)
  const codes = text.match(/\b[MABC]\d+\b/g)
  if (codes) {
    return codes.length
  }
  
  return 0
}

/**
 * Extract physics cues from text for later tagging
 */
export function extractPhysicsCues(text: string): string[] {
  const cues: string[] = []
  
  // Common physics formulas
  const formulas = text.match(/[A-Za-z]+\s*=\s*[^;]+/g)
  if (formulas) {
    cues.push(...formulas.map(f => f.trim()))
  }
  
  // Units (m, kg, N, J, W, V, A, Ω, etc.)
  const units = text.match(/\b\d+\.?\d*\s*(m|kg|N|J|W|V|A|Ω|Pa|Hz|°C|K|s)\b/g)
  if (units) {
    cues.push(...units.map(u => u.trim()))
  }
  
  // Key physics terms
  const terms = [
    'force', 'mass', 'acceleration', 'velocity', 'speed', 'energy',
    'power', 'work', 'pressure', 'density', 'temperature', 'current',
    'voltage', 'resistance', 'charge', 'field', 'wave', 'frequency'
  ]
  
  for (const term of terms) {
    const regex = new RegExp(`\\b${term}\\b`, 'i')
    if (regex.test(text)) {
      cues.push(term)
    }
  }
  
  return [...new Set(cues)] // Remove duplicates
}
