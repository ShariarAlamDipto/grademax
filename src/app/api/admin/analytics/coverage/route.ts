import { NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

export const dynamic = "force-dynamic"

/**
 * GET /api/admin/analytics/coverage
 * Returns per-subject QP/MS coverage stats.
 */
export async function GET() {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin() || auth.db

  const { data: subjects, error: subjErr } = await db
    .from("subjects")
    .select("id, name, code, level")
    .order("level")
    .order("name")

  if (subjErr) return NextResponse.json({ error: subjErr.message }, { status: 500 })

  const { data: papers, error: papersErr } = await db
    .from("papers")
    .select("subject_id, pdf_url, markscheme_pdf_url")

  if (papersErr) return NextResponse.json({ error: papersErr.message }, { status: 500 })

  // Aggregate per subject
  const statsMap = new Map<string, { total: number; withQP: number; withMS: number; both: number }>()
  for (const p of papers || []) {
    const s = statsMap.get(p.subject_id) || { total: 0, withQP: 0, withMS: 0, both: 0 }
    s.total++
    const hasQP = !!(p.pdf_url?.startsWith("http"))
    const hasMS = !!(p.markscheme_pdf_url?.startsWith("http"))
    if (hasQP) s.withQP++
    if (hasMS) s.withMS++
    if (hasQP && hasMS) s.both++
    statsMap.set(p.subject_id, s)
  }

  const rows = (subjects || []).map(s => {
    const stats = statsMap.get(s.id) || { total: 0, withQP: 0, withMS: 0, both: 0 }
    return {
      id: s.id,
      name: s.name,
      code: s.code,
      level: s.level,
      total: stats.total,
      withQP: stats.withQP,
      withMS: stats.withMS,
      both: stats.both,
      qpPct: stats.total > 0 ? Math.round((stats.withQP / stats.total) * 100) : 0,
      msPct: stats.total > 0 ? Math.round((stats.withMS / stats.total) * 100) : 0,
    }
  })

  return NextResponse.json({ rows })
}
