import { NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getR2Client, R2_BUCKET } from "@/lib/r2Client"
import { ListObjectsV2Command } from "@aws-sdk/client-s3"

export const dynamic = "force-dynamic"
// A full sequential bucket listing takes ~40s (37k objects, 1000 keys per
// call). Fanning out across second-level prefixes cuts that to a few seconds,
// but keep headroom for bucket growth.
export const maxDuration = 60

const CACHE_TTL_MS = 60 * 60 * 1000
let cache: { count: number; at: number } | null = null

async function countPrefix(prefix: string): Promise<number> {
  const r2 = getR2Client()
  let count = 0
  let token: string | undefined
  do {
    const res = await r2.send(
      new ListObjectsV2Command({ Bucket: R2_BUCKET, Prefix: prefix, MaxKeys: 1000, ContinuationToken: token })
    )
    count += res.KeyCount || 0
    token = res.NextContinuationToken
  } while (token)
  return count
}

async function listSubPrefixes(prefix: string): Promise<{ prefixes: string[]; looseFiles: number }> {
  const r2 = getR2Client()
  const res = await r2.send(
    new ListObjectsV2Command({ Bucket: R2_BUCKET, Prefix: prefix, Delimiter: "/", MaxKeys: 1000 })
  )
  const prefixes = (res.CommonPrefixes ?? []).map(p => p.Prefix!).filter(Boolean)
  const looseFiles = (res.Contents ?? []).length
  return { prefixes, looseFiles }
}

async function countBucket(): Promise<number> {
  // Fan out two prefix levels deep (subject folders), then count each
  // second-level prefix in parallel. Continuation tokens force sequential
  // paging within a prefix, so parallelism across prefixes is the only lever.
  const top = await listSubPrefixes("")
  let total = top.looseFiles
  const secondLevel: string[] = []
  for (const p of top.prefixes) {
    const sub = await listSubPrefixes(p)
    total += sub.looseFiles
    secondLevel.push(...sub.prefixes)
  }
  const counts = await Promise.all(secondLevel.map(countPrefix))
  return total + counts.reduce((s, n) => s + n, 0)
}

export async function GET() {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  if (cache && Date.now() - cache.at < CACHE_TTL_MS) {
    return NextResponse.json({ r2Objects: cache.count, cached: true })
  }

  try {
    const count = await countBucket()
    cache = { count, at: Date.now() }
    return NextResponse.json({ r2Objects: count, cached: false })
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "R2 listing failed"
    return NextResponse.json({ error: message }, { status: 502 })
  }
}
