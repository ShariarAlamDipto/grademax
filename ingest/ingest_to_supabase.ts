/**
 * ingest_to_supabase.ts
 * Takes a questions JSON (from extract_questions.ts) and inserts
 * paper + questions + naive topic tagging + markscheme placeholder.
 */
import fs from 'fs'
import path from 'path'
import { createClient } from '@supabase/supabase-js'
import yaml from 'yaml'

interface QuestionJSON {
  meta: { subject_id: number; year: number; session: string; paper_code: string }
  questions: Array<{ question_number: string; marks: number; text: string; page: number }>
}

interface TopicIndexRecord { id: number; name: string; vector: number[]; subject_id: number }

function cosine(a: number[], b: number[]) {
  let dot = 0, na = 0, nb = 0
  for (let i = 0; i < a.length; i++) { dot += a[i] * b[i]; na += a[i]*a[i]; nb += b[i]*b[i] }
  return dot / (Math.sqrt(na) * Math.sqrt(nb) + 1e-9)
}

async function main() {
  const file = process.argv[2]
  if (!file) { console.error('Usage: ts-node ingest/ingest_to_supabase.ts questions.json'); process.exit(1) }
  const data: QuestionJSON = JSON.parse(fs.readFileSync(file, 'utf-8'))

  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )

  // Upsert paper
  const { data: paperRow, error: pErr } = await supabase
    .from('papers')
    .upsert({
      subject_id: data.meta.subject_id,
      year: data.meta.year,
      session: data.meta.session,
      paper_code: data.meta.paper_code,
    }, { onConflict: 'subject_id,year,session,paper_code' })
    .select('id')
    .single()
  if (pErr) throw pErr

  // Load topic index
  const idxPath = path.join(__dirname, 'topic_index.json')
  const idx = JSON.parse(fs.readFileSync(idxPath, 'utf-8')) as { topics: TopicIndexRecord[] }

  // Optional synonyms boost
  let synonyms: Record<string, string[]> = {}
  const synPath = path.join(__dirname, 'synonyms.yml')
  if (fs.existsSync(synPath)) {
    synonyms = yaml.parse(fs.readFileSync(synPath, 'utf-8')) || {}
  }

  for (const q of data.questions) {
    // Insert question
    const { data: qRow, error: qErr } = await supabase
      .from('questions')
      .insert({
        paper_id: paperRow.id,
        question_number: q.question_number,
        marks: q.marks,
        text: q.text,
        page: q.page,
        difficulty: q.marks <= 2 ? 1 : q.marks <= 4 ? 2 : 3,
      })
      .select('id,text')
      .single()
    if (qErr) { console.error('Question insert failed', q.question_number, qErr.message); continue }

    // Embed question? (Simplified: average word hashing placeholder) — replace with real embedding reuse.
    const words = q.text.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean)
    const vec = new Array(idx.topics[0].vector.length).fill(0)
    for (const w of words.slice(0, 64)) {
      const h = [...w].reduce((acc, c) => acc + c.charCodeAt(0), 0)
      vec[h % vec.length] += 1
    }

    // Score similarity
    const scored = idx.topics.map(t => ({ t, score: cosine(vec, t.vector) }))
      .sort((a,b) => b.score - a.score)
      .slice(0, 3)

    for (const s of scored) {
      const synBoost = Object.entries(synonyms).some(([topicName, list]) =>
        topicName === s.t.name && list.some(kw => q.text.toLowerCase().includes(kw.toLowerCase()))
      ) ? 0.1 : 0
      const confidence = Math.min(1, s.score + synBoost)
      if (confidence < 0.35) continue
      await supabase.from('question_topics').insert({
        question_id: qRow.id,
        topic_id: s.t.id,
        confidence,
      })
    }
  }
  console.log('Ingestion complete.')
}

main().catch(e => { console.error(e); process.exit(1) })
