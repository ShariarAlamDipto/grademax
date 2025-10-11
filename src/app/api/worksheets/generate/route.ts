/**
 * /api/worksheets/generate
 * Generate a custom worksheet based on filters
 */
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import { z } from 'zod'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const RequestSchema = z.object({
  subjectCode: z.string(),
  topicCodes: z.array(z.string()).optional(),
  difficulties: z.array(z.number().int().min(1).max(3)).optional(),
  count: z.number().int().min(1).max(50).default(10),
  includeMarkscheme: z.boolean().default(false),
  shuffle: z.boolean().default(true)
})

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const params = RequestSchema.parse(body)
    
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    )
    
    // 1. Get subject_id
    const { data: subject } = await supabase
      .from('subjects')
      .select('id, name, code, level')
      .eq('code', params.subjectCode)
      .single()
    
    if (!subject) {
      return NextResponse.json({ error: 'Subject not found' }, { status: 404 })
    }
    
    // 2. Build topic filter
    let topicIds: string[] = []
    if (params.topicCodes && params.topicCodes.length > 0) {
      const { data: topics } = await supabase
        .from('topics')
        .select('id')
        .eq('subject_id', subject.id)
        .in('code', params.topicCodes)
      
      if (topics && topics.length > 0) {
        topicIds = topics.map(t => t.id)
      }
    }
    
    // 3. Query questions
    let query = supabase
      .from('questions')
      .select(`
        id,
        question_number,
        text,
        marks,
        difficulty,
        paper_id,
        papers!inner(paper_number, year, season, subject_id),
        markschemes(text),
        question_topics(topic_id, confidence)
      `)
      .eq('papers.subject_id', subject.id)
    
    // Filter by difficulty
    if (params.difficulties && params.difficulties.length > 0) {
      query = query.in('difficulty', params.difficulties)
    }
    
    const { data: allQuestions, error } = await query
    
    if (error) {
      console.error('Query error:', error)
      return NextResponse.json({ error: error.message }, { status: 500 })
    }
    
    if (!allQuestions || allQuestions.length === 0) {
      return NextResponse.json({ 
        error: 'No questions found matching criteria',
        items: [],
        params: { ...params, subject }
      })
    }
    
    // 4. Filter by topics (if specified)
    let filteredQuestions = allQuestions
    if (topicIds.length > 0) {
      // Check if ANY questions have topic tags
      const hasTopicTags = allQuestions.some(q => 
        Array.isArray(q.question_topics) && q.question_topics.length > 0
      )
      
      if (hasTopicTags) {
        // Only filter by topics if questions have tags
        filteredQuestions = allQuestions.filter(q => 
          Array.isArray(q.question_topics) && 
          q.question_topics.some(qt => topicIds.includes(qt.topic_id))
        )
      } else {
        // No topic tags exist yet - return all questions from this subject
        console.log('⚠️ No topic tags found - returning all questions from subject')
        filteredQuestions = allQuestions
      }
    }
    
    if (filteredQuestions.length === 0) {
      return NextResponse.json({ 
        error: 'No questions found for selected topics',
        items: [],
        params: { ...params, subject }
      })
    }
    
    // 5. Round-robin selection by topic (if topics specified)
    let selectedQuestions = []
    if (topicIds.length > 0 && params.count > topicIds.length) {
      // Group questions by topic
      const questionsByTopic = new Map<string, typeof filteredQuestions>()
      
      for (const topicId of topicIds) {
        const questionsForTopic = filteredQuestions.filter(q =>
          Array.isArray(q.question_topics) &&
          q.question_topics.some(qt => qt.topic_id === topicId)
        )
        if (questionsForTopic.length > 0) {
          questionsByTopic.set(topicId, questionsForTopic)
        }
      }
      
      // Round-robin pick
      const topics = Array.from(questionsByTopic.keys())
      let topicIdx = 0
      
      while (selectedQuestions.length < params.count && topics.length > 0) {
        const currentTopic = topics[topicIdx % topics.length]
        const pool = questionsByTopic.get(currentTopic)!
        
        if (pool.length > 0) {
          const q = pool.shift()!
          selectedQuestions.push(q)
        } else {
          // No more questions for this topic
          topics.splice(topicIdx % topics.length, 1)
        }
        
        topicIdx++
      }
    } else {
      // Simple random selection
      const shuffled = params.shuffle 
        ? filteredQuestions.sort(() => Math.random() - 0.5)
        : filteredQuestions
      
      selectedQuestions = shuffled.slice(0, params.count)
    }
    
    // 6. Format response
    const items = selectedQuestions.map((q, idx) => {
      const paper = Array.isArray(q.papers) ? q.papers[0] : q.papers
      
      return {
        position: idx + 1,
        questionId: q.id,
        questionNumber: q.question_number,
        text: q.text,
        marks: q.marks,
        difficulty: q.difficulty,
        source: paper ? `${paper.year} ${paper.season} Paper ${paper.paper_number}` : 'Unknown',
        markscheme: params.includeMarkscheme && q.markschemes?.[0]
          ? q.markschemes[0].text
          : undefined
      }
    })
    
    // 7. Store worksheet (optional - can track generated worksheets)
    const { data: worksheet } = await supabase
      .from('worksheets')
      .insert({
        params: {
          subjectCode: params.subjectCode,
          topicCodes: params.topicCodes,
          difficulties: params.difficulties,
          count: params.count
        }
      })
      .select('id')
      .single()
    
    if (worksheet) {
      await supabase.from('worksheet_items').insert(
        items.map(item => ({
          worksheet_id: worksheet.id,
          question_id: item.questionId,
          position: item.position
        }))
      )
    }
    
    return NextResponse.json({
      worksheetId: worksheet?.id,
      subject: {
        code: subject.code,
        name: subject.name,
        level: subject.level
      },
      params,
      items,
      generatedAt: new Date().toISOString()
    })
    
  } catch (err) {
    if (err instanceof z.ZodError) {
      return NextResponse.json({ 
        error: 'Invalid request', 
        details: err.errors 
      }, { status: 400 })
    }
    
    console.error('Worksheet generation error:', err)
    return NextResponse.json({ 
      error: 'Internal server error' 
    }, { status: 500 })
  }
}
