import { NextRequest, NextResponse } from "next/server"
import { getSupabaseServer } from "@/lib/supabaseServer"

// DELETE /api/lectures/[id] - Delete a lecture
export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const supabase = getSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  // Check role
  const { data: profile } = await supabase
    .from("profiles")
    .select("role")
    .eq("id", user.id)
    .single()

  if (!profile || !["teacher", "admin"].includes(profile.role)) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 })
  }

  // Get the lecture to find the storage path
  const { data: lecture } = await supabase
    .from("lectures")
    .select("file_url, teacher_id")
    .eq("id", id)
    .single()

  if (!lecture) {
    return NextResponse.json({ error: "Lecture not found" }, { status: 404 })
  }

  // Only the teacher who uploaded or an admin can delete
  if (lecture.teacher_id !== user.id && profile.role !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 })
  }

  // Delete from storage if it's a Supabase storage URL
  if (lecture.file_url.includes("/storage/")) {
    const path = lecture.file_url.split("/lectures/").pop()
    if (path) {
      await supabase.storage.from("lectures").remove([decodeURIComponent(path)])
    }
  }

  // Delete the record
  const { error } = await supabase.from("lectures").delete().eq("id", id)
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ success: true })
}
