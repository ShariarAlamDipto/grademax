/**
 * extract_questions.ts
 * Usage: ts-node ingest/extract_questions.ts input.pdf meta.json
 * meta.json should contain: {"subject_id":1,"year":2019,"session":"Jun","paper_code":"4PH1/1P"}
 */
import fs from 'fs'
import path from 'path'
import pdf from 'pdf-parse'

interface Meta { subject_id: number; year: number; session: string; paper_code: string }
interface ExtractedQuestion {
  question_number: string
  marks: number
  text: string
  page: number
}

function splitQuestions(pages: string[]): ExtractedQuestion[] {
  const results: ExtractedQuestion[] = []
  const qRegex = /(Q\d+)([\s\S]*?)(?=\nQ\d+|$)/g
  const markRegex = /\[(\d+) *marks?\]/i

  for (let i = 0; i < pages.length; i++) {
    const page = pages[i]
    let match: RegExpExecArray | null
    while ((match = qRegex.exec(page)) !== null) {
      const full = match[0]
      const qNum = match[1]
      const markMatch = full.match(markRegex)
      const marks = markMatch ? parseInt(markMatch[1], 10) : 1
      const cleaned = full.replace(/\s+/g, ' ').trim()
      results.push({ question_number: qNum, marks, text: cleaned, page: i + 1 })
    }
  }
  return results
}

async function main() {
  const pdfPath = process.argv[2]
  const metaPath = process.argv[3]
  if (!pdfPath || !metaPath) {
    console.error('Usage: ts-node ingest/extract_questions.ts input.pdf meta.json')
    process.exit(1)
  }
  const meta: Meta = JSON.parse(fs.readFileSync(metaPath, 'utf-8'))
  const data = await pdf(fs.readFileSync(pdfPath))
  const pages = data.text.split('\f').map((p: string) => p.trim()).filter(Boolean)
  const questions = splitQuestions(pages)
  const out = {
    meta,
    questions,
  }
  const outFile = path.join(path.dirname(pdfPath), meta.paper_code.replace(/\W+/g, '_') + '_questions.json')
  fs.writeFileSync(outFile, JSON.stringify(out, null, 2))
  console.log('Extracted', questions.length, 'questions ->', outFile)
}

main().catch(e => { console.error(e); process.exit(1) })
