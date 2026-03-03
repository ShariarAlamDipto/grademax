import { NextRequest, NextResponse } from "next/server"
import { getSupabaseServer } from "@/lib/supabaseServer"

// POST /api/lectures/upload - Upload file to Supabase Storage
export async function POST(req: NextRequest) {
  const supabase = getSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  // Check teacher/admin role
  const { data: profile } = await supabase
    .from("profiles")
    .select("role")
    .eq("id", user.id)
    .single()

  if (!profile || !["teacher", "admin"].includes(profile.role)) {
    return NextResponse.json({ error: "Only teachers can upload" }, { status: 403 })
  }

  const formData = await req.formData()
  const file = formData.get("file") as File | null
  const subjectId = formData.get("subject_id") as string
  const weekNumber = formData.get("week_number") as string
  const lessonName = formData.get("lesson_name") as string

  if (!file || !subjectId || !weekNumber || !lessonName) {
    return NextResponse.json({ error: "Missing required fields" }, { status: 400 })
  }

  // Create structured path: subject_id/week_N/lesson_name/filename
  const sanitizedLesson = lessonName.replace(/[^a-zA-Z0-9-_ ]/g, "").trim()
  const storagePath = `${subjectId}/week_${weekNumber}/${sanitizedLesson}/${file.name}`

  // Upload to Supabase Storage
  const buffer = Buffer.from(await file.arrayBuffer())
  const { error: uploadError } = await supabase.storage
    .from("lectures")
    .upload(storagePath, buffer, {
      contentType: file.type,
      upsert: true,
    })

  if (uploadError) {
    return NextResponse.json({ error: uploadError.message }, { status: 500 })
  }

  // Get public URL
  const { data: urlData } = supabase.storage
    .from("lectures")
    .getPublicUrl(storagePath)

  // Insert lecture record
  const { data: lecture, error: insertError } = await supabase
    .from("lectures")
    .insert({
      teacher_id: user.id,
      subject_id: subjectId,
      week_number: parseInt(weekNumber),
      lesson_name: sanitizedLesson,
      file_name: file.name,
      file_url: urlData.publicUrl,
      file_size: file.size,
      file_type: file.type,
    })
    .select()
    .single()

  if (insertError) {
    return NextResponse.json({ error: insertError.message }, { status: 500 })
  }

  return NextResponse.json({ lecture }, { status: 201 })
}
