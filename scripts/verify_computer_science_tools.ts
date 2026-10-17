// Read-only live verification plus PDFs assembled with the application's code.
// npx tsx --env-file=.env.local scripts/verify_computer_science_tools.ts
import assert from 'node:assert/strict'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { createClient } from '@supabase/supabase-js'
import * as pdfLib from 'pdf-lib'
import { assembleQuestionPdfs, questionLabel } from '../src/lib/questionPdfAssembly'
import { getQuestionMarks } from '../src/lib/questionMarks'

interface LivePage {
  id: string
  paper_id: string
  question_number: string
  topics: string[]
  difficulty: string
  qp_page_url: string
  ms_page_url: string
}

async function main() {
const base = 'data/analysis/live_rebuild/4CP1'
const sha = (bytes: Uint8Array) => createHash('sha256').update(bytes).digest('hex')
const staged = JSON.parse(await readFile(`${base}/verdicts.json`, 'utf8'))
const reads = JSON.parse(await readFile(`${base}/topic_reads.json`, 'utf8'))
const db = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!)
const { data: subject, error: subjectError } = await db.from('subjects').select('id').eq('code', '4CP1').single()
if (subjectError) throw subjectError
const { data: papers, error: paperError } = await db.from('papers').select('id,year,season,paper_number').eq('subject_id', subject.id)
if (paperError) throw paperError
const { data: pageRows, error: pageError, count } = await db.from('pages').select('*', { count: 'exact' }).in('paper_id', papers.map(p => p.id)).eq('is_question', true)
if (pageError) throw pageError
const pages = pageRows as LivePage[]
assert.equal(count, staged.rows.length)
assert.equal(pages.length, count)
const { data: mirrors, error: mirrorError } = await db.from('questions').select('*').in('id', pages.map(p => p.id))
if (mirrorError) throw mirrorError
assert.equal(mirrors.length, pages.length)
const byId = new Map(mirrors.map(m => [m.id, m]))
const expected = new Map(staged.rows.map((r: {paper_id: string; question: number}) => [`${r.paper_id}|${r.question}`, r]))
const bodies = new Map<string, ArrayBuffer>()
let downloaded = 0
let next = 0
await Promise.all(Array.from({ length: 4 }, async () => {
  while (next < pages.length) {
    const page = pages[next++]
    const row = expected.get(`${page.paper_id}|${page.question_number}`) as {paper: string; question: number; marks: number; qp: string; ms: string}
    assert.ok(row)
    const read = reads[`${row.paper}|${row.question}`]
    assert.deepEqual(page.topics, read.topics)
    assert.equal(page.difficulty, read.difficulty)
    assert.equal(getQuestionMarks(page.paper_id, page.question_number), row.marks)
    const mirror = byId.get(page.id)!
    assert.equal(mirror.page_pdf_url, page.qp_page_url)
    assert.equal(mirror.ms_pdf_url, page.ms_page_url)
    assert.equal(mirror.difficulty, page.difficulty)
    for (const [kind, url] of [['qp', page.qp_page_url], ['ms', page.ms_page_url]]) {
      let body: ArrayBuffer | undefined
      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          const response = await fetch(url, { signal: AbortSignal.timeout(60000) })
          if (!response.ok) throw new Error(`PDF HTTP ${response.status}`)
          body = await response.arrayBuffer()
          break
        } catch (error) { if (attempt === 2) throw error }
      }
      assert.ok(body)
      assert.equal(sha(new Uint8Array(body)), sha(await readFile(kind === 'qp' ? row.qp : row.ms)))
      bodies.set(url, body)
      downloaded++
    }
  }
}))

const anon = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!)
const { data: topics, error: topicError } = await anon.from('topics').select('code,name').eq('subject_id', subject.id).order('code')
if (topicError) throw topicError
assert.deepEqual(topics.map(t => [t.code, t.name]), Object.entries(staged.chapters))
const chapterCounts: Record<string, number> = {}
const sample: typeof pages = []
for (const topic of topics) {
  const chapterQuery = await anon.from('pages').select('id', { count: 'exact' })
    .in('paper_id', papers.map(p => p.id)).eq('is_question', true).not('qp_page_url', 'is', null).overlaps('topics', [topic.code])
  if (chapterQuery.error) throw chapterQuery.error
  const matchedCount: number = chapterQuery.count || 0
  assert.equal(matchedCount, pages.filter(p => p.topics.includes(topic.code)).length)
  assert.ok(matchedCount > 0)
  chapterCounts[topic.code] = matchedCount
  sample.push(pages.find(p => p.topics.includes(topic.code) && !sample.some(s => s.id === p.id))!)
}
assert.ok(sample.every(Boolean))
const difficultyCounts: Record<string, number> = {}
for (const difficulty of ['easy', 'medium', 'hard']) {
  const difficultyQuery = await anon.from('pages').select('id', { count: 'exact', head: true })
    .in('paper_id', papers.map(p => p.id)).eq('is_question', true).eq('difficulty', difficulty)
  if (difficultyQuery.error) throw difficultyQuery.error
  const matchedCount: number = difficultyQuery.count || 0
  assert.equal(matchedCount, pages.filter(p => p.difficulty === difficulty).length)
  difficultyCounts[difficulty] = matchedCount
}

await mkdir(`${base}/smoke`, { recursive: true })
const assembled = {}
for (const kind of ['worksheet', 'markscheme'] as const) {
  const doc = await pdfLib.PDFDocument.create()
  const sources = sample.map((page, index) => {
    const paper = papers.find(p => p.id === page.paper_id)!
    return { url: kind === 'worksheet' ? page.qp_page_url : page.ms_page_url,
      label: questionLabel(index + 1, { questionNumber: page.question_number, year: paper.year, season: paper.season, paper: paper.paper_number }) }
  })
  const result = await assembleQuestionPdfs(doc, pdfLib, sources, kind, async url => bodies.get(url) || null)
  assert.equal(result.placeholders, 0)
  assert.equal(result.merged, 6)
  await writeFile(`${base}/smoke/computer-science-${kind}.pdf`, await doc.save())
  Object.assign(assembled, { [kind]: { ...result, pages: doc.getPageCount() } })
}
const result = { questions: pages.length, mirrors: mirrors.length, chapters: chapterCounts,
  difficulties: difficultyCounts, publicPdfsVerified: downloaded, assembled, failures: [] }
await writeFile(`${base}/live_publication_audit.json`, JSON.stringify(result, null, 2) + '\n')
console.log(JSON.stringify(result, null, 2))
}

main().catch(error => { console.error(error); process.exitCode = 1 })
