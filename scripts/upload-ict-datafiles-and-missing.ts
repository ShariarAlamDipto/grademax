/**
 * upload-ict-datafiles-and-missing.ts
 *
 * For each ICT session in the FINAL folder:
 *   - Uploads any zipped Data_File to R2 and records data_file_url on the
 *     paper row that represents Paper 2 for that session (the practical exam).
 *   - Uploads any QP/MS PDFs that are present on disk but missing from R2 / DB.
 *
 * Idempotent: skips files already in R2 (HEAD), only fills empty DB columns.
 *
 * Pre-requisite: apply supabase/migrations/10_data_files_and_fpm_consolidation.sql
 * (adds the data_file_url column). Without it, the script logs a warning and
 * skips the DB update for data files, but still uploads PDFs and the zip to R2.
 *
 * Usage:
 *   npx tsx --env-file=.env.local scripts/upload-ict-datafiles-and-missing.ts
 *   npx tsx --env-file=.env.local scripts/upload-ict-datafiles-and-missing.ts --dry-run
 */

import { S3Client, PutObjectCommand, HeadObjectCommand } from '@aws-sdk/client-s3'
import { createClient } from '@supabase/supabase-js'
import * as fs from 'fs'
import * as path from 'path'
import { config } from 'dotenv'

const envPaths = [
  path.resolve(process.cwd(), '.env.local'),
  path.resolve('C:\\Users\\shari\\grademax', '.env.local'),
]
for (const p of envPaths) {
  if (fs.existsSync(p)) { config({ path: p }); break }
}

const ICT_FINAL_DIR = String.raw`C:\Users\shari\grademax scraper\grademax-scraper\data\FINAL\ICT`
const R2_FOLDER     = 'ICT'

const R2_ACCOUNT_ID    = process.env.R2_ACCOUNT_ID!
const R2_ACCESS_KEY_ID = process.env.R2_ACCESS_KEY_ID!
const R2_SECRET_KEY    = process.env.R2_SECRET_ACCESS_KEY!
const R2_BUCKET        = process.env.R2_BUCKET_NAME || 'grademax-papers'
const R2_PUBLIC_URL    = process.env.NEXT_PUBLIC_R2_PUBLIC_URL!
const SUPABASE_URL     = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SUPABASE_KEY     = process.env.SUPABASE_SERVICE_ROLE_KEY!

const DRY_RUN = process.argv.includes('--dry-run')

interface ParsedPaper { paperNumber: string; type: 'qp' | 'ms' }

function parsePaperFilename(filename: string): ParsedPaper | null {
  const base = filename.replace(/\.pdf$/i, '')
  const m = base.match(/_Paper_(\d+)([A-Z]*)_(QP|MS)$/i)
  if (!m) return null
  return { paperNumber: m[1] + (m[2] || '').toUpperCase(), type: m[3].toUpperCase() === 'QP' ? 'qp' : 'ms' }
}

function makeR2(): S3Client {
  return new S3Client({
    region: 'auto',
    endpoint: `https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
    credentials: { accessKeyId: R2_ACCESS_KEY_ID, secretAccessKey: R2_SECRET_KEY },
  })
}

async function fileExistsInR2(r2: S3Client, key: string): Promise<boolean> {
  try { await r2.send(new HeadObjectCommand({ Bucket: R2_BUCKET, Key: key })); return true }
  catch { return false }
}

async function uploadToR2(r2: S3Client, localPath: string, r2Key: string, contentType: string): Promise<string> {
  if (await fileExistsInR2(r2, r2Key)) return `${R2_PUBLIC_URL}/${r2Key}`
  if (DRY_RUN) return `${R2_PUBLIC_URL}/${r2Key}`
  await r2.send(new PutObjectCommand({
    Bucket: R2_BUCKET,
    Key: r2Key,
    Body: fs.readFileSync(localPath),
    ContentType: contentType,
    CacheControl: 'public, max-age=31536000, immutable',
  }))
  return `${R2_PUBLIC_URL}/${r2Key}`
}

async function main() {
  const missing = ['R2_ACCOUNT_ID','R2_ACCESS_KEY_ID','R2_SECRET_ACCESS_KEY',
    'NEXT_PUBLIC_R2_PUBLIC_URL','NEXT_PUBLIC_SUPABASE_URL','SUPABASE_SERVICE_ROLE_KEY']
    .filter(k => !process.env[k])
  if (missing.length) { console.error('Missing env:', missing.join(', ')); process.exit(1) }
  if (!fs.existsSync(ICT_FINAL_DIR)) { console.error('FINAL dir not found:', ICT_FINAL_DIR); process.exit(1) }

  const r2 = makeR2()
  const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

  console.log(DRY_RUN ? '⚠ DRY RUN' : 'Live run')
  console.log(`Source: ${ICT_FINAL_DIR}`)

  const { data: ict } = await supabase.from('subjects').select('id').eq('name', 'ICT').limit(1)
  if (!ict || ict.length === 0) { console.error('ICT subject not found'); process.exit(1) }
  const ictId = ict[0].id
  console.log(`ICT subject id: ${ictId}\n`)

  // Probe whether data_file_url column exists.
  const probe = await supabase.from('papers').select('data_file_url').limit(1)
  const hasDataFileCol = !probe.error
  if (!hasDataFileCol) {
    console.warn('⚠ data_file_url column missing — apply migration 10 to record data files in DB.\n')
  }

  let uploadedFiles = 0
  let updatedRows = 0

  const years = fs.readdirSync(ICT_FINAL_DIR, { withFileTypes: true })
    .filter(d => d.isDirectory() && /^\d{4}$/.test(d.name))
    .map(d => d.name).sort()

  for (const year of years) {
    const yDir = path.join(ICT_FINAL_DIR, year)
    const sessions = fs.readdirSync(yDir, { withFileTypes: true })
      .filter(d => d.isDirectory()).map(d => d.name).sort()

    for (const session of sessions) {
      const sDir = path.join(yDir, session)
      const seasonDb = session.toLowerCase()
      const files = fs.readdirSync(sDir)

      // Group PDFs by paper_number
      const groups = new Map<string, { qpFile?: string; qpName?: string; msFile?: string; msName?: string }>()
      let dataFile: { absolute: string; name: string } | null = null

      for (const f of files) {
        const full = path.join(sDir, f)
        if (/\.zip$/i.test(f)) { dataFile = { absolute: full, name: f }; continue }
        if (!/\.pdf$/i.test(f)) continue
        const parsed = parsePaperFilename(f)
        if (!parsed) continue
        if (!groups.has(parsed.paperNumber)) groups.set(parsed.paperNumber, {})
        const g = groups.get(parsed.paperNumber)!
        if (parsed.type === 'qp') { g.qpFile = full; g.qpName = f }
        else                     { g.msFile = full; g.msName = f }
      }

      // Upload PDFs and upsert paper rows
      for (const [paperNum, g] of [...groups.entries()].sort(([a],[b]) => a.localeCompare(b))) {
        let qpUrl: string | null = null
        let msUrl: string | null = null
        if (g.qpFile && g.qpName) {
          qpUrl = await uploadToR2(r2, g.qpFile, `${R2_FOLDER}/${year}/${session}/${g.qpName}`, 'application/pdf')
          uploadedFiles++
        }
        if (g.msFile && g.msName) {
          msUrl = await uploadToR2(r2, g.msFile, `${R2_FOLDER}/${year}/${session}/${g.msName}`, 'application/pdf')
          uploadedFiles++
        }

        if (DRY_RUN) {
          console.log(`  ${year} ${session.padEnd(8)} P${paperNum.padEnd(4)} QP:${qpUrl ? '✓' : '—'} MS:${msUrl ? '✓' : '—'}`)
          continue
        }

        const { data: existing } = await supabase
          .from('papers')
          .select('id, pdf_url, markscheme_pdf_url')
          .eq('subject_id', ictId)
          .eq('year', parseInt(year))
          .eq('season', seasonDb)
          .eq('paper_number', paperNum)
          .maybeSingle()

        const updates: Record<string, string | null> = {}
        if (qpUrl) updates.pdf_url = qpUrl
        if (msUrl) updates.markscheme_pdf_url = msUrl

        if (existing) {
          if (Object.keys(updates).length > 0) {
            const { error } = await supabase.from('papers').update(updates).eq('id', existing.id)
            if (error) { console.error(`  ✗ update ${year} ${session} P${paperNum}:`, error.message); continue }
            updatedRows++
          }
        } else {
          const { error } = await supabase.from('papers').insert({
            subject_id: ictId, paper_number: paperNum, year: parseInt(year),
            season: seasonDb, pdf_url: qpUrl, markscheme_pdf_url: msUrl,
          })
          if (error) { console.error(`  ✗ insert ${year} ${session} P${paperNum}:`, error.message); continue }
          updatedRows++
        }
        console.log(`  ${year} ${session.padEnd(8)} P${paperNum.padEnd(4)} QP:${qpUrl ? '✓' : '—'} MS:${msUrl ? '✓' : '—'}`)
      }

      // Upload data file (if any) and record it on the Paper 2 row
      if (dataFile) {
        const dfUrl = await uploadToR2(r2, dataFile.absolute, `${R2_FOLDER}/${year}/${session}/${dataFile.name}`, 'application/zip')
        uploadedFiles++
        if (!DRY_RUN && hasDataFileCol) {
          // Attach to Paper 2 row (the practical exam)
          const { data: p2 } = await supabase
            .from('papers').select('id')
            .eq('subject_id', ictId).eq('year', parseInt(year))
            .eq('season', seasonDb).eq('paper_number', '2')
            .maybeSingle()
          if (p2) {
            const { error } = await supabase.from('papers').update({ data_file_url: dfUrl }).eq('id', p2.id)
            if (error) console.error(`  ✗ data_file update ${year} ${session}:`, error.message)
            else { updatedRows++; console.log(`  ${year} ${session.padEnd(8)} DataFile attached to Paper 2`) }
          } else {
            console.warn(`  ⚠ ${year} ${session} has data file but no Paper 2 row — skipping`)
          }
        } else {
          console.log(`  ${year} ${session.padEnd(8)} DataFile:✓ R2 (DB ${hasDataFileCol ? 'updated' : 'skipped — column missing'})`)
        }
      }
    }
  }

  console.log('\n══════════════════════════════════')
  console.log(`Files uploaded: ${uploadedFiles}`)
  console.log(`DB rows touched: ${updatedRows}`)
  if (!hasDataFileCol) {
    console.log('\nNext step: open Supabase SQL editor and run:')
    console.log('  ALTER TABLE papers ADD COLUMN IF NOT EXISTS data_file_url TEXT;')
    console.log('Then re-run this script to populate data_file_url values.')
  }
}

main().catch(err => { console.error(err); process.exit(1) })
