/**
 * build_topic_index.ts
 * 1. Fetch topics from Supabase (id, name, content)
 * 2. Generate sentence embeddings for each topic.content
 * 3. Write to ingest/topic_index.json for reuse in auto-tagging
 */
import fs from 'fs'
import path from 'path'
import { createClient } from '@supabase/supabase-js'
import { pipeline } from '@xenova/transformers'

async function main() {
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )

  const { data: topics, error } = await supabase
    .from('topics')
    .select('id,name,content,subject_id')
    .order('id')

  if (error) throw error
  if (!topics || topics.length === 0) {
    console.error('No topics found. Seed the topics table first.')
    process.exit(1)
  }

  type Embedder = (text: string) => Promise<{ data: number[][] }>
  const embedder = (await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2')) as unknown as Embedder

  interface TopicRecord { id: number; subject_id: number; name: string; vector: number[] }
  const records: TopicRecord[] = []
  for (const t of topics) {
    const text = (t.content || t.name).slice(0, 1000)
    const output = await embedder(text)
    // Average pool token embeddings
    const vector = Array.from(
      (output.data as number[][])?.reduce((acc, row) => {
        row.forEach((v, i) => (acc[i] = (acc[i] || 0) + v))
        return acc
      }, [] as number[])
    ).map(v => v / output.data.length)

    records.push({ id: t.id, subject_id: t.subject_id, name: t.name, vector })
    console.log('Embedded topic', t.id, t.name)
  }

  const outPath = path.join(__dirname, 'topic_index.json')
  fs.writeFileSync(outPath, JSON.stringify({ created_at: new Date().toISOString(), topics: records }))
  console.log('Wrote', outPath)
}

main().catch(e => {
  console.error(e)
  process.exit(1)
})
