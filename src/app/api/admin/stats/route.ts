import { NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { getR2Client, R2_BUCKET } from "@/lib/r2Client"
import { ListObjectsV2Command } from "@aws-sdk/client-s3"

export const dynamic = "force-dynamic"

export async function GET() {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin() || auth.db

  const [subjectsRes, papersRes, profilesRes, withQPRes, withMSRes, pagesRes, questionPagesRes] = await Promise.all([
    db.from("subjects").select("id", { count: "exact", head: true }),
    db.from("papers").select("id", { count: "exact", head: true }),
    db.from("profiles").select("role"),
    db.from("papers").select("id", { count: "exact", head: true }).not("pdf_url", "is", null),
    db.from("papers").select("id", { count: "exact", head: true }).not("markscheme_pdf_url", "is", null),
    db.from("pages").select("id", { count: "exact", head: true }),
    db.from("pages").select("id", { count: "exact", head: true }).eq("is_question", true).not("qp_page_url", "is", null),
  ])

  if (subjectsRes.error || papersRes.error || profilesRes.error || withQPRes.error || withMSRes.error) {
    const message =
      subjectsRes.error?.message ||
      papersRes.error?.message ||
      profilesRes.error?.message ||
      withQPRes.error?.message ||
      withMSRes.error?.message ||
      "Failed to load admin stats"
    return NextResponse.json({ error: message }, { status: 500 })
  }

  const roles = { total: 0, admins: 0, teachers: 0, students: 0 }
  for (const p of profilesRes.data || []) {
    roles.total++
    if (p.role === "admin") roles.admins++
    else if (p.role === "teacher") roles.teachers++
    else roles.students++
  }

  // Count R2 objects (truncate at 1000 for speed)
  let r2Count = 0
  try {
    const r2 = getR2Client()
    const res = await r2.send(new ListObjectsV2Command({ Bucket: R2_BUCKET, MaxKeys: 1000 }))
    r2Count = res.KeyCount || 0
  } catch { /* R2 may not be reachable on Vercel */ }

  return NextResponse.json({
    subjects: subjectsRes.count ?? 0,
    papers: papersRes.count ?? 0,
    papersWithQP: withQPRes.count ?? 0,
    papersWithMS: withMSRes.count ?? 0,
    pages: pagesRes.count ?? 0,
    questionPages: questionPagesRes.count ?? 0,
    r2Objects: r2Count,
    users: roles,
  })
}
