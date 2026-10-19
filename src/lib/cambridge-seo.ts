import { subjects, boardOf, levelShort, type Subject } from "./subjects"

// ─────────────────────────────────────────────────────────────────────────────
// Cambridge (CAIE) SEO helpers — shared by the /cambridge-* landing pages, the
// /past-papers/cambridge catalog and the /qp/{syllabus-code} pages.
//
// SERP research (2026-07): pages that win Cambridge queries all (1) put the
// subject name IMMEDIATELY before the syllabus code ("Chemistry 0620"), (2)
// carry a CAIE/CIE board token, and (3) phrase A Level as "AS & A Level".
// Keep titles built here aligned with that grammar.
// ─────────────────────────────────────────────────────────────────────────────

/** All content-verified Cambridge subjects (they each carry a syllabus code). */
export const cambridgeSeoSubjects: Subject[] = subjects.filter(
  (s) => boardOf(s.level) === "cambridge" && Boolean(s.examCode)
)

/** "IGCSE" | "A Level" — short label used in H1s and breadcrumbs. */
export function cambridgeLevelShort(s: Subject): string {
  return levelShort(s.level)
}

/**
 * "IGCSE" | "AS & A Level" — how Cambridge itself (and every ranking
 * competitor) phrases the advanced level in titles and copy.
 */
export function cambridgeLevelSeo(s: Subject): string {
  return s.level === "cambridge-igcse" ? "IGCSE" : "AS & A Level"
}

// Subjects students search for most — surfaced first within each section (order
// matters). Matched as a case-insensitive substring so every variant is grouped,
// e.g. "Additional Mathematics" under Maths, "English Literature" under English.
export const POPULAR_ORDER = [
  "Mathematics", "Chemistry", "Biology", "Physics", "English",
  "Economics", "Accounting", "Computer Science",
]

export function popularRank(name: string): number {
  const n = name.toLowerCase()
  const i = POPULAR_ORDER.findIndex((k) => n.includes(k.toLowerCase()))
  return i === -1 ? POPULAR_ORDER.length : i
}

// Popular subjects first (in POPULAR_ORDER), the exact-name match ahead of its
// variants, then alphabetical for everything else.
export function byPopularity(a: Subject, b: Subject): number {
  const ra = popularRank(a.name)
  const rb = popularRank(b.name)
  if (ra !== rb) return ra - rb
  if (ra < POPULAR_ORDER.length) {
    const kw = POPULAR_ORDER[ra].toLowerCase()
    const ea = a.name.toLowerCase() === kw ? 0 : 1
    const eb = b.name.toLowerCase() === kw ? 0 : 1
    if (ea !== eb) return ea - eb
  }
  return a.name.localeCompare(b.name)
}

/**
 * URL slugs under /qp/ that resolve to a Cambridge subject: the bare syllabus
 * code plus a "-past-papers" variant — the two grammars students actually type
 * ("0620", "0620 past papers"). Codes are numeric and unique (verified), so
 * they can never collide with Edexcel's alphanumeric codes (4PH1, WMA11…).
 */
export function cambridgeQpSlugs(s: Subject): string[] {
  const code = (s.examCode ?? "").toLowerCase()
  if (!code) return []
  return [code, `${code}-past-papers`]
}

/** slug (e.g. "0620", "0620-past-papers") → Cambridge subject. */
export function getCambridgeQpMap(): Record<string, Subject> {
  const map: Record<string, Subject> = {}
  for (const s of cambridgeSeoSubjects) {
    for (const slug of cambridgeQpSlugs(s)) map[slug] = s
  }
  return map
}

/**
 * Code-specific FAQs rendered as visible content (and mirrored into ItemList
 * JSON-LD). Written per-subject so every /qp/{code} page has unique copy.
 */
export function cambridgeFaqs(s: Subject): { question: string; answer: string }[] {
  const lvl = cambridgeLevelSeo(s)
  const code = s.examCode ?? ""
  return [
    {
      question: `Where can I download ${code} past papers for free?`,
      answer: `GradeMax hosts free Cambridge ${lvl} ${s.name} (${code}) past papers with mark schemes. Papers are organised by year and exam series — February/March, May/June and October/November — and every question paper and mark scheme downloads as a free PDF.`,
    },
    {
      question: `What subject is syllabus code ${code}?`,
      answer: `${code} is the Cambridge (CAIE) syllabus code for ${lvl} ${s.name}. Students often search by the code alone — for example "${code} past papers" — instead of the subject name.`,
    },
    {
      question: `What do Cambridge paper numbers like ${code}/22 mean?`,
      answer: `Cambridge components combine the paper number and the time-zone variant: in "${code}/22" the first digit is Paper 2 and the second is Variant 2. Variants (1, 2, 3) are set for different exam time zones and have equivalent difficulty — practise whichever variant you can find.`,
    },
    {
      question: `Are ${code} mark schemes included?`,
      answer: `Yes. Every ${s.name} (${code}) paper on GradeMax is paired with its official mark scheme where published, so you can mark your own attempt the way an examiner would.`,
    },
  ]
}
