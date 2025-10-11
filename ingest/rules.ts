/**
 * rules.ts
 * Difficulty scoring, question number normalization, and topic keyword maps
 */

/**
 * Determine difficulty based on marks and command verbs
 * 1 = easy (1-3 marks, state/identify)
 * 2 = medium (4-6 marks, calculate/explain)
 * 3 = hard (7+ marks, evaluate/derive/justify)
 */
export function difficultyFromMarksAndVerbs(text: string, marks?: number): 1 | 2 | 3 {
  const lowerText = text.toLowerCase()
  
  // Command verb weights
  const hardVerbs = ['evaluate', 'derive', 'justify', 'assess', 'analyse', 'compare']
  const mediumVerbs = ['calculate', 'explain', 'describe', 'show', 'determine']
  const easyVerbs = ['state', 'identify', 'name', 'list', 'define']
  
  const hasHardVerb = hardVerbs.some(v => lowerText.includes(v))
  const hasMediumVerb = mediumVerbs.some(v => lowerText.includes(v))
  const hasEasyVerb = easyVerbs.some(v => lowerText.includes(v))
  
  // Combine marks and verbs
  if (marks) {
    if (marks >= 7 || hasHardVerb) return 3
    if (marks >= 4 || hasMediumVerb) return 2
    if (marks <= 3 || hasEasyVerb) return 1
  }
  
  // Verb-only fallback
  if (hasHardVerb) return 3
  if (hasMediumVerb) return 2
  return 1
}

/**
 * Normalize question number format
 * Examples: "Question 5" -> "Q5", "5(b)(ii)" -> "Q5(b)(ii)"
 */
export function cleanQuestionNumber(raw: string): string {
  return raw
    .replace(/Question\s+/gi, 'Q')
    .replace(/^(\d+)/, 'Q$1')
    .trim()
}

/**
 * Topic keyword synonyms for boosting confidence
 * Maps topic codes to relevant keywords
 */
export const topicKeywords: Record<string, string[]> = {
  '1a': ['unit', 'si', 'kilogram', 'metre', 'second', 'ampere', 'kelvin', 'mole', 'candela'],
  '1b': ['distance', 'time', 'speed', 'velocity', 'displacement', 'graph'],
  '1c': ['force', 'newton', 'momentum', 'mass', 'acceleration', 'law', 'motion'],
  '1d': ['energy', 'work', 'kinetic', 'potential', 'efficiency', 'joule'],
  '2a': ['electricity', 'current', 'voltage', 'resistance', 'ohm', 'circuit', 'ac', 'dc'],
  '2b': ['power', 'watt', 'series', 'parallel', 'circuit'],
  '2c': ['charge', 'coulomb', 'electron', 'static'],
  '3a': ['wave', 'wavelength', 'frequency', 'amplitude', 'transverse', 'longitudinal'],
  '3b': ['electromagnetic', 'spectrum', 'radio', 'microwave', 'infrared', 'ultraviolet', 'x-ray', 'gamma'],
  '3c': ['light', 'sound', 'reflection', 'refraction', 'diffraction'],
  '4a': ['energy', 'resource', 'fossil', 'nuclear', 'renewable', 'solar', 'wind'],
  '4b': ['work', 'power', 'efficiency'],
  '5a': ['density', 'pressure', 'pascal', 'fluid'],
  '5b': ['state', 'melting', 'boiling', 'evaporation', 'condensation', 'latent', 'heat'],
  '5c': ['gas', 'kinetic', 'theory', 'brownian', 'pressure', 'volume', 'temperature'],
  '6a': ['magnet', 'magnetic', 'field', 'pole', 'north', 'south'],
  '6b': ['electromagnetic', 'motor', 'generator', 'induction', 'transformer'],
  '7a': ['radioactivity', 'alpha', 'beta', 'gamma', 'radiation', 'half-life', 'decay'],
  '7b': ['fission', 'fusion', 'nuclear', 'chain', 'reaction'],
  '8a': ['orbit', 'gravity', 'satellite', 'planet', 'moon'],
  '8b': ['star', 'stellar', 'supernova', 'neutron', 'black hole', 'cosmology']
}

/**
 * Calculate keyword boost for a topic
 * Returns a multiplier (1.0 = no boost, up to 1.5 = strong match)
 */
export function calculateKeywordBoost(questionText: string, topicCode: string): number {
  const keywords = topicKeywords[topicCode] || []
  const lowerText = questionText.toLowerCase()
  
  let matchCount = 0
  for (const keyword of keywords) {
    if (lowerText.includes(keyword.toLowerCase())) {
      matchCount++
    }
  }
  
  // Boost: 0-2 matches = 1.0x, 3-5 = 1.2x, 6+ = 1.5x
  if (matchCount >= 6) return 1.5
  if (matchCount >= 3) return 1.2
  return 1.0
}
