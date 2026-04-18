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

  const [subjectsRes, papersRes, adminRes, teacherRes, studentRes, withQPRes, withMSRes, pagesRes, questionPagesRes, testsRes, worksheetsRes] = await Promise.all([
    db.from("subjects").select("id", { count: "exact", head: true }),
    db.from("papers").select("id", { count: "exact", head: true }),
    db.from("profiles").select("id", { count: "exact", head: true }).eq("role", "admin"),
    db.from("profiles").select("id", { count: "exact", head: true }).eq("role", "teacher"),
    db.from("profiles").select("id", { count: "exact", head: true }).not("role", "in", '("admin","teacher")'),
    db.from("papers").select("id", { count: "exact", head: true }).not("pdf_url", "is", null),
    db.from("papers").select("id", { count: "exact", head: true }).not("markscheme_pdf_url", "is", null),
    db.from("pages").select("id", { count: "exact", head: true }),
    db.from("pages").select("id", { count: "exact", head: true }).eq("is_question", true).not("qp_page_url", "is", null),
    db.from("tests").select("id", { count: "exact", head: true }),
    db.from("worksheets").select("id", { count: "exact", head: true }),
  ])

  if (subjectsRes.error || papersRes.error || adminRes.error || teacherRes.error || studentRes.error || withQPRes.error || withMSRes.error || pagesRes.error || questionPagesRes.error || testsRes.error || worksheetsRes.error) {
    const message =
      subjectsRes.error?.message ||
      papersRes.error?.message ||
      adminRes.error?.message ||
      teacherRes.error?.message ||
      studentRes.error?.message ||
      withQPRes.error?.message ||
      withMSRes.error?.message ||
      pagesRes.error?.message ||
      questionPagesRes.error?.message ||
      testsRes.error?.message ||
      worksheetsRes.error?.message ||
      "Failed to load admin stats"
    return NextResponse.json({ error: message }, { status: 500 })
  }

  const admins = adminRes.count ?? 0
  const teachers = teacherRes.count ?? 0
  const students = studentRes.count ?? 0
  const roles = { total: admins + teachers + students, admins, teachers, students }

  // Count all R2 objects with pagination (no 1000-key cap)
  let r2Count = 0
  try {
    const r2 = getR2Client()
    let token: string | undefined
    do {
      const res = await r2.send(new ListObjectsV2Command({ Bucket: R2_BUCKET, MaxKeys: 1000, ContinuationToken: token }))
      r2Count += res.KeyCount || 0
      token = res.NextContinuationToken
    } while (token)
  } catch { /* R2 may not be reachable */ }

  return NextResponse.json({
    subjects: subjectsRes.count ?? 0,
    papers: papersRes.count ?? 0,
    papersWithQP: withQPRes.count ?? 0,
    papersWithMS: withMSRes.count ?? 0,
    pages: pagesRes.count ?? 0,
    questionPages: questionPagesRes.count ?? 0,
    tests: testsRes.count ?? 0,
    worksheets: worksheetsRes.count ?? 0,
    r2Objects: r2Count,
    users: roles,
  })
}
