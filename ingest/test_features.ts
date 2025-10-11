/**
 * Test Features Extraction Module
 */

import { extractFeatures, generateFeatureStats } from './features'
import { tagQuestionsAndParts } from './tagging'
import { parseAndLinkMS } from './ms_parse_link'
import { segmentQuestions } from './segment'
import { parsePDFFromPath } from './parse_pdf_v2'
import type { TextItem } from '../types/ingestion'

const QP_PATH = 'c:/Users/shari/grademax/data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf'
const MS_PATH = 'c:/Users/shari/grademax/data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf'

async function testFeatures() {
  console.log('🧪 Testing Features Extraction Module\n')
  
  // Step 1: Parse and segment
  console.log('📄 Step 1: Parsing and segmenting...')
  const qpResult = await parsePDFFromPath(QP_PATH)
  const textItems: TextItem[] = []
  for (const page of qpResult.pages) {
    textItems.push(...page.textItems)
  }
  const segmentResult = await segmentQuestions(textItems)
  const questions = segmentResult.questions
  console.log(`  ✓ Segmented ${questions.length} questions\n`)
  
  // Step 2: Parse MS and tag
  console.log('📋 Step 2: Parsing MS and tagging...')
  const msLinks = await parseAndLinkMS(MS_PATH, questions)
  const taggingResult = await tagQuestionsAndParts(questions, msLinks)
  console.log(`  ✓ Tagged ${taggingResult.stats.taggedQuestions} questions\n`)
  
  // Step 3: Create MS text map
  const msTexts = new Map<string, string>()
  for (const link of msLinks) {
    if (link.confidence > 0) {
      msTexts.set(link.questionNumber.toString(), link.msSnippet)
    }
  }
  
  // Step 4: Extract features
  console.log('🔍 Step 3: Extracting features...')
  const features = extractFeatures(questions, taggingResult.questionTags, msTexts)
  
  // Step 5: Display results
  console.log('\n📊 Feature Extraction Results:\n')
  
  // Show first 5 questions
  let count = 0
  for (const [qNum, feature] of features.entries()) {
    if (count >= 5) break
    
    console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`)
    console.log(`Question ${qNum}:`)
    console.log(`  Difficulty: ${feature.difficulty} (score: ${feature.difficultyScore.toFixed(2)})`)
    console.log(`  Style: ${feature.style.join(', ')}`)
    console.log(`  Complexity:`)
    console.log(`    - Concepts: ${feature.complexity.conceptCount}`)
    console.log(`    - Steps: ${feature.complexity.stepCount}`)
    console.log(`    - Reasoning: ${feature.complexity.reasoning}`)
    console.log(`  Estimated time: ${feature.estimatedMinutes} minutes`)
    if (feature.characteristics.length > 0) {
      console.log(`  Characteristics: ${feature.characteristics.join(', ')}`)
    }
    console.log()
    
    count++
  }
  
  // Step 6: Generate statistics
  console.log('📈 Overall Statistics:\n')
  const stats = generateFeatureStats(features)
  
  console.log(`  Average difficulty: ${stats.averageDifficulty.toFixed(2)}`)
  console.log(`  Average time: ${stats.averageTime.toFixed(1)} minutes`)
  console.log()
  
  console.log(`  Style distribution:`)
  for (const [style, count] of Object.entries(stats.styleDistribution)) {
    if (count > 0) {
      console.log(`    - ${style}: ${count} questions`)
    }
  }
  console.log()
  
  console.log(`  Top characteristics:`)
  const topChars = Object.entries(stats.characteristicsFrequency)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
  for (const [char, count] of topChars) {
    console.log(`    - ${char}: ${count} questions`)
  }
  
  // Validation
  console.log('\n✅ Validation:\n')
  console.log(`  ${features.size === questions.length ? '✓' : '✗'} All questions have features`)
  console.log(`  ${stats.averageDifficulty > 0 && stats.averageDifficulty <= 1 ? '✓' : '✗'} Difficulty scores in valid range`)
  console.log(`  ${stats.averageTime > 0 ? '✓' : '✗'} Time estimates are positive`)
  
  const allHaveStyle = Array.from(features.values()).every(f => f.style.length > 0)
  console.log(`  ${allHaveStyle ? '✓' : '✗'} All questions have at least one style`)
  
  console.log('\n🎉 Features extraction test complete!')
}

testFeatures().catch(console.error)
