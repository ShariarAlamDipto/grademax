import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

export const dynamic = "force-dynamic"

/**
 * POST /api/admin/workbook/verify
 *
 * Sign off one question's section assignment. This is the gate: the RLS policy
 * on workbook_questions only exposes rows with verified_at set, so nothing
 * reaches a student until it has been through here.
 *
 * Body:
 *   questionId          - required
 *   sectionId           - optional; reassigns the section when it differs
 *   secondarySectionIds - optional; replaces the secondary list
 *   unverify            - optional; clears verification instead (undo)
 */

interface VerifyBody {
  questionId?: string
  sectionId?: string
  secondarySectionIds?: string[]
  unverify?: boolean
}

export async function POST(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin() || auth.db

  let body: VerifyBody
  try {
    body = (await req.json()) as VerifyBody
  } catch {
    return NextResponse.json({ error: "Body must be JSON" }, { status: 400 })
  }

  const { questionId, sectionId, secondarySectionIds, unverify } = body

  if (!questionId) {
    return NextResponse.json({ error: "questionId is required" }, { status: 400 })
  }

  const { data: question, error: loadError } = await db
    .from("workbook_questions")
    .select("id, section_id, subject_id")
    .eq("id", questionId)
    .single()

  if (loadError || !question) {
    return NextResponse.json({ error: "Question not found" }, { status: 404 })
  }

  if (unverify) {
    const { error } = await db
      .from("workbook_questions")
      .update({ verified_at: null, verified_by: null, updated_at: new Date().toISOString() })
      .eq("id", questionId)

    if (error) return NextResponse.json({ error: error.message }, { status: 500 })
    return NextResponse.json({ ok: true, verified: false })
  }

  const update: Record<string, unknown> = {
    verified_at: new Date().toISOString(),
    verified_by: auth.user.id,
    updated_at: new Date().toISOString(),
  }

  // A reassignment has to be checked against the real section list: an id from
  // another subject would silently move the question into a foreign chapter.
  if (sectionId && sectionId !== question.section_id) {
    const { data: valid, error: sectionError } = await db
      .from("workbook_sections")
      .select("id, chapter_id, workbook_chapters!inner(subject_id)")
      .eq("id", sectionId)
      .single()

    if (sectionError || !valid) {
      return NextResponse.json({ error: "Unknown section" }, { status: 400 })
    }

    const owner = (valid as unknown as { workbook_chapters: { subject_id: string } })
      .workbook_chapters?.subject_id
    if (owner !== question.subject_id) {
      return NextResponse.json(
        { error: "That section belongs to a different subject" },
        { status: 400 }
      )
    }

    update.section_id = sectionId
  }

  if (Array.isArray(secondarySectionIds)) {
    update.secondary_section_ids = secondarySectionIds.filter(
      (id) => id !== (update.section_id ?? question.section_id)
    )
  }

  const { error } = await db.from("workbook_questions").update(update).eq("id", questionId)

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  const { count } = await db
    .from("workbook_questions")
    .select("id", { count: "exact", head: true })
    .eq("subject_id", question.subject_id)
    .is("verified_at", null)

  return NextResponse.json({ ok: true, verified: true, remainingUnverified: count ?? 0 })
}
