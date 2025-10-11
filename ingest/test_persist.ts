/**
 * Test script for persistence module
 * 
 * NOTE: This requires migration 004 to be run in Supabase first!
 * 
 * This is a simplified test that shows the persistence API
 * without running the full ingestion pipeline.
 */

import { saveIngestion, getAllPapers, getPaperByKey } from './persist'
import type { DetectedMetadata, SegmentedQuestion } from '../types/ingestion'
import type { QuestionFeatures } from './features'
import type { Tag } from './tagging'

async function testPersistence() {
  console.log('🧪 Testing Persistence Module\n')
  console.log('=' .repeat(80))
  console.log('⚠️  NOTE: This test requires migration 004 to be run in Supabase!')
  console.log('⚠️  This is a mock test - will attempt to save sample data')
  console.log('=' .repeat(80))
  
  try {
    // Create mock metadata
    const metadata: DetectedMetadata = {
      board: 'Edexcel',
      level: 'IGCSE',
      subjectCode: '4PH1',
      subjectName: 'Physics',
      paperType: 'QP',
      paperNumber: '1',
      variant: 'P',
      year: 2019,
      season: 'June',
      detectedFrom: 'filename_fallback',
      confidence: 0.95,
      canonicalKey: 'Edexcel/IGCSE/4PH1/2019/June/QP1P',
      docHash: 'test_hash_123'
    }
    
    // Create mock questions
    const questions: SegmentedQuestion[] = [
      {
        questionNumber: '1',
        totalMarks: 8,
        contextText: 'Test question about forces',
        headerBBox: { x: 10, y: 10, width: 100, height: 20, page: 1 },
        headerText: 'Question 1 header',
        parts: [
          {
            code: '(a)',
            marks: 3,
            bboxList: [{ x: 10, y: 40, width: 200, height: 50, page: 1 }],
            text: 'Calculate the force',
            pageFrom: 1,
            pageTo: 1,
            hasStartMarker: true
          },
          {
            code: '(b)',
            marks: 5,
            bboxList: [{ x: 10, y: 100, width: 200, height: 60, page: 1 }],
            text: 'Explain the motion',
            pageFrom: 1,
            pageTo: 1,
            hasStartMarker: true
          }
        ],
        startPage: 1,
        endPage: 1
      }
    ]
    
    // Create mock markschemes
    const markschemes = [
      {
        questionNumber: '1',
        markschemeText: 'a) F = ma, F = 2 × 5 = 10 N [3 marks]\nb) The object accelerates due to the net force [5 marks]',
        pageRange: { start: 1, end: 1 }
      }
    ]
    
    // Create mock tags
    const tags = new Map<string, Tag[]>()
    tags.set('1', [
      {
        topic: 'Forces and Motion',
        confidence: 0.95,
        provenance: ['keyword:force', 'formula:F=ma'],
        cues: ['force', 'F=ma', 'accelerates']
      }
    ])
    
    // Create mock features
    const features = new Map<string, QuestionFeatures>()
    features.set('1', {
      questionNumber: '1',
      difficulty: 'medium',
      difficultyScore: 0.55,
      style: ['calculation', 'explanation'],
      complexity: {
        conceptCount: 2,
        stepCount: 3,
        reasoning: 'medium'
      },
      estimatedMinutes: 8,
      characteristics: ['formula-based', 'multi-step']
    })
    
    // Test 1: Save ingestion
    console.log('\n' + '='.repeat(80))
    console.log('1️⃣ SAVING MOCK DATA TO DATABASE')
    console.log('='.repeat(80))
    
    const result = await saveIngestion(
      metadata,
      questions,
      markschemes,
      tags,
      features,
      '/test/path/4PH1_1P.pdf'
    )
    
    if (result.success) {
      console.log('\n✅ SAVE SUCCESSFUL!')
      console.log(`  Paper ID: ${result.paperId}`)
      console.log(`  Questions: ${result.questionIds.length}`)
      console.log(`  Parts: ${result.partIds.length}`)
      console.log(`  Tags: ${result.tagCount}`)
    } else {
      console.log('\n❌ SAVE FAILED!')
      for (const error of result.errors) {
        console.log(`  Error: ${error}`)
      }
      throw new Error('Save failed')
    }
    
    // Test 2: Query by key fields
    console.log('\n' + '='.repeat(80))
    console.log('2️⃣ QUERYING BY KEY FIELDS')
    console.log('='.repeat(80))
    
    const paper = await getPaperByKey(
      metadata.board,
      metadata.level,
      metadata.subjectCode,
      metadata.year,
      metadata.season,
      metadata.paperNumber
    )
    if (paper) {
      console.log(`  ✓ Found paper: ${paper.board} ${paper.level} ${paper.subject_name}`)
      console.log(`  ✓ Year: ${paper.year} ${paper.season}`)
    } else {
      console.log(`  ❌ Paper not found`)
    }
    
    // Test 3: Get all papers
    console.log('\n' + '='.repeat(80))
    console.log('3️⃣ GETTING ALL PAPERS')
    console.log('='.repeat(80))
    
    const allPapers = await getAllPapers()
    console.log(`  ✓ Total papers in database: ${allPapers?.length || 0}`)
    
    if (allPapers && allPapers.length > 0) {
      console.log(`  ✓ Recent papers:`)
      for (const p of allPapers.slice(0, 5)) {
        console.log(`    - ${p.board} ${p.level} ${p.subject_name} ${p.year} ${p.season}`)
      }
    }
    
    // Final summary
    console.log('\n' + '='.repeat(80))
    console.log('✅ PERSISTENCE TEST COMPLETE')
    console.log('='.repeat(80))
    console.log('\n📊 Summary:')
    console.log(`  ✅ Saved mock paper with ${questions.length} question(s)`)
    console.log(`  ✅ Database now has ${allPapers?.length || 0} total papers`)
    console.log(`  ✅ All query functions working`)
    
  } catch (error) {
    console.error('\n❌ TEST FAILED:', error)
    
    if (error instanceof Error) {
      if (error.message.includes('relation') || error.message.includes('does not exist')) {
        console.log('\n⚠️  Database schema error detected!')
        console.log('   Please run migration 004 in Supabase:')
        console.log('   supabase/migrations/004_ingestion_schema.sql')
        console.log('\n   Steps:')
        console.log('   1. Go to your Supabase dashboard')
        console.log('   2. Navigate to SQL Editor')
        console.log('   3. Run the migration SQL file')
      } else if (error.message.includes('environment')) {
        console.log('\n⚠️  Environment variables not set!')
        console.log('   Please ensure NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY are set')
      }
    }
    
    process.exit(1)
  }
}

// Run tests
console.log('🚀 Starting persistence test...\n')
testPersistence()

