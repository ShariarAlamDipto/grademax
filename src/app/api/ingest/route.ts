/**
 * API Route: POST /api/ingest
 * 
 * Ingests a question paper and markscheme PDF
 * Processes through full pipeline and saves to database
 */

import { NextRequest, NextResponse } from 'next/server'
import { getSupabaseServer } from '@/lib/supabaseServer'
import { parsePDFFromPath, flattenTextItems } from '@/../../ingest/parse_pdf_v2'
import { segmentQuestions } from '@/../../ingest/segment'
import { parseAndLinkMS } from '@/../../ingest/ms_parse_link'
import { tagQuestionsAndParts } from '@/../../ingest/tagging'
import { extractFeatures } from '@/../../ingest/features'
import { detectMetadata } from '@/../../ingest/metadata'
import { saveIngestion } from '@/../../ingest/persist'
import * as fs from 'fs'

export const dynamic = 'force-dynamic'
export const maxDuration = 300 // 5 minutes for large PDFs

interface IngestRequest {
  qpPath: string
  msPath: string
}

interface IngestResponse {
  success: boolean
  paperId?: string
  questions?: number
  parts?: number
  tags?: number
  errors?: string[]
  processingTime?: number
}

export async function POST(request: NextRequest): Promise<NextResponse<IngestResponse>> {
  const startTime = Date.now()
  
  try {
    // Check authentication
    const supabase = getSupabaseServer()
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    
    if (authError || !user) {
      return NextResponse.json(
        { success: false, errors: ['Unauthorized'] },
        { status: 401 }
      )
    }
    
    // Parse request body
    const body: IngestRequest = await request.json()
    const { qpPath, msPath } = body
    
    if (!qpPath || !msPath) {
      return NextResponse.json(
        { success: false, errors: ['Missing qpPath or msPath'] },
        { status: 400 }
      )
    }
    
    // Verify files exist
    if (!fs.existsSync(qpPath)) {
      return NextResponse.json(
        { success: false, errors: [`QP file not found: ${qpPath}`] },
        { status: 404 }
      )
    }
    
    if (!fs.existsSync(msPath)) {
      return NextResponse.json(
        { success: false, errors: [`MS file not found: ${msPath}`] },
        { status: 404 }
      )
    }
    
    // Step 1: Parse PDFs
    console.log('📄 Parsing PDFs...')
    const qpParsed = await parsePDFFromPath(qpPath)
    const msParsed = await parsePDFFromPath(msPath)
    
    // Step 2: Segment questions
    console.log('✂️  Segmenting questions...')
    const qpTextItems = flattenTextItems(qpParsed)
    const segmented = await segmentQuestions(qpTextItems)
    
    if (segmented.questions.length === 0) {
      return NextResponse.json(
        { success: false, errors: ['No questions found in PDF'] },
        { status: 400 }
      )
    }
    
    // Step 3: Link markschemes
    console.log('🔗 Linking markschemes...')
    const msLinks = await parseAndLinkMS(msPath, segmented.questions)
    
    // Convert MS links to markscheme data format
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
    
    // Step 4: Tag questions
    console.log('🏷️  Tagging questions...')
    const taggingResult = await tagQuestionsAndParts(segmented.questions, msLinks)
    
    // Step 5: Extract features
    console.log('📊 Extracting features...')
    const features = extractFeatures(segmented.questions, taggingResult.questionTags)
    
    // Step 6: Detect metadata
    console.log('🔍 Detecting metadata...')
    const firstPageText = qpParsed.pages[0]?.textItems.map(t => t.text).join(' ') || ''
    const metadata = detectMetadata(qpPath, firstPageText)
    
    // Step 7: Save to database
    console.log('💾 Saving to database...')
    const result = await saveIngestion(
      metadata,
      segmented.questions,
      markschemes,
      taggingResult.questionTags,
      features,
      qpPath
    )
    
    const processingTime = Date.now() - startTime
    
    if (result.success) {
      return NextResponse.json({
        success: true,
        paperId: result.paperId,
        questions: result.questionIds.length,
        parts: result.partIds.length,
        tags: result.tagCount,
        processingTime
      })
    } else {
      return NextResponse.json(
        { success: false, errors: result.errors },
        { status: 500 }
      )
    }
    
  } catch (error) {
    console.error('❌ Ingestion error:', error)
    return NextResponse.json(
      {
        success: false,
        errors: [error instanceof Error ? error.message : 'Unknown error'],
        processingTime: Date.now() - startTime
      },
      { status: 500 }
    )
  }
}

/**
 * GET /api/ingest
 * 
 * Get ingestion status or list recent ingestions
 */
export async function GET(): Promise<NextResponse> {
  try {
    // Check authentication
    const supabase = getSupabaseServer()
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    
    if (authError || !user) {
      return NextResponse.json(
        { success: false, errors: ['Unauthorized'] },
        { status: 401 }
      )
    }
    
    // Get recent ingestions
    const { data: ingestions, error } = await supabase
      .from('ingestions')
      .select(`
        *,
        papers (
          board,
          level,
          subject_name,
          year,
          season,
          paper_type,
          paper_number
        )
      `)
      .order('created_at', { ascending: false })
      .limit(20)
    
    if (error) {
      return NextResponse.json(
        { success: false, errors: [error.message] },
        { status: 500 }
      )
    }
    
    return NextResponse.json({
      success: true,
      ingestions: ingestions || []
    })
    
  } catch (error) {
    console.error('❌ GET ingestions error:', error)
    return NextResponse.json(
      {
        success: false,
        errors: [error instanceof Error ? error.message : 'Unknown error']
      },
      { status: 500 }
    )
  }
}
