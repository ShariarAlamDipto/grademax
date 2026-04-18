import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { getR2Client, R2_BUCKET } from "@/lib/r2Client"
import { ListObjectsV2Command } from "@aws-sdk/client-s3"
import { parseR2Key, normalizeSessionForDB } from "@/lib/r2FilenameParser"

export interface R2PaperGroup {
  groupKey: string
  year: number
  session: string
  paperNumber: string
  r2QP: string | null
  r2MS: string | null
  inDb: boolean
  dbId: string | null
  hasPdfUrl: boolean
  hasMsUrl: boolean
}

export interface R2ScanResult {
  subjectCode: string
  subjectFolder: string
  r2Count: number
  dbCount: number
  comparison: R2PaperGroup[]
  dbOnly: Array<{ year: number; season: string; paperNumber: string }>
  stats: { inBoth: number; r2Only: number; dbOnly: number }
}

function buildSubjectFolder(name: string): string {
  return name.replace(/\s+/g, "_").replace(/[^a-zA-Z0-9_\-]/g, "_")
}

export async function GET(req: NextRequest) {
  const authResult = await requireAdmin()
  if ("error" in authResult) return authResult.error

  const { searchParams } = new URL(req.url)
  const subjectId = searchParams.get("subjectId")
  if (!subjectId) {
    return NextResponse.json({ error: "subjectId required" }, { status: 400 })
  }

  const db = getSupabaseAdmin()
  if (!db) return NextResponse.json({ error: "Admin client not available" }, { status: 500 })

  const { data: subject } = await db
    .from("subjects")
    .select("code, name")
    .eq("id", subjectId)
    .single()
  if (!subject) return NextResponse.json({ error: "Subject not found" }, { status: 404 })

  const subjectFolder = buildSubjectFolder(subject.name)
  const prefix = `${subjectFolder}/`

  // List all R2 objects under the subject prefix
  const r2 = getR2Client()
  const allKeys: string[] = []
  let continuationToken: string | undefined
  do {
    const result = await r2.send(new ListObjectsV2Command({
      Bucket: R2_BUCKET,
      Prefix: prefix,
      ContinuationToken: continuationToken,
    }))
    for (const obj of result.Contents || []) {
      if (obj.Key && obj.Key.endsWith(".pdf")) allKeys.push(obj.Key)
    }
    continuationToken = result.NextContinuationToken
  } while (continuationToken)

  // Group R2 keys by year+session+paperNumber
  const r2Map = new Map<string, { qp: string | null; ms: string | null }>()
  for (const key of allKeys) {
    const parsed = parseR2Key(key)
    if (!parsed) continue
    const session = normalizeSessionForDB(parsed.session)
    const gk = `${parsed.year}_${session}_${parsed.paperNumber}`
    if (!r2Map.has(gk)) r2Map.set(gk, { qp: null, ms: null })
    const group = r2Map.get(gk)!
    if (parsed.type === "QP") group.qp = key
    else if (parsed.type === "MS") group.ms = key
  }

  // Get DB papers for this subject
  const { data: dbPapers } = await db
    .from("papers")
    .select("id, year, season, paper_number, pdf_url, markscheme_pdf_url")
    .eq("subject_id", subjectId)

  type DBPaper = {
    id: string; year: number; season: string; paper_number: string
    pdf_url: string | null; markscheme_pdf_url: string | null
  }
  const dbMap = new Map<string, DBPaper>()
  for (const p of (dbPapers || []) as DBPaper[]) {
    dbMap.set(`${p.year}_${p.season}_${p.paper_number}`, p)
  }

  // Build comparison array
  const comparison: R2PaperGroup[] = Array.from(r2Map.entries()).map(([gk, r2]) => {
    const parts = gk.split("_")
    const year = parseInt(parts[0])
    const paperNumber = parts[parts.length - 1]
    const session = parts.slice(1, parts.length - 1).join("_")
    const dbEntry = dbMap.get(gk)
    return {
      groupKey: gk,
      year,
      session,
      paperNumber,
      r2QP: r2.qp,
      r2MS: r2.ms,
      inDb: !!dbEntry,
      dbId: dbEntry?.id || null,
      hasPdfUrl: !!dbEntry?.pdf_url,
      hasMsUrl: !!dbEntry?.markscheme_pdf_url,
    }
  }).sort((a, b) => b.year - a.year || a.session.localeCompare(b.session) || a.paperNumber.localeCompare(b.paperNumber))

  const dbOnly = (dbPapers || [])
    .filter((p: DBPaper) => !r2Map.has(`${p.year}_${p.season}_${p.paper_number}`))
    .map((p: DBPaper) => ({ year: p.year, season: p.season, paperNumber: p.paper_number }))

  const result: R2ScanResult = {
    subjectCode: subject.code,
    subjectFolder,
    r2Count: r2Map.size,
    dbCount: dbPapers?.length || 0,
    comparison,
    dbOnly,
    stats: {
      inBoth: comparison.filter(c => c.inDb).length,
      r2Only: comparison.filter(c => !c.inDb).length,
      dbOnly: dbOnly.length,
    },
  }

  return NextResponse.json(result)
}
