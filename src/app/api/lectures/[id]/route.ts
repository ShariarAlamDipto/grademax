import { NextRequest, NextResponse } from "next/server"
import { requireTeacher } from "@/lib/apiAuth"
import { getSupabaseAdmin, isSuperAdmin } from "@/lib/supabaseAdmin"
import { getR2Client, R2_BUCKET, R2_PUBLIC_URL } from "@/lib/r2Client"
import { DeleteObjectCommand } from "@aws-sdk/client-s3"

// PATCH /api/lectures/[id] - Update lecture metadata
export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const auth = await requireTeacher()
  if ("error" in auth) return auth.error
  const { user, role } = auth

  const admin = getSupabaseAdmin()
  const db = admin || auth.db

  // Get the lecture to check ownership
  const { data: lecture } = await db
    .from("lectures")
    .select("teacher_id")
    .eq("id", id)
    .single()

  if (!lecture) {
    return NextResponse.json({ error: "Lecture not found" }, { status: 404 })
  }

  // Only the teacher who uploaded or an admin can edit
  const effectiveRole = isSuperAdmin(user.email) ? "admin" : role
  if (lecture.teacher_id !== user.id && effectiveRole !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 })
  }

  const body = await req.json()
  const updates: Record<string, unknown> = {}
  if (body.lesson_name !== undefined) updates.lesson_name = body.lesson_name
  if (body.week_number !== undefined) updates.week_number = parseInt(body.week_number)
  if (body.subject_id !== undefined) updates.subject_id = body.subject_id

  if (Object.keys(updates).length === 0) {
    return NextResponse.json({ error: "No fields to update" }, { status: 400 })
  }

  const { data, error } = await db
    .from("lectures")
    .update(updates)
    .eq("id", id)
    .select()
    .single()

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ lecture: data })
}

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

  // Delete the underlying file. New uploads land in R2 under a `lectures/`
  // prefix; older rows may still point at Supabase Storage, so route by URL host.
  try {
    if (R2_PUBLIC_URL && lecture.file_url.startsWith(R2_PUBLIC_URL)) {
      const r2Key = decodeURIComponent(lecture.file_url.slice(R2_PUBLIC_URL.length + 1))
      const r2 = getR2Client()
      await r2.send(new DeleteObjectCommand({ Bucket: R2_BUCKET, Key: r2Key }))
    } else if (lecture.file_url.includes("/storage/")) {
      const path = lecture.file_url.split("/lectures/").pop()
      if (path) {
        await db.storage.from("lectures").remove([decodeURIComponent(path)])
      }
    }
  } catch (err) {
    // Storage cleanup is best-effort — failing to remove an orphan blob
    // should not block the DB-level delete.
    console.warn("[lectures/delete] failed to remove underlying file", err)
  }

  // Delete the record
  const { error } = await db.from("lectures").delete().eq("id", id)
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ success: true })
}
