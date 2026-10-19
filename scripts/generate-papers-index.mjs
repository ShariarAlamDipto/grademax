// Build-time papers-index snapshot.
//
// The past-papers routes are deploy-frozen (`revalidate = false`) — data only
// changes when the ingest pipeline runs and the site is redeployed. Yet every
// cold serverless render of an on-demand page (all ~10k Cambridge deep URLs)
// re-loaded the full papers table from Supabase: ~12 sequential 1000-row
// requests inside the function. This script runs as `prebuild`, snapshots the
// same rows once, and writes src/generated/papers-index.json; the runtime
// loader (src/lib/papersIndex.ts) reads the file and only falls back to
// Supabase when the snapshot is missing.
//
// NEVER fails the build: on any error it logs and exits 0, leaving the
// runtime on its DB fallback — identical to pre-snapshot behaviour.

import { createClient } from "@supabase/supabase-js"
import { mkdir, readFile, writeFile } from "node:fs/promises"
import path from "node:path"

const OUT_DIR = path.join(process.cwd(), "src", "generated")
const OUT_FILE = path.join(OUT_DIR, "papers-index.json")
const PAGE_SIZE = 1000

// `npm run prebuild` is a bare node process — Next.js only loads .env.local
// for its own build — so pick the vars up manually when they aren't exported
// (local builds). On Vercel they're already in process.env.
async function loadLocalEnv() {
  if (process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.SUPABASE_SERVICE_ROLE_KEY) return
  try {
    const raw = await readFile(path.join(process.cwd(), ".env.local"), "utf8")
    for (const line of raw.split(/\r?\n/)) {
      const m = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/)
      if (!m) continue
      const [, key, rawValue] = m
      if (process.env[key] !== undefined) continue
      process.env[key] = rawValue.replace(/^["']|["']$/g, "")
    }
  } catch {
    // No .env.local — fine; the env may simply be absent (dev without secrets).
  }
}

async function main() {
  await loadLocalEnv()

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!url || !key) {
    console.warn("papers-index: Supabase env not set — skipping snapshot (runtime will use DB fallback)")
    return
  }

  const supabase = createClient(url, key, {
    auth: { autoRefreshToken: false, persistSession: false },
  })

  // Same row set the runtime loader queries — keep the filters in sync with
  // src/lib/papersIndex.ts.
  const rows = []
  let lastSeenId = null
  while (true) {
    let q = supabase
      .from("papers")
      .select("id,year,season,paper_number,pdf_url,markscheme_pdf_url,subjects!inner(name)")
      .or("pdf_url.not.is.null,markscheme_pdf_url.not.is.null")
      .order("id", { ascending: true })
      .limit(PAGE_SIZE)
    if (lastSeenId) q = q.gt("id", lastSeenId)

    const { data, error } = await q
    if (error) throw new Error(`papers query failed: ${error.message}`)
    if (!data || data.length === 0) break

    for (const row of data) {
      const subject = Array.isArray(row.subjects) ? row.subjects[0] : row.subjects
      // Compact tuple keeps the snapshot ~40% smaller than keyed objects.
      rows.push([
        row.id,
        row.year,
        row.season,
        row.paper_number,
        row.pdf_url,
        row.markscheme_pdf_url,
        subject?.name ?? "",
      ])
    }

    lastSeenId = data[data.length - 1].id
    if (data.length < PAGE_SIZE) break
  }

  if (rows.length === 0) {
    console.warn("papers-index: query returned 0 rows — not writing snapshot")
    return
  }

  await mkdir(OUT_DIR, { recursive: true })
  const payload = { generatedAt: new Date().toISOString(), rows }
  await writeFile(OUT_FILE, JSON.stringify(payload))
  const kb = Math.round(JSON.stringify(payload).length / 1024)
  console.log(`papers-index: wrote ${rows.length} rows (${kb} KB) -> src/generated/papers-index.json`)
}

main().catch((err) => {
  console.warn(`papers-index: snapshot failed (${err?.message ?? err}) — runtime will use DB fallback`)
})
