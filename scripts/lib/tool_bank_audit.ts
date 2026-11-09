// Read-only audit helper. Dedicated subject entry points live in scripts/.
import { createClient } from '@supabase/supabase-js'
import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import * as pdfLib from 'pdf-lib'
import { assembleQuestionPdfs, questionLabel } from '../../src/lib/questionPdfAssembly'
import { getQuestionMarks } from '../../src/lib/questionMarks'

interface Paper { id: string; year: number; season: string; paper_number: string; pdf_url: string | null; markscheme_pdf_url: string | null }
interface Subject { id: string; code: string; name: string }
interface LivePage { id: string; paper_id: string; question_number: string; topics: string[]; difficulty: string | null; qp_page_url: string; ms_page_url: string }
interface Mirror { id: string; page_pdf_url: string; ms_pdf_url: string; difficulty: string | null }
interface StageRow { paper_id: string; paper: string; question: number; marks: number; topic: string; verdict: string; qp: string; ms: string }
type RecordItem = Record<string, unknown>
interface Download { pageId: string; paper?: string; question: string; kind: string; file: string; liveSha256: string; localSha256: string | null; matches: boolean }

const sha = (bytes: Uint8Array) => createHash('sha256').update(bytes).digest('hex')
const publishable = new Set(['PROVEN', 'SEQUENCE_PROVEN', 'LABEL_PROVEN', 'REVIEWED_PROVEN'])
const site = 'https://www.grademax.me'
async function get(url: string) {
  for (let i = 0; ; i++) {
    try { return await fetch(url, { signal: AbortSignal.timeout(45000) }) }
    catch (e) { if (i === 2) throw e }
  }
}
export async function auditToolBank(code: string) {
  const base = `data/analysis/live_rebuild/${code}`
  const out = `${base}/audit_2026-10-21`
  await mkdir(`${out}/live`, { recursive: true })
  const db = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!, { auth: { persistSession: false } })
  const anon = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!, { auth: { persistSession: false } })
  const query = async <T>(q: PromiseLike<{ data: T | null; error: { message: string } | null }>): Promise<T> => {
    const { data, error } = await q
    if (error) throw new Error(error.message)
    if (data === null) throw new Error('Query returned no data')
    return data
  }
  const subject = await query<Subject>(db.from('subjects').select('id,code,name').eq('code', code).single())
  if (!subject) throw new Error(`Subject ${code} not found`)
  const papers: Paper[] = await query(db.from('papers').select('id,year,season,paper_number,pdf_url,markscheme_pdf_url').eq('subject_id', subject.id))
  const ids = papers.map(p => p.id)
  const pages: LivePage[] = await query(db.from('pages').select('id,paper_id,page_number,question_number,topics,difficulty,qp_page_url,ms_page_url,is_question').in('paper_id', ids).eq('is_question', true).range(0, 9999))
  const topics: { code: string; name: string }[] = await query(db.from('topics').select('code,name').eq('subject_id', subject.id).order('code'))
  const mirrors: Mirror[] = []
  for (let i = 0; i < pages.length; i += 100) mirrors.push(...await query(db.from('questions').select('id,paper_id,question_number,difficulty,page_pdf_url,ms_pdf_url').in('id', pages.slice(i, i + 100).map(p => p.id))))
  const staged: { rows: StageRow[] } = JSON.parse(await readFile(`${base}/verdicts.json`, 'utf8'))
  const rows = staged.rows.filter(r => publishable.has(r.verdict))
  const expected = new Map(rows.map(r => [`${r.paper_id}|${r.question}`, r]))
  const reads = await readFile(`${base}/topic_reads.json`, 'utf8').then(JSON.parse).catch(() => null)
  const errors: RecordItem[] = [], downloads: Download[] = [], filters: RecordItem[] = [], http: RecordItem[] = []
  const byId = new Map(mirrors.map(m => [m.id, m]))
  const seen = new Set<string>()
  for (const page of pages) {
    const key = `${page.paper_id}|${page.question_number}`
    if (seen.has(key)) errors.push({ issue: 'duplicate live question', key })
    seen.add(key)
    const r = expected.get(key)
    if (!r) { errors.push({ issue: 'live row has no publishable staging proof', key }); continue }
    const read = reads?.[`${r.paper}|${r.question}`]
    const want = Array.isArray(read) ? read : read?.topics ?? [r.topic]
    if (JSON.stringify(page.topics) !== JSON.stringify(want)) errors.push({ issue: 'topics differ from recorded decisions', key, live: page.topics, expected: want })
    if (getQuestionMarks(page.paper_id, page.question_number) !== r.marks) errors.push({ issue: 'marks mismatch', key })
    const mirror = byId.get(page.id)
    if (!mirror || mirror.page_pdf_url !== page.qp_page_url || mirror.ms_pdf_url !== page.ms_page_url || mirror.difficulty !== page.difficulty) errors.push({ issue: 'saved-download mirror mismatch', key, pageId: page.id })
    if (!page.topics?.length || page.topics.some(t => !topics.some(a => a.code === t))) errors.push({ issue: 'missing or orphan topic', key })
  }
  for (const key of expected.keys()) if (!seen.has(key)) errors.push({ issue: 'publishable staging row absent live', key })
  await writeFile(`${out}/snapshot.json`, JSON.stringify({ subject, papers, topics, pages, mirrors }, null, 2))
  for (const topic of topics) {
    const { count, error } = await anon.from('pages').select('id', { count: 'exact', head: true }).in('paper_id', ids).eq('is_question', true).not('qp_page_url', 'is', null).overlaps('topics', [topic.code])
    const want = pages.filter(p => p.topics.includes(topic.code)).length
    filters.push({ code: topic.code, name: topic.name, expected: want, anonymousCount: count, error: error?.message })
    if (error || count !== want) errors.push({ issue: 'public filter count mismatch', topic: topic.code, count, expected: want })
  }
  for (const path of ['/test-builder', '/generate', `/api/test-builder/questions?subjectId=${subject.id}&limit=1`]) {
    const res = await get(site + path), body = await res.text()
    http.push({ path, status: res.status, url: res.url, type: res.headers.get('content-type'), body: path.includes('/api/') ? body.slice(0, 500) : undefined, includesSubject: path.includes('/api/') ? undefined : body.includes(code) })
  }
  let next = 0
  await Promise.all(Array.from({ length: 5 }, async () => {
    while (next < pages.length) {
      const page = pages[next++], r = expected.get(`${page.paper_id}|${page.question_number}`)
      for (const kind of ['qp', 'ms'] as const) {
        const url = kind === 'qp' ? page.qp_page_url : page.ms_page_url
        const file = `${out}/live/${page.id}_${kind}.pdf`
        try {
          const res = await get(url)
          if (!res.ok) throw new Error(`HTTP ${res.status}`)
          const bytes = new Uint8Array(await res.arrayBuffer())
          if (!Buffer.from(bytes.subarray(0, 5)).equals(Buffer.from('%PDF-'))) throw new Error('not a PDF')
          await writeFile(file, bytes)
          const localSha256 = r ? sha(await readFile(r[kind])) : null
          const liveSha256 = sha(bytes)
          downloads.push({ pageId: page.id, paper: r?.paper, question: page.question_number, kind, file, liveSha256, localSha256, matches: liveSha256 === localSha256 })
          if (liveSha256 !== localSha256) errors.push({ issue: 'live PDF differs from staged PDF', pageId: page.id, kind })
        } catch (e) { errors.push({ issue: 'PDF download failed', pageId: page.id, kind, detail: String(e) }) }
      }
      if (downloads.length % 100 === 0) console.log(`${code}: ${downloads.length} PDFs downloaded`)
    }
  }))
  const sample: LivePage[] = []
  for (const topic of topics) {
    const p = pages.find(p => p.topics.includes(topic.code) && !sample.some(s => s.id === p.id))
    if (p) sample.push(p)
  }
  // Use both papers even when chapter order yields a sample from only Paper 1.
  for (const n of ['1', '2']) {
    const p = pages.find(p => papers.find(a => a.id === p.paper_id)?.paper_number === n && !sample.some(s => s.id === p.id))
    if (p) sample.push(p)
  }
  const assembled: RecordItem = {}
  for (const kind of ['worksheet', 'markscheme'] as const) {
    const doc = await pdfLib.PDFDocument.create()
    const sources = sample.map((p, i) => { const paper = papers.find(r => r.id === p.paper_id)!; return { url: `${out}/live/${p.id}_${kind === 'worksheet' ? 'qp' : 'ms'}.pdf`, label: questionLabel(i + 1, { questionNumber: p.question_number, year: paper.year, season: paper.season, paper: paper.paper_number }) } })
    const result = await assembleQuestionPdfs(doc, pdfLib, sources, kind, async file => { const b = await readFile(file); return new Uint8Array(b).buffer })
    await writeFile(`${out}/assembled-${kind}.pdf`, await doc.save())
    assembled[kind] = { ...result, questions: sample.length, pages: doc.getPageCount() }
    if (result.placeholders || result.merged !== sample.length) errors.push({ issue: 'assembly incomplete', kind, result })
  }
  // Exercise production test-builder PDF generation without creating a saved test.
  for (const type of ['worksheet', 'markscheme']) {
    const selected = ['1', '2'].map(n => sample.find(p => papers.find(r => r.id === p.paper_id)?.paper_number === n)).filter((p): p is LivePage => !!p)
    const res = await fetch(site + '/api/test-builder/generate', { method: 'POST', signal: AbortSignal.timeout(90000), headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: `${code} audit`, type, subjectName: subject.name, level: 'IGCSE', totalMarks: selected.reduce((n, p) => n + (getQuestionMarks(p.paper_id, p.question_number) || 4), 0), pages: selected.map(p => { const paper = papers.find(r => r.id === p.paper_id)!; return { qpPageUrl: p.qp_page_url, msPageUrl: p.ms_page_url, questionNumber: p.question_number, year: paper.year, season: paper.season, paper: paper.paper_number } }) }) })
    const bytes = new Uint8Array(await res.arrayBuffer())
    http.push({ path: '/api/test-builder/generate', type, status: res.status, contentType: res.headers.get('content-type'), bytes: bytes.length })
    if (res.ok) await writeFile(`${out}/production-${type}.pdf`, bytes)
  }
  const result = { checkedAt: new Date().toISOString(), code, questions: pages.length, publishableStagedQuestions: rows.length, mirrors: mirrors.length, filters, http, downloads, assembled, sample: sample.map(p => p.id), errors }
  await writeFile(`${out}/live-audit.json`, JSON.stringify(result, null, 2) + '\n')
  console.log(JSON.stringify({ code, questions: pages.length, pdfs: downloads.length, matched: downloads.filter(d => d.matches).length, filters, assembled, http, errors }, null, 2))
}
