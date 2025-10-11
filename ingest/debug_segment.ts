/**
 * debug_segment.ts
 * Debug script to understand the fence and header structure
 */
import { parsePDFFromPath } from './parse_pdf_v2.js'
import { flattenTextItems } from './parse_pdf_v2.js'

const TEST_PDF = './data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf'

async function debugSegmentation() {
  console.log('🔍 Debug Segmentation\n')
  
  // Parse PDF
  console.log('📄 Parsing PDF...')
  const result = await parsePDFFromPath(TEST_PDF)
  const textItems = flattenTextItems(result)
  
  console.log(`  ✓ Total text items: ${textItems.length}\n`)
  
  // Find fences
  console.log('🔎 Finding fences...')
  const fencePattern = /Total\s+for\s+Question\s+(\d+)\s*=\s*(\d+)\s*marks?/i
  
  const fences = []
  for (let i = 0; i < textItems.length; i++) {
    const item = textItems[i]
    const match = item.text.match(fencePattern)
    if (match) {
      fences.push({
        index: i,
        questionNumber: parseInt(match[1]),
        totalMarks: parseInt(match[2]),
        text: item.text
      })
      console.log(`  Found: Q${match[1]} = ${match[2]} marks (index ${i})`)
    }
  }
  
  console.log(`\n  ✓ Found ${fences.length} fences\n`)
  
  // For first question, show text items before fence
  if (fences.length > 0) {
    const firstFence = fences[0]
    console.log(`📝 Text before first fence (Q${firstFence.questionNumber}):`)
    console.log(`   Looking from index 0 to ${firstFence.index}\n`)
    
    const startIndex = 0
    const endIndex = firstFence.index
    
    // Show last 30 items before fence
    const showFrom = Math.max(0, endIndex - 30)
    for (let i = showFrom; i < endIndex; i++) {
      const item = textItems[i]
      const indicator = item.text.trim() === firstFence.questionNumber.toString() ? ' ⭐' : ''
      console.log(`   [${i}]: "${item.text}"${indicator}`)
    }
    
    // Try to find question header
    console.log(`\n🔎 Looking for header pattern matching question ${firstFence.questionNumber}...`)
    const headerPattern = new RegExp(`^${firstFence.questionNumber}\\s+[A-Z]`)
    
    for (let i = startIndex; i < endIndex; i++) {
      const item = textItems[i]
      if (headerPattern.test(item.text)) {
        console.log(`   ✓ Found header at index ${i}: "${item.text}"`)
      }
    }
    
    // Also check if question number appears alone
    const qNumPattern = new RegExp(`^${firstFence.questionNumber}\\s*$`)
    for (let i = startIndex; i < endIndex; i++) {
      const item = textItems[i]
      if (qNumPattern.test(item.text.trim())) {
        console.log(`   📍 Found standalone Q number at index ${i}: "${item.text}"`)
      }
    }
  }
}

debugSegmentation().catch(console.error)
