import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { getR2Client, R2_BUCKET, R2_PUBLIC_URL } from "@/lib/r2Client"
import { buildR2Key, normalizeSessionForDB, normalizeSessionForR2, parseR2Filename } from "@/lib/r2FilenameParser"
import { PutObjectCommand } from "@aws-sdk/client-s3"

export const dynamic = "force-dynamic"

export async function POST(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const formData = await req.formData()
  const file = formData.get("file") as File | null
  if (!file) return NextResponse.json({ error: "No file provided" }, { status: 400 })
  if (!file.name.endsWith(".pdf")) return NextResponse.json({ error: "Only PDF files allowed" }, { status: 400 })

  // Accept either manual fields or auto-detect from filename
  let subjectId = formData.get("subject_id") as string
  let yearStr = formData.get("year") as string
  let session = formData.get("session") as string
  let paperNumber = formData.get("paper_number") as string
  let type = (formData.get("type") as string || "").toUpperCase() as "QP" | "MS"
  let subjectFolder = formData.get("subject_folder") as string

  // Auto-detect from filename if not provided
  if (!yearStr || !session || !paperNumber || !type) {
    const parsed = parseR2Filename(file.name)
    if (!parsed) return NextResponse.json({ error: "Cannot parse filename. Please provide fields manually." }, { status: 400 })
    yearStr = yearStr || String(parsed.year)
    session = session || parsed.session
    paperNumber = paperNumber || parsed.paperNumber
    type = type || parsed.type
    subjectFolder = subjectFolder || parsed.subject
  }

  if (!subjectId) return NextResponse.json({ error: "subject_id required" }, { status: 400 })
  if (!["QP", "MS"].includes(type)) return NextResponse.json({ error: "type must be QP or MS" }, { status: 400 })
  const year = parseInt(yearStr)
  if (isNaN(year) || year < 2000 || year > 2030) return NextResponse.json({ error: "Invalid year" }, { status: 400 })

  const db = getSupabaseAdmin() || auth.db

  // Resolve subject folder name from DB if not provided
  if (!subjectFolder) {
    const { data: subject } = await db.from("subjects").select("name").eq("id", subjectId).single()
    subjectFolder = subject?.name?.replace(/\s+/g, "_") || subjectId
  }

  const r2Session = normalizeSessionForR2(session)
  const r2Key = buildR2Key(subjectFolder, year, r2Session, paperNumber, type)
  const publicUrl = `${R2_PUBLIC_URL}/${r2Key}`

  // Upload to R2
  const bytes = await file.arrayBuffer()
  try {
    const r2 = getR2Client()
    await r2.send(new PutObjectCommand({
      Bucket: R2_BUCKET,
      Key: r2Key,
      Body: Buffer.from(bytes),
      ContentType: "application/pdf",
    }))
  } catch (e) {
    return NextResponse.json({ error: `R2 upload failed: ${e}` }, { status: 500 })
  }

  // Upsert papers table
  const dbSeason = normalizeSessionForDB(session)
  const updateField = type === "QP"
    ? { pdf_url: publicUrl, qp_source_path: r2Key }
    : { markscheme_pdf_url: publicUrl, ms_source_path: r2Key }

  // Check if row exists
  const { data: existing } = await db
    .from("papers")
    .select("id")
    .eq("subject_id", subjectId)
    .eq("year", year)
    .eq("season", dbSeason)
    .eq("paper_number", paperNumber)
    .maybeSingle()

  let paperId: string
  if (existing) {
    await db.from("papers").update(updateField).eq("id", existing.id)
    paperId = existing.id
  } else {
    const { data: inserted } = await db
      .from("papers")
      .insert({ subject_id: subjectId, year, season: dbSeason, paper_number: paperNumber, ...updateField })
      .select("id")
      .single()
    paperId = inserted?.id
  }

  return NextResponse.json({ success: true, paperId, r2Key, url: publicUrl })
}
