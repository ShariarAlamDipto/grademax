import { NextResponse } from "next/server"
import { createClient } from "@supabase/supabase-js"

/**
 * The subjects that actually have a workbook, for the verify UI's picker.
 *
 * `/api/subjects` returns all ~98 subjects on the site, but only a handful have
 * a workbook taxonomy loaded. Offering the rest means most of the picker leads
 * to a 404 from the queue endpoint, which got noticeably worse once there were
 * four workbook subjects rather than one.
 *
 * A subject qualifies by having at least one `workbook_chapters` row -- the same
 * condition the queue endpoint requires -- so the picker cannot offer something
 * the queue will reject.
 */
export const dynamic = "force-dynamic"

export async function GET() {
  const db = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
  )

  const { data: chapters, error: chapterError } = await db
    .from("workbook_chapters")
    .select("subject_id")

  if (chapterError) {
    return NextResponse.json({ error: chapterError.message }, { status: 500 })
  }

  const subjectIds = [...new Set((chapters ?? []).map((c) => c.subject_id))]
  if (subjectIds.length === 0) {
    return NextResponse.json({ subjects: [] })
  }

  const { data: subjects, error: subjectError } = await db
    .from("subjects")
    .select("id, code, name")
    .in("id", subjectIds)
    .order("code")

  if (subjectError) {
    return NextResponse.json({ error: subjectError.message }, { status: 500 })
  }

  // Unverified count per subject, so the picker can show what is left to do.
  const counts: Record<string, number> = {}
  for (const id of subjectIds) {
    const { count } = await db
      .from("workbook_questions")
      .select("id", { count: "exact", head: true })
      .eq("subject_id", id)
      .is("verified_at", null)
    counts[id] = count ?? 0
  }

  return NextResponse.json({
    subjects: (subjects ?? []).map((s) => ({ ...s, unverified: counts[s.id] ?? 0 })),
  })
}
