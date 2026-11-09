// Publish proven Cambridge IGCSE Physics (0625) Paper 42/62 questions to the tools.
// Dry run unless --execute is supplied. Inserts NEW questions only; it never edits
// or deletes a live row (saved downloads in `questions` depend on page ids).
//
//   node --env-file=.env.local scripts/publish-cambridge-physics-questions.mjs
//   node --env-file=.env.local scripts/publish-cambridge-physics-questions.mjs --execute
//
// Preconditions (scripts/onboard_cambridge_physics.py): stage -> read every proven
// pair into topic_reads.json -> audit (artifact_audit.json pins both files).
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { resolve, relative, isAbsolute } from 'node:path'
import { createHash } from 'node:crypto'
import { createClient } from '@supabase/supabase-js'
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3'

const CODE = '0625'
const COMPONENTS = ['42', '62']
const PROVEN = new Set(['PROVEN', 'SEQUENCE_PROVEN', 'LABEL_PROVEN', 'REVIEWED_PROVEN'])
const DIFFICULTIES = ['easy', 'medium', 'hard']
const execute = process.argv.includes('--execute')
const root = resolve('.')
const base = `data/analysis/live_rebuild/${CODE}`
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex')

for (const name of ['NEXT_PUBLIC_SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY', 'NEXT_PUBLIC_R2_PUBLIC_URL']) {
  if (!process.env[name]) throw new Error(`${name} is not set (run with --env-file=.env.local)`)
}

const verdictsText = await readFile(`${base}/verdicts.json`)
const readsText = await readFile(`${base}/topic_reads.json`)
const staged = JSON.parse(verdictsText)
const reads = JSON.parse(readsText)
const audit = JSON.parse(await readFile(`${base}/artifact_audit.json`, 'utf8'))
const rows = staged.rows.filter(r => PROVEN.has(r.verdict))
if (!rows.length) throw new Error('No proven question pairs')
if (audit.failures.length || audit.questions !== rows.length
  || audit.verdicts_sha256 !== sha256(verdictsText) || audit.reads_sha256 !== sha256(readsText)) {
  throw new Error('Run a fresh audit (onboard_cambridge_physics.py audit) before publishing')
}
if (Object.keys(reads).length !== rows.length || rows.some(r => !reads[`${r.paper}|${r.question}`])) {
  throw new Error('Every proven question needs a direct chapter read')
}

const db = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY)
const { data: subject, error } = await db.from('subjects').select('id').eq('code', CODE).single()
if (error) throw error
const { data: papers, error: paperError } = await db.from('papers').select('id')
  .eq('subject_id', subject.id).in('paper_number', COMPONENTS)
if (paperError) throw paperError
const ids = new Set(papers.map(p => p.id))
const { data: existing, error: pageError, count } = await db.from('pages')
  .select('*', { count: 'exact' }).in('paper_id', [...ids])
if (pageError) throw pageError
if (count !== existing.length) throw new Error('Existing questions were truncated; refusing to publish')
const present = new Map(existing.map(p => [`${p.paper_id}|${p.question_number}`, p]))
const { data: topics, error: topicError } = await db.from('topics').select('*').eq('subject_id', subject.id)
if (topicError) throw topicError

const prefix = process.env.NEXT_PUBLIC_R2_PUBLIC_URL.replace(/\/$/, '') + '/'
const inserts = [], uploads = new Map()

async function asset(file, row, kind) {
  const path = resolve(root, file)
  const inside = relative(resolve(root, base, 'segments'), path)
  if (inside.startsWith('..') || isAbsolute(inside)) throw new Error('Staged PDF is outside the subject segments')
  const bytes = await readFile(path)
  if (bytes.subarray(0, 5).toString() !== '%PDF-') throw new Error('Staged asset is not a PDF')
  const digest = sha256(bytes)
  if (reads[`${row.paper}|${row.question}`][`${kind}_sha256`] !== digest) {
    throw new Error(`${row.paper}|${row.question}: chapter read is for a different ${kind} PDF`)
  }
  const key = `cambridge/igcse/physics/pages-v2/${row.live_key}/q${row.question}${kind === 'ms' ? '_ms' : ''}-${digest.slice(0, 16)}.pdf`
  uploads.set(key, bytes)
  return prefix + key
}

for (const row of rows) {
  if (!ids.has(row.paper_id)) throw new Error(`${row.paper}: staged paper is not a live 0625 Paper 42/62`)
  if (!Number.isInteger(row.question) || row.question < 1 || row.question > 20) throw new Error('Invalid question number')
  const read = reads[`${row.paper}|${row.question}`]
  if (!Array.isArray(read.topics) || !read.topics.length || new Set(read.topics).size !== read.topics.length
    || read.topics.some(t => !Object.hasOwn(staged.chapters, t)) || !read.reason?.trim()
    || !DIFFICULTIES.includes(read.difficulty)) throw new Error(`${row.paper}|${row.question}: invalid chapter read`)
  const live = present.get(`${row.paper_id}|${row.question}`)
  if (live) {
    if (JSON.stringify(live.topics) !== JSON.stringify(read.topics) || live.difficulty !== read.difficulty) {
      throw new Error(`${row.paper}|${row.question}: live tags differ from the read; apply a guarded update instead`)
    }
    continue
  }
  inserts.push({
    paper_id: row.paper_id, question_number: String(row.question),
    page_number: 1000 + row.question, page_count: row.page_count, is_question: true,
    topics: read.topics, difficulty: read.difficulty, has_diagram: read.has_diagram === true,
    qp_page_url: await asset(row.qp, row, 'qp'), ms_page_url: await asset(row.ms, row, 'ms'),
  })
}

const wanted = Object.entries(staged.chapters)
  .filter(([code]) => !topics.some(t => t.code === code))
  .map(([code, name]) => ({ subject_id: subject.id, code, name,
    description: 'Cambridge 0625 syllabus topic; complete Paper 4 and Paper 6 questions keep all subparts and may cover several topics.' }))
console.log(`${CODE}: ${inserts.length} new questions, ${uploads.size} PDF uploads, ${wanted.length} chapters `
  + `(${rows.length - inserts.length} already live) [${execute ? 'EXECUTE' : 'DRY RUN'}]`)

if (execute) {
  const backup = `data/backups/cambridge_physics_onboarding_${new Date().toISOString().replace(/[:.]/g, '-')}`
  await mkdir(backup, { recursive: true })
  await writeFile(`${backup}/before.json`, JSON.stringify({ pages: existing, topics }, null, 2))
  const r2 = new S3Client({ region: 'auto', endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
    credentials: { accessKeyId: process.env.R2_ACCESS_KEY_ID, secretAccessKey: process.env.R2_SECRET_ACCESS_KEY } })
  const entries = [...uploads], bucket = process.env.R2_BUCKET_NAME || 'grademax-papers'
  let next = 0, done = 0
  await Promise.all(Array.from({ length: 6 }, async () => {
    while (next < entries.length) {
      const [Key, Body] = entries[next++]
      await r2.send(new PutObjectCommand({ Bucket: bucket, Key, Body, ContentType: 'application/pdf' }))
      if (++done % 100 === 0) console.log(`${CODE}: ${done}/${entries.length} PDFs uploaded`)
    }
  }))
  // Chapters first, then questions: every asset and topic exists before a row points at it.
  if (wanted.length) {
    const { error } = await db.from('topics').insert(wanted)
    if (error) throw error
  }
  const createdIds = []
  for (let n = 0; n < inserts.length; n += 100) {
    const { data, error } = await db.from('pages').insert(inserts.slice(n, n + 100)).select('*')
    if (error) throw error
    createdIds.push(...data.map(p => p.id))
    await writeFile(`${backup}/created-page-ids.json`, JSON.stringify(createdIds, null, 2))
    const { error: mirrorError } = await db.from('questions').upsert(data.map(p => ({
      id: p.id, paper_id: p.paper_id, question_number: p.question_number, difficulty: p.difficulty,
      page_pdf_url: p.qp_page_url, ms_pdf_url: p.ms_page_url, has_diagram: p.has_diagram || false,
    })))
    if (mirrorError) throw mirrorError
  }
  const { count: after, error: afterError } = await db.from('pages')
    .select('id', { count: 'exact', head: true }).in('paper_id', [...ids])
  if (afterError) throw afterError
  console.log(`${CODE}: published ${createdIds.length} questions; ${after} live; backup: ${backup}`)
}
