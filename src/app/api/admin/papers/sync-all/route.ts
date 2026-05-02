import { NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { getR2Client, R2_BUCKET, R2_PUBLIC_URL } from "@/lib/r2Client"
import { parseR2Key, normalizeSessionForDB, buildSubjectFolder } from "@/lib/r2FilenameParser"
import { ListObjectsV2Command } from "@aws-sdk/client-s3"
import type { SupabaseClient } from "@supabase/supabase-js"

export const dynamic = "force-dynamic"
export const maxDuration = 300

interface SubjectResult {
  subject_id: string
  subject_name: string
  r2_objects_scanned: number
  inserted: number
  updated: number
  failed: number
  error?: string
}

async function syncSubject(
  db: SupabaseClient,
  subjectId: string,
  subjectName: string,
): Promise<SubjectResult> {
  const result: SubjectResult = {
    subject_id: subjectId,
    subject_name: subjectName,
    r2_objects_scanned: 0,
    inserted: 0,
    updated: 0,
    failed: 0,
  }

  const subjectFolder = buildSubjectFolder(subjectName)
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
    result.error = `R2 listing failed: ${error instanceof Error ? error.message : String(error)}`
    return result
  }

  result.r2_objects_scanned = r2Objects.length

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
      result.failed++
      continue
    }

    if (existing) {
      const needsUpdate = obj.type === "QP" ? !existing.pdf_url : !existing.markscheme_pdf_url
      if (needsUpdate) {
        const { error: updateError } = await db.from("papers").update(updateField).eq("id", existing.id)
        if (updateError) {
          result.failed++
          continue
        }
        result.updated++
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
        result.failed++
        continue
      }
      result.inserted++
    }
  }

  return result
}

export async function POST() {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin()
  if (!db) return NextResponse.json({ error: "Server misconfiguration: admin client unavailable" }, { status: 500 })

  const { data: subjects, error: subjectsError } = await db.from("subjects").select("id, name")
  if (subjectsError || !subjects) {
    return NextResponse.json({ error: "Failed to load subjects" }, { status: 500 })
  }

  const results: SubjectResult[] = []
  for (const s of subjects) {
    results.push(await syncSubject(db, s.id, s.name))
  }

  const totals = results.reduce(
    (acc, r) => ({
      r2_objects_scanned: acc.r2_objects_scanned + r.r2_objects_scanned,
      inserted: acc.inserted + r.inserted,
      updated: acc.updated + r.updated,
      failed: acc.failed + r.failed,
    }),
    { r2_objects_scanned: 0, inserted: 0, updated: 0, failed: 0 },
  )

  return NextResponse.json({
    success: true,
    subjects_processed: results.length,
    totals,
    by_subject: results,
  })
}
