/**
 * test_visual_extract.ts
 * Test visual crop extraction
 */
import fs from 'fs'
import { extractAllVisualCrops } from './visual_extract.js'

async function main() {
  const pdfPath = process.argv[2] || './data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf'
  
  if (!fs.existsSync(pdfPath)) {
    console.error(`File not found: ${pdfPath}`)
    process.exit(1)
  }
  
  console.log(`📄 Extracting visual crops from: ${pdfPath}\n`)
  
  const pdfBuffer = fs.readFileSync(pdfPath)
  const crops = await extractAllVisualCrops(pdfBuffer, 300)
  
  console.log(`✅ Extracted ${crops.length} question crops\n`)
  
  // Save first few crops for verification
  const outputDir = './data/crops_test'
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true })
  }
  
  for (let i = 0; i < Math.min(3, crops.length); i++) {
    const crop = crops[i]
    const filename = `${outputDir}/question_${crop.questionNumber}.png`
    fs.writeFileSync(filename, crop.crop.pngBuffer)
    console.log(`💾 Saved: ${filename}`)
    console.log(`   Size: ${crop.crop.width}x${crop.crop.height}px`)
    console.log(`   Hash: ${crop.crop.visualHash.substring(0, 16)}...`)
    console.log(`   File size: ${(crop.crop.pngBuffer.length / 1024).toFixed(1)} KB\n`)
  }
  
  console.log(`\n✅ Test complete! Check ${outputDir}/ for visual crops`)
}

main().catch(console.error)
