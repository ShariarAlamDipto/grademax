/**
 * Test the tagging module
 */

import { parseAndLinkMS } from './ms_parse_link'
import { tagQuestionsAndParts } from './tagging'
import { segmentQuestions } from './segment'
import { parsePDFFromPath } from './parse_pdf_v2'
import type { TextItem } from '../types/ingestion'

const QP_PATH = 'c:/Users/shari/grademax/data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf'
const MS_PATH = 'c:/Users/shari/grademax/data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf'

async function testTagging() {
  console.log('🧪 Testing Tagging Module\n')
  
  // Step 1: Parse and segment question paper
  console.log('📄 Step 1: Parsing and segmenting question paper...')
  const qpResult = await parsePDFFromPath(QP_PATH)
  const textItems: TextItem[] = []
  for (const page of qpResult.pages) {
    textItems.push(...page.textItems)
  }
  const segmentResult = await segmentQuestions(textItems)
  const questions = segmentResult.questions
  console.log(`  ✓ Segmented ${questions.length} questions\n`)
  
  // Step 2: Parse markscheme and link
  console.log('📋 Step 2: Parsing markscheme and linking...')
  const msLinks = await parseAndLinkMS(MS_PATH, questions)
  const linkedCount = msLinks.filter(l => l.confidence > 0).length
  console.log(`  ✓ Linked ${linkedCount}/${questions.length} questions\n`)
  
  // Step 3: Tag questions with topics
  console.log('🏷️  Step 3: Tagging questions with topics...')
  const taggingResult = await tagQuestionsAndParts(questions, msLinks)
  
  // Step 4: Display results
  console.log('\n📊 Tagging Results:\n')
  console.log(`✓ Total questions: ${taggingResult.stats.totalQuestions}`)
  console.log(`✓ Tagged questions: ${taggingResult.stats.taggedQuestions} (${Math.round(taggingResult.stats.taggedQuestions / taggingResult.stats.totalQuestions * 100)}%)`)
  console.log(`✓ Average tags per question: ${taggingResult.stats.avgTagsPerQuestion.toFixed(1)}`)
  console.log()
  
  // Show detailed tags for first 5 questions
  console.log('📋 Detailed Tags (first 5 questions):\n')
  
  let count = 0
  for (const [qNum, tags] of taggingResult.questionTags.entries()) {
    if (count >= 5) break
    
    const question = questions.find(q => q.questionNumber === qNum)
    
    console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`)
    console.log(`Question ${qNum}:`)
    console.log(`  Parts: ${question?.parts.length || 0}`)
    console.log(`  Tags (${tags.length}):`)
    
    for (const tag of tags) {
      console.log(`    - ${tag.topic}${tag.subtopic ? ` / ${tag.subtopic}` : ''}`)
      console.log(`      Confidence: ${tag.confidence.toFixed(2)}`)
      console.log(`      Cues: ${tag.cues.slice(0, 5).join(', ')}${tag.cues.length > 5 ? '...' : ''}`)
      console.log(`      Provenance: ${tag.provenance.slice(0, 3).join(', ')}${tag.provenance.length > 3 ? '...' : ''}`)
    }
    console.log()
    
    count++
  }
  
  // Validation
  console.log('\n✅ Validation:\n')
  const tagCoverage = taggingResult.stats.taggedQuestions / taggingResult.stats.totalQuestions
  const avgTags = taggingResult.stats.avgTagsPerQuestion
  
  console.log(`  ${tagCoverage >= 0.9 ? '✓' : '✗'} Tag coverage ≥ 90% (${Math.round(tagCoverage * 100)}%)`)
  console.log(`  ${avgTags >= 1.5 ? '✓' : '✗'} Average tags per question ≥ 1.5 (${avgTags.toFixed(1)})`)
  console.log(`  ${avgTags <= 4.0 ? '✓' : '✗'} Average tags per question ≤ 4.0 (${avgTags.toFixed(1)})`)
  
  // Show topic distribution
  console.log('\n📊 Topic Distribution:\n')
  const topicCounts = new Map<string, number>()
  for (const tags of taggingResult.questionTags.values()) {
    for (const tag of tags) {
      topicCounts.set(tag.topic, (topicCounts.get(tag.topic) || 0) + 1)
    }
  }
  
  const sortedTopics = Array.from(topicCounts.entries())
    .sort((a, b) => b[1] - a[1])
  
  for (const [topic, count] of sortedTopics) {
    const percentage = Math.round(count / questions.length * 100)
    console.log(`  ${topic}: ${count} questions (${percentage}%)`)
  }
  
  console.log('\n🎉 Tagging test complete!')
}

testTagging().catch(console.error)
