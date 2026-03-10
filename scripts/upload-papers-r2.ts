/**
 * Upload all past papers to Cloudflare R2 and populate Supabase
 *
 * Usage:
 *   npx tsx scripts/upload-papers-r2.ts
 *
 * Prerequisites:
 *   1. Create R2 bucket "grademax-papers" in Cloudflare dashboard
 *   2. Enable public access (Settings → R2.dev subdomain → Allow Access)
 *   3. Generate R2 API token (R2 → Manage R2 API Tokens → Create API Token)
 *   4. Set R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, NEXT_PUBLIC_R2_PUBLIC_URL in .env.local
 */

import { S3Client, PutObjectCommand, HeadObjectCommand } from '@aws-sdk/client-s3'
import { createClient } from '@supabase/supabase-js'
import * as fs from 'fs'
import * as path from 'path'
import { config } from 'dotenv'

// Load .env.local — try multiple paths to be resilient
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

const RAW_DATA_DIR = String.raw`C:\Users\shari\grademax scraper\grademax-scraper\data\raw`

const R2_ACCOUNT_ID = process.env.R2_ACCOUNT_ID || '0130c4fe53f6f2cd3278a9355b54c937'
const R2_ACCESS_KEY_ID = process.env.R2_ACCESS_KEY_ID!
const R2_SECRET_ACCESS_KEY = process.env.R2_SECRET_ACCESS_KEY!
const R2_BUCKET = process.env.R2_BUCKET_NAME || 'grademax-papers'
const R2_PUBLIC_URL = process.env.NEXT_PUBLIC_R2_PUBLIC_URL! // e.g. https://pub-xxx.r2.dev

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY!

// ─── Subject Mapping ───────────────────────────────────────────────────────────

interface SubjectMeta {
  slug: string
  name: string
  level: string
  code: string
  board: string
}

const SUBJECT_MAP: Record<string, SubjectMeta> = {
  'Accounting':         { slug: 'accounting',          name: 'Accounting',               level: 'IGCSE', code: '4AC1', board: 'Edexcel' },
  'Bangla':             { slug: 'bangla',              name: 'Bangla',                   level: 'IGCSE', code: '4BN1', board: 'Edexcel' },
  'Biology':            { slug: 'biology',             name: 'Biology',                  level: 'IGCSE', code: '4BI1', board: 'Edexcel' },
  'Business':           { slug: 'business',            name: 'Business',                 level: 'IGCSE', code: '4BS1', board: 'Edexcel' },
  'Chemistry':          { slug: 'chemistry',           name: 'Chemistry',                level: 'IGCSE', code: '4CH1', board: 'Edexcel' },
  'Commerce':           { slug: 'commerce',            name: 'Commerce',                 level: 'IGCSE', code: '4CM1', board: 'Edexcel' },
  'Economics':          { slug: 'economics',           name: 'Economics',                level: 'IGCSE', code: '4EC1', board: 'Edexcel' },
  'English_A':          { slug: 'english-language-a',  name: 'English Language A',       level: 'IGCSE', code: '4EA1', board: 'Edexcel' },
  'English_B':          { slug: 'english-language-b',  name: 'English Language B',       level: 'IGCSE', code: '4EB1', board: 'Edexcel' },
  'Further Pure Maths': { slug: 'further-pure-maths',  name: 'Further Pure Mathematics', level: 'IGCSE', code: '4PM1', board: 'Edexcel' },
  'Human Biology':      { slug: 'human-biology',       name: 'Human Biology',            level: 'IGCSE', code: '4HB1', board: 'Edexcel' },
  'ICT':                { slug: 'ict',                 name: 'ICT',                      level: 'IGCSE', code: '4IT1', board: 'Edexcel' },
  'Mathematics_A':      { slug: 'maths-a',             name: 'Mathematics A',            level: 'IGCSE', code: '4MA1', board: 'Edexcel' },
  'Mathematics_B':      { slug: 'maths-b',             name: 'Mathematics B',            level: 'IGCSE', code: '4MB1', board: 'Edexcel' },
  'Mechanics_1':        { slug: 'mechanics-1',         name: 'Mechanics 1',              level: 'IAL',   code: 'WME01',board: 'Edexcel' },
  'Physics':            { slug: 'physics',             name: 'Physics',                  level: 'IGCSE', code: '4PH1', board: 'Edexcel' },
}

// ─── File Name Parser ──────────────────────────────────────────────────────────

interface ParsedFile {
  paperNumber: string   // e.g. "1", "1R", "2", "1F", "1HR"
  type: 'qp' | 'ms'
  displayName: string   // e.g. "Paper 1", "Paper 1R"
}

function parseFilename(filename: string): ParsedFile | null {
  const base = filename.replace(/\.pdf$/i, '')

  // Pattern A: "Paper 1.pdf", "Paper 1_MS.pdf", "Paper 1R.pdf", "Paper 1R_MS.pdf",
  //            "Paper 1F_MS.pdf", "Paper 1FR_MS.pdf", "Paper 1HR_MS.pdf"
  const patternA = /^Paper\s+(\d+)([A-Z]*)(?:_(MS))?$/i
  const matchA = base.match(patternA)
  if (matchA) {
    const num = matchA[1]
    const variant = (matchA[2] || '').toUpperCase()
    const isMS = !!matchA[3]
    return {
      paperNumber: num + variant,
      type: isMS ? 'ms' : 'qp',
      displayName: `Paper ${num}${variant}`,
    }
  }

  // Pattern B: hyphen-separated "4eb1-01-que-20240524.pdf", "4eb1-01r-rms-20240822.pdf"
  const patternB = /^\w+-(\d+)(r?)-(que|rms)-\d+$/i
  const matchB = base.match(patternB)
  if (matchB) {
    const paperNum = String(parseInt(matchB[1]))
    const replacement = matchB[2].toLowerCase() === 'r' ? 'R' : ''
    const isQP = matchB[3].toLowerCase() === 'que'
    return {
      paperNumber: paperNum + replacement,
      type: isQP ? 'qp' : 'ms',
      displayName: `Paper ${paperNum}${replacement}`,
    }
  }

  // Pattern C: underscore-separated "4HB1_01_que_20220108.pdf", "4HB1_01R_que_20201103.pdf",
  //            "4EC0_01_msc_20130822.pdf", "4HB0_01_rms_20110824a.pdf", "4HB1_02_que_20200305-.pdf"
  //            Also handles: "4CH1_1C_que_20211110.pdf", "4BI1_1B_que_20211106.pdf"
  const patternC = /^\w+_(\d+)([A-Z]*)_(que|rms|msc)_\d+[a-z\-_V\d]*$/i
  const matchC = base.match(patternC)
  if (matchC) {
    const paperNum = String(parseInt(matchC[1]))
    const variant = (matchC[2] || '').toUpperCase()
    const typeStr = matchC[3].toLowerCase()
    const isQP = typeStr === 'que'
    return {
      paperNumber: paperNum + variant,
      type: isQP ? 'qp' : 'ms',
      displayName: `Paper ${paperNum}${variant}`,
    }
  }

  // Pattern D: descriptive "Question-paper-Paper-1-June-2014.pdf", "Mark-scheme-Paper-1R-June-2014.pdf"
  const patternD = /^(Question-paper|Mark-scheme)-Paper-(\d+)([A-Z]*)-[A-Za-z]+-\d{4}$/i
  const matchD = base.match(patternD)
  if (matchD) {
    const typeStr = matchD[1].toLowerCase()
    const paperNum = matchD[2]
    const variant = (matchD[3] || '').toUpperCase()
    const isQP = typeStr === 'question-paper'
    return {
      paperNumber: paperNum + variant,
      type: isQP ? 'qp' : 'ms',
      displayName: `Paper ${paperNum}${variant}`,
    }
  }

  // Skip known non-exam files silently
  if (base.includes('past-paper-redraft') || base.includes('instructions') || base.includes('exampaper')) {
    return null
  }

  console.warn(`  ⚠ Unrecognized filename format: ${filename}`)
  return null
}

// ─── Clients ───────────────────────────────────────────────────────────────────

function createR2Client(): S3Client {
  return new S3Client({
    region: 'auto',
    endpoint: `https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
    credentials: {
      accessKeyId: R2_ACCESS_KEY_ID,
      secretAccessKey: R2_SECRET_ACCESS_KEY,
    },
  })
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function createSupabase(): any {
  return createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY)
}

// ─── Upload Logic ──────────────────────────────────────────────────────────────

async function uploadToR2(
  r2: S3Client,
  localPath: string,
  r2Key: string
): Promise<string> {
  // Check if already exists (idempotent)
  try {
    await r2.send(new HeadObjectCommand({ Bucket: R2_BUCKET, Key: r2Key }))
    // Already uploaded — return URL
    return `${R2_PUBLIC_URL}/${r2Key}`
  } catch {
    // Not found — proceed with upload
  }

  const fileBuffer = fs.readFileSync(localPath)

  await r2.send(
    new PutObjectCommand({
      Bucket: R2_BUCKET,
      Key: r2Key,
      Body: fileBuffer,
      ContentType: 'application/pdf',
      CacheControl: 'public, max-age=31536000, immutable',
    })
  )

  return `${R2_PUBLIC_URL}/${r2Key}`
}

// ─── Main Process ──────────────────────────────────────────────────────────────

interface PaperGroup {
  paperNumber: string
  displayName: string
  qpFile?: string      // local path
  msFile?: string      // local path
  qpFilename?: string  // original filename
  msFilename?: string
}

async function processSubject(
  r2: S3Client,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  supabase: any,
  folderName: string,
  subjectMeta: SubjectMeta
): Promise<{ uploaded: number; errors: number }> {
  const subjectDir = path.join(RAW_DATA_DIR, folderName)
  let uploaded = 0
  let errors = 0

  // Find existing subject by name (use limit(1) to handle duplicates gracefully)
  let subjectId: string
  const { data: existingSubjects } = await supabase
    .from('subjects')
    .select('id')
    .eq('name', subjectMeta.name)
    .limit(1)

  if (existingSubjects && existingSubjects.length > 0) {
    subjectId = existingSubjects[0].id
  } else {
    // Insert new subject — board is NOT NULL in the actual schema
    const { data: newSubject, error: insertErr } = await supabase
      .from('subjects')
      .insert({
        name: subjectMeta.name,
        code: subjectMeta.code,
        board: subjectMeta.board,
        level: subjectMeta.level,
      })
      .select('id')
      .single()

    if (insertErr || !newSubject) {
      console.error(`  ✗ Failed to insert subject ${subjectMeta.name}:`, insertErr?.message)
      return { uploaded: 0, errors: 1 }
    }
    subjectId = newSubject.id
  }
  console.log(`  Subject ID: ${subjectId}`)

  // Walk year directories
  const years = fs.readdirSync(subjectDir, { withFileTypes: true })
    .filter(d => d.isDirectory() && /^\d{4}$/.test(d.name))
    .map(d => d.name)
    .sort((a, b) => parseInt(b) - parseInt(a))

  for (const year of years) {
    const yearDir = path.join(subjectDir, year)

    // Walk session directories
    const sessions = fs.readdirSync(yearDir, { withFileTypes: true })
      .filter(d => d.isDirectory())
      .map(d => d.name)

    for (const session of sessions) {
      const sessionDir = path.join(yearDir, session)
      const seasonSlug = session // Keep original case: "May-Jun", "Oct-Nov", "Jan"
      const seasonR2 = session.toLowerCase() // lowercase for R2 paths

      // Read all PDF files in this session
      const pdfs = fs.readdirSync(sessionDir)
        .filter(f => f.toLowerCase().endsWith('.pdf'))

      // Parse and group by paper number
      const groups = new Map<string, PaperGroup>()

      for (const pdf of pdfs) {
        const parsed = parseFilename(pdf)
        if (!parsed) {
          errors++
          continue
        }

        const key = parsed.paperNumber
        if (!groups.has(key)) {
          groups.set(key, {
            paperNumber: key,
            displayName: parsed.displayName,
          })
        }

        const group = groups.get(key)!
        const fullPath = path.join(sessionDir, pdf)

        if (parsed.type === 'qp') {
          group.qpFile = fullPath
          group.qpFilename = pdf
        } else {
          group.msFile = fullPath
          group.msFilename = pdf
        }
      }

      // Upload each paper group
      for (const [, group] of groups) {
        try {
          let pdfUrl: string | null = null
          let msUrl: string | null = null

          // Upload QP
          if (group.qpFile) {
            const r2Key = `past-papers/${subjectMeta.slug}/${year}/${seasonR2}/${group.qpFilename!.replace(/\s+/g, '_')}`
            pdfUrl = await uploadToR2(r2, group.qpFile, r2Key)
          }

          // Upload MS
          if (group.msFile) {
            const r2Key = `past-papers/${subjectMeta.slug}/${year}/${seasonR2}/${group.msFilename!.replace(/\s+/g, '_')}`
            msUrl = await uploadToR2(r2, group.msFile, r2Key)
          }

          // Upsert paper record into Supabase
          const paperData = {
            subject_id: subjectId,
            paper_number: group.paperNumber,
            year: parseInt(year),
            season: seasonSlug,
            pdf_url: pdfUrl,
            markscheme_pdf_url: msUrl,
          }

          // Try to find existing paper
          const { data: existing } = await supabase
            .from('papers')
            .select('id')
            .eq('subject_id', subjectId)
            .eq('year', parseInt(year))
            .eq('season', seasonSlug)
            .eq('paper_number', group.paperNumber)
            .maybeSingle()

          if (existing) {
            await supabase
              .from('papers')
              .update({ pdf_url: pdfUrl, markscheme_pdf_url: msUrl })
              .eq('id', existing.id)
          } else {
            const { error: insertErr } = await supabase
              .from('papers')
              .insert(paperData)

            if (insertErr) {
              console.error(`    ✗ Insert failed for ${group.displayName} (${year} ${session}):`, insertErr.message)
              errors++
              continue
            }
          }

          uploaded++
          process.stdout.write(`    ✓ ${year} ${session} ${group.displayName} (QP: ${pdfUrl ? '✓' : '—'}, MS: ${msUrl ? '✓' : '—'})\n`)
        } catch (err) {
          console.error(`    ✗ Error processing ${group.displayName} (${year} ${session}):`, err)
          errors++
        }
      }
    }
  }

  return { uploaded, errors }
}

async function main() {
  console.log('╔══════════════════════════════════════════════════════════╗')
  console.log('║       GradeMax Past Papers → Cloudflare R2 Upload      ║')
  console.log('╚══════════════════════════════════════════════════════════╝')
  console.log()

  // Validate env
  const missing: string[] = []
  if (!R2_ACCESS_KEY_ID) missing.push('R2_ACCESS_KEY_ID')
  if (!R2_SECRET_ACCESS_KEY) missing.push('R2_SECRET_ACCESS_KEY')
  if (!R2_PUBLIC_URL) missing.push('NEXT_PUBLIC_R2_PUBLIC_URL')
  if (!SUPABASE_URL) missing.push('NEXT_PUBLIC_SUPABASE_URL')
  if (!SUPABASE_SERVICE_KEY) missing.push('SUPABASE_SERVICE_ROLE_KEY')

  if (missing.length > 0) {
    console.error('Missing required environment variables:')
    missing.forEach(v => console.error(`  - ${v}`))
    console.error('\nSee .env.local for configuration.')
    process.exit(1)
  }

  // Validate raw data directory
  if (!fs.existsSync(RAW_DATA_DIR)) {
    console.error(`Raw data directory not found: ${RAW_DATA_DIR}`)
    process.exit(1)
  }

  const r2 = createR2Client()
  const supabase = createSupabase()

  console.log(`R2 Bucket: ${R2_BUCKET}`)
  console.log(`R2 Public URL: ${R2_PUBLIC_URL}`)
  console.log(`Raw Data Dir: ${RAW_DATA_DIR}`)
  console.log()

  let totalUploaded = 0
  let totalErrors = 0

  // Get subject folders
  const subjectFolders = fs.readdirSync(RAW_DATA_DIR, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .map(d => d.name)

  for (const folder of subjectFolders) {
    const meta = SUBJECT_MAP[folder]
    if (!meta) {
      console.warn(`⚠ Unknown subject folder: ${folder} — skipping`)
      continue
    }

    console.log(`\n📚 Processing: ${meta.name} (${folder})`)

    const { uploaded, errors } = await processSubject(r2, supabase, folder, meta)
    totalUploaded += uploaded
    totalErrors += errors
  }

  console.log('\n══════════════════════════════════════════════════════════')
  console.log(`✅ Upload complete!`)
  console.log(`   Papers uploaded/updated: ${totalUploaded}`)
  console.log(`   Errors: ${totalErrors}`)
  console.log('══════════════════════════════════════════════════════════')
}

main().catch(console.error)
