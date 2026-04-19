import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { getR2Client, R2_BUCKET, R2_PUBLIC_URL } from "@/lib/r2Client"
import { buildR2Key, normalizeSessionForDB, normalizeSessionForR2, parseR2Filename } from "@/lib/r2FilenameParser"
import { DeleteObjectCommand, PutObjectCommand } from "@aws-sdk/client-s3"
import { logAdminAction } from "@/lib/auditLog"

export const dynamic = "force-dynamic"

export async function POST(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const formData = await req.formData()
  const file = formData.get("file") as File | null
  if (!file) return NextResponse.json({ error: "No file provided" }, { status: 400 })
  if (!file.name.toLowerCase().endsWith(".pdf")) return NextResponse.json({ error: "Only PDF files allowed" }, { status: 400 })

  const MAX_PDF_BYTES = 50 * 1024 * 1024 // 50 MB
  if (file.size > MAX_PDF_BYTES) return NextResponse.json({ error: "File too large (50 MB max)" }, { status: 413 })

  // Accept either manual fields or auto-detect from filename
  const subjectId = formData.get("subject_id") as string
  let yearStr = formData.get("year") as string
  let session = formData.get("session") as string
  let paperNumber = formData.get("paper_number") as string
  let type = (formData.get("type") as string || "").toUpperCase() as "QP" | "MS"
  let subjectFolder = formData.get("subject_folder") as string

  // Auto-detect from filename for any fields not explicitly provided
  if (!yearStr || !session || !paperNumber || !type) {
    const parsed = parseR2Filename(file.name)
    if (parsed) {
      yearStr = yearStr || String(parsed.year)
      session = session || parsed.session
      paperNumber = paperNumber || parsed.paperNumber
      type = (type || parsed.type) as "QP" | "MS"
      subjectFolder = subjectFolder || parsed.subject
    }
    // After attempting auto-detect, verify all required fields are present
    if (!yearStr || !session || !paperNumber) {
      return NextResponse.json({
        error: "Please fill in Year, Session, and Paper Number. Or name the file: SubjectName_YYYY_Jan|May-Jun|Oct-Nov_Paper_N_QP|MS.pdf",
      }, { status: 400 })
    }
  }

  if (!subjectId) return NextResponse.json({ error: "subject_id required" }, { status: 400 })
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(subjectId)) {
    return NextResponse.json({ error: "Invalid subject_id" }, { status: 400 })
  }
  if (!["QP", "MS"].includes(type)) return NextResponse.json({ error: "type must be QP or MS" }, { status: 400 })
  const year = parseInt(yearStr)
  if (isNaN(year) || year < 2000 || year > 2030) return NextResponse.json({ error: "Invalid year" }, { status: 400 })
  const normalizedPaperNumber = paperNumber.trim().toUpperCase()
  if (!normalizedPaperNumber) return NextResponse.json({ error: "paper_number required" }, { status: 400 })

  const db = getSupabaseAdmin() || auth.db

  // Resolve subject folder name from DB if not provided
  if (!subjectFolder) {
    const { data: subject, error: subjectError } = await db.from("subjects").select("name").eq("id", subjectId).maybeSingle()
    if (subjectError) {
      console.error("[admin/papers/upload] Failed to resolve subject", subjectError)
      return NextResponse.json({ error: "Failed to resolve subject" }, { status: 500 })
    }
    if (!subject) {
      return NextResponse.json({ error: "Subject not found" }, { status: 404 })
    }
    subjectFolder = subject.name?.replace(/\s+/g, "_") || subjectId
  }

  // Sanitize subject folder and strip characters that can break R2 key segments.
  const safeSubjectFolder = subjectFolder.replace(/[^a-zA-Z0-9_\- ]/g, "_")

  const r2Session = normalizeSessionForR2(session)
  const r2Key = buildR2Key(safeSubjectFolder, year, r2Session, paperNumber, type)
  const publicUrl = `${R2_PUBLIC_URL}/${r2Key}`

  // Upload to R2
  const bytes = await file.arrayBuffer()

  // Validate PDF magic bytes (%PDF-)
  const header = Buffer.from(bytes.slice(0, 5)).toString("ascii")
  if (header !== "%PDF-") return NextResponse.json({ error: "File is not a valid PDF" }, { status: 400 })

  try {
    const r2 = getR2Client()
    await r2.send(new PutObjectCommand({
      Bucket: R2_BUCKET,
      Key: r2Key,
      Body: Buffer.from(bytes),
      ContentType: "application/pdf",
    }))
  } catch (error) {
    console.error("[admin/papers/upload] R2 upload failed", error)
    return NextResponse.json({ error: "R2 upload failed" }, { status: 500 })
  }

  // Upsert papers table
  const dbSeason = normalizeSessionForDB(session)
  const updateField = type === "QP"
    ? { pdf_url: publicUrl }
    : { markscheme_pdf_url: publicUrl }

  // Check if row exists
  const { data: existing, error: existingError } = await db
    .from("papers")
    .select("id")
    .eq("subject_id", subjectId)
    .eq("year", year)
    .eq("season", dbSeason)
    .eq("paper_number", normalizedPaperNumber)
    .maybeSingle()

  if (existingError) {
    try {
      const r2 = getR2Client()
      await r2.send(new DeleteObjectCommand({ Bucket: R2_BUCKET, Key: r2Key }))
    } catch {
      // Keep original DB error as the primary response.
    }
    console.error("[admin/papers/upload] Failed to query existing paper", existingError)
    return NextResponse.json({ error: "Failed to query existing paper" }, { status: 500 })
  }

  let paperId: string | null = null
  if (existing) {
    const { error: updateError } = await db.from("papers").update(updateField).eq("id", existing.id)
    if (updateError) {
      try {
        const r2 = getR2Client()
        await r2.send(new DeleteObjectCommand({ Bucket: R2_BUCKET, Key: r2Key }))
      } catch {
        // Keep original DB error as the primary response.
      }
      console.error("[admin/papers/upload] Failed to update existing paper", updateError)
      return NextResponse.json({ error: "Failed to update existing paper" }, { status: 500 })
    }
    paperId = existing.id
  } else {
    const { data: inserted, error: insertError } = await db
      .from("papers")
      .insert({ subject_id: subjectId, year, season: dbSeason, paper_number: normalizedPaperNumber, ...updateField })
      .select("id")
      .single()
    if (insertError || !inserted?.id) {
      try {
        const r2 = getR2Client()
        await r2.send(new DeleteObjectCommand({ Bucket: R2_BUCKET, Key: r2Key }))
      } catch {
        // Keep original DB error as the primary response.
      }
      console.error("[admin/papers/upload] Failed to insert paper row", insertError)
      return NextResponse.json({ error: "Failed to insert paper row" }, { status: 500 })
    }
    paperId = inserted.id
  }

  if (!paperId) {
    try {
      const r2 = getR2Client()
      await r2.send(new DeleteObjectCommand({ Bucket: R2_BUCKET, Key: r2Key }))
    } catch {
      // Keep original DB error as the primary response.
    }
    return NextResponse.json({ error: "Failed to resolve paper id" }, { status: 500 })
  }

  void logAdminAction({
    admin_email: auth.user?.email,
    action: "upload_paper",
    entity_type: "paper",
    entity_id: paperId,
    details: { r2Key, year, session: dbSeason, paper_number: normalizedPaperNumber, type, subject_id: subjectId },
  })

  return NextResponse.json({ success: true, paperId, r2Key, url: publicUrl })
}
