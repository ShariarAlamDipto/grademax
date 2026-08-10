import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

export const dynamic = "force-dynamic"

/**
 * GET /api/admin/workbook/queue
 *
 * The Phase 4 verification queue: unverified workbook questions, hardest first.
 *
 * Ordering is by two-model agreement rather than by the classifier's own
 * confidence, which is measurably useless here — mean confidence was 0.858 when
 * two models agreed on the section and 0.827 when they flatly disagreed, a 0.03
 * spread across the whole range of correctness. Agreement separates them.
 *
 * Query params:
 *   subjectId  - required
 *   priority   - optional filter: disputed | same_chapter | unconfirmed | agreed
 *   includeVerified - "true" to review already-signed-off questions
 *   limit      - default 60, max 200
 */

const PRIORITY_ORDER = ["disputed", "same_chapter", "unconfirmed", "agreed"] as const
type Priority = (typeof PRIORITY_ORDER)[number]

interface QuestionRow {
  id: string
  slug: string
  section_id: string
  proposed_section_id: string | null
  review_priority: Priority | null
  classifier_confidence: number | null
  secondary_section_ids: string[] | null
  ordinal_in_chapter: number
  marks: number
  difficulty: string | null
  sub_parts: unknown
  qp_pdf_url: string | null
  ms_pdf_url: string | null
  text_status: string | null
  source_paper_key: string
  source_question_number: number
  verified_at: string | null
}

export async function GET(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin() || auth.db
  const { searchParams } = req.nextUrl
  const subjectId = searchParams.get("subjectId")
  const priority = searchParams.get("priority")
  const includeVerified = searchParams.get("includeVerified") === "true"
  const limit = Math.min(parseInt(searchParams.get("limit") || "60", 10) || 60, 200)

  if (!subjectId) {
    return NextResponse.json({ error: "subjectId is required" }, { status: 400 })
  }

  // Chapters and sections are small reference tables — send them whole so the
  // client can render a section picker without a request per question.
  const { data: chapters, error: chapterError } = await db
    .from("workbook_chapters")
    .select("id, number, title")
    .eq("subject_id", subjectId)
    .order("number")

  if (chapterError) {
    return NextResponse.json({ error: chapterError.message }, { status: 500 })
  }
  if (!chapters || chapters.length === 0) {
    return NextResponse.json({ error: "No workbook chapters for this subject" }, { status: 404 })
  }

  const chapterIds = chapters.map((c) => c.id)
  const { data: sections, error: sectionError } = await db
    .from("workbook_sections")
    .select("id, chapter_id, number, title")
    .in("chapter_id", chapterIds)
    .order("number")

  if (sectionError) {
    return NextResponse.json({ error: sectionError.message }, { status: 500 })
  }

  let query = db
    .from("workbook_questions")
    .select(
      `id, slug, section_id, proposed_section_id, review_priority, classifier_confidence,
       secondary_section_ids, ordinal_in_chapter, marks, difficulty, sub_parts,
       qp_pdf_url, ms_pdf_url, text_status, source_paper_key, source_question_number, verified_at`,
      { count: "exact" }
    )
    .eq("subject_id", subjectId)

  if (!includeVerified) query = query.is("verified_at", null)
  if (priority && (PRIORITY_ORDER as readonly string[]).includes(priority)) {
    query = query.eq("review_priority", priority)
  }

  const { data: questions, count, error } = await query.limit(limit * 4)

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  // Postgres cannot order by an arbitrary enum sequence without a CASE, and the
  // working set is a few hundred rows, so rank in memory instead.
  const rank = (row: QuestionRow) => {
    const index = PRIORITY_ORDER.indexOf((row.review_priority ?? "agreed") as Priority)
    return index === -1 ? PRIORITY_ORDER.length : index
  }

  const ordered = ((questions ?? []) as QuestionRow[])
    .sort((a, b) => rank(a) - rank(b) || a.slug.localeCompare(b.slug))
    .slice(0, limit)

  const remaining: Record<string, number> = {}
  for (const row of (questions ?? []) as QuestionRow[]) {
    const key = row.review_priority ?? "unconfirmed"
    remaining[key] = (remaining[key] ?? 0) + 1
  }

  return NextResponse.json({
    questions: ordered,
    chapters,
    sections: sections ?? [],
    totalUnverified: count ?? 0,
    remaining,
  })
}
