import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

export const dynamic = "force-dynamic"

export async function GET(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin() || auth.db
  const offset = parseInt(req.nextUrl.searchParams.get("offset") || "0")
  const limit = Math.min(parseInt(req.nextUrl.searchParams.get("limit") || "50"), 200)
  const untaggedOnly = req.nextUrl.searchParams.get("untagged") === "true"
  const minConf = parseFloat(req.nextUrl.searchParams.get("minConf") || "0")
  const subjectId = req.nextUrl.searchParams.get("subjectId") || ""

  // Resolve paper IDs for the subject filter
  let paperIdFilter: string[] | null = null
  if (subjectId) {
    const { data: papers, error: pErr } = await db
      .from("papers")
      .select("id")
      .eq("subject_id", subjectId)
    if (pErr) return NextResponse.json({ error: pErr.message }, { status: 500 })
    if (!papers || papers.length === 0) {
      return NextResponse.json({ questions: [], topics: [], total: 0 })
    }
    paperIdFilter = papers.map((p: { id: string }) => p.id)
  }

  let query = db
    .from("pages")
    .select("id, question_number, text_excerpt, difficulty, confidence, topics, paper_id", { count: "exact" })
    .eq("is_question", true)
    .order("id", { ascending: false })

  if (paperIdFilter) query = query.in("paper_id", paperIdFilter)
  if (untaggedOnly) query = query.or("topics.is.null,topics.eq.{}")

  const { data: pages, error: qErr, count } = await query.range(offset, offset + limit - 1)
  if (qErr) return NextResponse.json({ error: qErr.message }, { status: 500 })

  // Get topics for the subject
  let topicsQuery = db.from("topics").select("id, name, code").order("code")
  if (subjectId) topicsQuery = topicsQuery.eq("subject_id", subjectId)
  const { data: topicsData, error: tErr } = await topicsQuery
  if (tErr) return NextResponse.json({ error: tErr.message }, { status: 500 })

  // Build lookup maps: both code→topic and id→topic
  const byCode: Record<string, { code: string; name: string }> = {}
  const byId: Record<string, { code: string; name: string }> = {}
  for (const t of (topicsData || [])) {
    const entry = { code: String(t.code), name: t.name }
    byCode[String(t.code)] = entry
    byId[String(t.id)] = entry
  }

  const questions = (pages || []).map((p: {
    id: string; question_number: string; text_excerpt: string | null
    difficulty: string | null; confidence: number | null; topics: string[] | null
  }) => {
    const topicCodes: string[] = Array.isArray(p.topics) ? p.topics : []
    const conf = typeof p.confidence === "number" ? p.confidence : 0

    const predicted_topics = topicCodes
      .map(code => {
        const t = byCode[code] || byId[code]
        return t ? { code: t.code, name: t.name, confidence: conf } : null
      })
      .filter((t): t is { code: string; name: string; confidence: number } => t !== null)

    if (minConf > 0 && predicted_topics.length > 0 && predicted_topics.every(t => t.confidence >= minConf)) {
      return null
    }

    return {
      id: p.id,
      question_number: p.question_number || "",
      text: p.text_excerpt || "",
      difficulty: p.difficulty || "",
      predicted_topics,
    }
  }).filter(Boolean)

  const topics = (topicsData || []).map((t: { id: string; code: string; name: string }) => ({
    code: String(t.code),
    name: t.name,
  }))

  return NextResponse.json({ questions, topics, total: count ?? 0 })
}

export async function POST(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin() || auth.db
  const body = await req.json().catch(() => ({}))
  const { question_id, topic_codes } = body as { question_id?: string; topic_codes?: string[] }

  if (!question_id) return NextResponse.json({ error: "question_id required" }, { status: 400 })
  if (!Array.isArray(topic_codes)) return NextResponse.json({ error: "topic_codes must be an array" }, { status: 400 })

  const { error } = await db
    .from("pages")
    .update({ topics: topic_codes })
    .eq("id", question_id)

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  return NextResponse.json({ success: true, question_id, tagged: topic_codes.length })
}
