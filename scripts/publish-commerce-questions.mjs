// Publish verified commerce questions. Dry run unless --execute is supplied.
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { resolve, relative, isAbsolute } from 'node:path'
import { createHash } from 'node:crypto'
import { createClient } from '@supabase/supabase-js'
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3'

const code = process.argv[process.argv.indexOf('--subject') + 1]
const folders = { '4AC1': 'accounting', '4BS1': 'business', '4EC1': 'economics', '4CP1': 'computer-science' }
if (!folders[code]) throw new Error('Use --subject 4AC1, 4BS1, 4EC1 or 4CP1')
const execute = process.argv.includes('--execute')
const root = resolve('.')
const base = `data/analysis/live_rebuild/${code}`
const staged = JSON.parse(await readFile(`${base}/verdicts.json`, 'utf8'))
const proven = new Set(['PROVEN', 'SEQUENCE_PROVEN', 'LABEL_PROVEN', 'REVIEWED_PROVEN'])
const rows = staged.rows.filter(r => proven.has(r.verdict))
if (!rows.length) throw new Error('No proven question pairs')
const chapterReads = code === '4CP1' ? JSON.parse(await readFile(`${base}/topic_reads.json`, 'utf8')) : null
if (chapterReads && (Object.keys(chapterReads).length !== rows.length || rows.some(r => !chapterReads[`${r.paper}|${r.question}`]))) {
  throw new Error('Computer Science requires a direct chapter review for every proven question')
}
if (chapterReads) {
  const audit = JSON.parse(await readFile(`${base}/artifact_audit.json`, 'utf8'))
  const digest = async file => createHash('sha256').update(await readFile(file)).digest('hex')
  if (audit.failures.length || audit.questions !== rows.length
    || audit.verdicts_sha256 !== await digest(`${base}/verdicts.json`)
    || audit.reads_sha256 !== await digest(`${base}/topic_reads.json`)) throw new Error('Run a fresh Computer Science artifact audit before publishing')
}
const db = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY)
const { data: subject, error } = await db.from('subjects').select('id').eq('code', code).single()
if (error) throw error
const { data: papers, error: paperError } = await db.from('papers').select('id').eq('subject_id', subject.id)
if (paperError) throw paperError
const ids = papers.map(p => p.id)
const { data: existing, error: pageError, count } = await db.from('pages').select('*', { count: 'exact' }).in('paper_id', ids)
if (pageError) throw pageError
if (count !== existing.length) throw new Error('Existing questions were truncated; refusing to publish')
const present = new Set(existing.map(p => `${p.paper_id}|${p.question_number}`))
const { data: topics, error: topicError } = await db.from('topics').select('*').eq('subject_id', subject.id)
if (topicError) throw topicError
const prefix = process.env.NEXT_PUBLIC_R2_PUBLIC_URL.replace(/\/$/, '') + '/'
const inserts = [], uploads = new Map()

async function asset(file, row, suffix) {
  const path = resolve(root, file)
  const inside = relative(resolve(root, base, 'segments'), path)
  if (inside.startsWith('..') || isAbsolute(inside)) throw new Error('Staged PDF is outside subject segments')
  const bytes = await readFile(path)
  if (bytes.subarray(0, 5).toString() !== '%PDF-') throw new Error('Staged asset is not a PDF')
  const hash = createHash('sha256').update(bytes).digest('hex').slice(0, 16)
  if (chapterReads) {
    const kind = suffix ? 'ms' : 'qp'
    if (chapterReads[`${row.paper}|${row.question}`][`${kind}_sha256`] !== createHash('sha256').update(bytes).digest('hex')) {
      throw new Error('Chapter read is for a different PDF')
    }
  }
  const key = `igcse/${folders[code]}/pages-v2/${row.live_key}/q${row.question}${suffix}-${hash}.pdf`
  uploads.set(key, bytes)
  return prefix + key
}

for (const row of rows) {
  if (!ids.includes(row.paper_id)) throw new Error('Staged paper does not belong to this subject')
  const read = chapterReads?.[`${row.paper}|${row.question}`]
  if (read) {
    if (!Array.isArray(read.topics) || !read.topics.length || new Set(read.topics).size !== read.topics.length
      || read.topics.some(t => !Object.hasOwn(staged.chapters, t)) || !read.reason?.trim()
      || !['easy', 'medium', 'hard'].includes(read.difficulty)) throw new Error('Invalid chapter review')
  } else if (!['1', '2'].includes(row.topic)) throw new Error('Invalid exam-paper filter')
  const identity = `${row.paper_id}|${row.question}`
  if (present.has(identity)) {
    if (chapterReads) {
      const old = existing.find(p => `${p.paper_id}|${p.question_number}` === identity)
      if (JSON.stringify(old.topics) !== JSON.stringify(read.topics) || old.difficulty !== read.difficulty) {
        throw new Error('Existing Computer Science metadata differs; reconcile before publishing')
      }
    }
    continue
  }
  if (!Number.isInteger(row.question) || row.question < 1 || row.question > 99) throw new Error('Invalid question number')
  const qp = await asset(row.qp, row, '')
  const ms = await asset(row.ms, row, '_ms')
  inserts.push({ paper_id: row.paper_id, question_number: String(row.question),
    page_number: 1000 + row.question, page_count: row.page_count,
    is_question: true, topics: read ? read.topics : [row.topic], difficulty: read ? read.difficulty : null,
    ...(read ? { has_diagram: read.has_diagram === true } : {}),
    qp_page_url: qp, ms_page_url: ms })
  present.add(identity)
}
const names = {
  '4AC1': ['Introduction to Bookkeeping and Accounting (Paper 1)', 'Financial Statements (Paper 2)'],
  '4BS1': ['Investigating Small Businesses (Paper 1)', 'Investigating Large Businesses (Paper 2)'],
  '4EC1': ['Microeconomics and Business Economics (Paper 1)', 'Macroeconomics and the Global Economy (Paper 2)'],
}[code]
// 4AC1 is chapterwise since 2026-10-16 (apply_accounting_tool_topics.py retired
// its "1"/"2" paper topics), so never recreate them. New 4AC1 rows land with a
// paper tag only until they are read and the apply script re-tags them.
const chapterwiseLater = code === '4AC1'
if (chapterwiseLater) console.warn('4AC1: after --execute, read the new questions and run scripts/apply_accounting_tool_topics.py --execute')
const wanted = (chapterReads ? Object.entries(staged.chapters) : chapterwiseLater ? [] : names.map((name, i) => [String(i + 1), name]))
  .map(([topicCode, name]) => ({ subject_id: subject.id, code: topicCode, name,
  description: chapterReads ? 'Specification chapter; complete questions retain all subparts and may cover several chapters.' : 'Complete questions covering this exam paper, including all subparts.' }))
  .filter(t => !topics.some(e => e.code === t.code))
console.log(`${code}: ${inserts.length} questions, ${uploads.size} PDF uploads, ${wanted.length} ${chapterReads ? 'chapters' : 'paper filters'} [${execute ? 'EXECUTE' : 'DRY RUN'}]`)
if (execute) {
  const backup = `data/backups/commerce_onboarding_${new Date().toISOString().replace(/[:.]/g, '-')}/${code}`
  await mkdir(backup, { recursive: true })
  const mirrors = []
  for (let n = 0; n < existing.length; n += 100) {
    const { data, error } = await db.from('questions').select('*').in('id', existing.slice(n, n + 100).map(p => p.id))
    if (error) throw error
    mirrors.push(...data)
  }
  await writeFile(`${backup}/before.json`, JSON.stringify({ pages: existing, questions: mirrors, topics }, null, 2))
  const r2 = new S3Client({ region: 'auto', endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
    credentials: { accessKeyId: process.env.R2_ACCESS_KEY_ID, secretAccessKey: process.env.R2_SECRET_ACCESS_KEY } })
  const entries = [...uploads], bucket = process.env.R2_BUCKET_NAME || 'grademax-papers'
  let next = 0, done = 0
  await Promise.all(Array.from({ length: 6 }, async () => {
    while (next < entries.length) {
      const [Key, Body] = entries[next++]
      await r2.send(new PutObjectCommand({ Bucket: bucket, Key, Body, ContentType: 'application/pdf' }))
      if (++done % 100 === 0) console.log(`${code}: ${done}/${entries.length} PDFs uploaded`)
    }
  }))
  // All assets are available before any question URLs are inserted.
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
  if (wanted.length) {
    const { error } = await db.from('topics').insert(wanted)
    if (error) throw error
  }
  // Keep PDF cover totals in sync with the verified question bank without a
  // schema change to the legacy pages table.
  const marksFile = chapterReads ? 'src/lib/computerScienceQuestionMarks.json' : 'src/lib/commerceQuestionMarks.json'
  let marks = {}
  try { marks = JSON.parse(await readFile(marksFile, 'utf8')) }
  catch (error) { if (error.code !== 'ENOENT') throw error }
  for (const row of rows) {
    if (Number.isInteger(row.marks) && row.marks > 0) marks[`${row.paper_id}|${row.question}`] = row.marks
  }
  await writeFile(marksFile, JSON.stringify(marks, null, 2) + '\n')
  console.log(`${code}: published ${createdIds.length} questions; backup: ${backup}`)
}
