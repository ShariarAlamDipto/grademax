import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

export const maxDuration = 120 // seconds — needed for large classification jobs

const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
const MODEL = "llama-3.1-8b-instant"
const BATCH_SIZE = 4
const BATCH_SLEEP_MS = 1200
const GROQ_TIMEOUT_MS = 15000
const RATE_LIMIT_BACKOFF_MS = 8000
const RATE_LIMIT_MAX_RETRIES = 2
const DEFAULT_LIMIT = 40
const MAX_LIMIT = 100
const MIN_LIMIT = 1
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

interface TopicGuardrails {
  include_when?: string
  exclude_when?: string
}

interface Topic {
  id: string
  code: string
  name: string
  description: string
  keywords?: string[]
  guardrails?: TopicGuardrails
}

interface PageRow {
  id: string
  question_number: string
  text_excerpt: string | null
}

interface ClassifyResult {
  id: string
  topic: string
  difficulty: "easy" | "medium" | "hard"
  confidence: number
}

function buildClassifyPrompt(subjectName: string, topics: Topic[], pages: PageRow[]): string {
  const topicList = topics.map(t => {
    const parts = [
      `[${t.code}] ${t.name}: ${t.description}`,
      t.keywords?.length ? `Keywords: ${t.keywords.join(", ")}` : null,
      t.guardrails?.include_when ? `Classify as ${t.code} WHEN: ${t.guardrails.include_when}` : null,
      t.guardrails?.exclude_when ? `Do NOT classify as ${t.code} WHEN: ${t.guardrails.exclude_when}` : null,
    ].filter(Boolean)
    return parts.join("\n  ")
  }).join("\n\n")

  const questionList = pages.map((p, i) =>
    `Q${i + 1} [id=${p.id}]: ${(p.text_excerpt || "").slice(0, 400) || "(no text excerpt - skip this question)"}`
  ).join("\n\n")

  return `You are classifying ${subjectName} exam questions by topic.

TOPICS:
${topicList}

QUESTIONS:
${questionList}

For each question, choose the single best matching topic code from the list above.
Use the guardrails to resolve ambiguous cases.
Assess difficulty as: easy (recall/direct), medium (application), hard (analysis/multi-step).

Return ONLY a JSON array, one object per question, in order:
[{"id":"<uuid>","topic":"<CODE>","difficulty":"easy|medium|hard","confidence":0.0-1.0}]`
}

function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function callGroq(prompt: string, groqKey: string): Promise<Response> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), GROQ_TIMEOUT_MS)
  try {
    const response = await fetch(GROQ_URL, {
      method: "POST",
      headers: { Authorization: `Bearer ${groqKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        model: MODEL,
        messages: [{ role: "user", content: prompt }],
        temperature: 0.1,
        max_tokens: 1024,
      }),
      signal: controller.signal,
    })
    return response
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Groq API request timed out")
    }
    throw err
  } finally {
    clearTimeout(timeoutId)
  }
}

async function classifyBatch(
  subjectName: string,
  topics: Topic[],
  pages: PageRow[],
  groqKey: string
): Promise<ClassifyResult[]> {
  const prompt = buildClassifyPrompt(subjectName, topics, pages)

  let response: Response | null = null
  for (let attempt = 0; attempt <= RATE_LIMIT_MAX_RETRIES; attempt++) {
    response = await callGroq(prompt, groqKey)
    if (response.status !== 429) break
    if (attempt < RATE_LIMIT_MAX_RETRIES) {
      await sleep(RATE_LIMIT_BACKOFF_MS * (attempt + 1))
    }
  }

  if (!response || !response.ok) {
    const errText = response ? await response.text() : "no response"
    throw new Error(`Groq API error ${response?.status ?? 0}: ${errText.slice(0, 200)}`)
  }

  const data = await response.json()
  const text: string = data.choices?.[0]?.message?.content ?? ""

  const start = text.indexOf("[")
  const end = text.lastIndexOf("]") + 1
  if (start === -1 || end <= start) return []

  try {
    return JSON.parse(text.slice(start, end)) as ClassifyResult[]
  } catch {
    return []
  }
}

export async function POST(req: NextRequest) {
  const authResult = await requireAdmin()
  if ("error" in authResult) return authResult.error

  const groqKey = process.env.GROQ_API_KEY
  if (!groqKey) {
    return NextResponse.json({ error: "GROQ_API_KEY not configured" }, { status: 500 })
  }

  const body = await req.json().catch(() => null)
  if (!body || typeof body !== "object") {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 })
  }

  const {
    subjectId,
    topics: clientTopics,
    offset = 0,
    limit = DEFAULT_LIMIT,
    reclassify = false,
  } = body as {
    subjectId: string
    topics?: Topic[]
    offset?: number
    limit?: number
    reclassify?: boolean
  }

  if (!subjectId) {
    return NextResponse.json({ error: "subjectId required" }, { status: 400 })
  }
  if (!UUID_RE.test(subjectId)) {
    return NextResponse.json({ error: "Invalid subjectId" }, { status: 400 })
  }

  const safeOffset = Math.max(0, Math.trunc(Number(offset) || 0))
  const safeLimit = Math.min(MAX_LIMIT, Math.max(MIN_LIMIT, Math.trunc(Number(limit) || DEFAULT_LIMIT)))

  const db = getSupabaseAdmin()
  if (!db) return NextResponse.json({ error: "Admin client not available" }, { status: 500 })

  // Get subject name
  const { data: subject } = await db
    .from("subjects")
    .select("name")
    .eq("id", subjectId)
    .single()
  if (!subject) return NextResponse.json({ error: "Subject not found" }, { status: 404 })

  // Get topics (use client-provided for guardrails, fall back to DB)
  let topics: Topic[] = clientTopics || []
  if (topics.length === 0) {
    const { data: dbTopics } = await db
      .from("topics")
      .select("id, code, name, description")
      .eq("subject_id", subjectId)
      .order("code")
    topics = (dbTopics || []).map(t => ({
      id: t.id,
      code: t.code,
      name: t.name,
      description: t.description || "",
    }))
  }
  if (topics.length === 0) {
    return NextResponse.json({ error: "No topics found for this subject. Create topics first." }, { status: 400 })
  }

  // Build valid topic codes for validation
  const validCodes = new Set(topics.map(t => t.code.toUpperCase()))

  // Get paper IDs for this subject
  const { data: papers } = await db
    .from("papers")
    .select("id")
    .eq("subject_id", subjectId)
  const paperIds = (papers || []).map((p: { id: string }) => p.id)

  if (paperIds.length === 0) {
    return NextResponse.json({ processed: 0, classified: 0, errors: 0, total: 0, nextOffset: 0, done: true })
  }

  // Count total unclassified pages (for progress tracking)
  let totalQuery = db
    .from("pages")
    .select("id", { count: "exact", head: true })
    .in("paper_id", paperIds)
    .eq("is_question", true)
    .not("qp_page_url", "is", null)

  if (!reclassify) {
    totalQuery = totalQuery.or("topics.is.null,topics.eq.{}")
  }
  const { count: total } = await totalQuery

  // Fetch the current chunk
  let pageQuery = db
    .from("pages")
    .select("id, question_number, text_excerpt")
    .in("paper_id", paperIds)
    .eq("is_question", true)
    .not("qp_page_url", "is", null)
    .order("id")
    .range(safeOffset, safeOffset + safeLimit - 1)

  if (!reclassify) {
    pageQuery = pageQuery.or("topics.is.null,topics.eq.{}")
  }

  const { data: pages } = await pageQuery
  const chunk = (pages || []) as PageRow[]

  if (chunk.length === 0) {
    return NextResponse.json({
      processed: 0, classified: 0, errors: 0,
      total: total ?? 0, nextOffset: safeOffset, done: true,
    })
  }

  // Classify in batches of BATCH_SIZE
  let classified = 0
  let errors = 0
  const updates: Array<{ id: string; topics: string[]; difficulty: string; confidence: number }> = []

  for (let i = 0; i < chunk.length; i += BATCH_SIZE) {
    const batch = chunk.slice(i, i + BATCH_SIZE)
    const pagesWithText = batch.filter(p => p.text_excerpt && p.text_excerpt.trim())
    const allowedIds = new Set(batch.map(p => p.id))

    if (pagesWithText.length === 0) {
      errors += batch.length
      continue
    }

    try {
      const results = await classifyBatch(subject.name, topics, pagesWithText, groqKey)

      for (const r of results) {
        if (!r || typeof r.id !== "string" || !UUID_RE.test(r.id)) {
          errors++
          continue
        }
        if (!allowedIds.has(r.id)) {
          errors++
          continue
        }

        const topicCode = r.topic?.toUpperCase?.() ?? r.topic
        if (!validCodes.has(topicCode)) {
          errors++
          continue
        }

        updates.push({
          id: r.id,
          topics: [topicCode],
          difficulty: r.difficulty || "medium",
          confidence: Math.max(0, Math.min(1, r.confidence ?? 0.7)),
        })
        classified++
      }

      // Mark pages with no text as errors (already excluded from pagesWithText)
      errors += batch.length - pagesWithText.length
    } catch {
      errors += batch.length
    }

    if (i + BATCH_SIZE < chunk.length) {
      await sleep(BATCH_SLEEP_MS)
    }
  }

  // Batch update classified pages
  for (const u of updates) {
    const { error: updateError } = await db
      .from("pages")
      .update({ topics: u.topics, difficulty: u.difficulty, confidence: u.confidence })
      .eq("id", u.id)

    if (updateError) {
      errors++
      classified = Math.max(0, classified - 1)
    }
  }

  const nextOffset = safeOffset + chunk.length
  const done = chunk.length < safeLimit || nextOffset >= (total ?? 0)

  return NextResponse.json({
    processed: chunk.length,
    classified,
    errors,
    total: total ?? 0,
    nextOffset,
    done,
  })
}

