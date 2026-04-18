import { NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

export const dynamic = "force-dynamic"

/**
 * GET /api/admin/nav-badges
 * Returns lightweight counts for nav badge indicators.
 */
export async function GET() {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin() || auth.db

  const [missingQPRes, missingMSRes] = await Promise.all([
    db.from("papers").select("id", { count: "exact", head: true }).is("pdf_url", null),
    db.from("papers").select("id", { count: "exact", head: true }).is("markscheme_pdf_url", null),
  ])

  const missingPapers = (missingQPRes.count ?? 0) + (missingMSRes.count ?? 0)

  // Count untagged questions — gracefully skips if table doesn't exist
  let unreviewedQuestions = 0
  try {
    // Questions that have no rows in question_topics
    const { data: allQIds } = await db.from("questions").select("id")
    const { data: taggedQIds } = await db.from("question_topics").select("question_id")
    if (allQIds && taggedQIds) {
      const tagged = new Set(taggedQIds.map((r: { question_id: number }) => r.question_id))
      unreviewedQuestions = allQIds.filter((r: { id: number }) => !tagged.has(r.id)).length
    }
  } catch {
    // Tables may not exist
  }

  return NextResponse.json({ missingPapers, unreviewedQuestions })
}
