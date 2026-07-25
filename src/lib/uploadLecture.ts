import { MAX_LECTURE_BYTES, PROXY_UPLOAD_LIMIT_BYTES } from "./lectureStorage"

export interface LectureUploadTarget {
  subjectId: string
  weekNumber: number
  lessonName: string
}

export interface UploadOutcome {
  ok: boolean
  error?: string
}

/**
 * Pull a human-readable message out of a failed response without assuming the
 * body is JSON. Platform-level failures (Vercel's 413 payload-too-large page, a
 * 504 gateway timeout, an auth redirect) return HTML, and calling res.json() on
 * those throws — which is what used to leave the upload UI stuck on
 * "Uploading..." forever.
 */
async function readErrorMessage(res: Response): Promise<string> {
  let raw = ""
  try {
    raw = await res.text()
  } catch {
    return `Request failed (${res.status}).`
  }

  try {
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed.error === "string") return parsed.error
  } catch {
    // Not JSON — fall through to the status-based messages below.
  }

  if (res.status === 413) return "File is too large to upload."
  if (res.status === 401) return "Your session expired — please sign in again."
  if (res.status === 403) return "You do not have permission to upload lectures."
  if (res.status === 504) return "The server timed out while handling the file."
  return `Request failed (${res.status}).`
}

/** Promise-wrapped XHR: fetch cannot report upload progress. */
function putWithProgress(
  url: string,
  file: File,
  contentType: string,
  onProgress: (percent: number) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open("PUT", url, true)
    xhr.setRequestHeader("Content-Type", contentType)

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve()
      else reject(new Error(`Storage rejected the file (${xhr.status}).`))
    }
    xhr.onerror = () =>
      reject(
        new Error(
          "Could not reach storage. If this persists, R2 bucket CORS may not allow this site."
        )
      )
    xhr.ontimeout = () => reject(new Error("The upload timed out."))
    xhr.onabort = () => reject(new Error("The upload was cancelled."))

    xhr.send(file)
  })
}

/**
 * Small files stream through the serverless route, which records the DB row in
 * the same request.
 */
async function uploadViaProxy(
  file: File,
  target: LectureUploadTarget
): Promise<UploadOutcome> {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("subject_id", target.subjectId)
  formData.append("week_number", String(target.weekNumber))
  formData.append("lesson_name", target.lessonName)

  const res = await fetch("/api/lectures/upload", {
    method: "POST",
    body: formData,
  })
  if (!res.ok) return { ok: false, error: await readErrorMessage(res) }
  return { ok: true }
}

/**
 * Large files bypass the ~4.5 MB serverless body cap: mint a presigned URL, PUT
 * straight to R2, then record the row.
 */
async function uploadDirect(
  file: File,
  target: LectureUploadTarget,
  onProgress: (percent: number) => void
): Promise<UploadOutcome> {
  const meta = {
    subject_id: target.subjectId,
    week_number: target.weekNumber,
    lesson_name: target.lessonName,
    file_name: file.name,
    file_size: file.size,
    file_type: file.type || "application/octet-stream",
  }

  const signRes = await fetch("/api/lectures/upload-url", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(meta),
  })
  if (!signRes.ok) return { ok: false, error: await readErrorMessage(signRes) }

  const { uploadUrl, contentType } = await signRes.json()
  await putWithProgress(uploadUrl, file, contentType, onProgress)

  const recordRes = await fetch("/api/lectures/record", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(meta),
  })
  if (!recordRes.ok) return { ok: false, error: await readErrorMessage(recordRes) }
  return { ok: true }
}

/**
 * Upload one lecture file, picking the transport that suits its size. Never
 * rejects — every failure comes back as `{ ok: false, error }` so a single bad
 * file cannot abort a batch or strand the UI in its uploading state.
 */
export async function uploadLectureFile(
  file: File,
  target: LectureUploadTarget,
  onProgress: (percent: number) => void = () => {}
): Promise<UploadOutcome> {
  if (file.size === 0) {
    return { ok: false, error: "File is empty." }
  }
  if (file.size > MAX_LECTURE_BYTES) {
    return {
      ok: false,
      error: `File is larger than the ${Math.round(
        MAX_LECTURE_BYTES / (1024 * 1024)
      )} MB limit.`,
    }
  }

  try {
    if (file.size <= PROXY_UPLOAD_LIMIT_BYTES) {
      const outcome = await uploadViaProxy(file, target)
      onProgress(100)
      return outcome
    }
    return await uploadDirect(file, target, onProgress)
  } catch (error: unknown) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : "Unexpected upload error.",
    }
  }
}
