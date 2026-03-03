import { NextRequest, NextResponse } from "next/server"
import { requireTeacher } from "@/lib/apiAuth"
import { getSupabaseAdmin, isSuperAdmin } from "@/lib/supabaseAdmin"

// DELETE /api/lectures/[id] - Delete a lecture
export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const auth = await requireTeacher()
  if ("error" in auth) return auth.error
  const { user, role } = auth

  // Use admin client to bypass RLS circular reference on profiles
  const admin = getSupabaseAdmin()
  const db = admin || auth.db

  // Get the lecture to find the storage path
  const { data: lecture } = await db
    .from("lectures")
    .select("file_url, teacher_id")
    .eq("id", id)
    .single()

  if (!lecture) {
    return NextResponse.json({ error: "Lecture not found" }, { status: 404 })
  }

  // Only the teacher who uploaded or an admin can delete
  const effectiveRole = isSuperAdmin(user.email) ? "admin" : role
  if (lecture.teacher_id !== user.id && effectiveRole !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 })
  }

  // Delete from storage if it's a Supabase storage URL
  if (lecture.file_url.includes("/storage/")) {
    const path = lecture.file_url.split("/lectures/").pop()
    if (path) {
      await db.storage.from("lectures").remove([decodeURIComponent(path)])
    }
  }

  // Delete the record
  const { error } = await db.from("lectures").delete().eq("id", id)
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ success: true })
}
