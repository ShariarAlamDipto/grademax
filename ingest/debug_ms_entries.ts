/**
 * debug_ms_entries.ts
 * Show what MS entries we're finding
 */

import { parsePDFFromPath, flattenTextItems } from './parse_pdf_v2.js'
import type { TextItem } from '../types/ingestion.js'

const MS_PDF = './data/raw/IGCSE/4PH1/2019/Jun/4PH1_1P_MS.pdf'

// Minimal parser to see what we extract
function parseListFormatSimple(textItems: TextItem[]) {
  const entries: Array<{qNum: string, partCode: string, text: string}> = []
  let currentEntry: {qNum?: string, partCode?: string, text?: string} | null = null
  
  for (let i = 0; i < textItems.length; i++) {
    const item = textItems[i]
    const text = item.text.trim()
    
    // Standalone question number
    const standaloneQMatch = text.match(/^(\d+)\s*$/)
    if (standaloneQMatch && item.x < 100) {
      if (currentEntry && currentEntry.qNum) {
        entries.push({
          qNum: currentEntry.qNum,
          partCode: currentEntry.partCode || '',
          text: currentEntry.text || ''
        })
      }
      
      currentEntry = {
        qNum: standaloneQMatch[1],
        partCode: '',
        text: text
      }
      continue
    }
    
    // Part marker
    const partMatch = text.match(/^\(([a-z])\)(?:\s*\(([ivx]+)\))?/)
    if (partMatch && currentEntry) {
      const part = partMatch[1]
      const subpart = partMatch[2]
      
      if (currentEntry.partCode) {
        // Save previous part, start new one
        entries.push({
          qNum: currentEntry.qNum!,
          partCode: currentEntry.partCode,
          text: currentEntry.text || ''
        })
        
        currentEntry = {
          qNum: currentEntry.qNum,
          partCode: subpart ? `(${part})(${subpart})` : `(${part})`,
          text: text
        }
      } else {
        currentEntry.partCode = subpart ? `(${part})(${subpart})` : `(${part})`
        currentEntry.text += ' ' + text
      }
      continue
    }
    
    // Accumulate
    if (currentEntry) {
      currentEntry.text += ' ' + text
    }
  }
  
  if (currentEntry && currentEntry.qNum) {
    entries.push({
      qNum: currentEntry.qNum,
      partCode: currentEntry.partCode || '',
      text: currentEntry.text || ''
    })
  }
  
  return entries
}

async function debugMSEntries() {
  console.log('🔍 Debug MS Entries\n')
  
  const result = await parsePDFFromPath(MS_PDF)
  const textItems = flattenTextItems(result)
  
  const entries = parseListFormatSimple(textItems)
  
  console.log(`Found ${entries.length} MS entries\n`)
  
  console.log('📋 First 20 entries:\n')
  for (let i = 0; i < Math.min(20, entries.length); i++) {
    const e = entries[i]
    const key = `${e.qNum}${e.partCode}`
    const snippet = e.text.substring(0, 80).replace(/\s+/g, ' ')
    console.log(`${i + 1}. ${key}: "${snippet}..."`)
  }
  
  // Show summary by question
  console.log('\n📊 Entries by question:\n')
  const byQ = new Map<string, number>()
  for (const e of entries) {
    byQ.set(e.qNum, (byQ.get(e.qNum) || 0) + 1)
  }
  
  for (const [qNum, count] of byQ) {
    console.log(`  Q${qNum}: ${count} entries`)
  }
}

debugMSEntries().catch(console.error)
