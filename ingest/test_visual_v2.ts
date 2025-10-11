/**
 * test_visual_v2.ts
 * Test the hybrid visual extraction approach
 */
import fs from 'fs'
import { extractAllVisualCrops, savePagePngs } from './visual_extract_v2.js'

async function main() {
  const pdfPath = process.argv[2] || './data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P.pdf'
  
  if (!fs.existsSync(pdfPath)) {
    console.error(`File not found: ${pdfPath}`)
    process.exit(1)
  }
  
  console.log(`📄 Testing visual extraction V2: ${pdfPath}\n`)
  
  const pdfBuffer = fs.readFileSync(pdfPath)
  
  // Test 1: Save full page PNGs for verification
  console.log('Test 1: Rendering full pages...')
  const pagesDir = './data/pages_test'
  await savePagePngs(pdfBuffer, pagesDir, 150) // Lower DPI for testing
  console.log(`✅ Check ${pagesDir}/ for page renders\n`)
  
  // Test 2: Extract visual crops
  console.log('Test 2: Extracting question crops...')
  const crops = await extractAllVisualCrops(pdfBuffer, 300)
  
  // Save crops
  const cropsDir = './data/crops_test_v2'
  if (!fs.existsSync(cropsDir)) {
    fs.mkdirSync(cropsDir, { recursive: true })
  }
  
  console.log(`\n📸 Saving crops...`)
  for (let i = 0; i < Math.min(5, crops.length); i++) {
    const crop = crops[i]
    const filename = `${cropsDir}/question_${crop.questionNumber}.png`
    fs.writeFileSync(filename, crop.crop.pngBuffer)
    console.log(`  💾 ${filename}`)
    console.log(`     Size: ${crop.crop.width}x${crop.crop.height}px`)
    console.log(`     Hash: ${crop.crop.visualHash.substring(0, 16)}...`)
    console.log(`     File: ${(crop.crop.pngBuffer.length / 1024).toFixed(1)} KB`)
  }
  
  if (crops.length > 5) {
    console.log(`  ... and ${crops.length - 5} more crops`)
  }
  
  console.log(`\n✅ Test complete!`)
  console.log(`   Pages: ${pagesDir}/`)
  console.log(`   Crops: ${cropsDir}/`)
  console.log(`\n📊 Summary:`)
  console.log(`   Total crops: ${crops.length}`)
  console.log(`   Avg file size: ${(crops.reduce((sum, c) => sum + c.crop.pngBuffer.length, 0) / crops.length / 1024).toFixed(1)} KB`)
}

main().catch(console.error)
