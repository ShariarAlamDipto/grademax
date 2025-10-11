import { NextResponse } from "next/server"
import { createClient } from "@supabase/supabase-js"

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

export async function POST(req: Request) {
  try {
    const params = await req.json()
    const { subjectId, topicIds, difficulties, count, balanceTopics } = params as {
      subjectId: number
      topicIds?: number[]
      difficulties?: number[]
      count?: number
      balanceTopics?: boolean
    }

    if (!subjectId) return NextResponse.json({ error: 'subjectId required' }, { status: 400 })

    type RawQuestion = {
      id: number
      text: string
      marks: number
      difficulty: number
      paper_id: number
      question_number: string
      question_topics: { topic_id: number }[]
    }

    let base = supabase
      .from('questions')
      .select('id, text, marks, difficulty, paper_id, question_number, question_topics!inner(topic_id)')
      .eq('papers.subject_id', subjectId)

    if (topicIds?.length) base = base.in('question_topics.topic_id', topicIds)
    if (difficulties?.length) base = base.in('difficulty', difficulties)

    // Fetch more than needed to allow balancing
    const fetchCount = Math.min(200, (count || 10) * 4)
    const { data: rows, error } = await base.limit(fetchCount)
    if (error) return NextResponse.json({ error: error.message }, { status: 400 })

    let picked: RawQuestion[] = (rows as RawQuestion[]) || []
    if (balanceTopics && topicIds?.length) {
      const per = Math.max(1, Math.floor((count || 10) / topicIds.length))
      const byTopic: Record<number, RawQuestion[]> = {}
      for (const r of picked) {
        const t = r.question_topics?.[0]?.topic_id
        if (typeof t !== 'number') continue
        if (!byTopic[t]) byTopic[t] = []
        byTopic[t].push(r)
      }
      const final: RawQuestion[] = []
      for (const tid of topicIds) {
        const pool = (byTopic[tid] || []).slice(0, per)
        final.push(...pool)
      }
      while (final.length < (count || 10) && picked.length) {
        const x = picked.shift()
        if (x && !final.includes(x)) final.push(x)
      }
      picked = final.slice(0, count || 10)
    } else {
      picked = picked.slice(0, count || 10)
    }

    // Persist worksheet
    const { data: ws, error: wsErr } = await supabase
      .from('worksheets')
      .insert({ params })
      .select('id')
      .single()
    if (wsErr) return NextResponse.json({ error: wsErr.message }, { status: 400 })

    const items = picked.map((r, i) => ({
      worksheet_id: ws.id,
      question_id: r.id,
      position: i + 1,
    }))
    if (items.length) await supabase.from('worksheet_items').insert(items)

    // Fetch markschemes
  const qIds = picked.map(r => r.id)
    const { data: ms } = await supabase
      .from('markschemes')
      .select('question_id, text')
      .in('question_id', qIds)

    return NextResponse.json({ worksheetId: ws.id, questions: picked, markschemes: ms || [] })
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Server error'
    return NextResponse.json({ error: msg }, { status: 500 })
  }
}
