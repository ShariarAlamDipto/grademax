import { NextRequest, NextResponse } from "next/server"
import { requireTeacher } from "@/lib/apiAuth"
import { getR2Client, R2_BUCKET } from "@/lib/r2Client"
import { PutObjectCommand } from "@aws-sdk/client-s3"
import { getSignedUrl } from "@aws-sdk/s3-request-presigner"
import {
  MAX_LECTURE_BYTES,
  PRESIGN_EXPIRY_SECONDS,
  buildLectureKey,
  publicUrlForKey,
  validateLectureFields,
} from "@/lib/lectureStorage"

export const dynamic = "force-dynamic"

/**
 * POST /api/lectures/upload-url — mint a short-lived presigned PUT so the
 * browser can send the file straight to R2.
 *
 * This exists because /api/lectures/upload streams the file through a Vercel
 * serverless function, which caps request bodies at ~4.5 MB. Lecture videos and
 * slide decks routinely exceed that, and the platform rejects them at the edge
 * with an HTML error page. Uploading direct-to-R2 removes the cap entirely.
 */
export async function POST(req: NextRequest) {
  const auth = await requireTeacher()
  if ("error" in auth) return auth.error

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

  const fileSize = Number(body.file_size)
  if (!Number.isFinite(fileSize) || fileSize <= 0) {
    return NextResponse.json({ error: "Invalid file size." }, { status: 400 })
  }
  if (fileSize > MAX_LECTURE_BYTES) {
    return NextResponse.json(
      {
        error: `File is too large. The maximum lecture size is ${Math.round(
          MAX_LECTURE_BYTES / (1024 * 1024)
        )} MB.`,
      },
      { status: 413 }
    )
  }

  const contentType =
    typeof body.file_type === "string" && body.file_type
      ? body.file_type
      : "application/octet-stream"

  const key = buildLectureKey(validated.fields)

  try {
    const uploadUrl = await getSignedUrl(
      getR2Client(),
      new PutObjectCommand({
        Bucket: R2_BUCKET,
        Key: key,
        ContentType: contentType,
      }),
      { expiresIn: PRESIGN_EXPIRY_SECONDS }
    )

    return NextResponse.json({
      uploadUrl,
      key,
      publicUrl: publicUrlForKey(key),
      contentType,
    })
  } catch (error: unknown) {
    console.error("[lectures/upload-url] failed to presign", error)
    return NextResponse.json(
      { error: "Could not prepare the upload. Check R2 configuration." },
      { status: 500 }
    )
  }
}
