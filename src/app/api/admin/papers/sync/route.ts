import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { getR2Client, R2_BUCKET, R2_PUBLIC_URL } from "@/lib/r2Client"
import { parseR2Key, normalizeSessionForDB } from "@/lib/r2FilenameParser"
import { ListObjectsV2Command } from "@aws-sdk/client-s3"

export const dynamic = "force-dynamic"

// POST /api/admin/papers/sync
// Scans all R2 objects for a subject and upserts any missing DB rows
export async function POST(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const body = await req.json().catch(() => ({}))
  const subjectId = body.subject_id as string | undefined
  if (!subjectId) return NextResponse.json({ error: "subject_id required" }, { status: 400 })

  const db = getSupabaseAdmin()
  if (!db) return NextResponse.json({ error: "Server misconfiguration: admin client unavailable" }, { status: 500 })

  const { data: subject, error: subjectError } = await db.from("subjects").select("name").eq("id", subjectId).maybeSingle()
  if (subjectError) {
    console.error("[admin/papers/sync] Failed to load subject", subjectError)
    return NextResponse.json({ error: "Failed to load subject" }, { status: 500 })
  }
  if (!subject) return NextResponse.json({ error: "Subject not found" }, { status: 404 })

  const subjectFolder = subject.name.replace(/\s+/g, "_")

  // Collect all R2 objects
  const r2Objects: Array<{ key: string; type: "QP" | "MS"; year: number; season: string; paperNumber: string }> = []
  try {
    const r2 = getR2Client()
    let token: string | undefined
    do {
      const res = await r2.send(new ListObjectsV2Command({
        Bucket: R2_BUCKET,
        Prefix: `${subjectFolder}/`,
        MaxKeys: 1000,
        ContinuationToken: token,
      }))
      for (const obj of res.Contents || []) {
        if (!obj.Key) continue
        const parsed = parseR2Key(obj.Key)
        if (!parsed) continue
        r2Objects.push({ key: obj.Key, type: parsed.type, year: parsed.year, season: parsed.session, paperNumber: parsed.paperNumber })
      }
      token = res.NextContinuationToken
    } while (token)
  } catch (error) {
    console.error("[admin/papers/sync] R2 listing failed", error)
    return NextResponse.json({ error: "R2 listing failed" }, { status: 500 })
  }

  let inserted = 0
  let updated = 0
  const failedKeys: string[] = []

  for (const obj of r2Objects) {
    const dbSeason = normalizeSessionForDB(obj.season)
    const normalizedPaperNumber = obj.paperNumber.trim().toUpperCase()
    const publicUrl = `${R2_PUBLIC_URL}/${obj.key}`
    const updateField = obj.type === "QP"
      ? { pdf_url: publicUrl }
      : { markscheme_pdf_url: publicUrl }

    const { data: existing, error: existingError } = await db
      .from("papers")
      .select("id, pdf_url, markscheme_pdf_url")
      .eq("subject_id", subjectId)
      .eq("year", obj.year)
      .eq("season", dbSeason)
      .eq("paper_number", normalizedPaperNumber)
      .maybeSingle()

    if (existingError) {
      failedKeys.push(obj.key)
      continue
    }

    if (existing) {
      // Only update if the URL field is missing
      const needsUpdate = obj.type === "QP" ? !existing.pdf_url : !existing.markscheme_pdf_url
      if (needsUpdate) {
        const { error: updateError } = await db.from("papers").update(updateField).eq("id", existing.id)
        if (updateError) {
          failedKeys.push(obj.key)
          continue
        }
        updated++
      }
    } else {
      const { error: insertError } = await db.from("papers").insert({
        subject_id: subjectId,
        year: obj.year,
        season: dbSeason,
        paper_number: normalizedPaperNumber,
        ...updateField,
      })
      if (insertError) {
        failedKeys.push(obj.key)
        continue
      }
      inserted++
    }
  }

  if (failedKeys.length > 0) {
    return NextResponse.json({
      success: false,
      warning: "Sync completed with write failures",
      r2ObjectsScanned: r2Objects.length,
      inserted,
      updated,
      failedCount: failedKeys.length,
      failedKeys: failedKeys.slice(0, 25),
    }, { status: 200 })
  }

  return NextResponse.json({ success: true, r2ObjectsScanned: r2Objects.length, inserted, updated })
}
