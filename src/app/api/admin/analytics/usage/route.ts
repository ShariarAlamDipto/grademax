import { NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

export const dynamic = "force-dynamic"

const FEATURES = [
  "paper_view",
  "lecture_view",
  "lecture_download",
  "worksheet_generate",
  "worksheet_download",
  "test_builder_session",
  "test_builder_download",
] as const

type Feature = (typeof FEATURES)[number]

// PostgREST caps every select at 1000 rows, silently. Page through results —
// aggregate functions are disabled on this instance, so aggregation happens
// here. MAX_ROWS bounds the work; queries order newest-first so a capped
// result keeps the most recent events.
const PAGE_SIZE = 1000
const MAX_ROWS = 20000

interface PageResult<T> {
  data: T[] | null
}

async function fetchPaged<T>(fetchPage: (from: number, to: number) => PromiseLike<PageResult<T>>): Promise<T[]> {
  const rows: T[] = []
  for (let from = 0; from < MAX_ROWS; from += PAGE_SIZE) {
    const { data } = await fetchPage(from, from + PAGE_SIZE - 1)
    const page = data ?? []
    rows.push(...page)
    if (page.length < PAGE_SIZE) break
  }
  return rows
}

export async function GET() {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin() || auth.db

  // Total counts per feature (head requests — exact and cheap)
  const featureCounts = await Promise.all(
    FEATURES.map(f =>
      db.from("usage_events")
        .select("id", { count: "exact", head: true })
        .eq("feature", f)
        .then(r => ({ feature: f, count: r.count ?? 0 }))
    )
  )

  // Unique user counts per feature
  const uniqueUserCounts = await Promise.all(
    FEATURES.map(async f => {
      const rows = await fetchPaged<{ user_id: string }>((from, to) =>
        db.from("usage_events")
          .select("user_id")
          .eq("feature", f)
          .not("user_id", "is", null)
          .order("created_at", { ascending: false })
          .range(from, to)
      )
      return { feature: f, unique: new Set(rows.map(r => r.user_id)).size }
    })
  )

  const bySubjectRows = (features: Feature[]) =>
    fetchPaged<{ feature: Feature; subject_name: string | null }>((from, to) =>
      db.from("usage_events")
        .select("feature, subject_name")
        .in("feature", features)
        .not("subject_name", "is", null)
        .order("created_at", { ascending: false })
        .range(from, to)
    )

  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()

  const [worksheetRaw, testBuilderRaw, recentRaw, paperViewRaw] = await Promise.all([
    bySubjectRows(["worksheet_generate", "worksheet_download"]),
    bySubjectRows(["test_builder_session", "test_builder_download"]),
    fetchPaged<{ feature: Feature; created_at: string }>((from, to) =>
      db.from("usage_events")
        .select("feature, created_at")
        .gte("created_at", thirtyDaysAgo)
        .order("created_at", { ascending: false })
        .range(from, to)
    ),
    fetchPaged<{ created_at: string; subject_name: string | null; metadata: { title?: string } | null }>((from, to) =>
      db.from("usage_events")
        .select("created_at, subject_name, metadata")
        .eq("feature", "paper_view")
        .order("created_at", { ascending: false })
        .range(from, to)
    ),
  ])

  return NextResponse.json({
    totals: Object.fromEntries(featureCounts.map(r => [r.feature, r.count])),
    uniqueUsers: Object.fromEntries(uniqueUserCounts.map(r => [r.feature, r.unique])),
    worksheetBySubject: aggregateBySubject(worksheetRaw, ["worksheet_generate", "worksheet_download"]),
    testBuilderBySubject: aggregateBySubject(testBuilderRaw, ["test_builder_session", "test_builder_download"]),
    daily: buildDaily(recentRaw),
    topPapers: buildTopPapers(paperViewRaw, thirtyDaysAgo),
    paperViewsBySubject: buildPaperViewsBySubject(paperViewRaw),
  })
}

function aggregateBySubject(
  rows: { feature: Feature; subject_name: string | null }[],
  features: Feature[]
): Record<string, Record<string, number>> {
  const map: Record<string, Record<string, number>> = {}
  for (const row of rows) {
    const name = row.subject_name ?? "Unknown"
    if (!map[name]) {
      map[name] = Object.fromEntries(features.map(f => [f, 0]))
    }
    if (features.includes(row.feature)) {
      map[name][row.feature] = (map[name][row.feature] ?? 0) + 1
    }
  }
  // Sort by total descending
  return Object.fromEntries(
    Object.entries(map).sort(
      ([, a], [, b]) =>
        Object.values(b).reduce((s, n) => s + n, 0) -
        Object.values(a).reduce((s, n) => s + n, 0)
    )
  )
}

function buildDaily(
  rows: { feature: Feature; created_at: string }[]
): { date: string; [key: string]: number | string }[] {
  const map: Record<string, Record<string, number>> = {}
  for (const row of rows) {
    const date = row.created_at.slice(0, 10)
    if (!map[date]) map[date] = Object.fromEntries(FEATURES.map(f => [f, 0]))
    map[date][row.feature] = (map[date][row.feature] ?? 0) + 1
  }
  return Object.entries(map)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, counts]) => ({ date, ...counts }))
}

function buildTopPapers(
  rows: { created_at: string; metadata: { title?: string } | null }[],
  thirtyDaysAgo: string
): { title: string; total: number; last30: number }[] {
  const map: Record<string, { total: number; last30: number }> = {}
  for (const row of rows) {
    const title = row.metadata?.title || "Unknown"
    if (!map[title]) map[title] = { total: 0, last30: 0 }
    map[title].total += 1
    if (row.created_at >= thirtyDaysAgo) map[title].last30 += 1
  }
  return Object.entries(map)
    .map(([title, counts]) => ({ title, ...counts }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 30)
}

function buildPaperViewsBySubject(
  rows: { subject_name: string | null }[]
): { subject: string; views: number }[] {
  const map: Record<string, number> = {}
  for (const row of rows) {
    const name = row.subject_name ?? "Unknown"
    map[name] = (map[name] ?? 0) + 1
  }
  return Object.entries(map)
    .map(([subject, views]) => ({ subject, views }))
    .sort((a, b) => b.views - a.views)
}
