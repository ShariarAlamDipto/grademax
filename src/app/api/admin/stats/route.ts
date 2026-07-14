import { NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

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

  return NextResponse.json({
    subjects: subjectsRes.count ?? 0,
    papers: papersRes.count ?? 0,
    papersWithQP: withQPRes.count ?? 0,
    papersWithMS: withMSRes.count ?? 0,
    pages: pagesRes.count ?? 0,
    questionPages: questionPagesRes.count ?? 0,
    tests: testsRes.count ?? 0,
    worksheets: worksheetsRes.count ?? 0,
    // Counting 37k+ R2 objects takes ~40s of sequential list calls — far past
    // the serverless timeout, and it used to take the whole dashboard down
    // with it. The count now lives at /api/admin/stats/r2 (cached, parallel).
    r2Objects: null,
    users: roles,
  })
}
