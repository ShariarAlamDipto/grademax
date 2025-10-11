/**
 * test_segmentation.ts
 * Test fence-based segmentation with real PDF
 */

import { parsePDFFromPath, flattenTextItems } from './parse_pdf_v2.js'
import { segmentQuestions } from './segment.js'
import fs from 'fs'

async function main() {
  console.log('🧪 Testing Fence-Based Segmentation\n')
  
  // Test with sample paper
  const testPdfPath = './data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf'
  
  if (!fs.existsSync(testPdfPath)) {
    console.error(`❌ Test PDF not found: ${testPdfPath}`)
    console.log('Please ensure the file exists or update the path')
    process.exit(1)
  }
  
  console.log(`📄 Testing with: ${testPdfPath}\n`)
  
  try {
    // Step 1: Parse PDF
    console.log('Step 1: Parsing PDF...')
    const parseResult = await parsePDFFromPath(testPdfPath)
    console.log(`  ✓ Parsed ${parseResult.metadata.totalPages} pages`)
    console.log(`  ✓ Extracted ${parseResult.metadata.totalTextItems} text items`)
    console.log(`  ✓ Average text density: ${parseResult.metadata.averageTextDensity.toFixed(0)} chars/page`)
    
    if (parseResult.metadata.ocrPagesCount > 0) {
      console.log(`  ⚠️  ${parseResult.metadata.ocrPagesCount} pages need OCR (not implemented)`)
    }
    
    console.log()
    
    // Step 2: Flatten text items
    console.log('Step 2: Flattening text items...')
    const allTextItems = flattenTextItems(parseResult)
    console.log(`  ✓ Total ${allTextItems.length} text items across all pages\n`)
    
    // Step 3: Segment into questions
    console.log('Step 3: Segmenting questions...')
    const segmentResult = await segmentQuestions(allTextItems)
    
    console.log()
    console.log('📊 Segmentation Results:')
    console.log(`  Total questions: ${segmentResult.metadata.totalQuestions}`)
    console.log(`  Total parts: ${segmentResult.metadata.totalParts}`)
    console.log(`  Fences found: ${segmentResult.metadata.fencesFound}`)
    
    if (segmentResult.metadata.parsingErrors.length > 0) {
      console.log(`  ⚠️  Errors: ${segmentResult.metadata.parsingErrors.length}`)
      segmentResult.metadata.parsingErrors.forEach(err => {
        console.log(`     - ${err}`)
      })
    }
    
    console.log()
    
    // Step 4: Display question details
    console.log('📋 Question Details:\n')
    
    for (const question of segmentResult.questions.slice(0, 5)) { // Show first 5
      console.log(`Question ${question.questionNumber}:`)
      console.log(`  Total marks: ${question.totalMarks}`)
      console.log(`  Parts: ${question.parts.length}`)
      console.log(`  Header text: ${question.headerText.substring(0, 80)}...`)
      console.log(`  Context length: ${question.contextText.length} chars`)
      
      if (question.parts.length > 0) {
        console.log(`  Part breakdown:`)
        question.parts.forEach(part => {
          const code = part.code || '(whole question)'
          const marks = part.marks !== null ? `${part.marks} marks` : 'marks unknown'
          const hasMarker = part.hasStartMarker ? '✓' : '✗'
          console.log(`    ${code}: ${marks} [marker: ${hasMarker}]`)
        })
      }
      
      console.log()
    }
    
    if (segmentResult.questions.length > 5) {
      console.log(`... and ${segmentResult.questions.length - 5} more questions\n`)
    }
    
    // Step 5: Validation checks
    console.log('✓ Validation Checks:')
    
    const allQuestionsHaveContext = segmentResult.questions.every(q => q.contextText.length > 0)
    console.log(`  [${allQuestionsHaveContext ? '✓' : '✗'}] All questions have context text`)
    
    const allQuestionsHaveMarks = segmentResult.questions.every(q => q.totalMarks > 0)
    console.log(`  [${allQuestionsHaveMarks ? '✓' : '✗'}] All questions have total marks`)
    
    const allPartsHaveBbox = segmentResult.questions.every(q => 
      q.parts.every(p => p.bboxList.length > 0)
    )
    console.log(`  [${allPartsHaveBbox ? '✓' : '✗'}] All parts have bounding boxes`)
    
    const noEmptyParts = segmentResult.questions.every(q => q.parts.length > 0)
    console.log(`  [${noEmptyParts ? '✓' : '✗'}] No questions have zero parts`)
    
    console.log()
    console.log('🎉 Segmentation test complete!')
    
  } catch (error) {
    console.error('❌ Test failed:', error)
    if (error instanceof Error) {
      console.error(error.stack)
    }
    process.exit(1)
  }
}

main()
