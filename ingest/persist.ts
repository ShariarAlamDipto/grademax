/**
 * Persistence Module
 * 
 * Saves ingestion results to Supabase database:
 * - Papers metadata
 * - Questions and parts with bboxes
 * - Markscheme links
 * - Topic tags
 * - Question features
 * 
 * NOTE: Requires migration 004 to be run in Supabase first
 */

import { createClient } from '@supabase/supabase-js'
import type { 
  DetectedMetadata,
  SegmentedQuestion
} from '../types/ingestion'
import type { QuestionFeatures } from './features'
import type { Tag } from './tagging'

interface MarkschemeData {
  questionNumber: string
  markschemeText: string
  pageRange: { start: number; end: number }
}

// ============================================================================
// Supabase Client Setup
// ============================================================================

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

if (!supabaseUrl || !supabaseKey) {
  throw new Error('Missing Supabase environment variables')
}

const supabase = createClient(supabaseUrl, supabaseKey)

// ============================================================================
// Main Entry Point
// ============================================================================

export interface IngestionResult {
  paperId: string
  questionIds: string[]
  partIds: string[]
  tagCount: number
  success: boolean
  errors: string[]
}

/**
 * Save complete ingestion results to database
 */
export async function saveIngestion(
  metadata: DetectedMetadata,
  questions: SegmentedQuestion[],
  markschemes: MarkschemeData[],
  tags: Map<string, Tag[]>, // Changed from QuestionTag[] to Map<string, Tag[]>
  features: Map<string, QuestionFeatures>,
  pdfPath: string
): Promise<IngestionResult> {
  console.log('💾 Saving ingestion results to database...')
  
  const result: IngestionResult = {
    paperId: '',
    questionIds: [],
    partIds: [],
    tagCount: 0,
    success: false,
    errors: []
  }
  
  try {
    // Step 1: Save or get paper
    console.log('\n1️⃣ Saving paper metadata...')
    const paperId = await savePaper(metadata, pdfPath)
    result.paperId = paperId
    console.log(`  ✓ Paper ID: ${paperId}`)
    
    // Step 2: Save questions and parts
    console.log('\n2️⃣ Saving questions and parts...')
    const { questionIds, partIds } = await saveQuestions(paperId, questions, features)
    result.questionIds = questionIds
    result.partIds = partIds
    console.log(`  ✓ Saved ${questionIds.length} questions`)
    console.log(`  ✓ Saved ${partIds.length} parts`)
    
    // Step 3: Link markschemes
    console.log('\n3️⃣ Linking markschemes...')
    await linkMarkschemes(questionIds, markschemes)
    console.log(`  ✓ Linked ${markschemes.length} markschemes`)
    
    // Step 4: Save tags
    console.log('\n4️⃣ Saving topic tags...')
    const tagCount = await saveTags(paperId, tags)
    result.tagCount = tagCount
    console.log(`  ✓ Saved ${tagCount} tags`)
    
    // Step 5: Create ingestion record
    console.log('\n5️⃣ Creating ingestion record...')
    await createIngestionRecord(paperId, questions.length, partIds.length, tagCount)
    console.log(`  ✓ Ingestion record created`)
    
    result.success = true
    console.log('\n✅ Ingestion saved successfully!')
    
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error)
    result.errors.push(errorMsg)
    console.error('❌ Persistence error:', errorMsg)
  }
  
  return result
}

// ============================================================================
// Paper Persistence
// ============================================================================

/**
 * Save or update paper metadata
 * Returns paper ID (creates new if doesn't exist)
 */
async function savePaper(
  metadata: DetectedMetadata,
  pdfPath: string
): Promise<string> {
  // Check if paper already exists by matching key fields
  const { data: existing, error: fetchError } = await supabase
    .from('papers')
    .select('id')
    .eq('board', metadata.board)
    .eq('level', metadata.level)
    .eq('subject_code', metadata.subjectCode)
    .eq('year', metadata.year)
    .eq('season', metadata.season)
    .eq('paper_number', metadata.paperNumber)
    .maybeSingle() // Returns null if not found, doesn't throw
  
  if (fetchError) {
    throw new Error(`Failed to check for existing paper: ${fetchError.message}`)
  }
  
  if (existing) {
    console.log('  ℹ️  Paper already exists, updating...')
    
    // Update existing paper
    const { error: updateError } = await supabase
      .from('papers')
      .update({
        board: metadata.board,
        level: metadata.level,
        subject_code: metadata.subjectCode,
        subject_name: metadata.subjectName,
        paper_type: metadata.paperType,
        paper_number: metadata.paperNumber,
        variant: metadata.variant,
        year: metadata.year,
        season: metadata.season,
        doc_hash: metadata.docHash,
        pdf_path: pdfPath,
        updated_at: new Date().toISOString()
      })
      .eq('id', existing.id)
    
    if (updateError) {
      throw new Error(`Failed to update paper: ${updateError.message}`)
    }
    
    return existing.id
  } else {
    console.log('  ℹ️  Creating new paper...')
    
    // Create new paper
    const { data, error: insertError } = await supabase
      .from('papers')
      .insert({
        board: metadata.board,
        level: metadata.level,
        subject_code: metadata.subjectCode,
        subject_name: metadata.subjectName,
        paper_type: metadata.paperType,
        paper_number: metadata.paperNumber,
        variant: metadata.variant,
        year: metadata.year,
        season: metadata.season,
        doc_hash: metadata.docHash,
        pdf_path: pdfPath
      })
      .select('id')
      .single()
    
    if (insertError) {
      throw new Error(`Failed to insert paper: ${insertError.message}`)
    }
    
    if (!data) {
      throw new Error('No data returned from paper insert')
    }
    
    return data.id
  }
}

// ============================================================================
// Questions and Parts Persistence
// ============================================================================

interface SaveQuestionsResult {
  questionIds: string[]
  partIds: string[]
}

/**
 * Save questions and their parts
 */
async function saveQuestions(
  paperId: string,
  questions: SegmentedQuestion[],
  features: Map<string, QuestionFeatures>
): Promise<SaveQuestionsResult> {
  const questionIds: string[] = []
  const partIds: string[] = []
  
  // Delete existing questions for this paper (cascade will delete parts)
  const { error: deleteError } = await supabase
    .from('questions')
    .delete()
    .eq('paper_id', paperId)
  
  if (deleteError) {
    throw new Error(`Failed to delete old questions: ${deleteError.message}`)
  }
  
  // Save each question
  for (const question of questions) {
    const questionFeatures = features.get(question.questionNumber)
    
    // Insert question
    const { data: questionData, error: questionError } = await supabase
      .from('questions')
      .insert({
        paper_id: paperId,
        question_number: parseInt(question.questionNumber),
        header_bbox: question.headerBBox,
        total_marks: question.totalMarks,
        context_text: question.contextText || '',
        difficulty: questionFeatures?.difficulty || 'medium',
        difficulty_score: questionFeatures?.difficultyScore || 0.5,
        estimated_time_minutes: questionFeatures?.estimatedMinutes || null,
        style: questionFeatures?.style || [],
        characteristics: questionFeatures?.characteristics || []
      })
      .select('id')
      .single()
    
    if (questionError) {
      throw new Error(`Failed to insert question ${question.questionNumber}: ${questionError.message}`)
    }
    
    if (!questionData) {
      throw new Error(`No data returned from question insert for ${question.questionNumber}`)
    }
    
    questionIds.push(questionData.id)
    
    // Save parts for this question
    for (const part of question.parts) {
      const { data: partData, error: partError } = await supabase
        .from('question_parts')
        .insert({
          question_id: questionData.id,
          code: part.code, // Fixed: use 'code' not 'part_code'
          bbox_list: part.bboxList,
          marks: part.marks || 0,
          text_preview: part.text || '',
          page_from: part.pageFrom || 0,
          page_to: part.pageTo || 0
        })
        .select('id')
        .single()
      
      if (partError) {
        throw new Error(`Failed to insert part ${part.code}: ${partError.message}`)
      }
      
      if (!partData) {
        throw new Error(`No data returned from part insert for ${part.code}`)
      }
      
      partIds.push(partData.id)
    }
  }
  
  return { questionIds, partIds }
}

// ============================================================================
// Markscheme Linking
// ============================================================================

/**
 * Link markschemes to questions
 */
async function linkMarkschemes(
  questionIds: string[],
  markschemes: MarkschemeData[]
): Promise<void> {
  // Create a map of question numbers to IDs
  const { data: questions, error: fetchError } = await supabase
    .from('questions')
    .select('id, question_number')
    .in('id', questionIds)
  
  if (fetchError) {
    throw new Error(`Failed to fetch questions: ${fetchError.message}`)
  }
  
  const questionMap = new Map<string, string>()
  for (const q of questions || []) {
    questionMap.set(q.question_number.toString(), q.id)
  }
  
  // Update each question with its markscheme
  for (const ms of markschemes) {
    const questionId = questionMap.get(ms.questionNumber)
    if (!questionId) {
      console.warn(`  ⚠️  No question found for MS ${ms.questionNumber}`)
      continue
    }
    
    const { error: updateError } = await supabase
      .from('questions')
      .update({
        markscheme_text: ms.markschemeText,
        ms_page_range: ms.pageRange
      })
      .eq('id', questionId)
    
    if (updateError) {
      throw new Error(`Failed to link MS for Q${ms.questionNumber}: ${updateError.message}`)
    }
  }
}

// ============================================================================
// Tags Persistence
// ============================================================================

/**
 * Save topic tags
 */
async function saveTags(
  paperId: string,
  questionTags: Map<string, Tag[]>
): Promise<number> {
  if (questionTags.size === 0) {
    return 0
  }
  
  // Delete existing tags for this paper
  const { error: deleteError } = await supabase
    .from('question_tags')
    .delete()
    .eq('paper_id', paperId)
  
  if (deleteError) {
    throw new Error(`Failed to delete old tags: ${deleteError.message}`)
  }
  
  // Get question IDs for this paper
  const { data: questions, error: fetchError } = await supabase
    .from('questions')
    .select('id, question_number')
    .eq('paper_id', paperId)
  
  if (fetchError) {
    throw new Error(`Failed to fetch questions: ${fetchError.message}`)
  }
  
  const questionMap = new Map<string, string>()
  for (const q of questions || []) {
    questionMap.set(q.question_number.toString(), q.id)
  }
  
  // Prepare tag inserts
  const tagInserts = []
  for (const [questionNumber, tags] of questionTags.entries()) {
    const questionId = questionMap.get(questionNumber)
    if (!questionId) {
      console.warn(`  ⚠️  No question found for tag on Q${questionNumber}`)
      continue
    }
    
    for (const tag of tags) {
      tagInserts.push({
        paper_id: paperId,
        question_id: questionId,
        topic: tag.topic,
        confidence: tag.confidence,
        provenance: tag.provenance.join(', ')
      })
    }
  }
  
  if (tagInserts.length === 0) {
    return 0
  }
  
  // Insert tags in batch
  const { error: insertError } = await supabase
    .from('question_tags')
    .insert(tagInserts)
  
  if (insertError) {
    throw new Error(`Failed to insert tags: ${insertError.message}`)
  }
  
  return tagInserts.length
}

// ============================================================================
// Ingestion Tracking
// ============================================================================

/**
 * Create ingestion tracking record
 */
async function createIngestionRecord(
  paperId: string,
  questionCount: number,
  partCount: number,
  tagCount: number
): Promise<void> {
  const { error } = await supabase
    .from('ingestions')
    .insert({
      paper_id: paperId,
      status: 'completed',
      questions_found: questionCount,
      parts_found: partCount,
      tags_found: tagCount,
      completed_at: new Date().toISOString()
    })
  
  if (error) {
    throw new Error(`Failed to create ingestion record: ${error.message}`)
  }
}

// ============================================================================
// Query Helpers
// ============================================================================

/**
 * Get paper by key fields (board, level, subject, year, season, paper_number)
 */
export async function getPaperByKey(
  board: string,
  level: string,
  subjectCode: string,
  year: number,
  season: string,
  paperNumber: string
) {
  const { data, error } = await supabase
    .from('papers')
    .select('*')
    .eq('board', board)
    .eq('level', level)
    .eq('subject_code', subjectCode)
    .eq('year', year)
    .eq('season', season)
    .eq('paper_number', paperNumber)
    .maybeSingle()
  
  if (error) {
    throw new Error(`Failed to fetch paper: ${error.message}`)
  }
  
  return data
}

/**
 * Get questions for a paper
 */
export async function getQuestionsForPaper(paperId: string) {
  const { data, error } = await supabase
    .from('questions')
    .select(`
      *,
      question_parts (*),
      question_tags (*)
    `)
    .eq('paper_id', paperId)
    .order('question_number', { ascending: true })
  
  if (error) {
    throw new Error(`Failed to fetch questions: ${error.message}`)
  }
  
  return data
}

/**
 * Get all papers with basic info
 */
export async function getAllPapers() {
  const { data, error } = await supabase
    .from('papers')
    .select('id, board, level, subject_name, year, season, paper_type, paper_number')
    .order('year', { ascending: false })
    .order('season', { ascending: false })
  
  if (error) {
    throw new Error(`Failed to fetch papers: ${error.message}`)
  }
  
  return data
}

/**
 * Search questions by topic
 */
export async function searchQuestionsByTopic(topic: string, limit: number = 20) {
  const { data, error } = await supabase
    .from('question_tags')
    .select(`
      topic,
      confidence,
      questions (
        *,
        papers (board, level, subject_name, year, season)
      )
    `)
    .eq('topic', topic)
    .order('confidence', { ascending: false })
    .limit(limit)
  
  if (error) {
    throw new Error(`Failed to search questions: ${error.message}`)
  }
  
  return data
}
