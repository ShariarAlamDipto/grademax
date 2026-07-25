import { NextRequest, NextResponse } from "next/server"
import { requireTeacher } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { getR2Client, R2_BUCKET } from "@/lib/r2Client"
import { PutObjectCommand } from "@aws-sdk/client-s3"
import {
  PROXY_UPLOAD_LIMIT_BYTES,
  buildLectureKey,
  publicUrlForKey,
  validateLectureFields,
} from "@/lib/lectureStorage"

export const dynamic = "force-dynamic"

/**
 * POST /api/lectures/upload — stream a small lecture file through this function
 * and on to Cloudflare R2.
 *
 * Only used for files under PROXY_UPLOAD_LIMIT_BYTES. Anything larger is
 * rejected here and must go through /api/lectures/upload-url instead, because
 * Vercel caps serverless request bodies at ~4.5 MB.
 */
export async function POST(req: NextRequest) {
  const auth = await requireTeacher()
  if ("error" in auth) return auth.error
  const { user } = auth

  // Service role client is still needed to insert into the `lectures` table
  // because the RLS policy on `lectures` has a circular reference to
  // `profiles` that fails through the anon client (Postgres error 42P17).
  const admin = getSupabaseAdmin()
  if (!admin) {
    console.error(
      "[lectures/upload] Service role client unavailable.",
      "SUPABASE_SERVICE_ROLE_KEY set:", !!process.env.SUPABASE_SERVICE_ROLE_KEY,
    )
    return NextResponse.json(
      { error: "Server configuration error: service role key not set." },
      { status: 500 }
    )
  }

  let formData: FormData
  try {
    formData = await req.formData()
  } catch (error: unknown) {
    console.error("[lectures/upload] could not read request body", error)
    return NextResponse.json(
      { error: "Could not read the uploaded file. It may be too large." },
      { status: 400 }
    )
  }

  const file = formData.get("file")
  if (!(file instanceof File)) {
    return NextResponse.json({ error: "No file was received." }, { status: 400 })
  }

  const validated = validateLectureFields({
    subjectId: formData.get("subject_id"),
    weekNumber: formData.get("week_number"),
    lessonName: formData.get("lesson_name"),
    fileName: file.name,
  })
  if (!validated.ok) {
    return NextResponse.json({ error: validated.error }, { status: 400 })
  }

  // Guard the platform limit ourselves so the client gets JSON it can parse
  // instead of Vercel's HTML "payload too large" page.
  if (file.size > PROXY_UPLOAD_LIMIT_BYTES) {
    return NextResponse.json(
      { error: "File is too large for this endpoint — use the direct upload." },
      { status: 413 }
    )
  }

  const key = buildLectureKey(validated.fields)

  try {
    const bytes = await file.arrayBuffer()
    await getR2Client().send(new PutObjectCommand({
      Bucket: R2_BUCKET,
      Key: key,
      Body: Buffer.from(bytes),
      ContentType: file.type || "application/octet-stream",
    }))
  } catch (error: unknown) {
    console.error("[lectures/upload] R2 upload failed", error)
    return NextResponse.json({ error: "R2 upload failed." }, { status: 500 })
  }

  const { data: lecture, error: insertError } = await admin
    .from("lectures")
    .insert({
      teacher_id: user.id,
      subject_id: validated.fields.subjectId,
      week_number: validated.fields.weekNumber,
      lesson_name: validated.fields.lessonName,
      file_name: validated.fields.fileName,
      file_url: publicUrlForKey(key),
      file_size: file.size,
      file_type: file.type,
    })
    .select()
    .single()

  if (insertError) {
    return NextResponse.json(
      { error: insertError.message, code: insertError.code },
      { status: 500 }
    )
  }

  return NextResponse.json({ lecture }, { status: 201 })
}
