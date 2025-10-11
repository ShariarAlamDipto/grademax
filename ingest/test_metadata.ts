/**
 * Test script for metadata detection
 */

import { detectMetadata } from './metadata'
import { parsePDFFromPath } from './parse_pdf_v2'
import * as fs from 'fs'
import * as path from 'path'

async function testMetadata() {
  console.log('🧪 Testing Metadata Detection\n')
  console.log('=' .repeat(80))
  
  // Test PDF path
  const pdfPath = path.join(process.cwd(), 'data', 'raw', 'IGCSE', '4PH1', '2019', 'Jun', '4PH1_1P.pdf')
  
  if (!fs.existsSync(pdfPath)) {
    console.error('❌ Test PDF not found:', pdfPath)
    console.log('Please ensure 4PH1_1P.pdf is in the data/raw directory')
    return
  }
  
  console.log(`\n📄 Testing with: ${path.basename(pdfPath)}`)
  console.log('=' .repeat(80))
  
  // Parse first page for content detection
  console.log('\n1️⃣ Parsing first page...')
  const parsed = await parsePDFFromPath(pdfPath)
  const firstPageText = parsed.pages[0]?.textItems.map(t => t.text).join(' ') || ''
  console.log(`  ✓ Extracted ${firstPageText.length} chars from page 1`)
  
  // Detect metadata
  console.log('\n2️⃣ Detecting metadata...')
  const metadata = detectMetadata(pdfPath, firstPageText)
  
  // Display results
  console.log('\n' + '=' .repeat(80))
  console.log('📊 METADATA RESULTS')
  console.log('=' .repeat(80))
  
  console.log('\n🎯 Core Information:')
  console.log(`  Board:          ${metadata.board}`)
  console.log(`  Level:          ${metadata.level}`)
  console.log(`  Subject:        ${metadata.subjectName} (${metadata.subjectCode})`)
  console.log(`  Paper Type:     ${metadata.paperType}`)
  console.log(`  Paper Number:   ${metadata.paperNumber}`)
  console.log(`  Variant:        ${metadata.variant}`)
  
  console.log('\n📅 Temporal Information:')
  console.log(`  Year:           ${metadata.year}`)
  console.log(`  Season:         ${metadata.season}`)
  
  console.log('\n🔧 Technical Information:')
  console.log(`  Detected From:  ${metadata.detectedFrom}`)
  console.log(`  Confidence:     ${(metadata.confidence * 100).toFixed(1)}%`)
  console.log(`  Canonical Key:  ${metadata.canonicalKey}`)
  console.log(`  Doc Hash:       ${metadata.docHash}`)
  
  // Validation
  console.log('\n' + '=' .repeat(80))
  console.log('✅ VALIDATION')
  console.log('=' .repeat(80))
  
  const checks = [
    { name: 'Board detected', pass: metadata.board !== 'Unknown' },
    { name: 'Level detected', pass: metadata.level !== 'Unknown' },
    { name: 'Subject detected', pass: metadata.subjectName !== 'Unknown' },
    { name: 'Subject code detected', pass: metadata.subjectCode !== 'Unknown' },
    { name: 'Year is valid', pass: metadata.year >= 2010 && metadata.year <= 2030 },
    { name: 'Season detected', pass: metadata.season !== 'Unknown' },
    { name: 'Confidence above 50%', pass: metadata.confidence > 0.5 },
    { name: 'Canonical key formed', pass: metadata.canonicalKey.length > 0 }
  ]
  
  let passCount = 0
  for (const check of checks) {
    const status = check.pass ? '✅' : '❌'
    console.log(`  ${status} ${check.name}`)
    if (check.pass) passCount++
  }
  
  console.log(`\n📈 Score: ${passCount}/${checks.length} checks passed (${((passCount / checks.length) * 100).toFixed(0)}%)`)
  
  // Test with multiple filenames
  console.log('\n' + '=' .repeat(80))
  console.log('🧪 FILENAME PATTERN TESTS')
  console.log('=' .repeat(80))
  
  const testFilenames = [
    '4PH1_1P_Jun_2019.pdf',
    '4PH1_1P_MS_Jun_2019.pdf',
    '0625_s19_qp_11.pdf',
    '0625_s19_ms_11.pdf',
    '8463-1H-QP-JUN19.pdf',
    '8463-1H-MS-JUN19.pdf',
    '9702_w20_qp_42.pdf',
    '4CH1_2CR_May_2021.pdf'
  ]
  
  console.log('\nTesting various filename patterns:\n')
  
  for (const filename of testFilenames) {
    const testPath = path.join(process.cwd(), 'data', 'raw', filename)
    const meta = detectMetadata(testPath)
    
    console.log(`📄 ${filename}`)
    console.log(`   Board: ${meta.board}, Level: ${meta.level}, Subject: ${meta.subjectCode}`)
    console.log(`   ${meta.year} ${meta.season}, Paper ${meta.paperNumber}, Type: ${meta.paperType}`)
    console.log(`   Confidence: ${(meta.confidence * 100).toFixed(0)}%\n`)
  }
  
  console.log('=' .repeat(80))
  console.log('✅ METADATA DETECTION TESTS COMPLETE')
  console.log('=' .repeat(80))
}

// Run tests
testMetadata().catch(err => {
  console.error('❌ Test failed:', err)
  process.exit(1)
})
