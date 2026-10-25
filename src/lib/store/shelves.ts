/**
 * Shelves for the store page: with dozens of booklets a single grid is hard to
 * browse, so products are grouped by level and can be filtered by level or by
 * kind (yearwise question booklet vs chapterwise workbook).
 *
 * Both facts are derived from data every product already has -- the Pearson
 * code (4xxx = International GCSE, Wxxx = International A Level) and the slug
 * -- so no schema change is needed and a new listing is shelved automatically.
 */

export type Level = "IGCSE" | "IAL" | "Other"
export type Kind = "yearwise" | "workbook"
export type ShelfFilter = "all" | "igcse" | "ial" | "yearwise" | "workbook"

interface Shelvable {
  slug: string
  subject_code: string | null
}

export interface Shelf<T> {
  level: Level
  title: string
  items: T[]
}

export const SHELF_FILTERS: { key: ShelfFilter; label: string }[] = [
  { key: "all", label: "All books" },
  { key: "igcse", label: "IGCSE" },
  { key: "ial", label: "IAL" },
  { key: "yearwise", label: "Yearwise booklets" },
  { key: "workbook", label: "Chapterwise workbooks" },
]

const SHELF_TITLE: Record<Level, string> = {
  IGCSE: "IGCSE",
  IAL: "International A Level (IAL)",
  Other: "More books",
}

export function levelOf(product: Shelvable): Level {
  const code = product.subject_code?.trim().toUpperCase() ?? ""
  if (/^4[A-Z]{2}\d/.test(code)) return "IGCSE"
  if (/^W[A-Z]{2}\d/.test(code)) return "IAL"
  return "Other"
}

export function kindOf(product: Shelvable): Kind {
  return product.slug.includes("yearwise") ? "yearwise" : "workbook"
}

/** Query-string value -> a known filter; anything else shows everything. */
export function parseShelfFilter(value: string | string[] | undefined): ShelfFilter {
  const raw = Array.isArray(value) ? value[0] : value
  return SHELF_FILTERS.some(f => f.key === raw) ? (raw as ShelfFilter) : "all"
}

function matches(product: Shelvable, filter: ShelfFilter): boolean {
  switch (filter) {
    case "igcse": return levelOf(product) === "IGCSE"
    case "ial": return levelOf(product) === "IAL"
    case "yearwise": return kindOf(product) === "yearwise"
    case "workbook": return kindOf(product) === "workbook"
    default: return true
  }
}

/** Products in catalogue order, grouped by level; empty shelves are left out. */
export function shelve<T extends Shelvable>(products: T[], filter: ShelfFilter): Shelf<T>[] {
  const levels: Level[] = ["IGCSE", "IAL", "Other"]
  return levels
    .map(level => ({
      level,
      title: SHELF_TITLE[level],
      items: products.filter(p => levelOf(p) === level && matches(p, filter)),
    }))
    .filter(shelf => shelf.items.length > 0)
}
