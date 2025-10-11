/**
 * Features Extraction Module
 * 
 * Extracts metadata about questions:
 * - Difficulty estimation (based on marks, complexity)
 * - Style detection (calculation, explanation, diagram, practical)
 * - Complexity scoring
 * - Question type classification
 */

import type { SegmentedQuestion } from '../types/ingestion'

// Import Tag from tagging module
interface Tag {
  topic: string
  subtopic?: string
  confidence: number
  provenance: string[]
  cues: string[]
}

// ============================================================================
// Types
// ============================================================================

export interface QuestionFeatures {
  questionNumber: string
  difficulty: 'easy' | 'medium' | 'hard'
  difficultyScore: number // 0-1 scale
  style: QuestionStyle[]
  complexity: {
    conceptCount: number // Number of physics concepts involved
    stepCount: number // Estimated calculation steps
    reasoning: 'low' | 'medium' | 'high'
  }
  estimatedMinutes: number
  characteristics: string[] // e.g., 'multi-step', 'formula-based', 'requires-diagram'
}

export type QuestionStyle = 
  | 'calculation' 
  | 'explanation' 
  | 'diagram' 
  | 'practical' 
  | 'comparison'
  | 'multiple-choice'
  | 'true-false'

// ============================================================================
// Main Entry Point
// ============================================================================

/**
 * Extract features for all questions
 */
export function extractFeatures(
  questions: SegmentedQuestion[],
  questionTags?: Map<string, Tag[]>,
  msTexts?: Map<string, string>
): Map<string, QuestionFeatures> {
  console.log('🔍 Extracting question features...')
  
  const featuresMap = new Map<string, QuestionFeatures>()
  
  for (const question of questions) {
    const tags = questionTags?.get(question.questionNumber) || []
    const msText = msTexts?.get(question.questionNumber) || ''
    
    const features = extractQuestionFeatures(question, tags, msText)
    featuresMap.set(question.questionNumber, features)
    
    console.log(`  ✓ Q${question.questionNumber}: ${features.difficulty} (${features.style.join(', ')})`)
  }
  
  console.log(`\n📊 Features Summary:`)
  const difficulties = Array.from(featuresMap.values()).map(f => f.difficulty)
  console.log(`  Easy: ${difficulties.filter(d => d === 'easy').length}`)
  console.log(`  Medium: ${difficulties.filter(d => d === 'medium').length}`)
  console.log(`  Hard: ${difficulties.filter(d => d === 'hard').length}`)
  
  return featuresMap
}

// ============================================================================
// Feature Extraction
// ============================================================================

/**
 * Extract features for a single question
 */
function extractQuestionFeatures(
  question: SegmentedQuestion,
  tags: Tag[],
  msText: string
): QuestionFeatures {
  const combinedText = (question.contextText + ' ' + msText).toLowerCase()
  
  // Difficulty estimation
  const difficultyScore = estimateDifficulty(question, tags, msText, combinedText)
  const difficulty = scoreToDifficulty(difficultyScore)
  
  // Style detection
  const style = detectStyle(question, combinedText)
  
  // Complexity analysis
  const complexity = analyzeComplexity(question, tags, combinedText)
  
  // Time estimation (rough: 1-2 minutes per mark)
  const estimatedMinutes = Math.ceil(question.totalMarks * 1.5)
  
  // Characteristics
  const characteristics = detectCharacteristics(question, combinedText, tags)
  
  return {
    questionNumber: question.questionNumber,
    difficulty,
    difficultyScore,
    style,
    complexity,
    estimatedMinutes,
    characteristics
  }
}

// ============================================================================
// Difficulty Estimation
// ============================================================================

/**
 * Estimate difficulty on 0-1 scale
 */
function estimateDifficulty(
  question: SegmentedQuestion,
  tags: Tag[],
  msText: string,
  combinedText: string
): number {
  let score = 0.3 // Base score
  
  // Factor 1: Marks (higher marks = harder)
  const marksScore = Math.min(question.totalMarks / 20, 1) * 0.25
  score += marksScore
  
  // Factor 2: Number of parts (more parts = harder)
  const partsScore = Math.min(question.parts.length / 8, 1) * 0.15
  score += partsScore
  
  // Factor 3: Number of topics (more topics = harder)
  const topicsScore = Math.min(tags.length / 4, 1) * 0.15
  score += topicsScore
  
  // Factor 4: MS length (longer MS = more complex answer)
  const msLength = msText.length
  const msScore = Math.min(msLength / 1500, 1) * 0.15
  score += msScore
  
  // Factor 5: Hard keywords in MS
  const hardKeywords = [
    'derive', 'prove', 'justify', 'evaluate', 'analyse', 'assess',
    'compare', 'contrast', 'discuss', 'explain why', 'show that',
    'calculate and explain', 'multi-step'
  ]
  const hardKeywordCount = hardKeywords.filter(kw => combinedText.includes(kw)).length
  score += Math.min(hardKeywordCount / 5, 1) * 0.1
  
  return Math.min(score, 1)
}

/**
 * Convert difficulty score to category
 */
function scoreToDifficulty(score: number): 'easy' | 'medium' | 'hard' {
  if (score < 0.4) return 'easy'
  if (score < 0.7) return 'medium'
  return 'hard'
}

// ============================================================================
// Style Detection
// ============================================================================

/**
 * Detect question style(s)
 */
function detectStyle(question: SegmentedQuestion, combinedText: string): QuestionStyle[] {
  const styles: QuestionStyle[] = []
  
  // Calculation indicators
  const calculationKeywords = ['calculate', 'find', 'determine', 'compute', 'work out', 'show that']
  const hasCalculation = calculationKeywords.some(kw => combinedText.includes(kw))
  const hasNumbers = /\d+\.?\d*\s*(m|kg|n|j|w|v|a|ω|pa|hz|°c|k|s)\b/i.test(combinedText)
  if (hasCalculation || hasNumbers) {
    styles.push('calculation')
  }
  
  // Explanation indicators
  const explanationKeywords = ['explain', 'describe', 'why', 'how', 'reason', 'because', 'suggest']
  if (explanationKeywords.some(kw => combinedText.includes(kw))) {
    styles.push('explanation')
  }
  
  // Diagram indicators
  const diagramKeywords = ['draw', 'sketch', 'diagram', 'label', 'graph', 'plot', 'show on the diagram']
  if (diagramKeywords.some(kw => combinedText.includes(kw))) {
    styles.push('diagram')
  }
  
  // Practical indicators
  const practicalKeywords = ['experiment', 'practical', 'apparatus', 'procedure', 'method', 'equipment']
  if (practicalKeywords.some(kw => combinedText.includes(kw))) {
    styles.push('practical')
  }
  
  // Comparison indicators
  const comparisonKeywords = ['compare', 'contrast', 'difference', 'similarity', 'versus', 'vs']
  if (comparisonKeywords.some(kw => combinedText.includes(kw))) {
    styles.push('comparison')
  }
  
  // Multiple choice
  if (combinedText.includes('(a)') && combinedText.includes('(b)') && combinedText.includes('(c)') && combinedText.includes('(d)')) {
    // Check if they're options, not subparts
    if (question.parts.length === 1) {
      styles.push('multiple-choice')
    }
  }
  
  // Default to calculation if nothing detected
  if (styles.length === 0) {
    styles.push('calculation')
  }
  
  return styles
}

// ============================================================================
// Complexity Analysis
// ============================================================================

/**
 * Analyze question complexity
 */
function analyzeComplexity(
  question: SegmentedQuestion,
  tags: Tag[],
  combinedText: string
): QuestionFeatures['complexity'] {
  // Concept count (from tags)
  const conceptCount = tags.length
  
  // Step count estimation
  const stepIndicators = [
    'first', 'then', 'next', 'finally', 'step',
    'calculate', 'find', 'use', 'substitute', 'rearrange'
  ]
  const stepCount = Math.max(
    stepIndicators.filter(ind => combinedText.includes(ind)).length,
    question.parts.length
  )
  
  // Reasoning level
  const highReasoningKeywords = [
    'justify', 'evaluate', 'analyse', 'assess', 'explain why',
    'compare and contrast', 'discuss', 'derive', 'prove'
  ]
  const mediumReasoningKeywords = [
    'explain', 'describe', 'suggest', 'state why', 'give a reason'
  ]
  
  let reasoning: 'low' | 'medium' | 'high' = 'low'
  if (highReasoningKeywords.some(kw => combinedText.includes(kw))) {
    reasoning = 'high'
  } else if (mediumReasoningKeywords.some(kw => combinedText.includes(kw))) {
    reasoning = 'medium'
  }
  
  return {
    conceptCount,
    stepCount,
    reasoning
  }
}

// ============================================================================
// Characteristics Detection
// ============================================================================

/**
 * Detect question characteristics
 */
function detectCharacteristics(
  question: SegmentedQuestion,
  combinedText: string,
  tags: Tag[]
): string[] {
  const characteristics: string[] = []
  
  // Multi-step
  if (question.parts.length >= 3) {
    characteristics.push('multi-step')
  }
  
  // Formula-based
  if (/[a-z]\s*=\s*[^=]+/i.test(combinedText)) {
    characteristics.push('formula-based')
  }
  
  // Requires diagram
  if (/draw|sketch|diagram|label|graph|plot/i.test(combinedText)) {
    characteristics.push('requires-diagram')
  }
  
  // Unit conversion
  if (/convert|cm|mm|km|g\b|mg|ml|l\b/i.test(combinedText)) {
    characteristics.push('unit-conversion')
  }
  
  // Real-world context
  if (/car|ball|person|student|lift|crane|rocket|satellite|plane/i.test(combinedText)) {
    characteristics.push('real-world-context')
  }
  
  // Data interpretation
  if (/table|graph|chart|data|values|results/i.test(combinedText)) {
    characteristics.push('data-interpretation')
  }
  
  // Multiple concepts (interdisciplinary)
  if (tags.length >= 3) {
    characteristics.push('multiple-concepts')
  }
  
  // High marks
  if (question.totalMarks >= 10) {
    characteristics.push('high-marks')
  }
  
  return characteristics
}

// ============================================================================
// Stats and Utilities
// ============================================================================

/**
 * Generate statistics for a set of questions
 */
export function generateFeatureStats(featuresMap: Map<string, QuestionFeatures>): {
  averageDifficulty: number
  averageTime: number
  styleDistribution: Record<QuestionStyle, number>
  characteristicsFrequency: Record<string, number>
} {
  const features = Array.from(featuresMap.values())
  
  const averageDifficulty = features.reduce((sum, f) => sum + f.difficultyScore, 0) / features.length
  const averageTime = features.reduce((sum, f) => sum + f.estimatedMinutes, 0) / features.length
  
  const styleDistribution: Record<QuestionStyle, number> = {
    'calculation': 0,
    'explanation': 0,
    'diagram': 0,
    'practical': 0,
    'comparison': 0,
    'multiple-choice': 0,
    'true-false': 0
  }
  
  const characteristicsFrequency: Record<string, number> = {}
  
  for (const feature of features) {
    for (const style of feature.style) {
      styleDistribution[style]++
    }
    for (const char of feature.characteristics) {
      characteristicsFrequency[char] = (characteristicsFrequency[char] || 0) + 1
    }
  }
  
  return {
    averageDifficulty,
    averageTime,
    styleDistribution,
    characteristicsFrequency
  }
}
