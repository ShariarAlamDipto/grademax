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

  const [subjectsRes, papersRes, profilesRes] = await Promise.all([
    db.from("subjects").select("id", { count: "exact", head: true }),
    db.from("papers").select("id", { count: "exact", head: true }),
    db.from("profiles").select("role"),
  ])

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

  // Papers with QP and MS coverage
  const { data: withQP } = await db.from("papers").select("id", { count: "exact", head: true }).not("pdf_url", "is", null)
  const { data: withMS } = await db.from("papers").select("id", { count: "exact", head: true }).not("markscheme_pdf_url", "is", null)

  return NextResponse.json({
    subjects: subjectsRes.count ?? 0,
    papers: papersRes.count ?? 0,
    papersWithQP: (withQP as unknown as { count: number })?.count ?? 0,
    papersWithMS: (withMS as unknown as { count: number })?.count ?? 0,
    r2Objects: r2Count,
    users: roles,
  })
}
