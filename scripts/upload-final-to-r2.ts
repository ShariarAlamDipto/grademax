/**
 * upload-final-to-r2.ts
 *
 * 1. Clears ALL existing objects from the Cloudflare R2 bucket.
 * 2. Walks the FINAL folder and uploads every PDF preserving the
 *    exact naming convention: {Subject}/{Year}/{Session}/{filename}
 * 3. Upserts subjects + papers into Supabase.
 *
 * Usage:
 *   npx tsx --env-file=.env.local scripts/upload-final-to-r2.ts
 *
 * FINAL folder naming convention (must be preserved):
 *   {Subject}_{Year}_{Session}_Paper_{Number}_{Type}.pdf
 *   e.g. Mathematics_B_2017_Jan_Paper_1R_QP.pdf
 */

import {
  S3Client,
  PutObjectCommand,
  ListObjectsV2Command,
  DeleteObjectsCommand,
} from '@aws-sdk/client-s3'
import { createClient } from '@supabase/supabase-js'
import * as fs from 'fs'
import * as path from 'path'
import { config } from 'dotenv'

// ─── Load env ─────────────────────────────────────────────────────────────────

const envPaths = [
  path.resolve(process.cwd(), '.env.local'),
  path.resolve('C:\\Users\\shari\\grademax', '.env.local'),
]
for (const p of envPaths) {
  if (fs.existsSync(p)) {
    config({ path: p })
    console.log(`Loaded env from: ${p}`)
    break
  }
}

// ─── Configuration ─────────────────────────────────────────────────────────────

const FINAL_DIR = String.raw`C:\Users\shari\grademax scraper\grademax-scraper\data\FINAL`

const R2_ACCOUNT_ID    = process.env.R2_ACCOUNT_ID!
const R2_ACCESS_KEY_ID = process.env.R2_ACCESS_KEY_ID!
const R2_SECRET_KEY    = process.env.R2_SECRET_ACCESS_KEY!
const R2_BUCKET        = process.env.R2_BUCKET_NAME || 'grademax-papers'
const R2_PUBLIC_URL    = process.env.NEXT_PUBLIC_R2_PUBLIC_URL!

const SUPABASE_URL     = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SUPABASE_KEY     = process.env.SUPABASE_SERVICE_ROLE_KEY!

// ─── Subject metadata map (FINAL folder name → DB/URL metadata) ────────────────

interface SubjectMeta {
  slug: string
  name: string
  level: string
  code: string
  board: string
}

const SUBJECT_MAP: Record<string, SubjectMeta> = {
  Accounting:         { slug: 'accounting',         name: 'Accounting',               level: 'IGCSE', code: '4AC1',  board: 'Edexcel' },
  Bangla:             { slug: 'bangla',             name: 'Bangla',                   level: 'IGCSE', code: '4BN1',  board: 'Edexcel' },
  Biology:            { slug: 'biology',            name: 'Biology',                  level: 'IGCSE', code: '4BI1',  board: 'Edexcel' },
  Business_Studies:   { slug: 'business',           name: 'Business Studies',         level: 'IGCSE', code: '4BS1',  board: 'Edexcel' },
  Chemistry:          { slug: 'chemistry',          name: 'Chemistry',                level: 'IGCSE', code: '4CH1',  board: 'Edexcel' },
  Commerce:           { slug: 'commerce',           name: 'Commerce',                 level: 'IGCSE', code: '4CM1',  board: 'Edexcel' },
  Computer_Science:   { slug: 'computer-science',   name: 'Computer Science',         level: 'IGCSE', code: '4CP1',  board: 'Edexcel' },
  Economics:          { slug: 'economics',          name: 'Economics',                level: 'IGCSE', code: '4EC1',  board: 'Edexcel' },
  English_A:          { slug: 'english-language-a', name: 'English Language A',       level: 'IGCSE', code: '4EA1',  board: 'Edexcel' },
  English_B:          { slug: 'english-language-b', name: 'English Language B',       level: 'IGCSE', code: '4EB1',  board: 'Edexcel' },
  Further_Pure_Maths: { slug: 'further-pure-maths', name: 'Further Pure Mathematics', level: 'IGCSE', code: '4PM1',  board: 'Edexcel' },
  Geography:          { slug: 'geography',          name: 'Geography',                level: 'IGCSE', code: '4GE1',  board: 'Edexcel' },
  Human_Biology:      { slug: 'human-biology',      name: 'Human Biology',            level: 'IGCSE', code: '4HB1',  board: 'Edexcel' },
  ICT:                { slug: 'ict',                name: 'ICT',                      level: 'IGCSE', code: '4IT1',  board: 'Edexcel' },
  Mathematics_A:      { slug: 'maths-a',            name: 'Mathematics A',            level: 'IGCSE', code: '4MA1',  board: 'Edexcel' },
  Mathematics_B:      { slug: 'maths-b',            name: 'Mathematics B',            level: 'IGCSE', code: '4MB1',  board: 'Edexcel' },
  Mechanics_1:        { slug: 'mechanics-1',        name: 'Mechanics 1',              level: 'IAL',   code: 'WME01', board: 'Edexcel' },
  Physics:            { slug: 'physics',            name: 'Physics',                  level: 'IGCSE', code: '4PH1',  board: 'Edexcel' },
}

// ─── Filename parser ───────────────────────────────────────────────────────────

interface ParsedPaper {
  paperNumber: string  // e.g. "1", "1R", "2R"
  type: 'qp' | 'ms'
}

/**
 * Parses the FINAL naming convention:
 *   {Subject}_{Year}_{Session}_Paper_{Number}_{Type}.pdf
 *   e.g. Mathematics_B_2017_Jan_Paper_1R_QP.pdf
 */
function parseFilename(filename: string): ParsedPaper | null {
  const base = filename.replace(/\.pdf$/i, '')
  // Matches: anything_Paper_{digits}{optional letters}_{QP|MS}
  const m = base.match(/_Paper_(\d+)([A-Z]*)_(QP|MS)$/i)
  if (!m) return null
  return {
    paperNumber: m[1] + m[2].toUpperCase(),
    type: m[3].toUpperCase() === 'QP' ? 'qp' : 'ms',
  }
}

// ─── R2 helpers ───────────────────────────────────────────────────────────────

function makeR2Client(): S3Client {
  return new S3Client({
    region: 'auto',
    endpoint: `https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
    credentials: { accessKeyId: R2_ACCESS_KEY_ID, secretAccessKey: R2_SECRET_KEY },
  })
}

async function clearBucket(r2: S3Client): Promise<void> {
  console.log('\n🗑  Clearing R2 bucket…')
  let token: string | undefined
  let total = 0

  do {
    const list = await r2.send(new ListObjectsV2Command({
      Bucket: R2_BUCKET,
      ContinuationToken: token,
    }))

    const objects = list.Contents ?? []
    if (objects.length === 0) break

    await r2.send(new DeleteObjectsCommand({
      Bucket: R2_BUCKET,
      Delete: {
        Objects: objects.map(o => ({ Key: o.Key! })),
        Quiet: true,
      },
    }))

    total += objects.length
    process.stdout.write(`   deleted ${total} objects\r`)
    token = list.IsTruncated ? list.NextContinuationToken : undefined
  } while (token)

  console.log(`   ✅ Bucket cleared (${total} objects removed)`)
}

async function uploadToR2(r2: S3Client, localPath: string, r2Key: string): Promise<string> {
  const body = fs.readFileSync(localPath)
  await r2.send(new PutObjectCommand({
    Bucket: R2_BUCKET,
    Key: r2Key,
    Body: body,
    ContentType: 'application/pdf',
    CacheControl: 'public, max-age=31536000, immutable',
  }))
  return `${R2_PUBLIC_URL}/${r2Key}`
}

// ─── Main upload logic ─────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function processSubject(r2: S3Client, supabase: any, folderName: string, meta: SubjectMeta) {
  const subjectDir = path.join(FINAL_DIR, folderName)
  let uploaded = 0
  let errors = 0

  // Upsert subject into Supabase
  const { data: existing } = await supabase
    .from('subjects')
    .select('id')
    .eq('name', meta.name)
    .limit(1)

  let subjectId: string
  if (existing && existing.length > 0) {
    subjectId = existing[0].id
  } else {
    const { data: ins, error: insErr } = await supabase
      .from('subjects')
      .insert({ name: meta.name, code: meta.code, board: meta.board, level: meta.level })
      .select('id')
      .single()
    if (insErr || !ins) {
      console.error(`  ✗ Could not insert subject ${meta.name}:`, insErr?.message)
      return { uploaded: 0, errors: 1 }
    }
    subjectId = ins.id
  }

  // Walk year / session / files
  const years = fs.readdirSync(subjectDir, { withFileTypes: true })
    .filter(d => d.isDirectory() && /^\d{4}$/.test(d.name))
    .map(d => d.name)
    .sort((a, b) => parseInt(b) - parseInt(a))

  for (const year of years) {
    const yearDir = path.join(subjectDir, year)

    const sessions = fs.readdirSync(yearDir, { withFileTypes: true })
      .filter(d => d.isDirectory())
      .map(d => d.name)

    for (const session of sessions) {
      const sessionDir = path.join(yearDir, session)
      // Season stored in DB as lowercase (jan, may-jun, oct-nov)
      const seasonDb = session.toLowerCase()

      const pdfs = fs.readdirSync(sessionDir).filter(f => /\.pdf$/i.test(f))

      // Group QP/MS pairs by paper number
      const groups = new Map<string, { qpFile?: string; msFile?: string; qpName?: string; msName?: string }>()

      for (const pdf of pdfs) {
        const parsed = parseFilename(pdf)
        if (!parsed) {
          console.warn(`    ⚠ Unrecognised filename: ${pdf}`)
          errors++
          continue
        }
        if (!groups.has(parsed.paperNumber)) groups.set(parsed.paperNumber, {})
        const g = groups.get(parsed.paperNumber)!
        const fullPath = path.join(sessionDir, pdf)
        if (parsed.type === 'qp') { g.qpFile = fullPath; g.qpName = pdf }
        else                      { g.msFile = fullPath; g.msName = pdf }
      }

      for (const [paperNum, g] of groups) {
        try {
          let pdfUrl: string | null = null
          let msUrl:  string | null = null

          // R2 key preserves FINAL folder structure exactly
          if (g.qpFile && g.qpName) {
            const key = `${folderName}/${year}/${session}/${g.qpName}`
            pdfUrl = await uploadToR2(r2, g.qpFile, key)
          }
          if (g.msFile && g.msName) {
            const key = `${folderName}/${year}/${session}/${g.msName}`
            msUrl = await uploadToR2(r2, g.msFile, key)
          }

          // Upsert paper record
          const { data: existPaper } = await supabase
            .from('papers')
            .select('id')
            .eq('subject_id', subjectId)
            .eq('year', parseInt(year))
            .eq('season', seasonDb)
            .eq('paper_number', paperNum)
            .maybeSingle()

          if (existPaper) {
            await supabase.from('papers').update({ pdf_url: pdfUrl, markscheme_pdf_url: msUrl }).eq('id', existPaper.id)
          } else {
            const { error: ie } = await supabase.from('papers').insert({
              subject_id: subjectId,
              paper_number: paperNum,
              year: parseInt(year),
              season: seasonDb,
              pdf_url: pdfUrl,
              markscheme_pdf_url: msUrl,
            })
            if (ie) { console.error(`    ✗ Insert ${year} ${session} Paper ${paperNum}:`, ie.message); errors++; continue }
          }

          uploaded++
          process.stdout.write(
            `    ✓ ${year} ${session} Paper ${paperNum}` +
            ` QP:${pdfUrl ? '✓' : '—'} MS:${msUrl ? '✓' : '—'}\n`
          )
        } catch (err) {
          console.error(`    ✗ Error ${year} ${session} Paper ${paperNum}:`, err)
          errors++
        }
      }
    }
  }

  return { uploaded, errors }
}

// ─── Entry point ───────────────────────────────────────────────────────────────

async function main() {
  console.log('╔══════════════════════════════════════════════════════════╗')
  console.log('║     GradeMax FINAL → Cloudflare R2 + Supabase Upload    ║')
  console.log('╚══════════════════════════════════════════════════════════╝')

  // Validate env
  const missing = ['R2_ACCOUNT_ID','R2_ACCESS_KEY_ID','R2_SECRET_ACCESS_KEY',
    'NEXT_PUBLIC_R2_PUBLIC_URL','NEXT_PUBLIC_SUPABASE_URL','SUPABASE_SERVICE_ROLE_KEY']
    .filter(k => !process.env[k])
  if (missing.length) { console.error('Missing env vars:', missing.join(', ')); process.exit(1) }

  if (!fs.existsSync(FINAL_DIR)) {
    console.error('FINAL directory not found:', FINAL_DIR); process.exit(1)
  }

  const r2       = makeR2Client()
  const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

  console.log(`\nR2 Bucket   : ${R2_BUCKET}`)
  console.log(`R2 Public   : ${R2_PUBLIC_URL}`)
  console.log(`FINAL Dir   : ${FINAL_DIR}`)

  // Step 1: Clear bucket
  await clearBucket(r2)

  // Step 2: Upload all subjects
  const folders = fs.readdirSync(FINAL_DIR, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .map(d => d.name)

  let totalUploaded = 0
  let totalErrors   = 0

  for (const folder of folders) {
    const meta = SUBJECT_MAP[folder]
    if (!meta) { console.warn(`\n⚠ Unknown folder: ${folder} — skipping`); continue }

    console.log(`\n📚 ${meta.name} (${folder})`)
    const { uploaded, errors } = await processSubject(r2, supabase, folder, meta)
    totalUploaded += uploaded
    totalErrors   += errors
  }

  console.log('\n══════════════════════════════════════════════════════════')
  console.log(`✅  Upload complete!`)
  console.log(`    Papers uploaded : ${totalUploaded}`)
  console.log(`    Errors          : ${totalErrors}`)
  console.log('══════════════════════════════════════════════════════════')
}

main().catch(console.error)
