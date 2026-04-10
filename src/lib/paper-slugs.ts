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