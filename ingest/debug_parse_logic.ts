import { parsePDFFromPath } from './parse_pdf_v2'
import type { TextItem } from '../types/ingestion'

const MS_PATH = './data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf'

async function debugParseLogic() {
  console.log('🔍 Debug Parse Logic\n')
  
  // Parse MS PDF
  const msResult = await parsePDFFromPath(MS_PATH)
  
  // Flatten text items
  const textItems: TextItem[] = []
  for (const page of msResult.pages) {
    textItems.push(...page.textItems)
  }
  
  console.log(`Found ${textItems.length} text items\n`)
  
  // Show first few items from Question 2 area
  let currentQuestionNumber = ''
  let currentMainPart = ''
  let foundQ2 = false
  
  for (let i = 0; i < textItems.length; i++) {
    const item = textItems[i]
    const text = item.text.trim()
    
    // Look for Question 2 area
    if (text.match(/^2\s+\(/)) {
      foundQ2 = true
    }
    
    if (foundQ2) {
      console.log(`\nItem ${i}: "${text}"`)
      
      // Test various patterns
      const qWithPartMatch = text.match(/^(\d+)\s+\(([a-z]+|[ivx]+)\)/)
      const partMatch = text.match(/^\(([a-hj-uw-z])\)(?:\s*\(([ivx]+)\))?/)
      const subpartMatch = text.match(/^\(([ivx]+)\)/)
      
      console.log(`  - qWithPartMatch: ${qWithPartMatch ? qWithPartMatch[0] : 'NO'}`)
      console.log(`  - partMatch: ${partMatch ? partMatch[0] : 'NO'}`)
      console.log(`  - subpartMatch: ${subpartMatch ? subpartMatch[0] : 'NO'}`)
      console.log(`  - currentQuestionNumber: "${currentQuestionNumber}"`)
      console.log(`  - currentMainPart: "${currentMainPart}"`)
      
      // Update state as the real parser would
      if (qWithPartMatch) {
        const qNum = qWithPartMatch[1]
        const partStr = qWithPartMatch[2]
        currentQuestionNumber = qNum
        
        if (/^[ivx]+$/.test(partStr)) {
          currentMainPart = partStr
          console.log(`  ➜ Would set currentMainPart = "${partStr}" (roman after Q number)`)
        } else {
          currentMainPart = partStr
          console.log(`  ➜ Would set currentMainPart = "${partStr}" (letter)`)
        }
      } else if (partMatch && currentQuestionNumber) {
        const part = partMatch[1]
        currentMainPart = part
        console.log(`  ➜ Would set currentMainPart = "${part}"`)
      } else if (subpartMatch && currentMainPart) {
        const subpart = subpartMatch[1]
        console.log(`  ➜ Would create part code: (${currentMainPart})(${subpart})`)
      }
      
      // Stop after first 15 items in Q2 area
      const q2StartIndex = textItems.findIndex(it => it.text.trim().match(/^2\s+\(/))
      if (i > q2StartIndex + 15) {
        break
      }
    }
  }
}

debugParseLogic().catch(console.error)
