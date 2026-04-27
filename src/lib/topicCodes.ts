/**
 * Normalize topic codes from the topics table into numeric IDs stored in pages.topics.
 *
 * Physics (4PH1): topics table stores descriptive codes (FM, ELEC, WAVE, ENRG, SLG, MAG, RAD, ASTRO)
 *   but pages.topics stores numeric IDs ("1"–"8").
 *
 * FPM (4PM1/9FM0): topics table stores YAML codes (LOGS, QUAD, etc.)
 *   but pages.topics stores numeric IDs ("1"–"10").
 *
 * Maths B / new subjects: topics table stores numeric codes ("1"–"10"); no mapping needed.
 *
 * Chemistry/Bio: topics table stores "1.1", "1.2" etc.; passed through unchanged to match pages.topics.
 */
const CODE_TO_ID: Record<string, string> = {
  // Further Pure Maths (4PM1 / 9FM0)
  LOGS: '1', QUAD: '2', IDENT: '3', GRAPHS: '4', SERIES: '5',
  BINOM: '6', VECT: '7', COORD: '8', CALC: '9', TRIG: '10',
  // Physics (4PH1)
  FM: '1', ELEC: '2', WAVE: '3', ENRG: '4',
  SLG: '5', MAG: '6', RAD: '7', ASTRO: '8',
}

export function normalizeTopicCodes(codes: string[]): string[] {
  const normalized = new Set<string>()
  for (const code of codes) {
    if (CODE_TO_ID[code]) {
      normalized.add(CODE_TO_ID[code])
    } else if (code.includes('.')) {
      // Chemistry/Bio granular codes ("1.1", "2.4", etc.) — stored as-is in pages.topics
      normalized.add(code)
    } else {
      // Plain numerics ("1", "2") pass through unchanged
      const match = code.match(/^(\d+)/)
      normalized.add(match ? match[1] : code)
    }
  }
  return Array.from(normalized)
}
