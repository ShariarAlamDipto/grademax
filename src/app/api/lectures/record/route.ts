import { NextRequest, NextResponse } from "next/server"
import { requireTeacher } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { getR2Client, R2_BUCKET } from "@/lib/r2Client"
import { HeadObjectCommand } from "@aws-sdk/client-s3"
import {
  buildLectureKey,
  publicUrlForKey,
  validateLectureFields,
} from "@/lib/lectureStorage"

export const dynamic = "force-dynamic"

/**
 * POST /api/lectures/record — write the `lectures` row for a file the browser
 * already PUT straight to R2 via /api/lectures/upload-url.
 *
 * The object key is recomputed here from the same validated fields rather than
 * being accepted from the client, so a caller cannot point a lecture row at an
 * arbitrary URL.
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
      "[lectures/record] Service role client unavailable.",
      "SUPABASE_SERVICE_ROLE_KEY set:", !!process.env.SUPABASE_SERVICE_ROLE_KEY,
    )
    return NextResponse.json(
      { error: "Server configuration error: service role key not set." },
      { status: 500 }
    )
  }

  let body: Record<string, unknown>
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 })
  }

  const validated = validateLectureFields({
    subjectId: body.subject_id,
    weekNumber: body.week_number,
    lessonName: body.lesson_name,
    fileName: body.file_name,
  })
  if (!validated.ok) {
    return NextResponse.json({ error: validated.error }, { status: 400 })
  }

  const key = buildLectureKey(validated.fields)

  // Confirm the object really landed before creating a row that points at it —
  // otherwise a failed browser PUT leaves a lecture linking to a 404.
  let contentLength: number | undefined
  let contentType: string | undefined
  try {
    const head = await getR2Client().send(
      new HeadObjectCommand({ Bucket: R2_BUCKET, Key: key })
    )
    contentLength = head.ContentLength
    contentType = head.ContentType
  } catch (error: unknown) {
    console.error("[lectures/record] object missing in R2", key, error)
    return NextResponse.json(
      { error: "Upload did not complete — the file was not found in storage." },
      { status: 409 }
    )
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
      file_size: contentLength ?? null,
      file_type: contentType ?? null,
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
