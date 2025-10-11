/**
 * debug_pdf.ts
 * Show raw text from PDF to understand format
 */
import fs from 'fs'
import pdf from 'pdf-parse'

async function main() {
  const pdfPath = process.argv[2] || './data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf'
  
  if (!fs.existsSync(pdfPath)) {
    console.error(`File not found: ${pdfPath}`)
    process.exit(1)
  }
  
  console.log(`Reading: ${pdfPath}\n`)
  
  const dataBuffer = fs.readFileSync(pdfPath)
  const data = await pdf(dataBuffer)
  
  const lines = data.text.split('\n')
  
  console.log('='.repeat(80))
  console.log('LINES 80-200 (WHERE QUESTIONS START):')
  console.log('='.repeat(80))
  lines.slice(80, 200).forEach((line, i) => {
    console.log(`${String(80+i+1).padStart(3)}: ${line}`)
  })
  
  console.log('\n' + '='.repeat(80))
  console.log('SEARCHING FOR QUESTION PATTERNS:')
  console.log('='.repeat(80))
  const questionPattern = /^(\d{1,2})\s+[A-Z]/
  lines.forEach((line, i) => {
    if (questionPattern.test(line.trim())) {
      console.log(`Line ${i + 1}: "${line.trim()}"`)
    }
  })
}

main().catch(console.error)
