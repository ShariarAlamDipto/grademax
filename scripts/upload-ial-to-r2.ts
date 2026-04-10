/**
 * upload-ial-to-r2.ts
 *
 * Uploads all IAL past papers from data/raw/IAL/ to Cloudflare R2 and upserts
 * subjects + papers into Supabase.
 *
 * Filename convention (source):
 *   {Subject}_{Module}_{Year}_{Session}_{Type}.pdf
 *   e.g. Mathematics_P1_2014_Jan_QP.pdf
 *        Biology_Unit_1_2019_May-Jun_MS.pdf
 *        Further_Mathematics_FP1_2017_May-Jun_QP.pdf
 *        Law_Paper_1_2023_May-Jun_MS.pdf
 *
 * R2 key convention:
 *   ial/{subject-slug}/{year}/{session-lowercase}/{original-filename}
 *
 * Usage:
 *   npx tsx --env-file=.env.local scripts/upload-ial-to-r2.ts
 */

import { S3Client, PutObjectCommand, HeadObjectCommand } from '@aws-sdk/client-s3'
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

const IAL_DIR = path.resolve('C:\\Users\\shari\\grademax\\data\\IAL Final')

const R2_ACCOUNT_ID    = process.env.R2_ACCOUNT_ID!
const R2_ACCESS_KEY_ID = process.env.R2_ACCESS_KEY_ID!
const R2_SECRET_KEY    = process.env.R2_SECRET_ACCESS_KEY!
const R2_BUCKET        = process.env.R2_BUCKET_NAME || 'grademax-papers'
const R2_PUBLIC_URL    = process.env.NEXT_PUBLIC_R2_PUBLIC_URL!

const SUPABASE_URL     = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SUPABASE_KEY     = process.env.SUPABASE_SERVICE_ROLE_KEY!

// ─── Types ────────────────────────────────────────────────────────────────────

interface SubjectMeta {
  slug: string
  name: string
  level: string
  code: string
  board: string
}

interface ParsedFile {
  module: string   // e.g. "P1", "Unit_1", "FP1", "Paper_1"
  type: 'qp' | 'ms'
}

// ─── Math module → subject mapping ───────────────────────────────────────────

const MATH_MODULE_MAP: Record<string, SubjectMeta> = {
  P1: { slug: 'pure-mathematics-1', name: 'Pure Mathematics 1 (P1)', code: 'WMA11', board: 'Edexcel', level: 'IAL' },
  P2: { slug: 'pure-mathematics-2', name: 'Pure Mathematics 2 (P2)', code: 'WMA12', board: 'Edexcel', level: 'IAL' },
  P3: { slug: 'pure-mathematics-3', name: 'Pure Mathematics 3 (P3)', code: 'WMA13', board: 'Edexcel', level: 'IAL' },
  P4: { slug: 'pure-mathematics-4', name: 'Pure Mathematics 4 (P4)', code: 'WMA14', board: 'Edexcel', level: 'IAL' },
  M1: { slug: 'mechanics-1',         name: 'Mechanics 1 (M1)',         code: 'WME01', board: 'Edexcel', level: 'IAL' },
  M2: { slug: 'mechanics-2',         name: 'Mechanics 2 (M2)',         code: 'WME02', board: 'Edexcel', level: 'IAL' },
  M3: { slug: 'mechanics-3',         name: 'Mechanics 3 (M3)',         code: 'WME03', board: 'Edexcel', level: 'IAL' },
  D1: { slug: 'decision-mathematics-1', name: 'Decision Mathematics 1 (D1)', code: 'WDM11', board: 'Edexcel', level: 'IAL' },
  S1: { slug: 'statistics-1',        name: 'Statistics 1 (S1)',        code: 'WST01', board: 'Edexcel', level: 'IAL' },
  S2: { slug: 'statistics-2',        name: 'Statistics 2 (S2)',        code: 'WST02', board: 'Edexcel', level: 'IAL' },
  S3: { slug: 'statistics-3',        name: 'Statistics 3 (S3)',        code: 'WST03', board: 'Edexcel', level: 'IAL' },
}

// ─── Further Mathematics module → subject mapping ─────────────────────────────

const FURTHER_MATH_MODULE_MAP: Record<string, SubjectMeta> = {
  FP1: { slug: 'further-pure-maths-1', name: 'Further Pure Mathematics 1 (FP1)', code: 'WFM01', board: 'Edexcel', level: 'IAL' },
  FP2: { slug: 'further-pure-maths-2', name: 'Further Pure Mathematics 2 (FP2)', code: 'WFM02', board: 'Edexcel', level: 'IAL' },
  FP3: { slug: 'further-pure-maths-3', name: 'Further Pure Mathematics 3 (FP3)', code: 'WFM03', board: 'Edexcel', level: 'IAL' },
  FP4: { slug: 'further-pure-maths-4', name: 'Further Pure Mathematics 4 (FP4)', code: 'WFM04', board: 'Edexcel', level: 'IAL' },
  FM1: { slug: 'further-mechanics-1',  name: 'Further Mechanics 1 (FM1)',        code: 'WFME01', board: 'Edexcel', level: 'IAL' },
  FM2: { slug: 'further-mechanics-2',  name: 'Further Mechanics 2 (FM2)',        code: 'WFME02', board: 'Edexcel', level: 'IAL' },
  FS1: { slug: 'further-statistics-1', name: 'Further Statistics 1 (FS1)',       code: 'WFST01', board: 'Edexcel', level: 'IAL' },
  FS2: { slug: 'further-statistics-2', name: 'Further Statistics 2 (FS2)',       code: 'WFST02', board: 'Edexcel', level: 'IAL' },
  FD1: { slug: 'further-decision-1',   name: 'Further Decision Maths 1 (FD1)',   code: 'WFDM01', board: 'Edexcel', level: 'IAL' },
}

// ─── Folder → subject mapping (single-subject-per-folder) ─────────────────────

// For these folders, all modules (Unit_1, Unit_2, etc.) go into one subject,
// with paper_number = module name (e.g. "Unit_1").
const FOLDER_SUBJECT_MAP: Record<string, SubjectMeta> = {
  Accounting:         { slug: 'ial-accounting',         name: 'IAL Accounting',         code: 'WAC',  board: 'Edexcel', level: 'IAL' },
  Biology:            { slug: 'ial-biology',            name: 'IAL Biology',            code: 'WBI',  board: 'Edexcel', level: 'IAL' },
  Business:           { slug: 'ial-business',           name: 'IAL Business',           code: 'WBS',  board: 'Edexcel', level: 'IAL' },
  Chemistry:          { slug: 'ial-chemistry',          name: 'IAL Chemistry',          code: 'WCH',  board: 'Edexcel', level: 'IAL' },
  Economics:          { slug: 'ial-economics',          name: 'IAL Economics',          code: 'WEC',  board: 'Edexcel', level: 'IAL' },
  English_Language:   { slug: 'ial-english-language',   name: 'IAL English Language',   code: 'WEN',  board: 'Edexcel', level: 'IAL' },
  English_Literature: { slug: 'ial-english-literature', name: 'IAL English Literature', code: 'WLT',  board: 'Edexcel', level: 'IAL' },
  French:             { slug: 'ial-french',             name: 'IAL French',             code: 'WFR',  board: 'Edexcel', level: 'IAL' },
  Geography:          { slug: 'ial-geography',          name: 'IAL Geography',          code: 'WGE',  board: 'Edexcel', level: 'IAL' },
  German:             { slug: 'ial-german',             name: 'IAL German',             code: 'WGN',  board: 'Edexcel', level: 'IAL' },
  Greek:              { slug: 'ial-greek',              name: 'IAL Greek',              code: 'WGK',  board: 'Edexcel', level: 'IAL' },
  History:            { slug: 'ial-history',            name: 'IAL History',            code: 'WHI',  board: 'Edexcel', level: 'IAL' },
  Italian:            { slug: 'ial-italian',            name: 'IAL Italian',            code: 'WIT',  board: 'Edexcel', level: 'IAL' },
  Law:                { slug: 'ial-law',                name: 'IAL Law',                code: 'WLW',  board: 'Edexcel', level: 'IAL' },
  Physics:            { slug: 'ial-physics',            name: 'IAL Physics',            code: 'WPH',  board: 'Edexcel', level: 'IAL' },
  Psychology:         { slug: 'ial-psychology',         name: 'IAL Psychology',         code: 'WPS',  board: 'Edexcel', level: 'IAL' },
  Spanish:            { slug: 'ial-spanish',            name: 'IAL Spanish',            code: 'WSP',  board: 'Edexcel', level: 'IAL' },
  Sociology:          { slug: 'ial-sociology',          name: 'IAL Sociology',          code: 'WSO',  board: 'Edexcel', level: 'IAL' },
}

// ─── Filename parser ───────────────────────────────────────────────────────────

/**
 * Parses an IAL filename using the year and session from the directory path.
 *
 * Format: {FolderName}_{Module}_{Year}_{Session}_{QP|MS}.pdf
 * Strategy: anchor on _{year}_{session}_ to split prefix from type.
 */
function parseFilename(filename: string, folderName: string, year: string, session: string): ParsedFile | null {
  const base = filename.replace(/\.pdf$/i, '')

  const anchor = `_${year}_${session}_`
  const anchorIdx = base.indexOf(anchor)
  if (anchorIdx === -1) {
    console.warn(`    ⚠ Cannot anchor year/session in filename: ${filename}`)
    return null
  }

  const prefix = base.substring(0, anchorIdx)          // e.g. "Mathematics_P1"
  const typeStr = base.substring(anchorIdx + anchor.length).toUpperCase()  // "QP" or "MS"

  if (typeStr !== 'QP' && typeStr !== 'MS') {
    console.warn(`    ⚠ Unknown file type "${typeStr}" in: ${filename}`)
    return null
  }

  // Strip folder name prefix to get the module
  const folderPrefix = folderName + '_'
  const module = prefix.startsWith(folderPrefix)
    ? prefix.slice(folderPrefix.length)
    : prefix

  if (!module) {
    console.warn(`    ⚠ Empty module name in: ${filename}`)
    return null
  }

  return {
    module,
    type: typeStr === 'QP' ? 'qp' : 'ms',
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

async function uploadToR2(r2: S3Client, localPath: string, r2Key: string): Promise<string> {
  // Idempotent — skip if already exists
  try {
    await r2.send(new HeadObjectCommand({ Bucket: R2_BUCKET, Key: r2Key }))
    return `${R2_PUBLIC_URL}/${r2Key}`
  } catch {
    // Not found — upload
  }

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

// ─── Supabase helpers ─────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function getOrCreateSubject(supabase: any, meta: SubjectMeta): Promise<string> {
  // Try by name first
  const { data: byName } = await supabase
    .from('subjects')
    .select('id')
    .eq('name', meta.name)
    .limit(1)
  if (byName && byName.length > 0) return byName[0].id

  // Try by code (handles pre-existing records with different name format)
  if (meta.code) {
    const { data: byCode } = await supabase
      .from('subjects')
      .select('id')
      .eq('code', meta.code)
      .limit(1)
    if (byCode && byCode.length > 0) {
      // Update the name to match our convention
      await supabase.from('subjects').update({ name: meta.name }).eq('id', byCode[0].id)
      return byCode[0].id
    }
  }

  const { data: inserted, error } = await supabase
    .from('subjects')
    .insert({ name: meta.name, code: meta.code, board: meta.board, level: meta.level })
    .select('id')
    .single()

  if (error || !inserted) {
    throw new Error(`Failed to insert subject "${meta.name}": ${error?.message}`)
  }
  return inserted.id
}

// ─── Process a folder that maps all modules → one subject ─────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function processUnitFolder(r2: S3Client, supabase: any, folderName: string, meta: SubjectMeta) {
  const folderDir = path.join(IAL_DIR, folderName)
  let uploaded = 0
  let errors = 0

  const subjectId = await getOrCreateSubject(supabase, meta)
  console.log(`  Subject: ${meta.name} (${meta.slug}) — ID: ${subjectId}`)

  const years = fs.readdirSync(folderDir, { withFileTypes: true })
    .filter(d => d.isDirectory() && /^\d{4}$/.test(d.name))
    .map(d => d.name)
    .sort((a, b) => parseInt(b) - parseInt(a))

  for (const year of years) {
    const sessions = fs.readdirSync(path.join(folderDir, year), { withFileTypes: true })
      .filter(d => d.isDirectory())
      .map(d => d.name)

    for (const session of sessions) {
      const sessionDir = path.join(folderDir, year, session)
      const seasonDb = session.toLowerCase()

      const pdfs = fs.readdirSync(sessionDir).filter(f => /\.pdf$/i.test(f))

      // Group QP + MS by module
      const groups = new Map<string, { qpFile?: string; msFile?: string; qpName?: string; msName?: string }>()

      for (const pdf of pdfs) {
        const parsed = parseFilename(pdf, folderName, year, session)
        if (!parsed) { errors++; continue }

        if (!groups.has(parsed.module)) groups.set(parsed.module, {})
        const g = groups.get(parsed.module)!
        const fullPath = path.join(sessionDir, pdf)

        if (parsed.type === 'qp') { g.qpFile = fullPath; g.qpName = pdf }
        else                      { g.msFile = fullPath; g.msName = pdf }
      }

      for (const [module, g] of groups) {
        try {
          let pdfUrl: string | null = null
          let msUrl: string | null = null

          if (g.qpFile && g.qpName) {
            const key = `ial/${meta.slug}/${year}/${seasonDb}/${g.qpName}`
            pdfUrl = await uploadToR2(r2, g.qpFile, key)
          }
          if (g.msFile && g.msName) {
            const key = `ial/${meta.slug}/${year}/${seasonDb}/${g.msName}`
            msUrl = await uploadToR2(r2, g.msFile, key)
          }

          const { data: existPaper } = await supabase
            .from('papers')
            .select('id')
            .eq('subject_id', subjectId)
            .eq('year', parseInt(year))
            .eq('season', seasonDb)
            .eq('paper_number', module)
            .maybeSingle()

          if (existPaper) {
            await supabase.from('papers').update({ pdf_url: pdfUrl, markscheme_pdf_url: msUrl }).eq('id', existPaper.id)
          } else {
            const { error: ie } = await supabase.from('papers').insert({
              subject_id: subjectId,
              paper_number: module,
              year: parseInt(year),
              season: seasonDb,
              pdf_url: pdfUrl,
              markscheme_pdf_url: msUrl,
            })
            if (ie) { console.error(`    ✗ Insert ${year} ${session} ${module}:`, ie.message); errors++; continue }
          }

          uploaded++
          process.stdout.write(`    ✓ ${year} ${session} ${module} QP:${pdfUrl ? '✓' : '—'} MS:${msUrl ? '✓' : '—'}\n`)
        } catch (err) {
          console.error(`    ✗ Error ${year} ${session} ${module}:`, err)
          errors++
        }
      }
    }
  }

  return { uploaded, errors }
}

// ─── Process a folder that splits modules into separate subjects ───────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function processModuleFolder(
  r2: S3Client,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  supabase: any,
  folderName: string,
  moduleMap: Record<string, SubjectMeta>
) {
  const folderDir = path.join(IAL_DIR, folderName)
  let uploaded = 0
  let errors = 0

  // Cache subject IDs so we don't query repeatedly
  const subjectIdCache = new Map<string, string>()

  const years = fs.readdirSync(folderDir, { withFileTypes: true })
    .filter(d => d.isDirectory() && /^\d{4}$/.test(d.name))
    .map(d => d.name)
    .sort((a, b) => parseInt(b) - parseInt(a))

  for (const year of years) {
    const sessions = fs.readdirSync(path.join(folderDir, year), { withFileTypes: true })
      .filter(d => d.isDirectory())
      .map(d => d.name)

    for (const session of sessions) {
      const sessionDir = path.join(folderDir, year, session)
      const seasonDb = session.toLowerCase()

      const pdfs = fs.readdirSync(sessionDir).filter(f => /\.pdf$/i.test(f))

      // Group by module, then by QP/MS
      const groups = new Map<string, { qpFile?: string; msFile?: string; qpName?: string; msName?: string }>()

      for (const pdf of pdfs) {
        const parsed = parseFilename(pdf, folderName, year, session)
        if (!parsed) { errors++; continue }

        const meta = moduleMap[parsed.module]
        if (!meta) {
          console.warn(`    ⚠ No mapping for module "${parsed.module}" in ${folderName} — skipping ${pdf}`)
          continue
        }

        if (!groups.has(parsed.module)) groups.set(parsed.module, {})
        const g = groups.get(parsed.module)!
        const fullPath = path.join(sessionDir, pdf)

        if (parsed.type === 'qp') { g.qpFile = fullPath; g.qpName = pdf }
        else                      { g.msFile = fullPath; g.msName = pdf }
      }

      for (const [module, g] of groups) {
        const meta = moduleMap[module]
        if (!meta) continue

        try {
          // Ensure subject exists
          if (!subjectIdCache.has(meta.slug)) {
            const id = await getOrCreateSubject(supabase, meta)
            subjectIdCache.set(meta.slug, id)
            console.log(`  Subject: ${meta.name} (${meta.slug}) — ID: ${id}`)
          }
          const subjectId = subjectIdCache.get(meta.slug)!

          let pdfUrl: string | null = null
          let msUrl: string | null = null

          if (g.qpFile && g.qpName) {
            const key = `ial/${meta.slug}/${year}/${seasonDb}/${g.qpName}`
            pdfUrl = await uploadToR2(r2, g.qpFile, key)
          }
          if (g.msFile && g.msName) {
            const key = `ial/${meta.slug}/${year}/${seasonDb}/${g.msName}`
            msUrl = await uploadToR2(r2, g.msFile, key)
          }

          // paper_number = '1' since each module is its own subject (one paper per session)
          const { data: existPaper } = await supabase
            .from('papers')
            .select('id')
            .eq('subject_id', subjectId)
            .eq('year', parseInt(year))
            .eq('season', seasonDb)
            .eq('paper_number', '1')
            .maybeSingle()

          if (existPaper) {
            await supabase.from('papers').update({ pdf_url: pdfUrl, markscheme_pdf_url: msUrl }).eq('id', existPaper.id)
          } else {
            const { error: ie } = await supabase.from('papers').insert({
              subject_id: subjectId,
              paper_number: '1',
              year: parseInt(year),
              season: seasonDb,
              pdf_url: pdfUrl,
              markscheme_pdf_url: msUrl,
            })
            if (ie) { console.error(`    ✗ Insert ${year} ${session} ${module}:`, ie.message); errors++; continue }
          }

          uploaded++
          process.stdout.write(`    ✓ ${meta.name} ${year} ${session} QP:${pdfUrl ? '✓' : '—'} MS:${msUrl ? '✓' : '—'}\n`)
        } catch (err) {
          console.error(`    ✗ Error ${year} ${session} ${module}:`, err)
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
  console.log('║          GradeMax IAL Papers → R2 + Supabase            ║')
  console.log('╚══════════════════════════════════════════════════════════╝')

  const missing = ['R2_ACCOUNT_ID', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY',
    'NEXT_PUBLIC_R2_PUBLIC_URL', 'NEXT_PUBLIC_SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']
    .filter(k => !process.env[k])
  if (missing.length) { console.error('Missing env vars:', missing.join(', ')); process.exit(1) }

  if (!fs.existsSync(IAL_DIR)) {
    console.error('IAL directory not found:', IAL_DIR); process.exit(1)
  }

  const r2       = makeR2Client()
  const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

  console.log(`\nR2 Bucket  : ${R2_BUCKET}`)
  console.log(`R2 URL     : ${R2_PUBLIC_URL}`)
  console.log(`IAL Dir    : ${IAL_DIR}`)

  let totalUploaded = 0
  let totalErrors   = 0

  // ── Mathematics (split by module) ──────────────────────────────────────────
  console.log('\n\n📚 Mathematics (split by module)')
  {
    const { uploaded, errors } = await processModuleFolder(r2, supabase, 'Mathematics', MATH_MODULE_MAP)
    totalUploaded += uploaded; totalErrors += errors
  }

  // ── Further Mathematics (split by module) ──────────────────────────────────
  console.log('\n\n📚 Further Mathematics (split by module)')
  {
    const { uploaded, errors } = await processModuleFolder(r2, supabase, 'Further_Mathematics', FURTHER_MATH_MODULE_MAP)
    totalUploaded += uploaded; totalErrors += errors
  }

  // ── Unit-based subjects ────────────────────────────────────────────────────
  for (const [folderName, meta] of Object.entries(FOLDER_SUBJECT_MAP)) {
    const folderPath = path.join(IAL_DIR, folderName)
    if (!fs.existsSync(folderPath)) {
      console.warn(`\n⚠ Folder not found: ${folderName} — skipping`)
      continue
    }
    console.log(`\n\n📚 ${folderName} → ${meta.name}`)
    const { uploaded, errors } = await processUnitFolder(r2, supabase, folderName, meta)
    totalUploaded += uploaded; totalErrors += errors
  }

  console.log('\n══════════════════════════════════════════════════════════')
  console.log(`✅  Upload complete!`)
  console.log(`    Papers uploaded : ${totalUploaded}`)
  console.log(`    Errors          : ${totalErrors}`)
  console.log('══════════════════════════════════════════════════════════')
}

main().catch(console.error)
