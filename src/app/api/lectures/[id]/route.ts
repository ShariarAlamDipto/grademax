import { NextRequest, NextResponse } from "next/server"
import { getSupabaseServer } from "@/lib/supabaseServer"
import { getSupabaseAdmin, isSuperAdmin } from "@/lib/supabaseAdmin"

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

  // Check role using service role client
  const admin = getSupabaseAdmin()
  const { data: profile } = await admin
    .from("profiles")
    .select("role")
    .eq("id", user.id)
    .single()

  const isTeacherOrAdmin =
    isSuperAdmin(user.email) ||
    (profile && ["teacher", "admin"].includes(profile.role))

  if (!isTeacherOrAdmin) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 })
  }

  // Get the lecture to find the storage path
  const { data: lecture } = await admin
    .from("lectures")
    .select("file_url, teacher_id")
    .eq("id", id)
    .single()

  if (!lecture) {
    return NextResponse.json({ error: "Lecture not found" }, { status: 404 })
  }

  // Only the teacher who uploaded or an admin can delete
  const effectiveRole = isSuperAdmin(user.email) ? "admin" : (profile?.role || "student")
  if (lecture.teacher_id !== user.id && effectiveRole !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 })
  }

  // Delete from storage if it's a Supabase storage URL
  if (lecture.file_url.includes("/storage/")) {
    const path = lecture.file_url.split("/lectures/").pop()
    if (path) {
      await admin.storage.from("lectures").remove([decodeURIComponent(path)])
    }
  }

  // Delete the record
  const { error } = await admin.from("lectures").delete().eq("id", id)
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ success: true })
}
