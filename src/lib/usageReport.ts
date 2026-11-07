/**
 * The admin Usage report (Admin → Analytics → Feature Usage).
 *
 * Postgres counts everything (admin_usage, migration 44) and this module only
 * reshapes its answer into what the page draws. Until migration 44 is applied
 * the route falls back to paging the newest rows, which covers less than a day
 * of paper opens; `source: "sample"` tells the page to say so.
 */
export const USAGE_FEATURES = [
  "paper_view",
  "lecture_view",
  "lecture_download",
  "worksheet_generate",
  "worksheet_download",
  "test_builder_session",
  "test_builder_download",
] as const

export type UsageFeature = (typeof USAGE_FEATURES)[number]

const WORKSHEET_FEATURES: UsageFeature[] = ["worksheet_generate", "worksheet_download"]
const TEST_BUILDER_FEATURES: UsageFeature[] = ["test_builder_session", "test_builder_download"]

export interface UsageResponse {
  totals: Record<string, number>
  uniqueUsers: Record<string, number>
  worksheetBySubject: Record<string, Record<string, number>>
  testBuilderBySubject: Record<string, Record<string, number>>
  daily: { date: string; [key: string]: number | string }[]
  topPapers: { title: string; total: number; last30: number }[]
  paperViewsBySubject: { subject: string; views: number }[]
  /** "summary": every row counted. "sample": the newest rows only (migration 44 missing). */
  source: "summary" | "sample"
}

interface SubjectRow { feature: UsageFeature; subject: string; count: number }

const isFeature = (v: unknown): v is UsageFeature => USAGE_FEATURES.includes(v as UsageFeature)
const num = (v: unknown): number => (typeof v === "number" && Number.isFinite(v) ? v : Number(v) || 0)
const rows = (v: unknown): Record<string, unknown>[] =>
  Array.isArray(v) ? v.filter((r): r is Record<string, unknown> => typeof r === "object" && r !== null) : []

function perFeature(list: unknown, key: "count" | "users"): Record<string, number> {
  const out: Record<string, number> = Object.fromEntries(USAGE_FEATURES.map(f => [f, 0]))
  for (const r of rows(list)) if (isFeature(r.feature)) out[r.feature] = num(r[key])
  return out
}

/** Subject → counts for the given tool features, busiest subject first. */
export function groupBySubject(list: SubjectRow[], features: UsageFeature[]): Record<string, Record<string, number>> {
  const map = new Map<string, Record<string, number>>()
  for (const r of list) {
    if (!features.includes(r.feature)) continue
    const counts = map.get(r.subject) ?? Object.fromEntries(features.map(f => [f, 0]))
    map.set(r.subject, { ...counts, [r.feature]: (counts[r.feature] ?? 0) + r.count })
  }
  const total = (c: Record<string, number>) => Object.values(c).reduce((s, n) => s + n, 0)
  return Object.fromEntries([...map.entries()].sort(([, a], [, b]) => total(b) - total(a)))
}

export function fromUsageSummary(summary: Record<string, unknown>): UsageResponse {
  const subjects: SubjectRow[] = rows(summary.subjects)
    .filter(r => isFeature(r.feature) && typeof r.subject === "string")
    .map(r => ({ feature: r.feature as UsageFeature, subject: r.subject as string, count: num(r.count) }))

  const byDay = new Map<string, Record<string, number>>()
  for (const r of rows(summary.daily)) {
    if (typeof r.date !== "string" || !isFeature(r.feature)) continue
    const day = byDay.get(r.date) ?? Object.fromEntries(USAGE_FEATURES.map(f => [f, 0]))
    byDay.set(r.date, { ...day, [r.feature]: num(r.count) })
  }

  return {
    totals: perFeature(summary.totals, "count"),
    uniqueUsers: perFeature(summary.users, "users"),
    worksheetBySubject: groupBySubject(subjects, WORKSHEET_FEATURES),
    testBuilderBySubject: groupBySubject(subjects, TEST_BUILDER_FEATURES),
    daily: [...byDay.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([date, counts]) => ({ date, ...counts })),
    topPapers: rows(summary.papers)
      .map(r => ({ title: String(r.title ?? "Unknown"), total: num(r.total), last30: num(r.last30) }))
      .sort((a, b) => b.total - a.total),
    paperViewsBySubject: subjects
      .filter(r => r.feature === "paper_view")
      .map(r => ({ subject: r.subject, views: r.count }))
      .sort((a, b) => b.views - a.views),
    source: "summary",
  }
}
