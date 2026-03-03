import { NextRequest, NextResponse } from "next/server"
import { getSupabaseServer } from "@/lib/supabaseServer"
import { getSupabaseAdmin, isSuperAdmin } from "@/lib/supabaseAdmin"

// GET /api/lectures - List lectures, optionally filtered by subject_id
export async function GET(req: NextRequest) {
  const supabase = getSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const url = new URL(req.url)
  const subjectId = url.searchParams.get("subject_id")
  const weekNumber = url.searchParams.get("week")

  const admin = getSupabaseAdmin()
  // Use admin client if available, fall back to regular client for reads
  const db = admin || supabase
  let query = db
    .from("lectures")
    .select(`
      id,
      teacher_id,
      subject_id,
      week_number,
      lesson_name,
      file_name,
      file_url,
      file_size,
      file_type,
      created_at,
      subjects (id, name, board, level)
    `)
    .order("week_number", { ascending: true })
    .order("lesson_name", { ascending: true })

  if (subjectId) {
    query = query.eq("subject_id", subjectId)
  }
  if (weekNumber) {
    query = query.eq("week_number", parseInt(weekNumber))
  }

  const { data, error } = await query
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ lectures: data })
}

// POST /api/lectures - Create a lecture record (after file upload to storage)
export async function POST(req: NextRequest) {
  const supabase = getSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  // Check teacher/admin role — use admin client if available, fall back to regular
  const admin = getSupabaseAdmin()
  const db = admin || supabase
  const { data: profile } = await db
    .from("profiles")
    .select("role")
    .eq("id", user.id)
    .single()

  const isTeacherOrAdmin =
    isSuperAdmin(user.email) ||
    (profile && ["teacher", "admin"].includes(profile.role))

  if (!isTeacherOrAdmin) {
    return NextResponse.json({ error: "Only teachers can upload lectures" }, { status: 403 })
  }

  const body = await req.json()
  const { subject_id, week_number, lesson_name, file_name, file_url, file_size, file_type } = body

  if (!subject_id || !week_number || !lesson_name || !file_name || !file_url) {
    return NextResponse.json({ error: "Missing required fields" }, { status: 400 })
  }

  const { data, error } = await db
    .from("lectures")
    .insert({
      teacher_id: user.id,
      subject_id,
      week_number: parseInt(week_number),
      lesson_name,
      file_name,
      file_url,
      file_size: file_size || null,
      file_type: file_type || null,
    })
    .select()
    .single()

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ lecture: data }, { status: 201 })
}
