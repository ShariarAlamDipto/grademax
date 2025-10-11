/**
 * test_hybrid.ts
 * Test the hybrid extraction approach
 */
import { extractAllQuestionParts } from './visual_extract_hybrid.js'
import fs from 'fs'

async function main() {
  const pdfPath = process.argv[2] || './data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf'
  
  if (!fs.existsSync(pdfPath)) {
    console.error(`File not found: ${pdfPath}`)
    process.exit(1)
  }
  
  console.log(`📄 Testing HYBRID extraction: ${pdfPath}\n`)
  
  const pdfBuffer = fs.readFileSync(pdfPath)
  const parts = await extractAllQuestionParts(pdfBuffer, 300)
  
  // Save crops
  const cropsDir = './data/crops_hybrid'
  if (!fs.existsSync(cropsDir)) {
    fs.mkdirSync(cropsDir, { recursive: true })
  }
  
  console.log(`\n📸 Saving ${parts.length} crops...`)
  for (const part of parts) {
    const filename = `${cropsDir}/question_${part.questionNumber.replace(/[()]/g, '_')}.png`
    fs.writeFileSync(filename, part.crop.pngBuffer)
  }
  
  console.log(`  ✓ Saved to ${cropsDir}/`)
  
  // Show summary
  console.log(`\n📊 Summary:`)
  console.log(`   Total parts: ${parts.length}`)
  console.log(`   Avg file size: ${(parts.reduce((sum, p) => sum + p.crop.pngBuffer.length, 0) / parts.length / 1024).toFixed(1)} KB`)
  console.log(`   With marks: ${parts.filter(p => p.marks).length}`)
  
  // Show first 10
  console.log(`\n📋 First 10 parts:`)
  parts.slice(0, 10).forEach(p => {
    console.log(`   ${p.questionNumber.padEnd(12)} [${p.marks || '?'}] Page ${p.bbox.page} ${(p.crop.pngBuffer.length / 1024).toFixed(1)} KB`)
  })
}

main().catch(console.error)
