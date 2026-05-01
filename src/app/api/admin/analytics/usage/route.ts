import { NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

export const dynamic = "force-dynamic"

const FEATURES = [
  "lecture_view",
  "lecture_download",
  "worksheet_generate",
  "worksheet_download",
  "test_builder_session",
  "test_builder_download",
] as const

type Feature = (typeof FEATURES)[number]

interface SubjectRow {
  subject_name: string | null
  subject_id: string | null
  feature: Feature
  count: number
}

export async function GET() {
  const auth = await requireAdmin()
  if ("error" in auth) return auth.error

  const db = getSupabaseAdmin() || auth.db

  // Total counts per feature (parallel)
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
      const { data } = await db
        .from("usage_events")
        .select("user_id")
        .eq("feature", f)
        .not("user_id", "is", null)
      const unique = new Set((data ?? []).map(r => r.user_id)).size
      return { feature: f, unique }
    })
  )

  // Worksheet events by subject (generate + download)
  const { data: worksheetRaw } = await db
    .from("usage_events")
    .select("feature, subject_name, subject_id")
    .in("feature", ["worksheet_generate", "worksheet_download"])
    .not("subject_name", "is", null)

  // Test builder events by subject (session + download)
  const { data: testBuilderRaw } = await db
    .from("usage_events")
    .select("feature, subject_name, subject_id")
    .in("feature", ["test_builder_session", "test_builder_download"])
    .not("subject_name", "is", null)

  // Last 30 days — daily breakdown
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()
  const { data: recentRaw } = await db
    .from("usage_events")
    .select("feature, created_at")
    .gte("created_at", thirtyDaysAgo)

  // Aggregate totals
  const totals = Object.fromEntries(featureCounts.map(r => [r.feature, r.count]))
  const uniqueUsers = Object.fromEntries(uniqueUserCounts.map(r => [r.feature, r.unique]))

  // Aggregate worksheet by subject
  const worksheetBySubject = aggregateBySubject(
    (worksheetRaw ?? []) as SubjectRow[],
    ["worksheet_generate", "worksheet_download"]
  )

  // Aggregate test builder by subject
  const testBuilderBySubject = aggregateBySubject(
    (testBuilderRaw ?? []) as SubjectRow[],
    ["test_builder_session", "test_builder_download"]
  )

  // Daily breakdown
  const daily = buildDaily((recentRaw ?? []) as { feature: Feature; created_at: string }[])

  return NextResponse.json({
    totals,
    uniqueUsers,
    worksheetBySubject,
    testBuilderBySubject,
    daily,
  })
}

function aggregateBySubject(
  rows: { feature: Feature; subject_name: string | null; subject_id: string | null }[],
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
