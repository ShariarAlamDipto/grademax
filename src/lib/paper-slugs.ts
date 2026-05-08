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