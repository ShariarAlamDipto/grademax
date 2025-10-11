/**
 * Test the simplified MS parsing (question-level extraction)
 */

import { parseAndLinkMS } from './ms_parse_link'
import { segmentQuestions } from './segment'
import { parsePDFFromPath } from './parse_pdf_v2'
import type { TextItem } from '../types/ingestion'

const QP_PATH = 'c:/Users/shari/grademax/data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf'
const MS_PATH = 'c:/Users/shari/grademax/data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf'

async function testSimplifiedMSParsing() {
  console.log('🧪 Testing Simplified MS Parsing (Question-Level)\n')
  
  // Step 1: Parse and segment question paper
  console.log('📄 Step 1: Parsing question paper...')
  const qpResult = await parsePDFFromPath(QP_PATH)
  
  // Flatten text items for segmentation
  const textItems: TextItem[] = []
  for (const page of qpResult.pages) {
    textItems.push(...page.textItems)
  }
  
  const segmentResult = await segmentQuestions(textItems)
  const segmented = segmentResult.questions
  console.log(`  ✓ Segmented ${segmented.length} questions\n`)
  
  // Step 2: Parse markscheme and link
  console.log('📋 Step 2: Parsing markscheme...')
  const links = await parseAndLinkMS(MS_PATH, segmented)
  
  // Step 3: Display results
  console.log('\n📊 Results:\n')
  
  const linkedCount = links.filter(l => l.confidence > 0).length
  console.log(`✓ Total questions: ${segmented.length}`)
  console.log(`✓ Linked questions: ${linkedCount} (${Math.round(linkedCount / segmented.length * 100)}%)`)
  console.log(`✓ Average MS length: ${Math.round(links.reduce((sum, l) => sum + l.msSnippet.length, 0) / links.length)} characters\n`)
  
  // Show first 3 questions with their markschemes
  console.log('📋 Sample Markschemes (first 3 questions):\n')
  
  for (let i = 0; i < Math.min(3, links.length); i++) {
    const link = links[i]
    const question = segmented.find(q => q.questionNumber === link.questionNumber)
    
    console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`)
    console.log(`Question ${link.questionNumber}:`)
    console.log(`  Parts: ${question?.parts.length || 0}`)
    console.log(`  Confidence: ${link.confidence}`)
    console.log(`  MS Length: ${link.msSnippet.length} chars`)
    console.log(`  MS Preview:`)
    console.log(`  ${link.msSnippet.substring(0, 300)}...`)
    console.log()
  }
  
  // Validation
  console.log('\n✅ Validation:\n')
  const allLinked = links.every(l => l.confidence > 0)
  const avgLength = links.reduce((sum, l) => sum + l.msSnippet.length, 0) / links.length
  
  console.log(`  ${allLinked ? '✓' : '✗'} All questions have markschemes`)
  console.log(`  ${avgLength > 100 ? '✓' : '✗'} Average MS length > 100 chars`)
  console.log(`  ${links.length === segmented.length ? '✓' : '✗'} Link count matches question count`)
  
  console.log('\n🎉 Test complete!')
}

testSimplifiedMSParsing().catch(console.error)
