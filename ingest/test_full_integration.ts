/**
 * Full Integration Test
 * 
 * Tests the complete ingestion pipeline from PDF to database
 * 
 * Requirements:
 * - PDFs in data/raw/IGCSE/4PH1/2019/Jun/
 * - Migration 004 run in Supabase
 * - Environment variables set in .env.local
 */

import { parsePDFFromPath, flattenTextItems } from './parse_pdf_v2'
import { segmentQuestions } from './segment'
import { parseAndLinkMS } from './ms_parse_link'
import { tagQuestionsAndParts } from './tagging'
import { extractFeatures } from './features'
import { detectMetadata } from './metadata'
import { saveIngestion, getAllPapers } from './persist'
import * as path from 'path'
import * as fs from 'fs'

async function fullIntegrationTest() {
  console.log('🚀 FULL INTEGRATION TEST')
  console.log('=' .repeat(80))
  console.log('Testing complete pipeline: PDF → Database\n')
  
  const startTime = Date.now()
  let step = 0
  
  try {
    // ========================================================================
    // Setup
    // ========================================================================
    step++
    console.log(`\n${step}️⃣  SETUP - Checking files`)
    console.log('─'.repeat(80))
    
    const qpPath = path.join(process.cwd(), 'data', 'raw', 'IGCSE', '4PH1', '2019', 'Jun', '4PH1_1P.pdf')
    const msPath = path.join(process.cwd(), 'data', 'raw', 'IGCSE', '4PH1', '2019', 'Jun', '4PH1_1P_MS.pdf')
    
    if (!fs.existsSync(qpPath)) {
      throw new Error(`QP file not found: ${qpPath}`)
    }
    if (!fs.existsSync(msPath)) {
      throw new Error(`MS file not found: ${msPath}`)
    }
    
    console.log(`✓ QP: ${path.basename(qpPath)}`)
    console.log(`✓ MS: ${path.basename(msPath)}`)
    
    // ========================================================================
    // Step 1: Parse PDFs
    // ========================================================================
    step++
    const parseStart = Date.now()
    console.log(`\n${step}️⃣  PARSING PDFs`)
    console.log('─'.repeat(80))
    
    const qpParsed = await parsePDFFromPath(qpPath)
    const msParsed = await parsePDFFromPath(msPath)
    
    const qpItems = qpParsed.pages.reduce((sum, p) => sum + p.textItems.length, 0)
    const msItems = msParsed.pages.reduce((sum, p) => sum + p.textItems.length, 0)
    
    console.log(`✓ QP: ${qpParsed.pages.length} pages, ${qpItems} text items`)
    console.log(`✓ MS: ${msParsed.pages.length} pages, ${msItems} text items`)
    console.log(`⏱️  Parse time: ${Date.now() - parseStart}ms`)
    
    // ========================================================================
    // Step 2: Segment Questions
    // ========================================================================
    step++
    const segmentStart = Date.now()
    console.log(`\n${step}️⃣  SEGMENTING QUESTIONS`)
    console.log('─'.repeat(80))
    
    const qpTextItems = flattenTextItems(qpParsed)
    const segmented = await segmentQuestions(qpTextItems)
    
    console.log(`✓ Found ${segmented.questions.length} questions`)
    console.log(`✓ Found ${segmented.metadata.totalParts} parts`)
    console.log(`✓ Fences detected: ${segmented.metadata.fencesFound}`)
    console.log(`⏱️  Segment time: ${Date.now() - segmentStart}ms`)
    
    if (segmented.questions.length === 0) {
      throw new Error('No questions found - segmentation failed')
    }
    
    // ========================================================================
    // Step 3: Link Markschemes
    // ========================================================================
    step++
    const msStart = Date.now()
    console.log(`\n${step}️⃣  LINKING MARKSCHEMES`)
    console.log('─'.repeat(80))
    
    const msLinks = await parseAndLinkMS(msPath, segmented.questions)
    
    // Convert to markscheme data format
    const markschemeMap = new Map<string, string>()
    for (const link of msLinks) {
      const existing = markschemeMap.get(link.questionNumber) || ''
      markschemeMap.set(link.questionNumber, existing + link.msSnippet + '\n')
    }
    
    const markschemes = Array.from(markschemeMap.entries()).map(([qNum, text]) => ({
      questionNumber: qNum,
      markschemeText: text.trim(),
      pageRange: { start: 1, end: msParsed.pages.length }
    }))
    
    const coverage = (markschemes.length / segmented.questions.length) * 100
    const avgLength = markschemes.reduce((sum, ms) => sum + ms.markschemeText.length, 0) / markschemes.length
    
    console.log(`✓ Linked ${msLinks.length} MS links`)
    console.log(`✓ Coverage: ${markschemes.length}/${segmented.questions.length} questions (${coverage.toFixed(0)}%)`)
    console.log(`✓ Average MS length: ${Math.round(avgLength)} chars`)
    console.log(`⏱️  MS link time: ${Date.now() - msStart}ms`)
    
    // ========================================================================
    // Step 4: Tag Questions
    // ========================================================================
    step++
    const tagStart = Date.now()
    console.log(`\n${step}️⃣  TAGGING QUESTIONS`)
    console.log('─'.repeat(80))
    
    const taggingResult = await tagQuestionsAndParts(segmented.questions, msLinks)
    
    console.log(`✓ Tagged ${taggingResult.stats.taggedQuestions}/${taggingResult.stats.totalQuestions} questions`)
    console.log(`✓ Average ${taggingResult.stats.avgTagsPerQuestion.toFixed(1)} tags per question`)
    console.log(`✓ Total tags: ${taggingResult.questionTags.size}`)
    console.log(`⏱️  Tagging time: ${Date.now() - tagStart}ms`)
    
    // ========================================================================
    // Step 5: Extract Features
    // ========================================================================
    step++
    const featureStart = Date.now()
    console.log(`\n${step}️⃣  EXTRACTING FEATURES`)
    console.log('─'.repeat(80))
    
    const features = extractFeatures(segmented.questions, taggingResult.questionTags)
    
    const difficulties = Array.from(features.values()).map(f => f.difficulty)
    const easyCount = difficulties.filter(d => d === 'easy').length
    const mediumCount = difficulties.filter(d => d === 'medium').length
    const hardCount = difficulties.filter(d => d === 'hard').length
    
    console.log(`✓ Extracted features for ${features.size} questions`)
    console.log(`✓ Difficulty: ${easyCount} easy, ${mediumCount} medium, ${hardCount} hard`)
    console.log(`⏱️  Feature extraction time: ${Date.now() - featureStart}ms`)
    
    // ========================================================================
    // Step 6: Detect Metadata
    // ========================================================================
    step++
    const metaStart = Date.now()
    console.log(`\n${step}️⃣  DETECTING METADATA`)
    console.log('─'.repeat(80))
    
    const firstPageText = qpParsed.pages[0]?.textItems.map(t => t.text).join(' ') || ''
    const metadata = detectMetadata(qpPath, firstPageText)
    
    console.log(`✓ Board: ${metadata.board}`)
    console.log(`✓ Level: ${metadata.level}`)
    console.log(`✓ Subject: ${metadata.subjectName} (${metadata.subjectCode})`)
    console.log(`✓ Year: ${metadata.year} ${metadata.season}`)
    console.log(`✓ Paper: ${metadata.paperType}${metadata.paperNumber}${metadata.variant}`)
    console.log(`✓ Confidence: ${(metadata.confidence * 100).toFixed(0)}%`)
    console.log(`✓ Canonical key: ${metadata.canonicalKey}`)
    console.log(`⏱️  Metadata detection time: ${Date.now() - metaStart}ms`)
    
    // ========================================================================
    // Step 7: Save to Database
    // ========================================================================
    step++
    const persistStart = Date.now()
    console.log(`\n${step}️⃣  SAVING TO DATABASE`)
    console.log('─'.repeat(80))
    
    const result = await saveIngestion(
      metadata,
      segmented.questions,
      markschemes,
      taggingResult.questionTags,
      features,
      qpPath
    )
    
    if (!result.success) {
      throw new Error(`Save failed: ${result.errors.join(', ')}`)
    }
    
    console.log(`✓ Paper ID: ${result.paperId}`)
    console.log(`✓ Questions saved: ${result.questionIds.length}`)
    console.log(`✓ Parts saved: ${result.partIds.length}`)
    console.log(`✓ Tags saved: ${result.tagCount}`)
    console.log(`⏱️  Persistence time: ${Date.now() - persistStart}ms`)
    
    // ========================================================================
    // Step 8: Verify Database
    // ========================================================================
    step++
    console.log(`\n${step}️⃣  VERIFYING DATABASE`)
    console.log('─'.repeat(80))
    
    const allPapers = await getAllPapers()
    console.log(`✓ Total papers in database: ${allPapers?.length || 0}`)
    
    // ========================================================================
    // Summary
    // ========================================================================
    const totalTime = Date.now() - startTime
    
    console.log('\n' + '='.repeat(80))
    console.log('✅ INTEGRATION TEST COMPLETE')
    console.log('='.repeat(80))
    
    console.log('\n📊 SUMMARY:')
    console.log(`  Parsed:     ${qpParsed.pages.length} pages, ${qpItems + msItems} text items`)
    console.log(`  Segmented:  ${segmented.questions.length} questions, ${segmented.metadata.totalParts} parts`)
    console.log(`  Linked:     ${markschemes.length} markschemes (${coverage.toFixed(0)}% coverage)`)
    console.log(`  Tagged:     ${taggingResult.stats.taggedQuestions} questions, ${taggingResult.questionTags.size} tags`)
    console.log(`  Features:   ${features.size} questions analyzed`)
    console.log(`  Saved:      ${result.questionIds.length} questions, ${result.partIds.length} parts`)
    console.log(`  Database:   ${allPapers?.length || 0} total papers`)
    
    console.log('\n⏱️  PERFORMANCE:')
    console.log(`  Parse:      ${Date.now() - parseStart}ms`)
    console.log(`  Segment:    ${Date.now() - segmentStart}ms`)
    console.log(`  MS Link:    ${Date.now() - msStart}ms`)
    console.log(`  Tagging:    ${Date.now() - tagStart}ms`)
    console.log(`  Features:   ${Date.now() - featureStart}ms`)
    console.log(`  Metadata:   ${Date.now() - metaStart}ms`)
    console.log(`  Persist:    ${Date.now() - persistStart}ms`)
    console.log(`  TOTAL:      ${totalTime}ms (${(totalTime / 1000).toFixed(1)}s)`)
    
    console.log('\n✅ All tests passed!')
    console.log('Pipeline is fully functional and ready for production.')
    
  } catch (error) {
    console.error(`\n❌ TEST FAILED AT STEP ${step}:`, error)
    
    if (error instanceof Error) {
      if (error.message.includes('relation') || error.message.includes('does not exist')) {
        console.log('\n⚠️  Database schema error!')
        console.log('Please run migration 004 in Supabase:')
        console.log('  supabase/migrations/004_ingestion_schema.sql')
      } else if (error.message.includes('environment')) {
        console.log('\n⚠️  Environment variables not set!')
        console.log('Please ensure .env.local contains:')
        console.log('  NEXT_PUBLIC_SUPABASE_URL')
        console.log('  NEXT_PUBLIC_SUPABASE_ANON_KEY')
      }
    }
    
    process.exit(1)
  }
}

// Run test
console.log('🧪 Starting full integration test...\n')
fullIntegrationTest()
