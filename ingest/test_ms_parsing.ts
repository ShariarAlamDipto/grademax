/**
 * test_ms_parsing.ts
 * Test MS parsing and linking with real PDFs
 */

import { parsePDFFromPath, flattenTextItems } from './parse_pdf_v2.js'
import { segmentQuestions } from './segment.js'
import { parseAndLinkMS } from './ms_parse_link.js'

// Test files
const QUESTION_PDF = './data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf'
const MS_PDF = './data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf'

async function testMSParsing() {
  console.log('🧪 Testing MS Parsing & Linking\n')
  
  // Step 1: Parse question paper and segment
  console.log('📄 Step 1: Parsing question paper...')
  const qResult = await parsePDFFromPath(QUESTION_PDF)
  const qTextItems = flattenTextItems(qResult)
  const segmented = await segmentQuestions(qTextItems)
  
  console.log(`  ✓ Segmented ${segmented.questions.length} questions`)
  console.log(`  ✓ Total ${segmented.questions.reduce((sum: number, q) => sum + q.parts.length, 0)} parts\n`)
  
  // Step 2: Parse MS and link
  console.log('📋 Step 2: Parsing markscheme...')
  try {
    const msLinks = await parseAndLinkMS(MS_PDF, segmented.questions)
    
    // Calculate stats
    const totalParts = msLinks.length
    const linkedParts = msLinks.filter(l => l.confidence > 0).length
    const unlinkedParts = totalParts - linkedParts
    const avgConfidence = msLinks.reduce((sum, l) => sum + l.confidence, 0) / totalParts
    
    console.log(`\n📊 MS Parsing Results:`)
    console.log(`  Total links: ${totalParts}`)
    console.log(`  Linked parts: ${linkedParts} (${(linkedParts / totalParts * 100).toFixed(1)}%)`)
    console.log(`  Unlinked parts: ${unlinkedParts}`)
    console.log(`  Average confidence: ${avgConfidence.toFixed(3)}\n`)
    
    // Show sample links
    console.log('📋 Sample Links (first 5):\n')
    for (let i = 0; i < Math.min(5, msLinks.length); i++) {
      const link = msLinks[i]
      console.log(`${i + 1}. Q${link.questionNumber}${link.partCode}:`)
      console.log(`   Confidence: ${link.confidence.toFixed(3)}`)
      console.log(`   Match details: key=${link.matchDetails.keyMatch}, marks=${link.matchDetails.marksMatch}, cue=${link.matchDetails.cueOverlap.toFixed(2)}`)
      console.log(`   MS points: ${link.msPoints.length}`)
      if (link.msPoints.length > 0) {
        console.log(`   First point: "${link.msPoints[0]}"`)
      }
      console.log(`   Snippet: "${link.msSnippet.substring(0, 80)}..."\n`)
    }
    
    // Show confidence distribution
    console.log('📊 Confidence Distribution:')
    const perfect = msLinks.filter(l => l.confidence === 1.0).length
    const high = msLinks.filter(l => l.confidence >= 0.8 && l.confidence < 1.0).length
    const medium = msLinks.filter(l => l.confidence >= 0.5 && l.confidence < 0.8).length
    const low = msLinks.filter(l => l.confidence > 0 && l.confidence < 0.5).length
    const none = msLinks.filter(l => l.confidence === 0).length
    
    console.log(`  Perfect (1.0): ${perfect}`)
    console.log(`  High (0.8-0.99): ${high}`)
    console.log(`  Medium (0.5-0.79): ${medium}`)
    console.log(`  Low (0.01-0.49): ${low}`)
    console.log(`  None (0.0): ${none}\n`)
    
    // Validation
    console.log('✓ Validation Checks:')
    const checks = [
      { name: 'All questions have links', pass: msLinks.length === segmented.questions.length },
      { name: 'Link rate > 90%', pass: (linkedParts / totalParts) > 0.9 },
      { name: 'Average confidence > 0.8', pass: avgConfidence > 0.8 }
    ]
    
    for (const check of checks) {
      console.log(`  [${check.pass ? '✓' : '✗'}] ${check.name}`)
    }
    
    console.log('\n🎉 MS parsing test complete!')
    
  } catch (error) {
    console.error('❌ Error parsing MS:', error)
    if (error instanceof Error) {
      console.error('   Message:', error.message)
      console.error('   Stack:', error.stack)
    }
    
    // Check if MS file exists
    console.log('\n💡 Checking if MS file exists...')
    try {
      await parsePDFFromPath(MS_PDF)
      console.log('   ✓ MS file found and readable')
    } catch {
      console.log('   ✗ MS file not found or not readable')
      console.log(`   Expected location: ${MS_PDF}`)
      console.log('   Please ensure the markscheme PDF is in the correct location.')
    }
  }
}

testMSParsing().catch(console.error)
