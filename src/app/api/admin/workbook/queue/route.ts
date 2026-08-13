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

  const COLUMNS = `id, slug, section_id, proposed_section_id, review_priority, classifier_confidence,
       secondary_section_ids, ordinal_in_chapter, marks, difficulty, sub_parts,
       qp_pdf_url, ms_pdf_url, text_status, source_paper_key, source_question_number, verified_at`

  // Fill the page one priority at a time, HARDEST FIRST, letting the database
  // do the filtering.
  //
  // The previous version fetched `limit * 4` rows with no ORDER BY and ranked
  // them in memory, on the assumption that a few hundred rows covered the whole
  // working set. It did not. With 1046 unverified Maths B questions the query
  // returned 320 arbitrary rows -- and because physical order put them there,
  // all 320 were `agreed`. The reviewer would have been shown 320 questions the
  // models already agreed on while all 151 disputed ones sat unreachable, which
  // is precisely backwards: the two-model disagreement signal exists to put the
  // doubtful questions first.
  const wanted: readonly Priority[] =
    priority && (PRIORITY_ORDER as readonly string[]).includes(priority)
      ? [priority as Priority]
      : PRIORITY_ORDER

  const collected: QuestionRow[] = []
  const remaining: Record<string, number> = {}

  for (const bucket of wanted) {
    // Count every question in this bucket, not just the ones fetched, so the
    // progress readout reflects the work left rather than the page size.
    let counter = db
      .from("workbook_questions")
      .select("id", { count: "exact", head: true })
      .eq("subject_id", subjectId)
      .eq("review_priority", bucket)
    if (!includeVerified) counter = counter.is("verified_at", null)
    const { count: bucketCount } = await counter
    if (bucketCount) remaining[bucket] = bucketCount

    if (collected.length >= limit) continue

    let query = db
      .from("workbook_questions")
      .select(COLUMNS)
      .eq("subject_id", subjectId)
      .eq("review_priority", bucket)
      .order("slug")
      .limit(limit - collected.length)
    if (!includeVerified) query = query.is("verified_at", null)

    const { data, error } = await query
    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 })
    }
    collected.push(...((data ?? []) as unknown as QuestionRow[]))
  }

  // A row whose priority was never backfilled would otherwise be invisible --
  // it matches no bucket, so it could never be reviewed at all.
  if (!priority) {
    let orphanCounter = db
      .from("workbook_questions")
      .select("id", { count: "exact", head: true })
      .eq("subject_id", subjectId)
      .is("review_priority", null)
    if (!includeVerified) orphanCounter = orphanCounter.is("verified_at", null)
    const { count: orphanCount } = await orphanCounter

    if (orphanCount) {
      remaining.unset = orphanCount
      if (collected.length < limit) {
        let orphans = db
          .from("workbook_questions")
          .select(COLUMNS)
          .eq("subject_id", subjectId)
          .is("review_priority", null)
          .order("slug")
          .limit(limit - collected.length)
        if (!includeVerified) orphans = orphans.is("verified_at", null)
        const { data } = await orphans
        collected.push(...((data ?? []) as unknown as QuestionRow[]))
      }
    }
  }

  let totalQuery = db
    .from("workbook_questions")
    .select("id", { count: "exact", head: true })
    .eq("subject_id", subjectId)
  if (!includeVerified) totalQuery = totalQuery.is("verified_at", null)
  const { count } = await totalQuery

  return NextResponse.json({
    questions: collected.slice(0, limit),
    chapters,
    sections: sections ?? [],
    totalUnverified: count ?? 0,
    remaining,
  })
}
