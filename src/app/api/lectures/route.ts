import { NextRequest, NextResponse } from "next/server"
import { requireAuth, requireTeacher } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

// GET /api/lectures - List lectures, optionally filtered by subject_id
export async function GET(req: NextRequest) {
  const auth = await requireAuth()
  if ("error" in auth) return auth.error

  // Use admin client to bypass RLS circular reference on profiles
  const admin = getSupabaseAdmin()
  const db = admin || auth.db

  const url = new URL(req.url)
  const subjectId = url.searchParams.get("subject_id")
  const weekNumber = url.searchParams.get("week")

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
  const auth = await requireTeacher()
  if ("error" in auth) return auth.error
  const { user } = auth

  // Use admin client to bypass RLS circular reference
  const admin = getSupabaseAdmin()
  const db = admin || auth.db

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
