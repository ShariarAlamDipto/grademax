/**
 * Simple ingestion script without sharp dependency
 * Extracts text and questions from PDFs and saves to database
 */

import 'dotenv/config'
import { createClient } from '@supabase/supabase-js'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import { dirname } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// Load environment
const SUPABASE_URL = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL
const SUPABASE_SERVICE_ROLE = process.env.SUPABASE_SERVICE_ROLE || process.env.SUPABASE_ANON_KEY

if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE) {
  console.error('❌ Missing Supabase credentials')
  console.error('  SUPABASE_URL:', SUPABASE_URL ? 'Found' : 'Missing')
  console.error('  SUPABASE_SERVICE_ROLE:', SUPABASE_SERVICE_ROLE ? 'Found' : 'Missing')
  process.exit(1)
}

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE)

console.log('🚀 Simple PDF Ingestion Starting...\n')

// Find the Physics subject
async function getPhysicsSubject() {
  const { data, error } = await supabase
    .from('subjects')
    .select('id, code, name, level')
    .eq('code', '4PH1')
    .eq('level', 'IGCSE')
    .single()
  
  if (error) throw new Error(`Failed to find Physics subject: ${error.message}`)
  if (!data) throw new Error('Physics subject not found in database')
  
  console.log(`✅ Found subject: ${data.level} ${data.name} (${data.code})`)
  console.log(`   Subject ID: ${data.id}\n`)
  return data
}

// Find or create paper record
async function createPaperRecord(subjectId: string) {
  // Check if paper already exists
  const { data: existing } = await supabase
    .from('papers')
    .select('id')
    .eq('subject_code', '4PH1')
    .eq('year', 2019)
    .eq('season', 'June')
    .eq('paper_number', 1)
    .single()
  
  if (existing) {
    console.log(`ℹ️  Paper already exists: ${existing.id}`)
    console.log(`   Deleting old data to re-ingest...\n`)
    
    // Delete old questions
    await supabase
      .from('questions')
      .delete()
      .eq('paper_id', existing.id)
    
    return existing
  }
  
  // Create new paper record
  const { data: paper, error } = await supabase
    .from('papers')
    .insert({
      subject_id: subjectId,
      board: 'Edexcel',
      level: 'IGCSE',
      subject_code: '4PH1',
      subject_name: 'Physics',
      year: 2019,
      season: 'June',
      paper_number: 1,
      paper_type: 'QP',
      variant: 'P',
      pdf_path: 'data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf'
    })
    .select('id')
    .single()
  
  if (error) throw new Error(`Failed to create paper: ${error.message}`)
  
  console.log(`✅ Created paper record: ${paper.id}\n`)
  return paper
}

// Extract text from PDF using pdf-parse
async function extractTextFromPDF(pdfPath: string): Promise<string> {
  // @ts-expect-error - pdf-parse types are incomplete
  const pdfParse = await import('pdf-parse/lib/pdf-parse.js')
  const dataBuffer = fs.readFileSync(pdfPath)
  const data = await pdfParse.default(dataBuffer)
  return data.text
}

// Simple question splitter
function splitIntoQuestions(text: string): Array<{number: string, text: string, marks?: number}> {
  const questions = []
  
  // Match patterns like: "1", "2", "3 (a)", "4 (b) (i)"
  // Followed by question text
  // Ends with marks like [2] or (2 marks)
  
  const lines = text.split('\n')
  let currentQuestion: {number: string, text: string, marks?: number} | null = null
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    
    // Check if this line starts a new question
    const questionMatch = line.match(/^(\d+(?:\s*\([a-z]\)(?:\s*\([ivx]+\))?)?)\s+(.*)/)
    
    if (questionMatch) {
      // Save previous question
      if (currentQuestion && currentQuestion.text.length > 20) {
        questions.push(currentQuestion)
      }
      
      // Start new question
      currentQuestion = {
        number: questionMatch[1].trim(),
        text: questionMatch[2].trim()
      }
    } else if (currentQuestion && line) {
      // Continue current question
      currentQuestion.text += ' ' + line
    }
    
    // Check for marks
    if (currentQuestion) {
      const marksMatch = currentQuestion.text.match(/\[(\d+)\]|(\d+)\s*marks?/i)
      if (marksMatch) {
        currentQuestion.marks = parseInt(marksMatch[1] || marksMatch[2])
      }
    }
  }
  
  // Save last question
  if (currentQuestion && currentQuestion.text.length > 20) {
    questions.push(currentQuestion)
  }
  
  return questions
}

// Calculate simple difficulty
function calculateDifficulty(marks?: number): number {
  if (!marks) return 2 // medium
  if (marks <= 2) return 1 // easy
  if (marks <= 4) return 2 // medium
  return 3 // hard
}

// Save questions to database
async function saveQuestions(paperId: string, questions: Array<{number: string, text: string, marks?: number}>) {
  console.log(`📝 Saving ${questions.length} questions to database...\n`)
  
  for (const q of questions) {
    const { error } = await supabase
      .from('questions')
      .insert({
        paper_id: paperId,
        question_number: q.number,
        text: q.text,
        marks: q.marks,
        difficulty: calculateDifficulty(q.marks),
        context_text: q.text.substring(0, 200) // First 200 chars for search
      })
      .select('id')
      .single()
    
    if (error) {
      console.error(`   ❌ Failed to save question ${q.number}: ${error.message}`)
    } else {
      console.log(`   ✅ Saved Q${q.number} (${q.marks || '?'} marks, ${q.text.substring(0, 50)}...)`)
    }
  }
}

// Main ingestion function
async function ingestPaper() {
  try {
    // 1. Get Physics subject
    const subject = await getPhysicsSubject()
    
    // 2. Create/get paper record
    const paper = await createPaperRecord(subject.id)
    
    // 3. Extract text from QP
    const qpPath = path.join(__dirname, '../data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf')
    console.log(`📄 Extracting text from: ${qpPath}\n`)
    
    if (!fs.existsSync(qpPath)) {
      throw new Error(`QP file not found: ${qpPath}`)
    }
    
    const text = await extractTextFromPDF(qpPath)
    console.log(`✅ Extracted ${text.length} characters\n`)
    
    // 4. Split into questions
    console.log(`🔍 Splitting into questions...\n`)
    const questions = splitIntoQuestions(text)
    console.log(`✅ Found ${questions.length} questions\n`)
    
    if (questions.length === 0) {
      console.log('⚠️  No questions found. PDF text might need better parsing.')
      console.log('   First 500 chars of PDF:\n')
      console.log(text.substring(0, 500))
      return
    }
    
    // Show preview
    console.log('📋 Questions preview:')
    questions.slice(0, 5).forEach(q => {
      console.log(`   Q${q.number}: ${q.text.substring(0, 60)}... [${q.marks || '?'} marks]`)
    })
    console.log()
    
    // 5. Save to database
    await saveQuestions(paper.id, questions)
    
    // 6. Verify
    const { count } = await supabase
      .from('questions')
      .select('*', { count: 'exact', head: true })
      .eq('paper_id', paper.id)
    
    console.log('\n' + '='.repeat(60))
    console.log('✅ INGESTION COMPLETE!')
    console.log('='.repeat(60))
    console.log(`📊 Results:`)
    console.log(`   - Paper ID: ${paper.id}`)
    console.log(`   - Questions saved: ${count}`)
    console.log(`   - Subject: Physics 4PH1`)
    console.log(`   - Exam: June 2019 Paper 1`)
    console.log('\n👉 Next: Run test_questions_count.ts to verify')
    console.log('👉 Then: Generate worksheet at http://localhost:3001/worksheets')
    console.log('='.repeat(60))
    
  } catch (error) {
    console.error('\n❌ INGESTION FAILED:', error)
    throw error
  }
}

// Run ingestion
ingestPaper().catch(err => {
  console.error('Fatal error:', err)
  process.exit(1)
})
