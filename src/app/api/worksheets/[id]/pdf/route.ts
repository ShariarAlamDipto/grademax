/**
 * /api/worksheets/[id]/pdf
 * Generate PDF from worksheet using Phase 2 page-based system
 */
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import { spawn } from 'child_process'
import { writeFile, unlink, readFile } from 'fs/promises'
import { join } from 'path'
import { tmpdir } from 'os'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: worksheetId } = await params
    
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    )
    
    // 1. Get worksheet and its items
    const { data: worksheet } = await supabase
      .from('worksheets')
      .select(`
        id,
        params,
        worksheet_items(
          position,
          questions(
            id,
            question_number,
            page_pdf_url,
            ms_pdf_url,
            has_diagram
          )
        )
      `)
      .eq('id', worksheetId)
      .single()
    
    if (!worksheet || !worksheet.worksheet_items) {
      return NextResponse.json({ error: 'Worksheet not found' }, { status: 404 })
    }
    
    // 2. Sort items by position and extract questions
    type WorksheetItem = {
      position: number
      questions: {
        id: string
        question_number: string
        page_pdf_url: string | null
        ms_pdf_url: string | null
        has_diagram: boolean
      } | null
    }
    
    const sortedQuestions = (worksheet.worksheet_items as WorksheetItem[])
      .sort((a, b) => a.position - b.position)
      .map(item => item.questions)
      .filter((q): q is NonNullable<typeof q> => q !== null)
    
    if (sortedQuestions.length === 0) {
      return NextResponse.json({ error: 'No questions in worksheet' }, { status: 404 })
    }
    
    // 3. Check if we should use Phase 2 (page PDFs) or Phase 1 (text)
    const hasPagePdfs = sortedQuestions.some(q => q.page_pdf_url)
    
    if (!hasPagePdfs) {
      return NextResponse.json({ 
        error: 'This worksheet was generated with Phase 1 (text-based). Please regenerate to use Phase 2 (PDF pages).',
        phase: 1
      }, { status: 400 })
    }
    
    // 4. Download PDFs from Supabase Storage
    const questionPdfPaths: string[] = []
    const markSchemePdfPaths: string[] = []
    const includeMarkScheme = worksheet.params?.includeMarkscheme || false
    
    for (const question of sortedQuestions) {
      if (question.page_pdf_url) {
        // Download question PDF from Supabase Storage
        const { data: pdfData } = await supabase.storage
          .from('question-pdfs')
          .download(question.page_pdf_url)
        
        if (pdfData) {
          const tempPath = join(tmpdir(), `q_${question.id}.pdf`)
          const buffer = await pdfData.arrayBuffer()
          await writeFile(tempPath, Buffer.from(buffer))
          questionPdfPaths.push(tempPath)
        }
      }
      
      if (includeMarkScheme && question.ms_pdf_url) {
        // Download mark scheme PDF
        const { data: msPdfData } = await supabase.storage
          .from('question-pdfs')
          .download(question.ms_pdf_url)
        
        if (msPdfData) {
          const tempPath = join(tmpdir(), `ms_${question.id}.pdf`)
          const buffer = await msPdfData.arrayBuffer()
          await writeFile(tempPath, Buffer.from(buffer))
          markSchemePdfPaths.push(tempPath)
        }
      }
    }
    
    // 5. Merge PDFs using Python script
    const outputPath = join(tmpdir(), `worksheet_${worksheetId}.pdf`)
    
    const pythonArgs = [
      'scripts/merge_pdfs.py',
      outputPath,
      ...questionPdfPaths
    ]
    
    if (includeMarkScheme && markSchemePdfPaths.length > 0) {
      pythonArgs.push('--markschemes', ...markSchemePdfPaths)
    }
    
    await new Promise((resolve, reject) => {
      const python = spawn('python', pythonArgs)
      
      python.on('close', (code) => {
        if (code === 0) {
          resolve(null)
        } else {
          reject(new Error(`Python script exited with code ${code}`))
        }
      })
      
      python.on('error', reject)
    })
    
    // 6. Read merged PDF
    const pdfBuffer = await readFile(outputPath)
    
    // 7. Cleanup temporary files
    await Promise.all([
      unlink(outputPath),
      ...questionPdfPaths.map(p => unlink(p).catch(() => {})),
      ...markSchemePdfPaths.map(p => unlink(p).catch(() => {}))
    ])
    
    // 8. Return PDF as stream
    return new NextResponse(pdfBuffer as any, {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': `attachment; filename="worksheet_${worksheetId}.pdf"`,
        'Content-Length': pdfBuffer.length.toString()
      }
    })
    
  } catch (err) {
    console.error('PDF generation error:', err)
    return NextResponse.json({ 
      error: 'Failed to generate PDF',
      details: err instanceof Error ? err.message : 'Unknown error'
    }, { status: 500 })
  }
}
