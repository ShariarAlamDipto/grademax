import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

export const dynamic = "force-dynamic"

/**
 * GET /api/admin/tagger?offset=0&limit=50&untagged=true&minConf=0
 * Returns paginated questions with their topic tags.
 */
export async function GET(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin() || auth.db
  const offset = parseInt(req.nextUrl.searchParams.get("offset") || "0")
  const limit = Math.min(parseInt(req.nextUrl.searchParams.get("limit") || "50"), 200)
  const untaggedOnly = req.nextUrl.searchParams.get("untagged") === "true"
  const minConf = parseFloat(req.nextUrl.searchParams.get("minConf") || "0")

  let query = db
    .from("questions")
    .select("id, question_number, text, difficulty, marks, question_topics(topic_id, confidence, topics(id, name))", { count: "exact" })
    .order("id", { ascending: false })
    .range(offset, offset + limit - 1)

  const { data: qs, error: qErr, count } = await query
  if (qErr) return NextResponse.json({ error: qErr.message }, { status: 500 })

  const { data: topics, error: tErr } = await db.from("topics").select("id, name").order("name")
  if (tErr) return NextResponse.json({ error: tErr.message }, { status: 500 })

  type RawQT = { topic_id: number; confidence: number; topics: { id: number; name: string } | { id: number; name: string }[] | null }
  type RawQ = { id: number; question_number: string; text: string; difficulty: number; marks: number; question_topics: RawQT[] | null }

  let questions = ((qs || []) as RawQ[]).map(q => {
    const predictedTopics = (q.question_topics || [])
      .map(qt => {
        const topic = Array.isArray(qt.topics) ? qt.topics[0] : qt.topics
        if (!topic?.id || !topic?.name) return null
        return { id: topic.id, name: topic.name, confidence: qt.confidence }
      })
      .filter((t): t is { id: number; name: string; confidence: number } => t !== null)
    return { id: q.id, question_number: q.question_number, text: q.text, difficulty: q.difficulty, marks: q.marks, predicted_topics: predictedTopics }
  })

  if (untaggedOnly) questions = questions.filter(q => q.predicted_topics.length === 0)
  if (minConf > 0) questions = questions.filter(q =>
    q.predicted_topics.length === 0 || q.predicted_topics.some(t => t.confidence < minConf)
  )

  return NextResponse.json({ questions, topics: topics || [], total: count ?? 0 })
}

/**
 * POST /api/admin/tagger
 * Body: { question_id: number, topic_ids: number[] }
 * Replaces all tags for the given question.
 */
export async function POST(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin() || auth.db
  const body = await req.json().catch(() => ({}))
  const { question_id, topic_ids } = body as { question_id?: number; topic_ids?: number[] }

  if (!question_id) return NextResponse.json({ error: "question_id required" }, { status: 400 })
  if (!Array.isArray(topic_ids)) return NextResponse.json({ error: "topic_ids must be an array" }, { status: 400 })

  const { error: deleteError } = await db.from("question_topics").delete().eq("question_id", question_id)
  if (deleteError) return NextResponse.json({ error: deleteError.message }, { status: 500 })

  if (topic_ids.length > 0) {
    const { error: insertError } = await db
      .from("question_topics")
      .insert(topic_ids.map(tid => ({ question_id, topic_id: tid, confidence: 1.0 })))
    if (insertError) return NextResponse.json({ error: insertError.message }, { status: 500 })
  }

  return NextResponse.json({ success: true, question_id, tagged: topic_ids.length })
}
