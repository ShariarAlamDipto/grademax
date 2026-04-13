import { NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { getR2Client, R2_BUCKET } from "@/lib/r2Client"
import { parseR2Key, normalizeSessionForDB } from "@/lib/r2FilenameParser"
import { ListObjectsV2Command } from "@aws-sdk/client-s3"

export const dynamic = "force-dynamic"

interface AuditRow {
  subject: string
  level: string
  year: number
  season: string
  paperNumber: string
  dbHasQP: boolean
  dbHasMS: boolean
  r2HasQP: boolean
  r2HasMS: boolean
}

/**
 * GET /api/admin/papers/full-audit
 * Runs DB + R2 audit for ALL subjects and returns rows where at least one field is missing.
 * Used to power the "Export Full Audit Report" CSV download in the admin panel.
 */
export async function GET() {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin() || auth.db

  // Load all subjects
  const { data: subjects, error: subjErr } = await db
    .from("subjects")
    .select("id, name, code, level")
    .order("level")
    .order("name")

  if (subjErr) return NextResponse.json({ error: subjErr.message }, { status: 500 })

  // Load all papers from DB in one query
  const { data: allPapers, error: papersErr } = await db
    .from("papers")
    .select("id, subject_id, year, season, paper_number, pdf_url, markscheme_pdf_url")

  if (papersErr) return NextResponse.json({ error: papersErr.message }, { status: 500 })

  // Build DB lookup: subjectId → Map<compositeKey, { hasQP, hasMS }>
  const dbBySubject = new Map<string, Map<string, { hasQP: boolean; hasMS: boolean }>>()
  for (const paper of allPapers || []) {
    let subjectMap = dbBySubject.get(paper.subject_id)
    if (!subjectMap) { subjectMap = new Map(); dbBySubject.set(paper.subject_id, subjectMap) }

    const key = `${paper.year}_${normalizeSessionForDB(paper.season)}_${(paper.paper_number || "").toUpperCase()}`
    const existing = subjectMap.get(key) || { hasQP: false, hasMS: false }
    existing.hasQP = existing.hasQP || !!(paper.pdf_url?.startsWith("http"))
    existing.hasMS = existing.hasMS || !!(paper.markscheme_pdf_url?.startsWith("http"))
    subjectMap.set(key, existing)
  }

  // List all R2 objects in a single pass
  const r2BySubjectFolder = new Map<string, Map<string, { qpKey?: string; msKey?: string }>>()
  try {
    const r2 = getR2Client()
    let token: string | undefined
    do {
      const res = await r2.send(new ListObjectsV2Command({
        Bucket: R2_BUCKET,
        MaxKeys: 1000,
        ContinuationToken: token,
      }))
      for (const obj of res.Contents || []) {
        if (!obj.Key) continue
        const parsed = parseR2Key(obj.Key)
        if (!parsed) continue

        // The folder is the first segment of the key (e.g. "ICT" or "Physics")
        const folder = obj.Key.split("/")[0]
        let folderMap = r2BySubjectFolder.get(folder)
        if (!folderMap) { folderMap = new Map(); r2BySubjectFolder.set(folder, folderMap) }

        const key = `${parsed.year}_${normalizeSessionForDB(parsed.session)}_${parsed.paperNumber.toUpperCase()}`
        const existing = folderMap.get(key) || {}
        if (parsed.type === "QP") existing.qpKey = obj.Key
        else existing.msKey = obj.Key
        folderMap.set(key, existing)
      }
      token = res.NextContinuationToken
    } while (token)
  } catch (e) {
    console.warn("[full-audit] R2 listing failed:", e)
    // Continue without R2 data — DB audit is still valuable
  }

  const rows: AuditRow[] = []

  for (const subject of subjects || []) {
    const subjectFolder = subject.name.replace(/\s+/g, "_")
    const dbMap = dbBySubject.get(subject.id) || new Map<string, { hasQP: boolean; hasMS: boolean }>()
    const r2Map = r2BySubjectFolder.get(subjectFolder) || new Map<string, { qpKey?: string; msKey?: string }>()

    // Union of all keys from DB and R2
    const allKeys = new Set([...dbMap.keys(), ...r2Map.keys()])

    for (const key of allKeys) {
      const [yearStr, season, paperNumber] = key.split("_", 3)
      const db = dbMap.get(key)
      const r2 = r2Map.get(key)

      rows.push({
        subject: subject.name,
        level: subject.level,
        year: parseInt(yearStr),
        season,
        paperNumber,
        dbHasQP: db?.hasQP ?? false,
        dbHasMS: db?.hasMS ?? false,
        r2HasQP: !!(r2?.qpKey),
        r2HasMS: !!(r2?.msKey),
      })
    }
  }

  // Sort: subject, year desc, season, paper
  rows.sort((a, b) =>
    a.subject.localeCompare(b.subject) ||
    b.year - a.year ||
    a.season.localeCompare(b.season) ||
    a.paperNumber.localeCompare(b.paperNumber)
  )

  const totalMissing = rows.filter(r => !r.dbHasQP || !r.dbHasMS).length

  return NextResponse.json({ rows, total: rows.length, totalMissing })
}
