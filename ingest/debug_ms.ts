/**
 * debug_ms.ts
 * Debug MS structure to understand format
 */

import { parsePDFFromPath, flattenTextItems } from './parse_pdf_v2.js'

const MS_PDF = './data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf'

async function debugMS() {
  console.log('🔍 Debug MS Structure\n')
  
  const result = await parsePDFFromPath(MS_PDF)
  const textItems = flattenTextItems(result)
  
  console.log(`Total text items: ${textItems.length}\n`)
  
  // Show first 100 items
  console.log('📄 First 100 text items:\n')
  for (let i = 0; i < Math.min(100, textItems.length); i++) {
    const item = textItems[i]
    const indent = ' '.repeat(Math.floor(item.x / 20))
    console.log(`[${i}] x=${item.x.toFixed(0)} y=${item.y.toFixed(0)}: ${indent}"${item.text}"`)
  }
  
  // Find patterns
  console.log('\n🔎 Looking for patterns...\n')
  
  // Question numbers
  const qNumbers = textItems.filter(item => 
    /^(\d+)\s*$/.test(item.text.trim()) && item.x < 100
  )
  console.log(`Question numbers found: ${qNumbers.length}`)
  for (const item of qNumbers.slice(0, 5)) {
    const idx = textItems.indexOf(item)
    console.log(`  "${item.text}" at index ${idx}`)
  }
  
  // Part codes
  const parts = textItems.filter(item => 
    /^\(([a-z])\)/.test(item.text.trim())
  )
  console.log(`\nPart codes found: ${parts.length}`)
  for (const item of parts.slice(0, 10)) {
    const idx = textItems.indexOf(item)
    console.log(`  "${item.text}" at index ${idx}`)
  }
  
  // Mark codes
  const markCodes = textItems.filter(item => 
    /\b[MABC]\d\b/.test(item.text)
  )
  console.log(`\nMark codes found: ${markCodes.length}`)
  for (const item of markCodes.slice(0, 10)) {
    const idx = textItems.indexOf(item)
    console.log(`  "${item.text}" at index ${idx}`)
  }
  
  // Table headers
  const headers = textItems.filter(item => 
    /Question|Answer|Mark/i.test(item.text)
  )
  console.log(`\nTable headers found: ${headers.length}`)
  for (const item of headers) {
    const idx = textItems.indexOf(item)
    console.log(`  "${item.text}" at index ${idx}`)
  }
}

debugMS().catch(console.error)
