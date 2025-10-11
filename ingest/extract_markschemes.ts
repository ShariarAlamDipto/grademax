/**
 * extract_markschemes.ts
 * Usage: ts-node ingest/extract_markschemes.ts markscheme.pdf meta.json
 * Extracts markscheme text and aligns by question_number
 */
import fs from 'fs'
import path from 'path'
import pdf from 'pdf-parse'

interface Meta { paper_code: string }
interface ExtractedMS { question_number: string; text: string; page: number }

function splitMarkscheme(pages: string[]): ExtractedMS[] {
  const results: ExtractedMS[] = []
  const qRegex = /(Q\d+[\s\S]*?)(?=\nQ\d+|$)/g

  for (let i = 0; i < pages.length; i++) {
    const page = pages[i]
    let match: RegExpExecArray | null
    while ((match = qRegex.exec(page)) !== null) {
      const full = match[0]
      const qNum = match[1].split(/\s/)[0]
      const cleaned = full.replace(/\s+/g, ' ').trim()
      results.push({ question_number: qNum, text: cleaned, page: i + 1 })
    }
  }
  return results
}

async function main() {
  const pdfPath = process.argv[2]
  const metaPath = process.argv[3]
  if (!pdfPath || !metaPath) {
    console.error('Usage: ts-node ingest/extract_markschemes.ts markscheme.pdf meta.json')
    process.exit(1)
  }
  const meta: Meta = JSON.parse(fs.readFileSync(metaPath, 'utf-8'))
  const data = await pdf(fs.readFileSync(pdfPath))
  const pages = data.text.split('\f').map((p: string) => p.trim()).filter(Boolean)
  const markschemes = splitMarkscheme(pages)
  const out = { meta, markschemes }
  const outFile = path.join(path.dirname(pdfPath), meta.paper_code.replace(/\W+/g, '_') + '_markschemes.json')
  fs.writeFileSync(outFile, JSON.stringify(out, null, 2))
  console.log('Extracted', markschemes.length, 'markschemes ->', outFile)
}

main().catch(e => { console.error(e); process.exit(1) })
