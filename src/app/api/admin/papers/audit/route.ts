import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { getR2Client, R2_BUCKET } from "@/lib/r2Client"
import { parseR2Key, normalizeSessionForDB } from "@/lib/r2FilenameParser"
import { ListObjectsV2Command } from "@aws-sdk/client-s3"

export const dynamic = "force-dynamic"

export async function GET(req: NextRequest) {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const subjectId = req.nextUrl.searchParams.get("subject_id")
  if (!subjectId) return NextResponse.json({ error: "subject_id required" }, { status: 400 })
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(subjectId)) {
    return NextResponse.json({ error: "Invalid subject_id" }, { status: 400 })
  }

  const db = getSupabaseAdmin() || auth.db

  // Get subject name (for R2 folder prefix)
  const { data: subject } = await db.from("subjects").select("name, code").eq("id", subjectId).single()
  if (!subject) return NextResponse.json({ error: "Subject not found" }, { status: 404 })

  // Query DB papers for this subject
  const { data: dbPapers } = await db
    .from("papers")
    .select("id, year, season, paper_number, pdf_url, markscheme_pdf_url")
    .eq("subject_id", subjectId)
    .order("year", { ascending: false })

  // Build DB lookup: key = "{year}_{season}_{paperNumber}"
  const dbMap = new Map<string, { id: string; hasQP: boolean; hasMS: boolean }>()
  for (const p of dbPapers || []) {
    const key = `${p.year}_${normalizeSessionForDB(p.season)}_${(p.paper_number || "").toUpperCase()}`
    const existing = dbMap.get(key)
    const hasQP = !!(p.pdf_url?.startsWith("http"))
    const hasMS = !!(p.markscheme_pdf_url?.startsWith("http"))
    if (!existing || (hasQP && !existing.hasQP) || (hasMS && !existing.hasMS)) {
      dbMap.set(key, { id: p.id, hasQP: existing ? existing.hasQP || hasQP : hasQP, hasMS: existing ? existing.hasMS || hasMS : hasMS })
    }
  }

  // List R2 objects for this subject
  const r2Map = new Map<string, { qpKey?: string; msKey?: string }>()
  try {
    const r2 = getR2Client()
    // Try the subject name as folder (e.g. "ICT/")
    const subjectFolder = subject.name.replace(/\s+/g, "_")
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
        const key = `${parsed.year}_${normalizeSessionForDB(parsed.session)}_${parsed.paperNumber.toUpperCase()}`
        const existing = r2Map.get(key) || {}
        if (parsed.type === "QP") existing.qpKey = obj.Key
        else existing.msKey = obj.Key
        r2Map.set(key, existing)
      }
      token = res.NextContinuationToken
    } while (token)
  } catch (e) {
    console.warn("[papers/audit] R2 listing failed:", e)
  }

  // Merge all unique keys from both DB and R2
  const allKeys = new Set([...dbMap.keys(), ...r2Map.keys()])
  const rows = Array.from(allKeys).map(key => {
    const [year, season, paperNumber] = key.split("_", 3)
    const dbEntry = dbMap.get(key)
    const r2Entry = r2Map.get(key)
    return {
      paperId: dbEntry?.id ?? null,
      year: parseInt(year),
      season,
      paperNumber,
      dbHasQP: dbEntry?.hasQP ?? false,
      dbHasMS: dbEntry?.hasMS ?? false,
      r2HasQP: !!(r2Entry?.qpKey),
      r2HasMS: !!(r2Entry?.msKey),
      r2QpKey: r2Entry?.qpKey ?? null,
      r2MsKey: r2Entry?.msKey ?? null,
    }
  })

  rows.sort((a, b) => b.year - a.year || a.season.localeCompare(b.season) || a.paperNumber.localeCompare(b.paperNumber))

  return NextResponse.json({ subject: subject.name, rows })
}
