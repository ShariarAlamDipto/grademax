/**
 * parse_pdf.ts
 * Extract raw text from PDF and split into questions
 */
import fs from 'fs'
import pdf from 'pdf-parse'

export interface ParsedQuestion {
  questionNumber: string
  text: string
  marks?: number
}

/**
 * Parse PDF and extract raw text per page
 */
export async function parsePaper(pdfPath: string): Promise<{ pages: Array<{ text: string }>, raw: string }> {
  const dataBuffer = fs.readFileSync(pdfPath)
  const data = await pdf(dataBuffer)
  
  return {
    pages: data.text.split('\f').map((pageText: string) => ({ text: pageText })),
    raw: data.text
  }
}

/**
 * Split raw text into questions using pattern matching
 * Specifically designed for IGCSE/IAL paper format
 */
export function extractQuestions(raw: string): ParsedQuestion[] {
  const questions: ParsedQuestion[] = []
  
  // Split by lines to preserve structure - DON'T clean to single line
  const lines = raw.split('\n')
  
  // Main question pattern: line starts with number (1-2 digits) followed by space and capital letter
  // Example: "1 The passage describes..." or "12 This question is about..."
  const mainQuestionPattern = /^(\d{1,2})\s+[A-Z]/
  
  const mainQuestionIndices: Array<{ lineIndex: number, questionNum: string }> = []
  
  lines.forEach((line, i) => {
    const trimmed = line.trim()
    const match = trimmed.match(mainQuestionPattern)
    if (match) {
      mainQuestionIndices.push({
        lineIndex: i,
        questionNum: match[1]
      })
    }
  })
  
  if (mainQuestionIndices.length === 0) {
    console.warn('No main questions found - text may not be properly formatted')
    return []
  }
  
  console.log(`Found ${mainQuestionIndices.length} main questions`)
  
  // Extract text for each question
  for (let i = 0; i < mainQuestionIndices.length; i++) {
    const { lineIndex, questionNum } = mainQuestionIndices[i]
    const nextLineIndex = i < mainQuestionIndices.length - 1 
      ? mainQuestionIndices[i + 1].lineIndex 
      : lines.length
    
    // Get all lines for this question
    let questionText = lines.slice(lineIndex, nextLineIndex).join('\n').trim()
    
    // Remove the question number from start
    questionText = questionText.replace(/^\d{1,2}\s+/, '')
    
    // Look for "Total for Question X: Y marks" to mark end
    const totalMatch = questionText.match(/Total\s+for\s+Question\s+\d+\s*:?\s*(\d+)\s*marks?/i)
    if (totalMatch) {
      const totalIdx = questionText.indexOf(totalMatch[0])
      questionText = questionText.substring(0, totalIdx).trim()
    }
    
    // Extract marks patterns [X marks] or (X marks) or [X]
    const marksPattern = /[\[\(](\d+)\s*marks?[\]\)]|[\[\(](\d+)[\]\)]/gi
    const allMarksMatches = [...questionText.matchAll(marksPattern)]
    
    // Try to split into subparts (a), (b), (c), etc.
    const subpartPattern = /\(([a-e])\)\s*(?=[A-Z]|[A-Za-z])/g
    const subpartMatches = [...questionText.matchAll(subpartPattern)]
    
    if (subpartMatches.length > 0) {
      console.log(`  Question ${questionNum} has ${subpartMatches.length} subparts`)
      
      // Process each subpart
      for (let j = 0; j < subpartMatches.length; j++) {
        const subpartMatch = subpartMatches[j]
        const subpartLetter = subpartMatch[1]
        const subStartIdx = subpartMatch.index!
        const subEndIdx = j < subpartMatches.length - 1 
          ? subpartMatches[j + 1].index! 
          : questionText.length
        
        const subText = questionText.substring(subStartIdx, subEndIdx).trim()
        
        // Look for sub-subparts (i), (ii), (iii) within this subpart
        const subSubPattern = /\((i{1,3}|iv|v|vi)\)\s*(?=[A-Z]|[A-Za-z])/g
        const subSubMatches = [...subText.matchAll(subSubPattern)]
        
        if (subSubMatches.length > 0) {
          console.log(`    ${questionNum}(${subpartLetter}) has ${subSubMatches.length} sub-subparts`)
          
          for (let k = 0; k < subSubMatches.length; k++) {
            const subSubMatch = subSubMatches[k]
            const subSubNum = subSubMatch[1]
            const subSubStartIdx = subSubMatch.index!
            const subSubEndIdx = k < subSubMatches.length - 1
              ? subSubMatches[k + 1].index!
              : subText.length
            
            const subSubText = subText.substring(subSubStartIdx, subSubEndIdx).trim()
            const subSubMarks = subSubText.match(marksPattern)
            const marks = subSubMarks ? parseInt(subSubMarks[1] || subSubMarks[2]) : undefined
            
            questions.push({
              questionNumber: `${questionNum}(${subpartLetter})(${subSubNum})`,
              text: subSubText,
              marks
            })
          }
        } else {
          // No sub-subparts, just add the subpart
          const subMarks = subText.match(marksPattern)
          const marks = subMarks ? parseInt(subMarks[1] || subMarks[2]) : undefined
          
          questions.push({
            questionNumber: `${questionNum}(${subpartLetter})`,
            text: subText,
            marks
          })
        }
      }
    } else {
      // No subparts - single question
      const marks = allMarksMatches.length > 0 
        ? parseInt(allMarksMatches[0][1] || allMarksMatches[0][2])
        : undefined
      
      questions.push({
        questionNumber: questionNum,
        text: questionText,
        marks
      })
    }
  }
  
  console.log(`Extracted ${questions.length} total questions/subparts`)
  return questions
}

/**
 * Extract markschemes from markscheme PDF
 * Markschemes have format:
 * Question
 * number
 * Answer  Notes  Marks
 * 2 (a) (i) downward arrow...
 *   (ii) (a quantity with)...
 *   (iii) any correct vector...
 *  (b) (i) pressure...
 */
export function extractMarkschemes(raw: string): ParsedQuestion[] {
  const markschemes: ParsedQuestion[] = []
  
  const lines = raw.split('\n')
  
  // Track the main question number (1, 2, 3, etc.)
  let currentMainQuestion: string | null = null
  let currentSubpart: string | null = null // e.g., "(a)", "(b)"
  let currentSubSubpart: string | null = null // e.g., "(i)", "(ii)"
  let currentText: string[] = []
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const trimmed = line.trim()
    
    // Skip header lines
    if (trimmed === 'Question' || trimmed === 'number' || trimmed === 'Answer  Notes  Marks' || trimmed === '') {
      continue
    }
    
    // Check for "Total for Question X" - marks end of question
    if (trimmed.startsWith('Total for Question')) {
      // Save current item
      if (currentMainQuestion && currentText.length > 0) {
        let questionNum = currentMainQuestion
        if (currentSubpart) questionNum += currentSubpart
        if (currentSubSubpart) questionNum += currentSubSubpart
        
        markschemes.push({
          questionNumber: questionNum.replace(/\s+/g, ''),
          text: currentText.join('\n').trim(),
          marks: undefined
        })
      }
      
      currentMainQuestion = null
      currentSubpart = null
      currentSubSubpart = null
      currentText = []
      continue
    }
    
    // Pattern: "2 (a) (i) some text" - Main question with subparts
    const fullPattern = /^(\d{1,2})\s+\(([a-e])\)\s+\((i{1,3}|iv|v|vi)\)\s+(.+)/
    const fullMatch = trimmed.match(fullPattern)
    
    if (fullMatch) {
      // Save previous
      if (currentMainQuestion && currentText.length > 0) {
        let questionNum = currentMainQuestion
        if (currentSubpart) questionNum += currentSubpart
        if (currentSubSubpart) questionNum += currentSubSubpart
        
        markschemes.push({
          questionNumber: questionNum.replace(/\s+/g, ''),
          text: currentText.join('\n').trim(),
          marks: undefined
        })
      }
      
      currentMainQuestion = fullMatch[1]
      currentSubpart = `(${fullMatch[2]})`
      currentSubSubpart = `(${fullMatch[3]})`
      currentText = [fullMatch[4]]
      continue
    }
    
    // Pattern: "2 (a) some text" - Main question with subpart
    const mainSubPattern = /^(\d{1,2})\s+\(([a-e])\)\s+(.+)/
    const mainSubMatch = trimmed.match(mainSubPattern)
    
    if (mainSubMatch) {
      // Save previous
      if (currentMainQuestion && currentText.length > 0) {
        let questionNum = currentMainQuestion
        if (currentSubpart) questionNum += currentSubpart
        if (currentSubSubpart) questionNum += currentSubSubpart
        
        markschemes.push({
          questionNumber: questionNum.replace(/\s+/g, ''),
          text: currentText.join('\n').trim(),
          marks: undefined
        })
      }
      
      currentMainQuestion = mainSubMatch[1]
      currentSubpart = `(${mainSubMatch[2]})`
      currentSubSubpart = null
      currentText = [mainSubMatch[3]]
      continue
    }
    
    // Pattern: "2 some text" - Just main question
    const mainOnlyPattern = /^(\d{1,2})\s+(.+)/
    const mainOnlyMatch = trimmed.match(mainOnlyPattern)
    
    if (mainOnlyMatch && !trimmed.match(/^\d{1,2}\s*$/)) { // Don't match just numbers
      // Save previous
      if (currentMainQuestion && currentText.length > 0) {
        let questionNum = currentMainQuestion
        if (currentSubpart) questionNum += currentSubpart
        if (currentSubSubpart) questionNum += currentSubSubpart
        
        markschemes.push({
          questionNumber: questionNum.replace(/\s+/g, ''),
          text: currentText.join('\n').trim(),
          marks: undefined
        })
      }
      
      currentMainQuestion = mainOnlyMatch[1]
      currentSubpart = null
      currentSubSubpart = null
      currentText = [mainOnlyMatch[2]]
      continue
    }
    
    // Pattern: "  (ii) some text" or " (b) (i) some text" - Continuation subparts
    const contSubSubPattern = /^\s+\((i{1,3}|iv|v|vi)\)\s+(.+)/
    const contSubSubMatch = line.match(contSubSubPattern)
    
    if (contSubSubMatch && currentMainQuestion) {
      // Save previous sub-subpart
      if (currentSubSubpart && currentText.length > 0) {
        let questionNum = currentMainQuestion
        if (currentSubpart) questionNum += currentSubpart
        if (currentSubSubpart) questionNum += currentSubSubpart
        
        markschemes.push({
          questionNumber: questionNum.replace(/\s+/g, ''),
          text: currentText.join('\n').trim(),
          marks: undefined
        })
      }
      
      // Start new sub-subpart
      currentSubSubpart = `(${contSubSubMatch[1]})`
      currentText = [contSubSubMatch[2]]
      continue
    }
    
    // Pattern: " (b) some text" or " (b) (i) some text" - New subpart
    const contSubPattern = /^\s+\(([a-e])\)(?:\s+\((i{1,3}|iv|v|vi)\))?\s+(.+)/
    const contSubMatch = line.match(contSubPattern)
    
    if (contSubMatch && currentMainQuestion) {
      // Save previous
      if (currentText.length > 0) {
        let questionNum = currentMainQuestion
        if (currentSubpart) questionNum += currentSubpart
        if (currentSubSubpart) questionNum += currentSubSubpart
        
        markschemes.push({
          questionNumber: questionNum.replace(/\s+/g, ''),
          text: currentText.join('\n').trim(),
          marks: undefined
        })
      }
      
      // Start new subpart
      currentSubpart = `(${contSubMatch[1]})`
      currentSubSubpart = contSubMatch[2] ? `(${contSubMatch[2]})` : null
      currentText = [contSubMatch[3]]
      continue
    }
    
    // Otherwise, it's a continuation line
    if (currentMainQuestion) {
      currentText.push(line) // Keep original formatting
    }
  }
  
  // Don't forget last question
  if (currentMainQuestion && currentText.length > 0) {
    let questionNum = currentMainQuestion
    if (currentSubpart) questionNum += currentSubpart
    if (currentSubSubpart) questionNum += currentSubSubpart
    
    markschemes.push({
      questionNumber: questionNum.replace(/\s+/g, ''),
      text: currentText.join('\n').trim(),
      marks: undefined
    })
  }
  
  console.log(`Extracted ${markschemes.length} markscheme entries`)
  return markschemes
}
