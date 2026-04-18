/**
 * Utilities for parsing and building R2 filenames and keys.
 * Convention: {Subject}_{Year}_{Session}_Paper_{N}_{QP|MS}.pdf
 * Example:    ICT_2025_Oct-Nov_Paper_2_QP.pdf
 * R2 key:     ICT/2025/Oct-Nov/ICT_2025_Oct-Nov_Paper_2_QP.pdf
 */

export type PaperType = "QP" | "MS"

export interface ParsedFilename {
  subject: string    // e.g. "ICT"
  year: number       // e.g. 2025
  session: string    // R2 format e.g. "Oct-Nov"
  paperNumber: string // e.g. "1", "2", "1R"
  type: PaperType
}

/** Normalize season to the R2 folder format (title-case) */
export function normalizeSessionForR2(s: string): string {
  const lower = s.toLowerCase().replace(/\s/g, "-")
  if (lower === "jan" || lower === "january") return "Jan"
  if (lower === "may-jun" || lower === "may" || lower === "june" || lower === "summer") return "May-Jun"
  if (lower === "oct-nov" || lower === "oct" || lower === "november" || lower === "winter") return "Oct-Nov"
  if (lower === "specimen" || lower === "spec") return "Specimen"
  // Return as-is with first-letter caps per segment
  return s.split("-").map(p => p.charAt(0).toUpperCase() + p.slice(1).toLowerCase()).join("-")
}

/** Normalize season to the DB format (lowercase) */
export function normalizeSessionForDB(s: string): string {
  const r2 = normalizeSessionForR2(s)
  return r2.toLowerCase()
}

/** Parse a filename like "ICT_2025_Oct-Nov_Paper_2_QP.pdf" */
export function parseR2Filename(filename: string): ParsedFilename | null {
  // Remove .pdf extension
  const base = filename.replace(/\.pdf$/i, "")
  // Pattern: {Subject}_{Year}_{Session}_Paper_{N}_{Type}
  // Session can contain hyphens (Oct-Nov, May-Jun)
  const m = base.match(/^(.+?)_(\d{4})_(Jan|May-Jun|Oct-Nov|Specimen)_Paper_(\w+)_(QP|MS)$/i)
  if (!m) return null
  return {
    subject: m[1],
    year: parseInt(m[2]),
    session: normalizeSessionForR2(m[3]),
    paperNumber: m[4].toUpperCase(),
    type: m[5].toUpperCase() as PaperType,
  }
}

/** Build R2 key from components */
export function buildR2Key(subject: string, year: number, session: string, paperNumber: string, type: PaperType): string {
  const r2Session = normalizeSessionForR2(session)
  const filename = `${subject}_${year}_${r2Session}_Paper_${paperNumber}_${type}.pdf`
  return `${subject}/${year}/${r2Session}/${filename}`
}

/** Build the public URL for an R2 key */
export function buildR2PublicUrl(r2Key: string): string {
  const base = process.env.NEXT_PUBLIC_R2_PUBLIC_URL
  if (!base) throw new Error("Missing required env var: NEXT_PUBLIC_R2_PUBLIC_URL")
  return `${base}/${r2Key}`
}

/** Parse an R2 key like "ICT/2025/Oct-Nov/ICT_2025_Oct-Nov_Paper_2_QP.pdf" */
export function parseR2Key(key: string): ParsedFilename | null {
  const parts = key.split("/")
  if (parts.length < 4) return null
  const filename = parts[parts.length - 1]
  return parseR2Filename(filename)
}
