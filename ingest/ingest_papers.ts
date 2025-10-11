/**
 * ingest_papers.ts
 * Main ingestion pipeline:
 * 1. Upload PDFs to Supabase Storage
 * 2. Parse questions and markschemes
 * 3. Auto-tag topics using embeddings + keywords
 * 4. Insert into database
 * 
 * Usage:
 *   npm run ingest:papers -- --help
 *   npm run ingest:papers -- --dry-run
 *   npm run ingest:papers -- --data-dir=./data/raw
 */

import 'dotenv/config'
import { createClient } from '@supabase/supabase-js'
import fs from 'fs'
import path from 'path'
import { parsePaper, extractQuestions, extractMarkschemes } from './parse_pdf.js'
import { difficultyFromMarksAndVerbs, cleanQuestionNumber, calculateKeywordBoost } from './rules.js'
import { embed, cosineSimilarity } from './embeddings.js'
import { uploadPdf } from './upload_storage.js'
import { extractAllQuestionParts } from './visual_extract_hybrid.js'
import { uploadAllCrops } from './storage_upload.js'

// Config
const SUPABASE_URL = process.env.SUPABASE_URL!
const SUPABASE_SERVICE_ROLE = process.env.SUPABASE_SERVICE_ROLE!

if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE) {
  console.error('❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE in .env.ingest')
  process.exit(1)
}

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE)

// Parse args
const args = process.argv.slice(2)
const dryRun = args.includes('--dry-run')
const dataDir = args.find(a => a.startsWith('--data-dir='))?.split('=')[1] || './data/raw'
const help = args.includes('--help')

if (help) {
  console.log(`
GradeMax Paper Ingestion Tool

Usage:
  npm run ingest:papers -- [options]

Options:
  --help              Show this help
  --dry-run           Parse files but don't insert to database
  --data-dir=<path>   Path to data directory (default: ./data/raw)

Expected directory structure:
  data/raw/
    IGCSE/
      4PH1/
        2019/Jun/
          4PH1_1P.pdf
          4PH1_1P_MS.pdf

Environment:
  Set SUPABASE_URL and SUPABASE_SERVICE_ROLE in .env.ingest
`)
  process.exit(0)
}

// Topic cache (for embeddings)
interface TopicCache {
  id: string
  code: string
  name: string
  content: string
  embedding?: number[]
}

const topicsCache = new Map<string, TopicCache>()

/**
 * Load all topics and compute embeddings
 */
async function loadTopics() {
  console.log('📚 Loading topics...')
  
  const { data: topics, error } = await supabase
    .from('topics')
    .select('id, code, name, content, subject_id')
  
  if (error) throw error
  if (!topics || topics.length === 0) {
    console.warn('⚠️  No topics found. Run schema and seed SQL first.')
    return
  }
  
  for (const topic of topics) {
    const embedding = await embed(topic.content || topic.name)
    topicsCache.set(topic.id, {
      id: topic.id,
      code: topic.code,
      name: topic.name,
      content: topic.content || '',
      embedding
    })
    console.log(`  ✓ ${topic.code} - ${topic.name}`)
  }
  
  console.log(`✓ Loaded ${topicsCache.size} topics\n`)
}

/**
 * Find best matching topics for a question
 * Returns array of { topicId, confidence }
 */
async function tagQuestion(questionText: string): Promise<Array<{ topicId: string, confidence: number }>> {
  const questionEmbedding = await embed(questionText)
  const scores: Array<{ topicId: string, topicCode: string, confidence: number }> = []
  
  for (const [topicId, topic] of topicsCache.entries()) {
    if (!topic.embedding) continue
    
    // Semantic similarity
    const similarity = cosineSimilarity(questionEmbedding, topic.embedding)
    
    // Keyword boost
    const keywordBoost = calculateKeywordBoost(questionText, topic.code)
    
    // Combined confidence
    const confidence = Math.min(similarity * keywordBoost, 1.0)
    
    scores.push({ topicId, topicCode: topic.code, confidence })
  }
  
  // Return top 3 with confidence > 0.4
  return scores
    .filter(s => s.confidence > 0.4)
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 3)
    .map(({ topicId, confidence }) => ({ topicId, confidence }))
}

/**
 * Process a single paper
 */
async function processPaper(
  level: string,
  subjectCode: string,
  year: number,
  season: string,
  paperCode: string,
  paperPath: string,
  msPath: string
) {
  console.log(`\n📄 Processing ${level}/${subjectCode}/${year}/${season}/${paperCode}`)
  
  // 1. Get subject_id
  const { data: subject } = await supabase
    .from('subjects')
    .select('id')
    .eq('level', level)
    .eq('code', subjectCode)
    .single()
  
  if (!subject) {
    console.error(`  ❌ Subject not found: ${level} ${subjectCode}`)
    return
  }
  
  const subjectId = subject.id
  
  // 2. Check if paper already exists
  const { data: existingPaper } = await supabase
    .from('papers')
    .select('id')
    .eq('subject_id', subjectId)
    .eq('year', year)
    .eq('season', season)
    .eq('paper_number', paperCode)
    .maybeSingle()
  
  if (existingPaper) {
    console.log(`  ⏭️  Paper already exists (id: ${existingPaper.id}), skipping`)
    return
  }
  
  // 3. Upload PDFs
  console.log('  📤 Uploading PDFs...')
  const paperDestKey = `${level}/${subjectCode}/${year}/${season}/${paperCode}.pdf`
  const msDestKey = `${level}/${subjectCode}/${year}/${season}/${paperCode}_MS.pdf`
  
  const { publicUrl: paperUrl } = dryRun 
    ? { publicUrl: 'dry-run-url' }
    : await uploadPdf(SUPABASE_URL, SUPABASE_SERVICE_ROLE, paperPath, paperDestKey)
  
  const { publicUrl: msUrl } = dryRun
    ? { publicUrl: 'dry-run-url' }
    : await uploadPdf(SUPABASE_URL, SUPABASE_SERVICE_ROLE, msPath, msDestKey)
  
  console.log(`    ✓ Paper: ${paperUrl}`)
  console.log(`    ✓ MS: ${msUrl}`)
  
  // 4. Parse paper questions
  console.log('  📖 Parsing questions...')
  const { raw: paperRaw } = await parsePaper(paperPath)
  const questions = extractQuestions(paperRaw)
  console.log(`    ✓ Found ${questions.length} questions`)
  
  // 4.5. Extract visual crops
  console.log('  🎨 Extracting visual crops...')
  const pdfBuffer = fs.readFileSync(paperPath)
  const visualParts = dryRun ? [] : await extractAllQuestionParts(pdfBuffer, 300)
  console.log(`    ✓ Extracted ${visualParts.length}/${questions.length} visual crops`)
  
  // Map question numbers to visual parts
  const visualMap = new Map(visualParts.map(vp => [vp.questionNumber, vp]))
  
  // 5. Parse markscheme
  console.log('  📖 Parsing markscheme...')
  const { raw: msRaw } = await parsePaper(msPath)
  const msQuestions = extractMarkschemes(msRaw)
  console.log(`    ✓ Found ${msQuestions.length} markscheme entries`)
  
  // 6. Insert paper
  if (dryRun) {
    console.log('  🔍 DRY RUN - would insert paper')
  } else {
    const { data: paper, error: paperError } = await supabase
      .from('papers')
      .insert({
        subject_id: subjectId,
        paper_number: paperCode,
        year,
        season,
        pdf_url: paperUrl,
        markscheme_pdf_url: msUrl
      })
      .select('id')
      .single()
    
    if (paperError) {
      console.error(`    ❌ Failed to insert paper: ${paperError.message}`)
      return
    }
    
    const paperId = paper.id
    console.log(`    ✓ Inserted paper (id: ${paperId})`)
    
    // 6.5. Upload visual crops to Supabase Storage
    if (visualParts.length > 0) {
      console.log('  📤 Uploading visual crops...')
      
      // TODO: Upload full page renders separately
      // For now, we only upload the question crops
      
      // Upload question crops
      const cropData = visualParts.map(vp => ({
        questionNumber: vp.questionNumber,
        pngBuffer: vp.crop.pngBuffer,
        visualHash: vp.crop.visualHash
      }))
      
      const cropUploads = await uploadAllCrops(paperCode, cropData)
      console.log(`    ✓ Uploaded ${cropUploads.length} crops`)
    }
    
    // 7. Insert questions
    console.log('  💾 Inserting questions...')
    for (const q of questions) {
      const difficulty = difficultyFromMarksAndVerbs(q.text, q.marks)
      const embedding = await embed(q.text)
      
      // Get visual data if available
      const visual = visualMap.get(q.questionNumber)
      
      const { data: question, error: qError } = await supabase
        .from('questions')
        .insert({
          paper_id: paperId,
          question_number: cleanQuestionNumber(q.questionNumber),
          text: q.text,
          marks: q.marks,
          difficulty,
          embedding,
          ...(visual ? {
            visual_url: visual.crop.visualHash ? `papers/${paperCode}/crops/${visual.questionNumber}_${visual.crop.visualHash.substring(0, 8)}.png` : null,
            visual_dims: { width: visual.crop.width, height: visual.crop.height, dpi: visual.crop.dpi },
            visual_hash: visual.crop.visualHash,
            bbox: visual.bbox
          } : {})
        })
        .select('id')
        .single()
      
      if (qError) {
        console.error(`    ❌ Failed to insert question ${q.questionNumber}: ${qError.message}`)
        continue
      }
      
      const questionId = question.id
      
      // 8. Tag topics
      const tags = await tagQuestion(q.text)
      
      if (tags.length > 0) {
        await supabase.from('question_topics').insert(
          tags.map(t => ({
            question_id: questionId,
            topic_id: t.topicId,
            confidence: t.confidence
          }))
        )
        console.log(`    ✓ ${q.questionNumber}: ${tags.length} topic(s) tagged`)
      }
      
      // 9. Match markscheme
      const matchingMs = msQuestions.find(ms => 
        cleanQuestionNumber(ms.questionNumber) === cleanQuestionNumber(q.questionNumber)
      )
      
      if (matchingMs) {
        await supabase.from('markschemes').insert({
          question_id: questionId,
          text: matchingMs.text
        })
        console.log(`    ✓ ${q.questionNumber}: markscheme linked`)
      } else {
        console.log(`    ⚠️  ${q.questionNumber}: no markscheme found`)
      }
    }
    
    console.log(`  ✅ Completed ${paperCode}`)
  }
}

/**
 * Scan data directory and process papers
 */
async function main() {
  console.log('🚀 GradeMax Paper Ingestion\n')
  console.log(`Data directory: ${dataDir}`)
  console.log(`Dry run: ${dryRun}\n`)
  
  if (!fs.existsSync(dataDir)) {
    console.error(`❌ Data directory not found: ${dataDir}`)
    console.log('Create it with structure: data/raw/IGCSE/4PH1/2019/Jun/...')
    process.exit(1)
  }
  
  await loadTopics()
  
  // Scan directory structure: LEVEL/SUBJECT/YEAR/SEASON/
  const levels = fs.readdirSync(dataDir).filter(f => 
    fs.statSync(path.join(dataDir, f)).isDirectory()
  )
  
  for (const level of levels) {
    const levelPath = path.join(dataDir, level)
    const subjects = fs.readdirSync(levelPath).filter(f =>
      fs.statSync(path.join(levelPath, f)).isDirectory()
    )
    
    for (const subjectCode of subjects) {
      const subjectPath = path.join(levelPath, subjectCode)
      const years = fs.readdirSync(subjectPath).filter(f =>
        fs.statSync(path.join(subjectPath, f)).isDirectory()
      )
      
      for (const year of years) {
        const yearPath = path.join(subjectPath, year)
        const seasons = fs.readdirSync(yearPath).filter(f =>
          fs.statSync(path.join(yearPath, f)).isDirectory()
        )
        
        for (const season of seasons) {
          const seasonPath = path.join(yearPath, season)
          const files = fs.readdirSync(seasonPath)
          
          // Find paper/MS pairs
          const papers = files.filter(f => f.endsWith('.pdf') && !f.endsWith('_MS.pdf'))
          
          for (const paperFile of papers) {
            const paperCode = paperFile.replace('.pdf', '')
            const msFile = `${paperCode}_MS.pdf`
            
            const paperPath = path.join(seasonPath, paperFile)
            const msPath = path.join(seasonPath, msFile)
            
            if (!fs.existsSync(msPath)) {
              console.warn(`⚠️  Markscheme not found for ${paperCode}, skipping`)
              continue
            }
            
            await processPaper(
              level,
              subjectCode,
              parseInt(year),
              season,
              paperCode,
              paperPath,
              msPath
            )
          }
        }
      }
    }
  }
  
  console.log('\n✅ Ingestion complete!')
}

main().catch(err => {
  console.error('❌ Fatal error:', err)
  process.exit(1)
})
