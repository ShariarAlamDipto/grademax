import { isSingleUnitEdexcelCode, type SEOSubject } from "@/lib/seo-subjects"

/**
 * Canonical URL selection for the /qp landing pages.
 *
 * Each subject answers on several /qp slugs so that the different ways students
 * phrase the same query all resolve ("4ph1", "4ph1-past-papers",
 * "igcse-physics-past-papers"…). Those variants render byte-for-byte identical
 * pages with an identical <title>, so they can never rank differently — they can
 * only compete with each other. Every variant used to self-canonicalise, which
 * left Google to pick a winner per cluster and bucket the rest as duplicates.
 *
 * The variants stay live (they are real inbound URLs), but exactly one is
 * canonical, it is the only one published in sitemap.xml, and it is the one the
 * site links internally.
 */

/** Level segment used by the readable /qp slugs. */
function levelPrefix(subject: SEOSubject): string {
  return subject.level === "igcse" ? "igcse" : "a-level"
}

/**
 * Every /qp slug an Edexcel subject answers on. Keep in sync with the route's
 * slug map — this is the set of URLs that must not 404.
 */
export function edexcelQpSlugs(subject: SEOSubject): string[] {
  const prefix = levelPrefix(subject)
  const code = subject.examCode.toLowerCase()
  return [
    `${prefix}-${subject.slug}`,
    `${prefix}-${subject.slug}-past-papers`,
    `${prefix}-${subject.slug}-question-papers`,
    code,
    `${code}-past-papers`,
  ]
}

/**
 * The single /qp slug that carries an Edexcel subject.
 *
 * Single-unit codes (4PH1, WME01…) win because that is the exact string students
 * search and the one the page <title> already leads with. Multi-unit and IAL
 * subjects — where the code is not the searched term — fall back to the readable
 * level+subject slug. Same predicate as the code-led title rule, so canonical URL
 * and <title> always agree.
 */
export function canonicalEdexcelQpSlug(subject: SEOSubject): string {
  return isSingleUnitEdexcelCode(subject.examCode) && !subject.name.startsWith("IAL ")
    ? subject.examCode.toLowerCase()
    : `${levelPrefix(subject)}-${subject.slug}`
}

/**
 * The single /qp slug that carries a Cambridge subject. Cambridge answers on
 * `{code}` and `{code}-past-papers`; the bare syllabus code is the searched term.
 */
export function canonicalCambridgeQpSlug(examCode: string | null | undefined): string | null {
  const code = (examCode ?? "").toLowerCase()
  return code || null
}
