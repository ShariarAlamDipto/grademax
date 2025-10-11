/**
 * Tagging Module - Topic Detection for Questions
 * 
 * Uses markscheme cues, question text, and rulepacks to identify topics.
 * Strategy: Context-aware matching with provenance tracking.
 */

import type { SegmentedQuestion, MSLink, SegmentedPart } from '../types/ingestion'

// ============================================================================
// Main Entry Point
// ============================================================================

export interface Tag {
  topic: string
  subtopic?: string
  confidence: number
  provenance: string[]
  cues: string[]
}

export interface TaggingResult {
  questionTags: Map<string, Tag[]>
  partTags: Map<string, Tag[]>
  stats: {
    totalQuestions: number
    taggedQuestions: number
    avgTagsPerQuestion: number
    totalParts: number
    taggedParts: number
  }
}

/**
 * Tag questions and parts with topics
 */
export async function tagQuestionsAndParts(
  questions: SegmentedQuestion[],
  msLinks: MSLink[]
): Promise<TaggingResult> {
  console.log('🏷️  Tagging questions with topics...')
  
  const questionTags = new Map<string, Tag[]>()
  const partTags = new Map<string, Tag[]>()
  
  // Create MS lookup for quick access
  const msLookup = new Map<string, string>()
  for (const link of msLinks) {
    if (link.confidence > 0) {
      msLookup.set(link.questionNumber.toString(), link.msSnippet)
    }
  }
  
  // Tag each question
  for (const question of questions) {
    const msText = msLookup.get(question.questionNumber) || ''
    
    // Extract tags from question and MS
    const tags = extractTags(question, msText)
    
    if (tags.length > 0) {
      questionTags.set(question.questionNumber, tags)
      console.log(`  ✓ Q${question.questionNumber}: ${tags.map(t => t.topic).join(', ')}`)
    } else {
      console.log(`  ⚠️  Q${question.questionNumber}: No topics detected`)
    }
    
    // Tag individual parts (if needed for granular tracking)
    for (const part of question.parts) {
      const partSpecificTags = extractPartTags(part, question, msText)
      if (partSpecificTags.length > 0) {
        partTags.set(part.code, partSpecificTags)
      }
    }
  }
  
  // Calculate stats
  const stats = {
    totalQuestions: questions.length,
    taggedQuestions: questionTags.size,
    avgTagsPerQuestion: questionTags.size > 0 
      ? Array.from(questionTags.values()).reduce((sum, tags) => sum + tags.length, 0) / questionTags.size
      : 0,
    totalParts: questions.reduce((sum, q) => sum + q.parts.length, 0),
    taggedParts: partTags.size
  }
  
  console.log(`\n📊 Tagging Summary:`)
  console.log(`  Total questions: ${stats.totalQuestions}`)
  console.log(`  Tagged questions: ${stats.taggedQuestions} (${Math.round(stats.taggedQuestions / stats.totalQuestions * 100)}%)`)
  console.log(`  Average tags per question: ${stats.avgTagsPerQuestion.toFixed(1)}`)
  
  return { questionTags, partTags, stats }
}

// ============================================================================
// Tag Extraction
// ============================================================================

/**
 * Extract tags for a question using MS cues and question text
 */
function extractTags(question: SegmentedQuestion, msText: string): Tag[] {
  const tags: Tag[] = []
  const detectedTopics = new Set<string>()
  
  // Combine question text and MS text for analysis
  const questionText = question.parts.map(p => p.text).join(' ')
  const combinedText = (questionText + ' ' + msText).toLowerCase()
  
  // Physics topic rules (simplified - in production would load from YAML rulepacks)
  const topicRules = getPhysicsTopicRules()
  
  for (const rule of topicRules) {
    const match = matchRule(rule, combinedText, msText)
    
    if (match.matched && !detectedTopics.has(rule.topic)) {
      tags.push({
        topic: rule.topic,
        subtopic: rule.subtopic,
        confidence: match.confidence,
        provenance: match.provenance,
        cues: match.cues
      })
      detectedTopics.add(rule.topic)
    }
  }
  
  return tags.sort((a, b) => b.confidence - a.confidence)
}

/**
 * Extract tags for individual parts (optional granular tracking)
 */
function extractPartTags(
  part: SegmentedPart,
  question: SegmentedQuestion,
  msText: string
): Tag[] {
  // For now, parts inherit question-level tags
  // In future, could do more granular MS parsing
  return extractTags(question, msText)
}

// ============================================================================
// Rule Matching
// ============================================================================

interface TopicRule {
  topic: string
  subtopic?: string
  keywords: string[]
  formulas?: string[]
  units?: string[]
  msKeywords?: string[] // Keywords that should appear in markscheme
  weight: number // How important this rule is
}

interface MatchResult {
  matched: boolean
  confidence: number
  provenance: string[]
  cues: string[]
}

/**
 * Match a rule against text
 */
function matchRule(rule: TopicRule, combinedText: string, msText: string): MatchResult {
  const provenance: string[] = []
  const cues: string[] = []
  let score = 0
  let maxScore = 0
  
  // Check keywords in combined text
  for (const keyword of rule.keywords) {
    maxScore += 1
    if (combinedText.includes(keyword.toLowerCase())) {
      score += 1
      provenance.push(`keyword: ${keyword}`)
      cues.push(keyword)
    }
  }
  
  // Check MS-specific keywords (higher weight)
  if (rule.msKeywords) {
    const msLower = msText.toLowerCase()
    for (const keyword of rule.msKeywords) {
      maxScore += 2
      if (msLower.includes(keyword.toLowerCase())) {
        score += 2
        provenance.push(`ms_keyword: ${keyword}`)
        cues.push(keyword)
      }
    }
  }
  
  // Check formulas
  if (rule.formulas) {
    for (const formula of rule.formulas) {
      maxScore += 1.5
      if (combinedText.includes(formula.toLowerCase())) {
        score += 1.5
        provenance.push(`formula: ${formula}`)
        cues.push(formula)
      }
    }
  }
  
  // Check units
  if (rule.units) {
    for (const unit of rule.units) {
      maxScore += 0.5
      const unitRegex = new RegExp(`\\b\\d+\\.?\\d*\\s*${unit}\\b`, 'i')
      if (unitRegex.test(combinedText)) {
        score += 0.5
        provenance.push(`unit: ${unit}`)
        cues.push(unit)
      }
    }
  }
  
  // Calculate confidence
  const confidence = maxScore > 0 ? Math.min(1.0, (score / maxScore) * rule.weight) : 0
  
  // Require minimum score to match
  const matched = score >= 1.0 && confidence >= 0.3
  
  return {
    matched,
    confidence,
    provenance,
    cues
  }
}

// ============================================================================
// Topic Rules (Physics - IGCSE/Edexcel)
// ============================================================================

/**
 * Get physics topic rules
 * In production, this would load from YAML rulepacks
 */
function getPhysicsTopicRules(): TopicRule[] {
  return [
    // Mechanics
    {
      topic: 'Forces and Motion',
      subtopic: 'Speed, Velocity, Acceleration',
      keywords: ['speed', 'velocity', 'acceleration', 'displacement', 'distance', 'motion'],
      formulas: ['v = u + at', 'a = (v - u) / t', 's = ut + ½at²'],
      units: ['m/s', 'm/s²', 'ms⁻¹', 'ms⁻²'],
      weight: 1.2
    },
    {
      topic: 'Forces and Motion',
      subtopic: 'Forces',
      keywords: ['force', 'newton', 'weight', 'mass', 'friction', 'gravity'],
      formulas: ['f = ma', 'w = mg'],
      units: ['N', 'kg', 'g'],
      msKeywords: ['resultant force', 'net force', 'unbalanced force'],
      weight: 1.2
    },
    {
      topic: 'Forces and Motion',
      subtopic: 'Pressure',
      keywords: ['pressure', 'area', 'force'],
      formulas: ['p = f/a', 'pressure = force / area'],
      units: ['Pa', 'N/m²', 'kPa'],
      msKeywords: ['pressure difference', 'atmospheric pressure'],
      weight: 1.1
    },
    {
      topic: 'Forces and Motion',
      subtopic: 'Moments',
      keywords: ['moment', 'turning effect', 'pivot', 'lever', 'torque'],
      formulas: ['moment = force × distance'],
      units: ['Nm', 'N·m'],
      weight: 1.1
    },
    
    // Energy
    {
      topic: 'Energy',
      subtopic: 'Work and Power',
      keywords: ['work', 'power', 'energy', 'joule', 'watt'],
      formulas: ['w = fs', 'p = e/t', 'p = w/t'],
      units: ['J', 'W', 'kJ', 'kW'],
      msKeywords: ['work done', 'energy transferred', 'power output'],
      weight: 1.2
    },
    {
      topic: 'Energy',
      subtopic: 'Energy Stores and Transfers',
      keywords: ['kinetic', 'potential', 'thermal', 'chemical', 'elastic', 'gravitational'],
      formulas: ['ke = ½mv²', 'pe = mgh', 'ee = ½kx²'],
      msKeywords: ['energy store', 'energy transfer', 'conservation of energy'],
      weight: 1.2
    },
    {
      topic: 'Energy',
      subtopic: 'Efficiency',
      keywords: ['efficiency', 'useful', 'wasted', 'input', 'output'],
      formulas: ['efficiency = useful / total', 'efficiency = output / input'],
      weight: 1.1
    },
    
    // Electricity
    {
      topic: 'Electricity',
      subtopic: 'Current and Voltage',
      keywords: ['current', 'voltage', 'potential difference', 'amp', 'volt', 'charge'],
      formulas: ['q = it', 'v = w/q', 'i = q/t'],
      units: ['A', 'V', 'C'],
      msKeywords: ['current flow', 'pd', 'emf'],
      weight: 1.2
    },
    {
      topic: 'Electricity',
      subtopic: 'Resistance',
      keywords: ['resistance', 'resistor', 'ohm'],
      formulas: ['v = ir', 'r = v/i'],
      units: ['Ω', 'ohm'],
      msKeywords: ['ohms law', "ohm's law"],
      weight: 1.2
    },
    {
      topic: 'Electricity',
      subtopic: 'Power',
      keywords: ['power', 'electrical', 'watt'],
      formulas: ['p = vi', 'p = i²r', 'p = v²/r'],
      units: ['W', 'kW'],
      msKeywords: ['power dissipated', 'power output'],
      weight: 1.1
    },
    {
      topic: 'Electricity',
      subtopic: 'Circuits',
      keywords: ['series', 'parallel', 'circuit', 'component', 'ammeter', 'voltmeter'],
      msKeywords: ['series circuit', 'parallel circuit', 'in series', 'in parallel'],
      weight: 1.0
    },
    
    // Waves
    {
      topic: 'Waves',
      subtopic: 'Wave Properties',
      keywords: ['wave', 'frequency', 'wavelength', 'amplitude', 'period'],
      formulas: ['v = fλ', 'f = 1/t'],
      units: ['Hz', 'm', 's'],
      msKeywords: ['transverse', 'longitudinal'],
      weight: 1.2
    },
    {
      topic: 'Waves',
      subtopic: 'Light',
      keywords: ['light', 'refraction', 'reflection', 'ray', 'normal', 'incident'],
      formulas: ['n = sin i / sin r', 'sin c = 1/n'],
      msKeywords: ['angle of incidence', 'angle of refraction', 'refractive index'],
      weight: 1.1
    },
    {
      topic: 'Waves',
      subtopic: 'Sound',
      keywords: ['sound', 'ultrasound', 'echo', 'vibration'],
      units: ['Hz', 'kHz'],
      weight: 1.0
    },
    
    // Magnetism
    {
      topic: 'Magnetism and Electromagnetism',
      subtopic: 'Magnets',
      keywords: ['magnet', 'magnetic', 'field', 'pole', 'attract', 'repel'],
      msKeywords: ['magnetic field', 'field line', 'north pole', 'south pole'],
      weight: 1.1
    },
    {
      topic: 'Magnetism and Electromagnetism',
      subtopic: 'Electromagnetism',
      keywords: ['electromagnet', 'solenoid', 'coil', 'induced', 'generator', 'motor'],
      msKeywords: ['electromagnetic induction', 'induced current', 'induced emf'],
      weight: 1.1
    },
    
    // Thermal Physics
    {
      topic: 'Thermal Physics',
      subtopic: 'Temperature',
      keywords: ['temperature', 'celsius', 'kelvin', 'hot', 'cold', 'thermometer'],
      units: ['°C', 'K'],
      weight: 1.0
    },
    {
      topic: 'Thermal Physics',
      subtopic: 'Heat Transfer',
      keywords: ['conduction', 'convection', 'radiation', 'insulation', 'thermal'],
      msKeywords: ['heat transfer', 'thermal energy', 'thermal conductor'],
      weight: 1.1
    },
    {
      topic: 'Thermal Physics',
      subtopic: 'Gas Laws',
      keywords: ['gas', 'pressure', 'volume', 'temperature', 'particle', 'kinetic'],
      formulas: ['pv = nrt', 'p₁v₁ = p₂v₂'],
      msKeywords: ['gas law', 'ideal gas', 'kinetic theory'],
      weight: 1.1
    },
    
    // Atomic Physics
    {
      topic: 'Atomic Physics',
      subtopic: 'Radioactivity',
      keywords: ['radioactive', 'radiation', 'alpha', 'beta', 'gamma', 'decay', 'nucleus'],
      msKeywords: ['radioactive decay', 'half-life', 'ionising'],
      weight: 1.2
    },
    {
      topic: 'Atomic Physics',
      subtopic: 'Nuclear',
      keywords: ['nuclear', 'fission', 'fusion', 'atom', 'proton', 'neutron', 'electron'],
      weight: 1.0
    },
    
    // Density and Matter
    {
      topic: 'Properties of Matter',
      subtopic: 'Density',
      keywords: ['density', 'mass', 'volume'],
      formulas: ['ρ = m/v', 'density = mass / volume'],
      units: ['kg/m³', 'g/cm³'],
      msKeywords: ['dense', 'less dense', 'more dense'],
      weight: 1.1
    },
    {
      topic: 'Properties of Matter',
      subtopic: 'Hooke\'s Law',
      keywords: ['spring', 'elastic', 'extension', 'hooke'],
      formulas: ['f = kx', 'f = ke'],
      units: ['N/m'],
      msKeywords: ['spring constant', 'elastic limit'],
      weight: 1.0
    }
  ]
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Extract numeric values with units from text
 */
export function extractNumericCues(text: string): Array<{value: number, unit: string}> {
  const cues: Array<{value: number, unit: string}> = []
  
  // Pattern: number (with optional decimal) followed by unit
  const pattern = /(\d+\.?\d*)\s*(m\/s²|m\/s|ms⁻²|ms⁻¹|m|kg|N|J|W|Pa|kPa|Hz|kHz|A|V|C|Ω|°C|K|N\/m²|Nm)/gi
  
  const matches = text.matchAll(pattern)
  for (const match of matches) {
    cues.push({
      value: parseFloat(match[1]),
      unit: match[2]
    })
  }
  
  return cues
}

/**
 * Extract formula patterns from text
 */
export function extractFormulas(text: string): string[] {
  const formulas: string[] = []
  
  // Pattern: variable = expression
  const pattern = /([a-z]+)\s*=\s*([^;,.]+)/gi
  
  const matches = text.matchAll(pattern)
  for (const match of matches) {
    formulas.push(match[0].trim())
  }
  
  return formulas
}
