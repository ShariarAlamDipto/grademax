/**
 * debug_format.ts
 * Debug format detection
 */

import { parsePDFFromPath, flattenTextItems } from './parse_pdf_v2.js'

const MS_PDF = './data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf'

async function debugFormat() {
  console.log('🔍 Debug Format Detection\n')
  
  const result = await parsePDFFromPath(MS_PDF)
  const textItems = flattenTextItems(result)
  const sample = textItems.slice(0, 200)
  
  console.log(`Sample size: ${sample.length} items\n`)
  
  // Check table headers
  console.log('🔎 Checking for table headers...\n')
  for (let i = 0; i < sample.length; i++) {
    const item = sample[i]
    if (/^Question\s*$/i.test(item.text.trim())) {
      console.log(`Found "Question" at index ${i}`)
      // Check nearby items
      const nearby = sample.slice(Math.max(0, i - 5), Math.min(sample.length, i + 5))
      console.log('Nearby items:')
      for (const n of nearby) {
        const idx = textItems.indexOf(n)
        console.log(`  [${idx}] "${n.text}"`)
      }
      
      const hasAnswer = nearby.some(n => /^Answer\s*$/i.test(n.text.trim()))
      const hasMarks = nearby.some(n => /^Marks?\s*$/i.test(n.text.trim()))
      console.log(`  Has "Answer": ${hasAnswer}`)
      console.log(`  Has "Marks": ${hasMarks}`)
      console.log()
    }
  }
  
  // Check list format
  console.log('🔎 Checking for list format...\n')
  const qNumbers = sample.filter(item => 
    /^(\d+)\s*$/.test(item.text.trim()) && item.x < 100
  )
  console.log(`Question numbers at left: ${qNumbers.length}`)
  for (const item of qNumbers) {
    const idx = textItems.indexOf(item)
    console.log(`  [${idx}] "${item.text}" at x=${item.x}`)
  }
  
  const partCodes = sample.filter(item =>
    /^\([a-z]\)\s*$/.test(item.text.trim()) || /^\([ivx]+\)\s*$/.test(item.text.trim())
  )
  console.log(`\nPart codes: ${partCodes.length}`)
  for (const item of partCodes.slice(0, 10)) {
    const idx = textItems.indexOf(item)
    console.log(`  [${idx}] "${item.text}" at x=${item.x}`)
  }
  
  // Determine format
  console.log('\n🎯 Format Decision:')
  if (qNumbers.length >= 3 && partCodes.length >= 5) {
    console.log('  → LIST FORMAT')
  } else {
    console.log('  → Unknown/Other')
  }
}

debugFormat().catch(console.error)
