export function normalizePaperToken(value: unknown): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
}

export function toPaperSlug(value: unknown): string | null {
  const token = normalizePaperToken(value)
  if (!token) return null
  return `paper-${token}`
}

export function extractPaperTokenFromSlug(slug: string): string | null {
  const match = slug.trim().toLowerCase().match(/^paper-([a-z0-9-]+)$/)
  if (!match) return null
  return match[1] ?? null
}

/**
 * Human-readable label for a raw paper_number value.
 *
 * Examples:
 *   "1"       → "Paper 1"
 *   "1R"      → "Paper 1R"
 *   "Unit_3"  → "Unit 3"
 *   "Unit 3"  → "Unit 3"
 *   "P1"      → "P1"
 *   "FP2"     → "FP2"
 */
export function formatPaperLabel(raw: string): string {
  const value = String(raw ?? "").trim()
  if (!value) return "Paper"
  const unitMatch = value.match(/^Unit[_\s-]?(\d+[A-Z]*)$/i)
  if (unitMatch) return `Unit ${unitMatch[1].toUpperCase()}`
  const paperPrefix = value.match(/^Paper[_\s-]?(.+)$/i)
  if (paperPrefix) return `Paper ${paperPrefix[1].toUpperCase()}`
  if (/^[A-Z]{1,3}\d+[A-Z]*$/i.test(value)) return value.toUpperCase()
  return `Paper ${value.toUpperCase()}`
}

/**
 * Human-readable label for a Cambridge component code.
 *
 * Cambridge encodes papers as `{paper}{variant}` where the second digit is the
 * time-zone variant (not difficulty): "22" = Paper 2, Variant 2; "11" = Paper 1,
 * Variant 1. Older/single-component papers use a single digit with no variant.
 * Making the variant explicit lets students who think in "Paper 2" find "22".
 *
 * Examples:
 *   "22" → "Paper 2 · Variant 2"
 *   "1"  → "Paper 1"
 *   "4"  → "Paper 4"
 */
export function formatCambridgePaperLabel(raw: string): string {
  const value = String(raw ?? "").trim()
  if (/^\d{2}$/.test(value)) return `Paper ${value[0]} · Variant ${value[1]}`
  if (/^\d$/.test(value)) return `Paper ${value}`
  return formatPaperLabel(value)
}

/**
 * Cambridge component reference students search verbatim, e.g. "9702/22".
 * Falls back to just the component when no syllabus code is known.
 */
export function cambridgePaperCode(examCode: string | undefined, component: string): string {
  const c = String(component ?? "").trim()
  return examCode ? `${examCode}/${c}` : c
}