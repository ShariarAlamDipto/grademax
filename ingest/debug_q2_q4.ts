/**
 * Debug script to find Questions 2 and 4 in the PDF
 */
import fs from 'fs'
import pdf from 'pdf-parse'

async function main() {
  const pdfPath = './data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf'
  const buffer = fs.readFileSync(pdfPath)
  const data = await pdf(buffer)
  
  const lines = data.text.split('\n')
  
  console.log('🔍 Searching for Question 2...')
  lines.forEach((line, i) => {
    const trimmed = line.trim()
    if (trimmed.startsWith('2 ') || trimmed === '2') {
      console.log(`  Line ${i}: "${line.substring(0, 100)}"`)
    }
  })
  
  console.log('\n🔍 Searching for Question 4...')
  lines.forEach((line, i) => {
    const trimmed = line.trim()
    if (trimmed.startsWith('4 ') || trimmed === '4') {
      console.log(`  Line ${i}: "${line.substring(0, 100)}"`)
    }
  })
}

main()
