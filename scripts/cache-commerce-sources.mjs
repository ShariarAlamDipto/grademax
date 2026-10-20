// Cache the exact live paper rows and source PDFs for offline staging.
// Run with node --env-file=.env.local scripts/cache-commerce-sources.mjs.
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { createClient } from '@supabase/supabase-js'
import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3'

const db = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY)
const r2 = new S3Client({
  region: 'auto', endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
  credentials: { accessKeyId: process.env.R2_ACCESS_KEY_ID, secretAccessKey: process.env.R2_SECRET_ACCESS_KEY },
})
const prefix = process.env.NEXT_PUBLIC_R2_PUBLIC_URL.replace(/\/$/, '') + '/'
const bucket = process.env.R2_BUCKET_NAME || 'grademax-papers'

const requested = process.argv.indexOf('--subject')
const codes = requested < 0 ? ['4AC1', '4BS1', '4EC1'] : [process.argv[requested + 1]]
if (codes.some(code => !['4AC1', '4BS1', '4EC1', '4CP1'].includes(code))) throw new Error('Unsupported subject')
for (const code of codes) {
  const { data: subject, error } = await db.from('subjects').select('id').eq('code', code).single()
  if (error) throw error
  const { data: papers, error: paperError } = await db.from('papers')
    .select('id,year,season,paper_number,pdf_url,markscheme_pdf_url').eq('subject_id', subject.id)
  if (paperError) throw paperError
  const base = `data/analysis/live_rebuild/${code}`
  await mkdir(`${base}/sources`, { recursive: true })
  await writeFile(`${base}/papers.json`, JSON.stringify(papers, null, 2))
  const tasks = papers.flatMap(p => [
    { url: p.pdf_url, file: `${base}/sources/${p.year}_${p.season}_P${p.paper_number}_qp.pdf` },
    { url: p.markscheme_pdf_url, file: `${base}/sources/${p.year}_${p.season}_P${p.paper_number}_ms.pdf` },
  ]).filter(t => t.url)
  let next = 0, done = 0
  await Promise.all(Array.from({ length: 8 }, async () => {
    while (next < tasks.length) {
      const task = tasks[next++]
      if (!task.url.startsWith(prefix)) throw new Error('Unexpected PDF storage host')
      if (existsSync(task.file) && (await readFile(task.file)).subarray(0, 5).toString() === '%PDF-') {
        done++
        continue
      }
      const result = await r2.send(new GetObjectCommand({ Bucket: bucket, Key: task.url.slice(prefix.length) }))
      const bytes = Buffer.from(await result.Body.transformToByteArray())
      if (bytes.subarray(0, 5).toString() !== '%PDF-') throw new Error('Source is not a PDF')
      await writeFile(task.file, bytes)
      done++
      if (done % 20 === 0) console.log(`${code}: ${done}/${tasks.length} source PDFs cached`)
    }
  }))
  console.log(`${code}: ${papers.length} live papers cached`)
}
