// Deliberately dependency-free: the upload UI imports the limits and the key
// helpers from here, so pulling in r2Client (and with it the AWS S3 SDK) would
// drag the whole SDK into the browser bundle.

/**
 * Vercel serverless functions reject request bodies larger than ~4.5 MB at the
 * edge, before the handler ever runs, and the rejection comes back as an HTML
 * error page rather than JSON. Files at or above this threshold must therefore
 * go straight to R2 through a presigned URL instead of being streamed through
 * /api/lectures/upload. Kept a little under the platform cap to leave room for
 * multipart framing and the other form fields.
 */
export const PROXY_UPLOAD_LIMIT_BYTES = 4 * 1024 * 1024

/** Hard ceiling for a single lecture file, enforced on both upload paths. */
export const MAX_LECTURE_BYTES = 500 * 1024 * 1024

/** How long a presigned PUT stays valid. Long enough for a slow connection to
 *  finish a large video, short enough that a leaked URL expires quickly. */
export const PRESIGN_EXPIRY_SECONDS = 60 * 60

export interface LectureUploadFields {
  subjectId: string
  weekNumber: number
  lessonName: string
  fileName: string
}

export type LectureFieldResult =
  | { ok: true; fields: LectureUploadFields }
  | { ok: false; error: string }

export function sanitizeLessonName(value: string): string {
  return value.replace(/[^a-zA-Z0-9-_ ]/g, "").trim()
}

/**
 * Reduce an uploaded filename to a single safe path segment. Browsers can send
 * names containing slashes (directory drag-and-drop), which would otherwise let
 * a caller steer the object key outside its own lecture folder.
 */
export function sanitizeFileName(value: string): string {
  const base = value.split(/[\\/]/).pop() ?? ""
  const cleaned = base
    .replace(/[^a-zA-Z0-9-_. ]/g, "_")
    .replace(/^\.+/, "")
    .trim()
  return cleaned || "file"
}

/**
 * Validate and normalise the four fields that identify a lecture file. Both
 * upload paths run this so a presigned upload cannot describe itself
 * differently from the row that later records it.
 */
export function validateLectureFields(raw: {
  subjectId?: unknown
  weekNumber?: unknown
  lessonName?: unknown
  fileName?: unknown
}): LectureFieldResult {
  const subjectId = typeof raw.subjectId === "string" ? raw.subjectId.trim() : ""
  if (!/^[a-zA-Z0-9-]{1,64}$/.test(subjectId)) {
    return { ok: false, error: "Invalid or missing subject." }
  }

  const weekNumber = Number.parseInt(String(raw.weekNumber ?? ""), 10)
  if (!Number.isInteger(weekNumber) || weekNumber < 1 || weekNumber > 52) {
    return { ok: false, error: "Week number must be between 1 and 52." }
  }

  const lessonName = sanitizeLessonName(
    typeof raw.lessonName === "string" ? raw.lessonName : ""
  )
  if (!lessonName) {
    return { ok: false, error: "Lesson name is required." }
  }

  const fileName = sanitizeFileName(
    typeof raw.fileName === "string" ? raw.fileName : ""
  )

  return { ok: true, fields: { subjectId, weekNumber, lessonName, fileName } }
}

/**
 * Object key layout, unchanged from the original Supabase Storage scheme so
 * URL semantics survived the R2 migration:
 * lectures/{subject_id}/week_N/{lesson}/{filename}
 */
export function buildLectureKey(fields: LectureUploadFields): string {
  return [
    "lectures",
    fields.subjectId,
    `week_${fields.weekNumber}`,
    fields.lessonName,
    fields.fileName,
  ].join("/")
}

/** Percent-encode each key segment — lesson names and filenames contain spaces. */
export function publicUrlForKey(key: string): string {
  const encoded = key.split("/").map(encodeURIComponent).join("/")
  return `${process.env.NEXT_PUBLIC_R2_PUBLIC_URL || ""}/${encoded}`
}
